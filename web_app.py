"""
Task Manager Web App
A Flask-based web application for managing tasks with Firebase integration
"""

from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
from datetime import datetime, timedelta
import firebase_admin
from firebase_admin import credentials, firestore
import os
from dotenv import load_dotenv
import threading
import time

# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'your-secret-key-here')

# Firebase Setup
cred = credentials.Certificate("serviceAccountKey.json")
firebase_admin.initialize_app(cred)
db = firestore.client()

# Global variable to track if reminder loop is running
reminder_thread_running = False

# --- Helper Functions ---
def decode_recurrence_days(bitmask):
    """Decode recurrence days bitmask to readable format"""
    day_map = {1: "Mon", 2: "Tue", 4: "Wed", 8: "Thu", 16: "Fri", 32: "Sat", 64: "Sun"}
    weekdays = [name for bit, name in day_map.items() if bitmask and (bitmask & bit)]
    return ", ".join(weekdays)

def calculate_next_occurrence(current_due, recurrence_days):
    """Calculate the next occurrence date based on the recurrence bitmask"""
    day_map = {1: 0, 2: 1, 4: 2, 8: 3, 16: 4, 32: 5, 64: 6}  # Monday=0, Sunday=6
    selected_days = [day_map[bit] for bit in day_map.keys() if recurrence_days & bit]
    
    if not selected_days:
        return None
    
    # Start from the day after current due date
    next_date = current_due + timedelta(days=1)
    
    # Look for the next occurrence within the next 7 days
    for i in range(7):
        check_date = next_date + timedelta(days=i)
        if check_date.weekday() in selected_days:
            return check_date.replace(hour=current_due.hour, minute=current_due.minute, second=current_due.second)
    
    # If no occurrence found in the next 7 days, return the next week
    return next_date + timedelta(days=7)

def create_future_recurring_instances(name, course, start_dt, due_dt, recurrence_days, reminder_hours, parent_task_id):
    """Create future instances of a recurring task (up to 12 weeks ahead)"""
    current_due = due_dt
    duration = due_dt - start_dt
    
    # Create instances for the next 12 weeks
    for week in range(1, 13):  # 12 weeks ahead
        next_occurrence = calculate_next_occurrence(current_due, recurrence_days)
        if next_occurrence:
            new_start = next_occurrence - duration
            new_due = next_occurrence
            
            # Check if instance already exists
            existing_tasks = db.collection("tasks").where("name", "==", name).where("due", "==", new_due.strftime("%Y-%m-%d %H:%M:%S")).stream()
            if not list(existing_tasks):
                try:
                    db.collection("tasks").add({
                        "name": name,
                        "course": course,
                        "start": new_start.strftime("%Y-%m-%d %H:%M:%S"),
                        "due": new_due.strftime("%Y-%m-%d %H:%M:%S"),
                        "status": "Not Started",
                        "recurrence_days": recurrence_days,
                        "reminder_hours": reminder_hours,
                        "reminder_sent": 0,
                        "parent_task_id": parent_task_id,
                        "is_recurring_instance": True
                    })
                except Exception as e:
                    print(f"Failed to create future recurring instance: {e}")
            
            # Update current_due for next iteration
            current_due = new_due
        else:
            break

# --- Routes ---
@app.route('/')
def index():
    """Main page showing all tasks"""
    tasks = []
    try:
        docs = db.collection("tasks").stream()
        for doc in docs:
            task = doc.to_dict()
            task['id'] = doc.id
            # Format dates for display
            task['start_formatted'] = datetime.strptime(task.get("start"), "%Y-%m-%d %H:%M:%S").strftime("%m/%d/%y %I:%M %p")
            task['due_formatted'] = datetime.strptime(task.get("due"), "%Y-%m-%d %H:%M:%S").strftime("%m/%d/%y %I:%M %p")
            tasks.append(task)
    except Exception as e:
        flash(f"Error loading tasks: {e}", "error")
    
    return render_template('index.html', tasks=tasks)

@app.route('/add_task', methods=['GET', 'POST'])
def add_task():
    """Add a new task"""
    if request.method == 'POST':
        try:
            # Get form data
            name = request.form.get('name')
            course = request.form.get('course')
            start_date = request.form.get('start_date')
            start_time = request.form.get('start_time')
            due_date = request.form.get('due_date')
            due_time = request.form.get('due_time')
            status = request.form.get('status')
            reminder_hours = int(request.form.get('reminder_hours', 24))
            
            # Parse dates
            start_dt = datetime.strptime(f"{start_date} {start_time}", "%Y-%m-%d %H:%M")
            due_dt = datetime.strptime(f"{due_date} {due_time}", "%Y-%m-%d %H:%M")
            
            # Handle recurrence days
            recurrence_days = 0
            for day in ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']:
                if request.form.get(f'recurrence_{day.lower()}'):
                    day_map = {'mon': 1, 'tue': 2, 'wed': 4, 'thu': 8, 'fri': 16, 'sat': 32, 'sun': 64}
                    recurrence_days |= day_map[day.lower()]
            
            # Create task
            task_ref = db.collection("tasks").add({
                "name": name,
                "course": course,
                "start": start_dt.strftime("%Y-%m-%d %H:%M:%S"),
                "due": due_dt.strftime("%Y-%m-%d %H:%M:%S"),
                "status": status,
                "recurrence_days": recurrence_days,
                "reminder_hours": reminder_hours,
                "reminder_sent": 0,
                "is_recurring_instance": False
            })
            
            # If recurring task, create future instances
            if recurrence_days > 0:
                create_future_recurring_instances(name, course, start_dt, due_dt, recurrence_days, reminder_hours, task_ref[1].id)
            
            flash('Task added successfully!', 'success')
            return redirect(url_for('index'))
            
        except Exception as e:
            flash(f'Error adding task: {e}', 'error')
    
    return render_template('add_task.html')

