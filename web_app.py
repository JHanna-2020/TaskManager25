"""
Task Manager Web App
A Flask-based web application for managing tasks (MongoDB-backed)
"""

from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
from datetime import datetime, timedelta
from pymongo import MongoClient
from bson.objectid import ObjectId
import os
from dotenv import load_dotenv
import urllib.parse

# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'your-secret-key-here')

def get_db():
    """Initialize MongoDB connection with proper error handling"""
    db_user = os.getenv("DB_USER")
    db_password = os.getenv("DB_PASSWORD")  # Fixed: was "dbPassword"
    db_name = os.getenv("DB_NAME", "TaskManager")
    print(db_user, db_password, db_name)
    
    if not db_user or not db_password:
        raise Exception("DB_USER and DB_PASSWORD must be set in .env")

    # URL encode credentials to handle special characters
    encoded_user = urllib.parse.quote_plus(db_user)
    encoded_password = urllib.parse.quote_plus(db_password)
    
    # Fixed URI with proper encoding
    mongo_uri = f"mongodb+srv://{db_user}:{db_password}@taskmanger.3gfydvt.mongodb.net/?retryWrites=true&w=majority&appName=taskmanger"

    try:
        client = MongoClient(mongo_uri, tls=True, tlsAllowInvalidCertificates=False)
        client.admin.command("ping")  # Test connection
        print("[DEBUG] MongoDB connection successful.")
        return client[db_name]
    except Exception as e:
        print(f"[ERROR] MongoDB connection failed: {e}")
        raise Exception(f"Failed to connect to MongoDB: {e}")

# Initialize database connection
try:
    db = get_db()
    tasks_col = db["tasks"]
    print("[DEBUG] Database initialized successfully")
except Exception as e:
    print(f"[ERROR] Failed to initialize database: {e}")
    db = None
    tasks_col = None

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

def create_future_recurring_instances(name, course, start_dt, due_dt, recurrence_days, parent_task_id):
    """Create future instances of a recurring task (up to 12 weeks ahead)"""
    if tasks_col is None:
        flash("Database connection error", "error")
        return redirect(url_for('index'))
    current_due = due_dt
    duration = due_dt - start_dt
    
    # Create instances for the next 12 weeks
    for week in range(1, 13):  # 12 weeks ahead
        next_occurrence = calculate_next_occurrence(current_due, recurrence_days)
        if next_occurrence:
            new_start = next_occurrence - duration
            new_due = next_occurrence
            
            # Check if instance already exists
            exists = tasks_col.find_one({
                "name": name,
                "due": new_due.strftime("%Y-%m-%d %H:%M:%S"),
            })
            if not exists:
                try:
                    tasks_col.insert_one({
                        "name": name,
                        "course": course,
                        "start": new_start.strftime("%Y-%m-%d %H:%M:%S"),
                        "due": new_due.strftime("%Y-%m-%d %H:%M:%S"),
                        "status": "Not Started",
                        "recurrence_days": recurrence_days,
                        "parent_task_id": str(parent_task_id) if parent_task_id else None,
                        "is_recurring_instance": True
                    })
                except Exception as e:
                    print(f"Failed to create future recurring instance: {e}")
            
            # Update current_due for next iteration
            current_due = new_due
        else:
            break

def create_due_weekday_instance(name, course, start_dt, due_dt, parent_task_id):
    """Create next week's instance for due weekday recurrence"""
    if tasks_col is None:
        flash("Database connection error", "error")
        return redirect(url_for('index'))
        
    duration = due_dt - start_dt
    # Add 7 days to get next week's same weekday
    next_due = due_dt + timedelta(days=7)
    next_start = next_due - duration
    
    # Check if instance already exists
    exists = tasks_col.find_one({
        "name": name,
        "due": next_due.strftime("%Y-%m-%d %H:%M:%S"),
    })
    if not exists:
        try:
            tasks_col.insert_one({
                "name": name,
                "course": course,
                "start": next_start.strftime("%Y-%m-%d %H:%M:%S"),
                "due": next_due.strftime("%Y-%m-%d %H:%M:%S"),
                "status": "Not Started",
                "recurrence_days": -1,  # Special flag for due weekday recurrence
                "parent_task_id": str(parent_task_id) if parent_task_id else None,
                "is_recurring_instance": True
            })
        except Exception as e:
            print(f"Failed to create due weekday instance: {e}")

