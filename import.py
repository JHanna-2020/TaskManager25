import os
import pandas as pd
import firebase_admin
from firebase_admin import credentials, firestore
from dotenv import load_dotenv

load_dotenv()

def import_from_excel(file_path):
    if not firebase_admin._apps:
        cred = credentials.Certificate(os.getenv("FIREBASE_CREDENTIALS_PATH", "firebase-credentials.json"))
        firebase_admin.initialize_app(cred)

    db = firestore.client()
    tasks_col = db.collection("tasks")
    print("✅ Successfully connected to Firestore.")

    try:
        df = pd.read_excel(file_path)
        print(f"📄 Found {len(df)} rows in the Excel file.")

        df['start'] = pd.to_datetime(df['start'])
        df['due'] = pd.to_datetime(df['due'])

        tasks_to_insert = df.to_dict('records')

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

        for task in tasks_to_insert:
            tasks_col.add(task)

        print(f"✅ Successfully inserted {len(tasks_to_insert)} tasks into Firestore!")

    except FileNotFoundError:
        print(f"❌ Error: The file was not found at {file_path}")
    except Exception as e:
        print(f"❌ An error occurred: {e}")

if __name__ == '__main__':
    excel_file = 'tasks.xlsx'
    import_from_excel(excel_file)
