# Task Manager 2.5
[![Ask DeepWiki](https://devin.ai/assets/askdeepwiki.png)](https://deepwiki.com/JHanna-2020/TaskManager25)

A comprehensive task management application with synchronized desktop and web interfaces, built with a MongoDB backend, offering email reminders, and recurring task support.

## Features

This project provides two distinct interfaces that share the same real-time database.

### Desktop App (`main.py`)
- **Native GUI:** Built with Python's `tkinter` for a traditional desktop experience.
- **Background Operation:** Can run in the system tray for continuous monitoring.
- **Email Reminders:** Automatically sends email notifications for upcoming deadlines.
- **Status Tracking:** Manage tasks with statuses: `Not Started`, `In Progress`, `Completed`, and `Graded`.
- **Class Filtering:** Organize and view tasks by academic course.
- **Recurring Tasks:** Set up tasks that repeat on specific days of the week.

### Web App (`web_app.py`)
- **Responsive UI:** Modern interface built with Flask and Bootstrap, optimized for desktops, tablets, and phones.
- **Cross-Platform Access:** Accessible from any device with a web browser on the same local network.
- **Full Functionality:** Supports adding, editing, deleting, and updating tasks.
- **Filtered Views:** Easily view all, active, or completed tasks, or filter by class.
- **Mobile-First Actions:** Quick-action buttons and dropdowns for easy management on touch devices.

## Setup Instructions

### Prerequisites
- Python 3.8 or higher
- A MongoDB Atlas account for the cloud database
- A Gmail account for sending email reminders (with 2-Factor Authentication enabled)

### 1. Clone the Repository
```bash
git clone https://github.com/JHanna-2020/TaskManager25.git
cd TaskManager25
```

### 2. Install Dependencies
The project has separate dependencies for the desktop and web versions.

**For the Desktop App:**
```bash
pip install -r requirements.txt
```

**For the Web App:**
```bash
pip install -r requirements_web.txt
```

### 3. Configure MongoDB Atlas
1.  **Create a free cluster** on [MongoDB Atlas](https://www.mongodb.com/cloud/atlas/register).
2.  **Create a Database User:** In the "Database Access" section, create a new user. Note the username and password.
3.  **Whitelist your IP Address:** In the "Network Access" section, add your current IP address or `0.0.0.0/0` to allow access from anywhere (less secure).
4.  **Get a Connection String:** Go to your cluster's "Overview" tab, click "Connect", choose "Drivers", and copy the Python connection string (`mongodb+srv://...`). You will need this for the `.env` file.

### 4. Create Environment File
Create a file named `.env` in the root of the project directory and add the following variables. Replace the placeholder values with your credentials.

```env
# MongoDB Credentials (from Step 3)
DB_USER=your_mongo_db_username
DB_PASSWORD=your_mongo_db_password

# Email Credentials (for reminders)
EMAIL_USER=your-email@gmail.com
EMAIL_PASSWORD=your-gmail-app-password

# Flask Web App Secret Key
SECRET_KEY=a_long_random_and_secret_string
```
**Important:** For `EMAIL_PASSWORD`, you must generate a **Gmail App Password**. Do not use your regular account password. You can create one here: [Google Account App Passwords](https://myaccount.google.com/apppasswords).

## Usage

### Running the Desktop App
Execute the `main.py` script to launch the Tkinter GUI.
```bash
python main.py
```

### Running the Web App
Execute the `start_web_app.py` script.
```bash
python start_web_app.py
```
-   Access the web app on your local machine at `http://localhost:8080`.
-   To access from other devices (like a phone) on the same Wi-Fi network, find your computer's local IP address and navigate to `http://<YOUR_IP_ADDRESS>:8080`.

## Project Structure
```
TaskManager25/
├── main.py                 # Main script for the desktop (Tkinter) application
├── web_app.py              # Core logic for the web (Flask) application
├── start_web_app.py        # Startup script for the web server
├── email_utils.py          # Handles sending email notifications via Gmail SMTP
├── reminders.py            # Background scheduler for reminder jobs
│
├── requirements.txt        # Dependencies for the desktop app
├── requirements_web.txt    # Dependencies for the web app
│
├── templates/              # HTML templates for the Flask web app
│   ├── base.html           # Base template with navbar and styling
│   ├── index.html          # Main page showing all tasks
│   ├── add_task.html       # Form for adding a new task
│   ├── edit_task.html      # Form for editing an existing task
│   ├── view_active.html    # View for active tasks
│   ├── view_completed.html # View for completed tasks
│   └── view_by_class.html  # View for tasks filtered by class
│
├── .env                    # (You create this) Stores secret credentials
└── README.md               # This file
```

## Troubleshooting
- **MongoDB Connection Error:**
  -   Ensure your `DB_USER` and `DB_PASSWORD` in the `.env` file are correct.
  -   Verify that your current IP address is whitelisted in MongoDB Atlas under "Network Access".
  -   Check that your internet connection is active.

- **Email Sending Failed:**
  -   Confirm you are using a **Gmail App Password** in `EMAIL_PASSWORD`, not your regular login password.
  -   Ensure 2-Factor Authentication is enabled for the Gmail account.
  -   Run `python email_utils.py` to test your email configuration directly. The script will send a test email to the `EMAIL_USER` address.

- **Web App Not Accessible from Other Devices:**
  -   Make sure your computer and the other device are on the same Wi-Fi network.
  -   Check that your computer's firewall is not blocking incoming connections on port `8080`.