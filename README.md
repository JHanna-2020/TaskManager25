# Task Manager

A comprehensive task management application with synchronized desktop and web interfaces, built with a Firebase Firestore backend, offering Discord reminders, and recurring task support.

-----

## Features

This project provides two distinct interfaces that share the same real-time Firestore database.

### Desktop App (`main.py`)

  * **Native GUI**: Built with Python's `tkinter` for a traditional desktop experience.
  * **Discord Reminders**: Automatically sends notifications for upcoming deadlines to a Discord channel.
  * **Status Tracking**: Manage tasks with statuses: `Not Started`, `In Progress`, `Completed`, and `Graded`.
  * **Class Filtering**: Organize and view tasks by academic course.
  * **Recurring Tasks**: Set up tasks that repeat on specific days of the week.

### Web App (`web_app.py`)

  * **Responsive UI**: Modern interface built with Flask and Bootstrap, optimized for desktops, tablets, and phones.
  * **Cross-Platform Access**: Accessible from any device with a web browser on the same local network.
  * **Discord Reminders**: Sends reminders to a Discord channel via webhooks.
  * **Full Functionality**: Supports adding, editing, deleting, and updating tasks.
  * **Filtered Views**: Easily view all, active, or completed tasks, or filter by class.
  * **Mobile-First Actions**: Quick-action buttons and dropdowns for easy management on touch devices.

-----

## Setup Instructions

### Prerequisites

  * Python 3.8 or higher
  * A Firebase project with Firestore enabled
  * A Discord account and server for Discord reminders

### 1\. Clone the Repository

```bash
git clone https://github.com/JHanna-2020/TaskManager25.git
cd TaskManager25
```

### 2\. Install Dependencies

The project has separate dependencies for the desktop and web versions.

**For the Desktop App:**

```bash
pip install -r requirements.txt
```

**For the Web App:**

```bash
pip install -r requirements_web.txt
```

### 3\. Configure Firebase

1.  **Create a Firebase project** at [Firebase Console](https://console.firebase.google.com).
2.  **Enable Firestore:** Navigate to Firestore Database → Create database.
3.  **Generate a service account key:** Go to Project Settings → Service Accounts → Generate new private key. Save the downloaded file as `firebase-credentials.json` in the project root.

### 4\. Create Environment File

Create a file named `.env` in the root of the project directory and add the following variables. Replace the placeholder values with your credentials.

```env
# Firebase credentials (from Step 3)
FIREBASE_CREDENTIALS_PATH=firebase-credentials.json

# Discord Webhook URL
DISCORD_WEBHOOK_URL=your_discord_webhook_url

# Flask Web App Secret Key
SECRET_KEY=a_long_random_and_secret_string
```

-----

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

  * Access the web app on your local machine at `http://localhost:8081`.
  * To access from other devices (like a phone) on the same Wi-Fi network, find your computer's local IP address and navigate to `http://<YOUR_IP_ADDRESS>:8081`.

### Importing Tasks from Excel

To bulk-import tasks from a spreadsheet:

```bash
python import.py
```

This reads from `tasks.xlsx` in the project root and uploads the tasks to Firestore.

### Testing Discord Notifications

To send a test message to your configured Discord channel:

```bash
python discord_utils.py
```

-----

## Project Structure

```
TaskManager25/
├── main.py                 # Main script for the desktop (Tkinter) application
├── web_app.py              # Core logic for the web (Flask) application
├── start_web_app.py        # Startup script for the web server (port 8081)
├── discord_utils.py        # Handles sending Discord notifications via webhooks
├── import.py               # Bulk-imports tasks from tasks.xlsx into Firestore
├── reminders.py            # Standalone reminder module (unused)
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
├── firebase-credentials.json  # (You create this) Firebase service account key
├── .env                       # (You create this) Stores secret credentials
└── README.md                  # This file
```

-----

## Troubleshooting

  * **Firebase Connection Error:**
      * Ensure `firebase-credentials.json` exists in the project root and is a valid service account key.
      * Verify that `FIREBASE_CREDENTIALS_PATH` in your `.env` file points to the correct file.
      * Confirm that Firestore is enabled in your Firebase project (not just the Realtime Database).
  * **Discord Reminders Not Working:**
      * Double-check that your `DISCORD_WEBHOOK_URL` in the `.env` file is correct.
      * Run `python discord_utils.py` to send a test message.
  * **Web App Not Accessible from Other Devices:**
      * Make sure your computer and the other device are on the same Wi-Fi network.
      * Check that your computer's firewall is not blocking incoming connections on port `8081`.
