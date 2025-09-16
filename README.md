# Task Manager

A comprehensive task management application with both desktop and web interfaces, featuring Firebase integration, email reminders, and recurring task support.

## Features

### Desktop App (main.py)
- **GUI Interface** - Built with tkinter for cross-platform desktop use
- **Firebase Integration** - Real-time cloud synchronization
- **Email Reminders** - Automated email notifications before due dates
- **Recurring Tasks** - Support for tasks that repeat on specific days
- **Class Filtering** - Organize tasks by academic classes
- **System Tray** - Runs in background with system tray integration
- **Status Management** - Track task progress (Not Started, In Progress, Completed, Graded)

### Web App (web_app.py)
- **Mobile-Friendly** - Responsive design for phones, tablets, and desktops
- **Cross-Platform** - Works on any device with a web browser
- **Real-Time Sync** - Same data as desktop app via Firebase
- **Modern UI** - Clean, professional interface with Bootstrap
- **Touch Optimized** - Designed for mobile interaction

## Setup Instructions

### Prerequisites
- Python 3.8 or higher
- Firebase project with Firestore database
- Gmail account (for email reminders)

### 1. Clone the Repository
```bash
git clone https://github.com/yourusername/TaskManager.git
cd TaskManager
```

### 2. Install Dependencies

#### For Desktop App:
```bash
pip install -r requirements.txt
```

#### For Web App:
```bash
pip install -r requirements_web.txt
```

### 3. Firebase Setup
1. Create a Firebase project at https://console.firebase.google.com
2. Enable Firestore database
3. Generate a service account key
4. Download the key file and rename it to `serviceAccountKey.json`
5. Place it in the project root directory

### 4. Environment Configuration
Create a `.env` file in the project root:
```env
EMAIL_USER=your-email@gmail.com
EMAIL_PASSWORD=your-gmail-app-password
SECRET_KEY=your-secret-key-for-web-app
```

**Note:** Use Gmail App Password, not your regular password. Enable 2-Factor Authentication and generate an App Password at https://myaccount.google.com/apppasswords

## Usage

### Desktop App
```bash
python main.py
```

### Web App
```bash
python start_web_app.py
```
Then open http://localhost:5000 in your browser

### Mobile Access
- Start the web app on your computer
- Find your computer's IP address
- Access via http://[your-ip]:5000 from any device on the same network

## Project Structure

```
TaskManager/
├── main.py                 # Desktop application
├── web_app.py             # Web application
├── start_web_app.py       # Web app startup script
├── email_utils.py         # Email functionality
├── reminders.py           # Reminder scheduling
├── requirements.txt       # Desktop app dependencies
├── requirements_web.txt   # Web app dependencies
├── templates/             # Web app HTML templates
│   ├── base.html
│   ├── index.html
│   ├── add_task.html
│   ├── edit_task.html
│   └── view_by_class.html
├── serviceAccountKey.json # Firebase credentials (not in repo)
├── .env                   # Environment variables (not in repo)
└── README.md
```

## Features in Detail

### Task Management
- **Add Tasks** - Create new assignments with due dates, classes, and reminders
- **Edit Tasks** - Modify existing tasks
- **Delete Tasks** - Remove individual tasks or all tasks
- **Status Updates** - Change task status with dropdown selection

### Recurring Tasks
- **Set Recurrence** - Choose specific days of the week for task repetition
- **Automatic Creation** - Future instances created automatically
- **Multiple Instances** - See all upcoming occurrences in your task list

### Class Organization
- **Class Filtering** - View tasks by specific academic classes
- **Class View Window** - Dedicated interface for class-specific tasks

### Email Reminders
- **Configurable Timing** - Set reminder hours before due date
- **Duplicate Prevention** - Email lock system prevents multiple devices from sending same reminder
- **Test Functionality** - Built-in email testing

### Cross-Device Sync
- **Real-Time Updates** - Changes sync instantly across all devices
- **Cloud Storage** - All data stored in Firebase Firestore
- **Platform Independent** - Works on Windows, Mac, Linux, phones, tablets

## Security Notes

- **Never commit** `serviceAccountKey.json` or `.env` files
- **Use App Passwords** for Gmail authentication
- **Keep Firebase credentials** secure and private
- **Regular backups** recommended for important data

## Troubleshooting

### Common Issues
1. **Email not working** - Check Gmail App Password setup
2. **Firebase connection failed** - Verify serviceAccountKey.json is present
3. **Web app not accessible** - Check firewall settings and IP address
4. **Tasks not syncing** - Ensure internet connection and Firebase project is active

### Support
For issues or questions, please check the troubleshooting section or create an issue in the GitHub repository.

## License

This project is open source and available under the MIT License.
