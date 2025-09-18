import tkinter as tk
from tkinter import messagebox, ttk
from tkcalendar import DateEntry
from datetime import datetime, timedelta
import threading
import time
import os
import sys
from dotenv import load_dotenv
print("✅ TaskManager started successfully!", file=sys.stderr)

load_dotenv()

from pymongo import MongoClient
from bson.objectid import ObjectId

from email_utils import send_email

def get_db():
    db_user = os.getenv("DB_USER")
    db_password = os.getenv("dbPassword")
    if not db_user or not db_password:
        raise Exception("DB_USER and dbPassword must be set in .env")

    mongo_uri = f"mongodb+srv://{db_user}:{db_password}@taskmanger.3gfydvt.mongodb.net/taskmanager?retryWrites=true&w=majority&appName=taskmanger"
    db_name = os.getenv("DB_NAME", "TaskManager")
    client = MongoClient(mongo_uri)
    return client[db_name]

db = get_db()
tasks_col = db["tasks"]
email_locks_col = db["email_locks"]

# --- Decode recurrence days (bitmask) ---
def decode_recurrence_days(bitmask):
    day_map = {1: "Mon", 2: "Tue", 4: "Wed", 8: "Thu", 16: "Fri", 32: "Sat", 64: "Sun"}
    weekdays = [name for bit, name in day_map.items() if bitmask and (bitmask & bit)]
    return ", ".join(weekdays)

# --- Calculate next occurrence based on recurrence pattern ---
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
            # Found the next occurrence, set the time to match the original due time
            return check_date.replace(hour=current_due.hour, minute=current_due.minute, second=current_due.second)
    
    # If no occurrence found in the next 7 days, return the next week
    return next_date + timedelta(days=7)

# --- Create future recurring instances ---
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
                        "reminder_hours": reminder_hours,
                        "reminder_sent": 0,
                        "parent_task_id": str(parent_task_id) if parent_task_id else None,
                        "is_recurring_instance": True
                    })
                except Exception as e:
                    print(f"Failed to create future recurring instance: {e}")
            
            # Update current_due for next iteration
            current_due = new_due
        else:
            break

# --- System Tray (pystray) ---
import pystray
from PIL import Image, ImageDraw