# --- Routes ---
@app.route('/')
def index():
    """Main page showing all tasks"""
    if tasks_col is None:
        flash("Database connection error", "error")
        return render_template('index.html', tasks=[], total_count=0, active_count=0, completed_count=0)
        
    tasks = []
    active_tasks = []
    completed_tasks = []
    
    try:
        # Get all tasks and sort them: active tasks first (by due date), then completed/graded (by due date)
        all_tasks = list(tasks_col.find({}))
        
        for doc in all_tasks:
            task = dict(doc)
            task['id'] = str(doc.get('_id'))
            
            # Safely format dates for display
            try:
                start_dt = datetime.strptime(task.get("start", ""), "%Y-%m-%d %H:%M:%S")
                due_dt = datetime.strptime(task.get("due", ""), "%Y-%m-%d %H:%M:%S")
                task['start_formatted'] = start_dt.strftime("%m/%d/%y %I:%M %p")
                task['due_formatted'] = due_dt.strftime("%m/%d/%y %I:%M %p")
            except (ValueError, TypeError):
                task['start_formatted'] = "Invalid Date"
                task['due_formatted'] = "Invalid Date"
            
            if task.get("status") in ["Completed", "Graded"]:
                completed_tasks.append(task)
            else:
                active_tasks.append(task)
        
        # Sort each group by due date
        active_tasks.sort(key=lambda x: x.get("due", ""))
        completed_tasks.sort(key=lambda x: x.get("due", ""))
        
        # Combine: active tasks first, then completed tasks
        tasks = active_tasks + completed_tasks
        
    except Exception as e:
        flash(f"Error loading tasks: {e}", "error")
        print(f"[ERROR] Exception in index(): {e}")
    
    return render_template('index.html', tasks=tasks, total_count=len(tasks), active_count=len(active_tasks), completed_count=len(completed_tasks))

@app.route('/add_task', methods=['GET', 'POST'])
def add_task():
    """Add a new task"""
    if tasks_col is None:
        flash("Database connection error", "error")
        return render_template('add_task.html')
        
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
            
            # Validate required fields
            if not all([name, course, start_date, start_time, due_date, due_time]):
                flash('All fields are required!', 'error')
                return render_template('add_task.html')
            
            # Parse dates
            start_dt = datetime.strptime(f"{start_date} {start_time}", "%Y-%m-%d %H:%M")
            due_dt = datetime.strptime(f"{due_date} {due_time}", "%Y-%m-%d %H:%M")
            
            # Handle recurrence options
            recurrence_type = request.form.get('recurrence_type', 'none')
            recurrence_days = 0
            
            if recurrence_type == 'weekly':
                # Use the current bitmask system for specific days
                day_map = {'mon': 1, 'tue': 2, 'wed': 4, 'thu': 8, 'fri': 16, 'sat': 32, 'sun': 64}
                for day in day_map.keys():
                    if request.form.get(f'recurrence_{day}'):
                        recurrence_days |= day_map[day]
            elif recurrence_type == 'due_weekday':
                # Set a special flag for due weekday recurrence
                recurrence_days = -1  # Special value to indicate due weekday recurrence
            
            # Create task
            insert_result = tasks_col.insert_one({
                "name": name,
                "course": course,
                "start": start_dt.strftime("%Y-%m-%d %H:%M:%S"),
                "due": due_dt.strftime("%Y-%m-%d %H:%M:%S"),
                "status": status,
                "recurrence_days": recurrence_days,
                "is_recurring_instance": False
            })
            
            # If recurring task, create future instances
            if recurrence_days > 0:
                create_future_recurring_instances(name, course, start_dt, due_dt, recurrence_days, insert_result.inserted_id)
            elif recurrence_days == -1:
                # For due weekday recurrence, create next week's instance
                create_due_weekday_instance(name, course, start_dt, due_dt, insert_result.inserted_id)
            
            flash('Task added successfully!', 'success')
            return redirect(url_for('index'))
            
        except ValueError as e:
            flash(f'Invalid date/time format: {e}', 'error')
        except Exception as e:
            flash(f'Error adding task: {e}', 'error')
    
    return render_template('add_task.html')

@app.route('/edit_task/<task_id>', methods=['GET', 'POST'])
def edit_task(task_id):
    """Edit an existing task"""
    if tasks_col is None:
        flash("Database connection error", "error")
        return redirect(url_for('index'))
        
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
            
            # Validate required fields
            if not all([name, course, start_date, start_time, due_date, due_time]):
                flash('All fields are required!', 'error')
                return redirect(url_for('edit_task', task_id=task_id))
            
            # Parse dates
            start_dt = datetime.strptime(f"{start_date} {start_time}", "%Y-%m-%d %H:%M")
            due_dt = datetime.strptime(f"{due_date} {due_time}", "%Y-%m-%d %H:%M")
            
            # Update task
            result = tasks_col.update_one(
                {"_id": ObjectId(task_id)},
                {"$set": {
                    "name": name,
                    "course": course,
                    "start": start_dt.strftime("%Y-%m-%d %H:%M:%S"),
                    "due": due_dt.strftime("%Y-%m-%d %H:%M:%S"),
                    "status": status
                }}
            )
            
            if result.modified_count > 0:
                flash('Task updated successfully!', 'success')
            else:
                flash('No changes made to task.', 'info')
            return redirect(url_for('index'))
            
        except ValueError as e:
            flash(f'Invalid date/time format: {e}', 'error')
        except Exception as e:
            flash(f'Error updating task: {e}', 'error')
    
    # Get task data for editing
    try:
        doc = tasks_col.find_one({"_id": ObjectId(task_id)})
        if doc:
            task = dict(doc)
            task['id'] = str(doc.get('_id'))
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
    if tasks_col is None:
        flash("Database connection error", "error")
        return redirect(url_for('index'))
        
    try:
        result = tasks_col.delete_one({"_id": ObjectId(task_id)})
        if result.deleted_count > 0:
            flash('Task deleted successfully!', 'success')
        else:
            flash('Task not found!', 'error')
    except Exception as e:
        flash(f'Error deleting task: {e}', 'error')
    return redirect(url_for('index'))