@app.route('/edit_task/<task_id>', methods=['GET', 'POST'])
def edit_task(task_id):
    """Edit an existing task"""
    if request.method == 'POST':
        try:
            # Get form data
            name = request.form.get('name')
            course = request.form.get('course')
            start_date = request.form.get('start_date')
            start_time = request.form.get('start_time')
            due_date = request.form.get('due_date')
            due_time = request.form.get('due_time')
            status = request.form.get('status')
            reminder_hours = int(request.form.get('reminder_hours', 24))
            
            # Parse dates
            start_dt = datetime.strptime(f"{start_date} {start_time}", "%Y-%m-%d %H:%M")
            due_dt = datetime.strptime(f"{due_date} {due_time}", "%Y-%m-%d %H:%M")
            
            # Update task
            db.collection("tasks").document(task_id).update({
                "name": name,
                "course": course,
                "start": start_dt.strftime("%Y-%m-%d %H:%M:%S"),
                "due": due_dt.strftime("%Y-%m-%d %H:%M:%S"),
                "status": status,
                "reminder_hours": reminder_hours,
                "reminder_sent": 0
            })
            
            flash('Task updated successfully!', 'success')
            return redirect(url_for('index'))
            
        except Exception as e:
            flash(f'Error updating task: {e}', 'error')
    
    # Get task data for editing
    try:
        doc = db.collection("tasks").document(task_id).get()
        if doc.exists:
            task = doc.to_dict()
            task['id'] = doc.id
            # Parse dates for form
            start_dt = datetime.strptime(task.get("start"), "%Y-%m-%d %H:%M:%S")
            due_dt = datetime.strptime(task.get("due"), "%Y-%m-%d %H:%M:%S")
            task['start_date'] = start_dt.strftime("%Y-%m-%d")
            task['start_time'] = start_dt.strftime("%H:%M")
            task['due_date'] = due_dt.strftime("%Y-%m-%d")
            task['due_time'] = due_dt.strftime("%H:%M")
            return render_template('edit_task.html', task=task)
        else:
            flash('Task not found!', 'error')
            return redirect(url_for('index'))
    except Exception as e:
        flash(f'Error loading task: {e}', 'error')
        return redirect(url_for('index'))

@app.route('/delete_task/<task_id>')
def delete_task(task_id):
    """Delete a task"""
    try:
        db.collection("tasks").document(task_id).delete()
        flash('Task deleted successfully!', 'success')
    except Exception as e:
        flash(f'Error deleting task: {e}', 'error')
    return redirect(url_for('index'))

@app.route('/update_status/<task_id>/<status>')
def update_status(task_id, status):
    """Update task status"""
    try:
        db.collection("tasks").document(task_id).update({"status": status})
        flash('Status updated successfully!', 'success')
    except Exception as e:
        flash(f'Error updating status: {e}', 'error')
    return redirect(url_for('index'))

@app.route('/view_by_class/<class_name>')
def view_by_class(class_name):
    """View tasks filtered by class"""
    tasks = []
    try:
        docs = db.collection("tasks").where("course", "==", class_name).stream()
        for doc in docs:
            task = doc.to_dict()
            task['id'] = doc.id
            task['start_formatted'] = datetime.strptime(task.get("start"), "%Y-%m-%d %H:%M:%S").strftime("%m/%d/%y %I:%M %p")
            task['due_formatted'] = datetime.strptime(task.get("due"), "%Y-%m-%d %H:%M:%S").strftime("%m/%d/%y %I:%M %p")
            tasks.append(task)
    except Exception as e:
        flash(f"Error loading tasks: {e}", "error")
    
    return render_template('view_by_class.html', tasks=tasks, class_name=class_name)

@app.route('/delete_all_tasks')
def delete_all_tasks():
    """Delete all tasks with confirmation"""
    try:
        tasks = db.collection("tasks").stream()
        deleted_count = 0
        for doc in tasks:
            db.collection("tasks").document(doc.id).delete()
            deleted_count += 1
        flash(f'Successfully deleted {deleted_count} tasks!', 'success')
    except Exception as e:
        flash(f'Error deleting all tasks: {e}', 'error')
    return redirect(url_for('index'))

# --- Email reminder functionality (simplified for web) ---
def reminder_loop():
    """Background reminder loop (simplified version)"""
    global reminder_thread_running
    reminder_thread_running = True
    
    while reminder_thread_running:
        try:
            now = datetime.now()
            tasks = db.collection("tasks").stream()
            
            for doc in tasks:
                task = doc.to_dict()
                task_id = doc.id
                due = datetime.strptime(task["due"], "%Y-%m-%d %H:%M:%S")
                reminder_hours = task.get("reminder_hours", 24)
                reminder_sent = task.get("reminder_sent", 0)
                status = task.get("status", "Not Started")
                
                # Simple reminder logic (no email for web version)
                if due - timedelta(hours=reminder_hours) <= now < due and status != "Completed" and reminder_sent == 0:
                    print(f"Reminder: {task['name']} is due soon!")
                    db.collection("tasks").document(task_id).update({"reminder_sent": 1})
            
            time.sleep(60)  # Check every minute
        except Exception as e:
            print(f"Error in reminder loop: {e}")
            time.sleep(60)

# Start reminder loop in background
if not reminder_thread_running:
    threading.Thread(target=reminder_loop, daemon=True).start()

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