def create_image(width, height, color1, color2):
    image = Image.new('RGB', (width, height), color1)
    dc = ImageDraw.Draw(image)
    dc.rectangle([(width // 3, height // 3), (width * 2 // 3, height * 2 // 3)], fill=color2)
    return image

def on_quit(icon, item):
    icon.stop()
    root.destroy()

def show_window(icon, item):
    root.deiconify()
    root.lift()
    root.attributes('-topmost', True)
    root.after(100, lambda: root.attributes('-topmost', False))

def setup_tray():
    global tray_icon
    image = create_image(64, 64, "black", "white")
    menu = pystray.Menu(
        pystray.MenuItem("Show Task Manager", show_window),
        pystray.MenuItem("Quit", on_quit)
    )
    tray_icon = pystray.Icon("taskmanager", image, "Task Manager", menu)
    threading.Thread(target=tray_icon.run, daemon=True).start()

# --- Main Window ---
root = tk.Tk()
root.title("Task Manager")
root.geometry("900x700")

def on_close():
    root.withdraw()
root.protocol("WM_DELETE_WINDOW", on_close)

# --- Treeview Setup ---
tree = ttk.Treeview(root, columns=("Name", "Class", "Start", "Due", "Status"), show="headings")
tree.heading("Name", text="Assignment Name")
tree.heading("Class", text="Class")
tree.heading("Start", text="Start Date/Time")
tree.heading("Due", text="Due Date/Time")
tree.heading("Status", text="Status")
tree.pack(fill="both", expand=True)

tree.tag_configure("Not Started", background="#ff7171")
tree.tag_configure("In Progress", background="#fffacd")
tree.tag_configure("Completed", background="#d0f0c0")
tree.tag_configure("Graded", background="#add8e6")

# --- Load tasks from Firestore ---
def load_tasks():
    tree.delete(*tree.get_children())
    tasks = tasks_col.find({}).sort("due", 1)
    for doc in tasks:
        task = dict(doc)
        status_tag = task.get("status", "Not Started")
        tree.insert(
            "",
            tk.END,
            iid=str(doc.get("_id")),
            values=(
                task.get("name"),
                task.get("course"),
                datetime.strptime(task.get("start"), "%Y-%m-%d %H:%M:%S").strftime("%m/%d/%y %I:%M %p"),
                datetime.strptime(task.get("due"), "%Y-%m-%d %H:%M:%S").strftime("%m/%d/%y %I:%M %p"),
                status_tag
            ),
            tags=(status_tag,)
        )

load_tasks()

# --- Add Assignment Window ---
def open_new_window():
    new_window = tk.Toplevel(root)
    new_window.title("Add New Assignment")
    new_window.geometry("900x700")

    tk.Label(new_window, text="Add New Assignment", font=("Arial", 16)).grid(column=0, row=0, columnspan=2, pady=10)
    form_frame = tk.Frame(new_window)
    form_frame.grid(column=0, row=1, padx=20, pady=10)

    tk.Label(form_frame, text="Assignment Name:").grid(column=0, row=0, sticky="w", padx=5, pady=5)
    name_entry = tk.Entry(form_frame, width=40)
    name_entry.grid(column=1, row=0, sticky="w", padx=5, pady=5)

    tk.Label(form_frame, text="Class:").grid(column=0, row=1, sticky="w", padx=5, pady=5)
    classes = [
        "Select Class",
        "Database Design",
        "Computer Organization & Assembly Language",
        "Modern Software Design & Development",
        "Web Application Development",
        "CTC"
    ]
    selected_class = tk.StringVar(value=classes[0])
    tk.OptionMenu(form_frame, selected_class, *classes).grid(column=1, row=1, sticky="w", padx=5, pady=5)

    tk.Label(form_frame, text="Start Date:").grid(column=0, row=2, sticky="w", padx=5, pady=5)
    start_date = DateEntry(form_frame, width=40)
    start_date.grid(column=1, row=2, sticky="w", padx=5, pady=5)

    tk.Label(form_frame, text="Start Time (HH:MM AM/PM):").grid(column=0, row=3, sticky="w", padx=5, pady=5)
    start_time_entry = tk.Entry(form_frame, width=40)
    start_time_entry.insert(0, "09:00 AM")
    start_time_entry.grid(column=1, row=3, sticky="w", padx=5, pady=5)

    tk.Label(form_frame, text="Due Date:").grid(column=0, row=4, sticky="w", padx=5, pady=5)
    due_date = DateEntry(form_frame, width=40)
    due_date.grid(column=1, row=4, sticky="w", padx=5, pady=5)

    tk.Label(form_frame, text="Due Time (HH:MM AM/PM):").grid(column=0, row=5, sticky="w", padx=5, pady=5)
    due_time_entry = tk.Entry(form_frame, width=40)
    due_time_entry.insert(0, "05:00 PM")
    due_time_entry.grid(column=1, row=5, sticky="w", padx=5, pady=5)

    tk.Label(form_frame, text="Status:").grid(column=0, row=6, sticky="w", padx=5, pady=5)
    status_options = ["Select Status", "Not Started", "In Progress", "Completed", "Graded"]
    current_status = tk.StringVar(value=status_options[0])
    tk.OptionMenu(form_frame, current_status, *status_options).grid(column=1, row=6, sticky="w", padx=5, pady=5)

    tk.Label(form_frame, text="Reminder Hours Before Due:").grid(column=0, row=7, sticky="w", padx=5, pady=5)
    reminder_hours_entry = tk.Entry(form_frame, width=10)
    reminder_hours_entry.insert(0, "24")
    reminder_hours_entry.grid(column=1, row=7, sticky="w", padx=5, pady=5)

    # --- Recurrence Days Selection ---
    tk.Label(form_frame, text="Recurrence Days (Mon=1, Tue=2, Wed=4, Thu=8, Fri=16, Sat=32, Sun=64):").grid(column=0, row=8, sticky="w", padx=5, pady=5)
    # Create checkboxes for each day
    recurrence_vars = {}
    days = [("Mon", 1), ("Tue", 2), ("Wed", 4), ("Thu", 8), ("Fri", 16), ("Sat", 32), ("Sun", 64)]
    recur_days_frame = tk.Frame(form_frame)
    recur_days_frame.grid(column=1, row=8, sticky="w", padx=5, pady=5)
    for i, (day, bit) in enumerate(days):
        var = tk.IntVar(value=0)
        cb = tk.Checkbutton(recur_days_frame, text=day, variable=var)
        cb.grid(row=0, column=i, sticky="w")
        recurrence_vars[bit] = var

    def save_assignment():
        name = name_entry.get().strip()
        course = selected_class.get()
        status = current_status.get()
        if not name or course == "Select Class" or status == "Select Status":
            messagebox.showerror("Error", "Please fill all required fields.")
            return

        try:
            start_dt = datetime.combine(datetime.strptime(start_date.get(), "%m/%d/%y"),
                                        datetime.strptime(start_time_entry.get().strip(), "%I:%M %p").time())
            due_dt = datetime.combine(datetime.strptime(due_date.get(), "%m/%d/%y"),
                                      datetime.strptime(due_time_entry.get().strip(), "%I:%M %p").time())
            reminder_hours = int(reminder_hours_entry.get())
        except ValueError:
            messagebox.showerror("Error", "Invalid date/time format.")
            return

        if due_dt < start_dt:
            messagebox.showerror("Error", "Due date cannot be before start date.")
            return

        # Build recurrence_days bitmask from checkboxes
        recurrence_days = 0
        for bit, var in recurrence_vars.items():
            if var.get():
                recurrence_days |= bit

        # Save to MongoDB
        insert_result = tasks_col.insert_one({
            "name": name,
            "course": course,
            "start": start_dt.strftime("%Y-%m-%d %H:%M:%S"),
            "due": due_dt.strftime("%Y-%m-%d %H:%M:%S"),
            "status": status,
            "recurrence_days": recurrence_days,
            "reminder_hours": reminder_hours,
            "reminder_sent": 0,
            "is_recurring_instance": False  # Original task
        })
        
        # If this is a recurring task, create future instances
        if recurrence_days > 0:
            create_future_recurring_instances(name, course, start_dt, due_dt, recurrence_days, reminder_hours, insert_result.inserted_id)
        
        load_tasks()
        new_window.destroy()

    tk.Button(new_window, text="Save & Close", command=save_assignment).grid(column=0, row=9, columnspan=2, pady=20)

# --- Edit Selected Task ---
def edit_selected_task():
    selected_item = tree.selection()
    if not selected_item:
        messagebox.showwarning("Edit Task", "Select a task to edit.")
        return
    task_id = selected_item[0]
    doc = tasks_col.find_one({"_id": ObjectId(task_id)})
    if not doc:
        messagebox.showerror("Error", "Selected task not found.")
        return
    task = dict(doc)

    edit_window = tk.Toplevel(root)
    edit_window.title("Edit Assignment")
    edit_window.geometry("800x600")

    tk.Label(edit_window, text="Edit Assignment", font=("Arial", 16)).grid(column=0, row=0, columnspan=2, pady=10)
    form_frame = tk.Frame(edit_window)
    form_frame.grid(column=0, row=1, padx=20, pady=10)

    tk.Label(form_frame, text="Assignment Name:").grid(column=0, row=0, sticky="w", padx=5, pady=5)
    name_entry = tk.Entry(form_frame, width=40)
    name_entry.grid(column=1, row=0, sticky="w", padx=5, pady=5)
    name_entry.insert(0, task.get("name", ""))

    tk.Label(form_frame, text="Class:").grid(column=0, row=1, sticky="w", padx=5, pady=5)
    classes = [
        "Select Class",
        "Database Design",
        "Computer Organization & Assembly Language",
        "Modern Software Design & Development",
        "Web Application Development",
        "CTC"
    ]
    selected_class = tk.StringVar(value=task.get("course", "Select Class"))
    tk.OptionMenu(form_frame, selected_class, *classes).grid(column=1, row=1, sticky="w", padx=5, pady=5)

    tk.Label(form_frame, text="Start Date:").grid(column=0, row=2, sticky="w", padx=5, pady=5)
    start_date = DateEntry(form_frame, width=40)
    start_date.grid(column=1, row=2, sticky="w", padx=5, pady=5)
    start_dt = datetime.strptime(task.get("start"), "%Y-%m-%d %H:%M:%S")
    start_date.set_date(start_dt.date())

    tk.Label(form_frame, text="Start Time (HH:MM AM/PM):").grid(column=0, row=3, sticky="w", padx=5, pady=5)
    start_time_entry = tk.Entry(form_frame, width=40)
    start_time_entry.grid(column=1, row=3, sticky="w", padx=5, pady=5)
    start_time_entry.insert(0, start_dt.strftime("%I:%M %p"))

    tk.Label(form_frame, text="Due Date:").grid(column=0, row=4, sticky="w", padx=5, pady=5)
    due_date = DateEntry(form_frame, width=40)
    due_date.grid(column=1, row=4, sticky="w", padx=5, pady=5)
    due_dt = datetime.strptime(task.get("due"), "%Y-%m-%d %H:%M:%S")
    due_date.set_date(due_dt.date())

    tk.Label(form_frame, text="Due Time (HH:MM AM/PM):").grid(column=0, row=5, sticky="w", padx=5, pady=5)
    due_time_entry = tk.Entry(form_frame, width=40)
    due_time_entry.grid(column=1, row=5, sticky="w", padx=5, pady=5)
    due_time_entry.insert(0, due_dt.strftime("%I:%M %p"))

    tk.Label(form_frame, text="Status:").grid(column=0, row=6, sticky="w", padx=5, pady=5)
    status_options = ["Select Status", "Not Started", "In Progress", "Completed", "Graded"]
    current_status = tk.StringVar(value=task.get("status", "Select Status"))
    tk.OptionMenu(form_frame, current_status, *status_options).grid(column=1, row=6, sticky="w", padx=5, pady=5)

    tk.Label(form_frame, text="Reminder Hours Before Due:").grid(column=0, row=7, sticky="w", padx=5, pady=5)
    reminder_hours_entry = tk.Entry(form_frame, width=10)
    reminder_hours_entry.grid(column=1, row=7, sticky="w", padx=5, pady=5)
    reminder_hours_entry.insert(0, str(task.get("reminder_hours", 24)))

    def save_edited_assignment():
        name = name_entry.get().strip()
        course = selected_class.get()
        status = current_status.get()
        if not name or course == "Select Class" or status == "Select Status":
            messagebox.showerror("Error", "Please fill all required fields.")
            return

        try:
            start_dt_new = datetime.combine(datetime.strptime(start_date.get(), "%m/%d/%y"),
                                        datetime.strptime(start_time_entry.get().strip(), "%I:%M %p").time())
            due_dt_new = datetime.combine(datetime.strptime(due_date.get(), "%m/%d/%y"),
                                      datetime.strptime(due_time_entry.get().strip(), "%I:%M %p").time())
            reminder_hours = int(reminder_hours_entry.get())
        except ValueError:
            messagebox.showerror("Error", "Invalid date/time format.")
            return

        if due_dt_new < start_dt_new:
            messagebox.showerror("Error", "Due date cannot be before start date.")
            return

        try:
            tasks_col.update_one(
                {"_id": ObjectId(task_id)},
                {"$set": {
                    "name": name,
                    "course": course,
                    "start": start_dt_new.strftime("%Y-%m-%d %H:%M:%S"),
                    "due": due_dt_new.strftime("%Y-%m-%d %H:%M:%S"),
                    "status": status,
                    "reminder_hours": reminder_hours,
                    "reminder_sent": 0
                }}
            )
            load_tasks()
            edit_window.destroy()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to update task: {e}")

    tk.Button(edit_window, text="Save & Close", command=save_edited_assignment).grid(column=0, row=8, columnspan=2, pady=20)

# --- Buttons ---
tk.Button(root, text="Add Assignment", command=open_new_window).pack(pady=5)

# --- View by Class Button ---
def open_class_view():
    class_window = tk.Toplevel(root)
    class_window.title("View by Class")
    class_window.geometry("800x600")
    
    # Class selection frame
    selection_frame = tk.Frame(class_window)
    selection_frame.pack(pady=10)
    
    tk.Label(selection_frame, text="Select Class:", font=("Arial", 12)).pack(side=tk.LEFT, padx=5)
    
    classes = [
        "Database Design",
        "Computer Organization & Assembly Language", 
        "Modern Software Design & Development",
        "Web Application Development",
        "CTC"
    ]
    selected_class = tk.StringVar(value=classes[0])
    class_dropdown = ttk.Combobox(selection_frame, textvariable=selected_class, values=classes, 
                                 state="readonly", width=40)
    class_dropdown.pack(side=tk.LEFT, padx=5)
    
    # Treeview for filtered tasks
    filtered_tree = ttk.Treeview(class_window, columns=("Name", "Class", "Start", "Due", "Status"), show="headings")
    filtered_tree.heading("Name", text="Assignment Name")
    filtered_tree.heading("Class", text="Class")
    filtered_tree.heading("Start", text="Start Date/Time")
    filtered_tree.heading("Due", text="Due Date/Time")
    filtered_tree.heading("Status", text="Status")
    filtered_tree.pack(fill="both", expand=True, padx=10, pady=10)
    
    # Configure treeview tags
    filtered_tree.tag_configure("Not Started", background="#ff7171")
    filtered_tree.tag_configure("In Progress", background="#fffacd")
    filtered_tree.tag_configure("Completed", background="#d0f0c0")
    filtered_tree.tag_configure("Graded", background="#add8e6")
    
    def load_filtered_tasks():
        filtered_tree.delete(*filtered_tree.get_children())
        selected_class_name = selected_class.get()
        tasks = tasks_col.find({"course": selected_class_name}).sort("due", 1)
        
        for doc in tasks:
            task = dict(doc)
            status_tag = task.get("status", "Not Started")
            filtered_tree.insert(
                "",
                tk.END,
                iid=str(doc.get("_id")),
                values=(
                    task.get("name"),
                    task.get("course"),
                    datetime.strptime(task.get("start"), "%Y-%m-%d %H:%M:%S").strftime("%m/%d/%y %I:%M %p"),
                    datetime.strptime(task.get("due"), "%Y-%m-%d %H:%M:%S").strftime("%m/%d/%y %I:%M %p"),
                    status_tag
                ),
                tags=(status_tag,)
            )
    
    def refresh_tasks():
        load_filtered_tasks()
    
    # Buttons
    button_frame = tk.Frame(class_window)
    button_frame.pack(pady=10)
    
    tk.Button(button_frame, text="Load Tasks", command=load_filtered_tasks).pack(side=tk.LEFT, padx=5)
    tk.Button(button_frame, text="Refresh", command=refresh_tasks).pack(side=tk.LEFT, padx=5)
    tk.Button(button_frame, text="Close", command=class_window.destroy).pack(side=tk.LEFT, padx=5)
    
    # Load tasks initially
    load_filtered_tasks()

tk.Button(root, text="View by Class", command=open_class_view).pack(pady=5)

# --- Status Update ---
status_frame = tk.Frame(root)
status_frame.pack(pady=5)
tk.Label(status_frame, text="Change Status:").pack(side=tk.LEFT)
status_combobox = ttk.Combobox(status_frame, values=["Not Started", "In Progress", "Completed", "Graded"],
                               state="readonly", width=15)
status_combobox.set("Not Started")
status_combobox.pack(side=tk.LEFT, padx=5)

def update_task_status():
    selected_item = tree.selection()
    if not selected_item:
        messagebox.showwarning("Update Status", "Select a task.")
        return
    task_id = selected_item[0]
    new_status = status_combobox.get()
    tasks_col.update_one({"_id": ObjectId(task_id)}, {"$set": {"status": new_status}})
    load_tasks()

tk.Button(status_frame, text="Update Status", command=update_task_status).pack(side=tk.LEFT, padx=5)

# --- Delete Task ---
def delete_selected_task():
    selected_item = tree.selection()
    if not selected_item:
        messagebox.showwarning("Delete Task", "Select a task.")
        return
    task_id = selected_item[0]
    tasks_col.delete_one({"_id": ObjectId(task_id)})
    load_tasks()

tk.Button(root, text="Delete Selected Task", command=delete_selected_task).pack(pady=5)

# --- Edit Task Button ---
tk.Button(root, text="Edit Selected Task", command=edit_selected_task).pack(pady=5)

# --- Delete All Tasks Button ---
def delete_all_tasks():
    # Show confirmation dialog
    result = messagebox.askyesno(
        "Delete All Tasks", 
        "Are you sure you want to delete ALL tasks? This action cannot be undone.",
        icon="warning"
    )
    
    if result:
        try:
            tasks = tasks_col.find({})
            deleted_count = 0
            
            for doc in tasks:
                tasks_col.delete_one({"_id": doc.get("_id")})
                deleted_count += 1
            
            load_tasks()
            messagebox.showinfo("Delete All Tasks", f"Successfully deleted {deleted_count} tasks.")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to delete all tasks: {e}")

tk.Button(root, text="Delete All Tasks", command=delete_all_tasks).pack(pady=5)

# --- Test Email Setup Button ---
def test_email_setup():
    """Test the email configuration by sending a test email"""
    try:
        # Get email from environment
        test_email = os.getenv("EMAIL_USER")
        if not test_email:
            messagebox.showerror("Email Setup Error", "EMAIL_USER not found in .env file")
            return
        
        # Send test email
        result = send_email(
            test_email,
            "Task Manager - Test Email",
            "This is a test email from your Task Manager application. If you receive this, your email setup is working correctly!"
        )
        
        if result:
            messagebox.showinfo("Email Test", f"Test email sent successfully to {test_email}!")
        else:
            messagebox.showerror("Email Test Failed", "Failed to send test email. Check your .env file and email credentials.")
            
    except Exception as e:
        messagebox.showerror("Email Test Error", f"Error testing email setup: {e}")

tk.Button(root, text="Test Email Setup", command=test_email_setup).pack(pady=5)

# Recurrence is only set when adding new assignments

# --- Reminder Loop ---
def reminder_loop():
    while True:
        now = datetime.now()
        tasks = tasks_col.find({})
        for doc in tasks:
            task = dict(doc)
            task_id = str(doc.get("_id"))
            due = datetime.strptime(task["due"], "%Y-%m-%d %H:%M:%S")
            start = datetime.strptime(task["start"], "%Y-%m-%d %H:%M:%S")
            reminder_hours = task.get("reminder_hours", 24)
            reminder_sent = task.get("reminder_sent", 0)
            status = task.get("status", "Not Started")
            recurrence_days = task.get("recurrence_days", 0)

            # Reminder logic with email lock to prevent duplicates across devices
            if due - timedelta(hours=reminder_hours) <= now < due and status != "Completed" and reminder_sent == 0:
                try:
                    # Try to acquire email lock to prevent duplicate emails from multiple devices
                    email_lock_key = f"email_lock_{task_id}_{due.strftime('%Y-%m-%d-%H')}"
                    
                    # Check if another device is already sending this reminder
                    lock_doc = email_locks_col.find_one({"_id": email_lock_key})
                    if lock_doc:
                        # Another device is handling this reminder
                        continue
                    
                    # Acquire the lock (expires in 1 hour)
                    email_locks_col.insert_one({
                        "_id": email_lock_key,
                        "task_id": task_id,
                        "acquired_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "expires_at": (datetime.now() + timedelta(hours=1)).strftime("%Y-%m-%d %H:%M:%S")
                    })
                    
                    # Send the email
                    send_email(
                        os.getenv("EMAIL_USER"),
                        f"Reminder: {task['name']} due soon",
                        f"Your assignment '{task['name']}' for {task['course']} is due at {due.strftime('%m/%d/%y %I:%M %p')}"
                    )
                    
                    # Mark as sent and clean up lock
                    tasks_col.update_one({"_id": ObjectId(task_id)}, {"$set": {"reminder_sent": 1}})
                    email_locks_col.delete_one({"_id": email_lock_key})
                    
                except Exception as e:
                    print(f"Failed to send reminder: {e}")
                    # Clean up lock on error
                    try:
                        email_locks_col.delete_one({"_id": email_lock_key})
                    except:
                        pass

            # Recurring task logic: if recurrence_days > 0, and due date has passed, create next instance
            if recurrence_days and recurrence_days > 0:
                # Only create next instance if due has passed (with a little grace period)
                if now >= due:
                    # Calculate next occurrence based on recurrence pattern
                    next_occurrence = calculate_next_occurrence(due, recurrence_days)
                    if next_occurrence:
                        # Calculate the duration of the original task
                        duration = due - start
                        new_start = next_occurrence - duration
                        new_due = next_occurrence
                        
                        # Check if next instance already exists to avoid duplicates
                        exists = tasks_col.find_one({"name": task["name"], "due": new_due.strftime("%Y-%m-%d %H:%M:%S")})
                        if not exists:
                            # Create new instance of the recurring task
                            try:
                                tasks_col.insert_one({
                                    "name": task["name"],
                                    "course": task["course"],
                                    "start": new_start.strftime("%Y-%m-%d %H:%M:%S"),
                                    "due": new_due.strftime("%Y-%m-%d %H:%M:%S"),
                                    "status": "Not Started",
                                    "recurrence_days": recurrence_days,
                                    "reminder_hours": task.get("reminder_hours", 24),
                                    "reminder_sent": 0,
                                    "parent_task_id": task_id,
                                    "is_recurring_instance": True
                                })
                                print(f"Created new recurring task instance: {task['name']} for {new_due.strftime('%m/%d/%y %I:%M %p')}")
                                # Refresh the treeview from the main thread
                                root.after(0, load_tasks)
                            except Exception as e:
                                print(f"Failed to create recurring task instance: {e}")
        time.sleep(60)

threading.Thread(target=reminder_loop, daemon=True).start()

# --- System Tray ---
setup_tray()
root.mainloop()