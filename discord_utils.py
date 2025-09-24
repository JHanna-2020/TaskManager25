"""
Discord utility module for Task Manager
Handles sending messages to a Discord channel via webhooks
"""
import requests
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def send_discord_message(message):
    """
    Sends a message to the Discord channel configured via a webhook URL.

    Args:
        message (str): The message content to send.

    Returns:
        bool: True if the message was sent successfully, False otherwise.
    """
    webhook_url = os.getenv("DISCORD_WEBHOOK_URL")
    if not webhook_url:
        print("Error: DISCORD_WEBHOOK_URL not found in .env file")
        return False

    data = {
        "content": message
    }

    response = requests.post(webhook_url, json=data)

    if response.status_code == 204:
        print("Discord message sent successfully!")
        return True
    else:
        print(f"Error sending Discord message: {response.status_code} - {response.text}")
        return False

if __name__ == '__main__':
    # Test the Discord webhook setup
    send_discord_message("This is a test message from the Task Manager!")