@app.route('/update_status/<task_id>/<status>')
def update_status(task_id, status):
    """Update task status"""
    if tasks_col is None:
        flash("Database connection error", "error")
        return redirect(url_for('index'))
        
    try:
        result = tasks_col.update_one({"_id": ObjectId(task_id)}, {"$set": {"status": status}})
        if result.modified_count > 0:
            flash('Status updated successfully!', 'success')
        else:
            flash('Task not found!', 'error')
    except Exception as e:
        flash(f'Error updating status: {e}', 'error')
    return redirect(url_for('index'))

@app.route('/view_by_class/<class_name>')
def view_by_class(class_name):
    """View tasks filtered by class"""
    if tasks_col is None:
        flash("Database connection error", "error")
        return render_template('view_by_class.html', tasks=[], class_name=class_name, class_count=0)
        
    tasks = []
    try:
        cursor = tasks_col.find({"course": class_name}).sort("due", 1)
        for doc in cursor:
            task = dict(doc)
            task['id'] = str(doc.get('_id'))
            try:
                start_dt = datetime.strptime(task.get("start", ""), "%Y-%m-%d %H:%M:%S")
                due_dt = datetime.strptime(task.get("due", ""), "%Y-%m-%d %H:%M:%S")
                task['start_formatted'] = start_dt.strftime("%m/%d/%y %I:%M %p")
                task['due_formatted'] = due_dt.strftime("%m/%d/%y %I:%M %p")
            except (ValueError, TypeError):
                task['start_formatted'] = "Invalid Date"
                task['due_formatted'] = "Invalid Date"
            tasks.append(task)
    except Exception as e:
        flash(f"Error loading tasks: {e}", "error")
    
    return render_template('view_by_class.html', tasks=tasks, class_name=class_name, class_count=len(tasks))

@app.route('/view_completed')
def view_completed():
    """View completed and graded tasks"""
    if tasks_col is None:
        flash("Database connection error", "error")
        return render_template('view_completed.html', tasks=[], completed_count=0)
        
    tasks = []
    try:
        cursor = tasks_col.find({"status": {"$in": ["Completed", "Graded"]}}).sort("due", 1)
        for doc in cursor:
            task = dict(doc)
            task['id'] = str(doc.get('_id'))
            # Format dates for display
            try:
                start_dt = datetime.strptime(task.get("start", ""), "%Y-%m-%d %H:%M:%S")
                due_dt = datetime.strptime(task.get("due", ""), "%Y-%m-%d %H:%M:%S")
                task['start_formatted'] = start_dt.strftime("%m/%d/%y %I:%M %p")
                task['due_formatted'] = due_dt.strftime("%m/%d/%y %I:%M %p")
            except (ValueError, TypeError):
                task['start_formatted'] = "Invalid Date"
                task['due_formatted'] = "Invalid Date"
            tasks.append(task)
    except Exception as e:
        flash(f"Error loading completed tasks: {e}", "error")
    
    return render_template('view_completed.html', tasks=tasks, completed_count=len(tasks))

@app.route('/view_active')
def view_active():
    """View not started and in progress tasks"""
    if tasks_col is None:
        flash("Database connection error", "error")
        return render_template('view_active.html', tasks=[], active_count=0)
        
    tasks = []
    try:
        cursor = tasks_col.find({"status": {"$in": ["Not Started", "In Progress"]}}).sort("due", 1)
        for doc in cursor:
            task = dict(doc)
            task['id'] = str(doc.get('_id'))
            # Format dates for display
            try:
                start_dt = datetime.strptime(task.get("start", ""), "%Y-%m-%d %H:%M:%S")
                due_dt = datetime.strptime(task.get("due", ""), "%Y-%m-%d %H:%M:%S")
                task['start_formatted'] = start_dt.strftime("%m/%d/%y %I:%M %p")
                task['due_formatted'] = due_dt.strftime("%m/%d/%y %I:%M %p")
            except (ValueError, TypeError):
                task['start_formatted'] = "Invalid Date"
                task['due_formatted'] = "Invalid Date"
            tasks.append(task)
    except Exception as e:
        flash(f"Error loading active tasks: {e}", "error")
    
    return render_template('view_active.html', tasks=tasks, active_count=len(tasks))

@app.route('/delete_all_tasks')
def delete_all_tasks():
    """Delete all tasks with confirmation"""
    if tasks_col is None:
        flash("Database connection error", "error")
        return redirect(url_for('index'))
        
    try:
        result = tasks_col.delete_many({})
        deleted_count = result.deleted_count
        flash(f'Successfully deleted {deleted_count} tasks!', 'success')
    except Exception as e:
        flash(f'Error deleting all tasks: {e}', 'error')
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8080)