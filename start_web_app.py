#!/usr/bin/env python3
"""
Startup script for Task Manager Web App
"""

import os
import sys
from web_app import app

if __name__ == '__main__':
    # Check if required files exist
    if not os.path.exists('serviceAccountKey.json'):
        print("Error: serviceAccountKey.json not found!")
        print("Please make sure your Firebase credentials file is in the same directory.")
        sys.exit(1)
    
    if not os.path.exists('.env'):
        print("Warning: .env file not found!")
        print("Email functionality may not work without EMAIL_USER and EMAIL_PASSWORD.")
    
    print("Starting Task Manager Web App...")
    print("Open your browser and go to: http://localhost:8080")
    print("Press Ctrl+C to stop the server")
    
    # Run the Flask app
    app.run(debug=True, host='0.0.0.0', port=8080)
