"""
Reminders module for Task Manager
Handles scheduling and managing task reminders
"""
import schedule
import time
import threading
from datetime import datetime
from discord_utils import send_discord_message

def check_reminders():
    """
    Function to check for due reminders
    This will be run in a separate thread
    """
    while True:
        schedule.run_pending()
        time.sleep(60)

def start_reminder_thread():
    """Start the reminder checking thread"""
    reminder_thread = threading.Thread(target=check_reminders, daemon=True)
    reminder_thread.start()
