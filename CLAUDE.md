# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Running the Apps

**Desktop app (Tkinter GUI):**
```bash
pip install -r requirements.txt
python main.py
```

**Web app (Flask):**
```bash
pip install -r requirements_web.txt
python start_web_app.py
# Runs on http://localhost:8081
```

**Test Discord webhook:**
```bash
python discord_utils.py
```

**Import tasks from Excel:**
```bash
python import.py
```

## Environment Setup

Create a `.env` file in the project root:
```env
FIREBASE_CREDENTIALS_PATH=firebase-credentials.json
DISCORD_WEBHOOK_URL=your_discord_webhook_url
SECRET_KEY=a_long_random_secret_string
```

Both apps require a Firebase service account key JSON file (default: `firebase-credentials.json` in the project root). To get one:
1. Go to [Firebase Console](https://console.firebase.google.com) → Project Settings → Service Accounts
2. Click "Generate new private key" and save the file as `firebase-credentials.json`
3. Enable Firestore in the Firebase console (Firestore Database → Create database)

## Architecture

Two parallel interfaces share the same Firestore backend:

- **`main.py`** — Tkinter desktop GUI. Runs a background `reminder_loop` thread (polls every 60s) that sends Discord alerts and auto-creates recurring task instances.
- **`web_app.py`** — Flask web app. Uses APScheduler (60s interval) for the same reminder logic. Runs on port 8080 when invoked directly, port 8081 via `start_web_app.py`.
- **`discord_utils.py`** — Single function `send_discord_message()` used by both apps.
- **`import.py`** — One-off script to bulk-import tasks from `tasks.xlsx` into Firestore.
- **`reminders.py`** — Unused standalone reminder module (not imported by either app).

## Firestore Document Schema

Tasks are stored as documents in the `tasks` collection (Firestore auto-generates string IDs — no ObjectId):
```
name, course, start, due  — strings in "%Y-%m-%d %H:%M:%S" format
status                    — "Not Started" | "In Progress" | "Completed" | "Graded"
recurrence_days           — bitmask (Mon=1, Tue=2, Wed=4, Thu=8, Fri=16, Sat=32, Sun=64); -1 = "due weekday" recurrence
reminder_hours            — int, hours before due to send Discord alert
reminder_sent             — 0 or 1
is_recurring_instance     — bool
parent_task_id            — string ObjectId of the original task (recurring instances only)
```

Recurring tasks: when a task with `recurrence_days > 0` is created, `create_future_recurring_instances()` pre-generates 12 weeks of instances. The reminder loop also creates the next instance on-the-fly when `now >= due`.

## Hard-coded Course List

Both apps share the same fixed class list. To add/remove classes, update in both `main.py` (`open_new_window` and `edit_selected_task`) and `web_app.py` templates (`add_task.html`):
- Database Design
- Computer Organization & Assembly Language
- Modern Software Design & Development
- Web Application Development
- CTC
