import os
import pandas as pd
from pymongo import MongoClient
from dotenv import load_dotenv
import urllib.parse

# Load environment variables from your .env file
load_dotenv()

def import_from_excel(file_path):
    """
    Imports tasks from an Excel file into the MongoDB database.
    """
    # --- Database Connection ---
    db_user = os.getenv("DB_USER")
    db_password = os.getenv("DB_PASSWORD")
    db_name = os.getenv("DB_NAME", "TaskManager")

    if not db_user or not db_password:
        print("Error: DB_USER and DB_PASSWORD must be set in .env")
        return

    # Connect to MongoDB Atlas
    mongo_uri = f"mongodb+srv://{db_user}:{db_password}@taskmanger.3gfydvt.mongodb.net/?retryWrites=true&w=majority&appName=taskmanger"
    try:
        client = MongoClient(mongo_uri, tls=True, tlsAllowInvalidCertificates=False)
        db = client[db_name]
        tasks_col = db["tasks"]
        print("✅ Successfully connected to MongoDB.")
    except Exception as e:
        print(f"❌ Error connecting to MongoDB: {e}")
        return

    # --- Read and Process Excel File ---
    try:
        # Read the Excel file into a pandas DataFrame
        df = pd.read_excel(file_path)
        print(f"📄 Found {len(df)} rows in the Excel file.")

        # --- Data Validation and Transformation ---
        # Ensure date columns are converted to datetime objects
        # This handles various date/time formats in your Excel sheet
        df['start'] = pd.to_datetime(df['start'])
        df['due'] = pd.to_datetime(df['due'])

        # Convert the DataFrame to a list of dictionaries (the format MongoDB needs)
        tasks_to_insert = df.to_dict('records')

        # Add default values for fields that might be missing
        for task in tasks_to_insert:
            task['start'] = task['start'].strftime("%Y-%m-%d %H:%M:%S")
            task['due'] = task['due'].strftime("%Y-%m-%d %H:%M:%S")
            task.setdefault('status', 'Not Started')
            task.setdefault('reminder_hours', 24)
            task.setdefault('reminder_sent', 0)
            task.setdefault('recurrence_days', 0)
            task.setdefault('is_recurring_instance', False)

        if not tasks_to_insert:
            print("⚠️ No tasks to insert.")
            return

        # --- Insert Data into MongoDB ---
        result = tasks_col.insert_many(tasks_to_insert)
        print(f"✅ Successfully inserted {len(result.inserted_ids)} tasks into the database!")

    except FileNotFoundError:
        print(f"❌ Error: The file was not found at {file_path}")
    except Exception as e:
        print(f"❌ An error occurred: {e}")

if __name__ == '__main__':
    # IMPORTANT: Replace 'YourAssignments.xlsx' with the actual name of your file.
    # Make sure the Excel file is in the same directory as this script.
    excel_file = 'tasks.xlsx'
    import_from_excel(excel_file)