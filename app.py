import os
import logging
from flask import Flask, request, jsonify
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.date import DateTrigger
from dotenv import load_dotenv
from gemini_utils import extract_task_plan
from database import DatabaseManager
import requests
from datetime import datetime, timezone
import dateparser
import pytz
import atexit

# Load environment variables
load_dotenv()

# Timezone constants - Single source of truth
USER_TIMEZONE = pytz.timezone('Asia/Kolkata')
UTC = pytz.UTC

def get_current_time_in_user_tz():
    """Get current time in user's timezone (Asia/Kolkata)"""
    return datetime.now(USER_TIMEZONE)

def get_current_time_utc():
    """Get current time in UTC"""
    return datetime.now(UTC)

def convert_to_utc(dt):
    """Convert any timezone-aware datetime to UTC"""
    if dt.tzinfo is None:
        # If naive datetime, assume it's in user timezone
        dt = USER_TIMEZONE.localize(dt)
    return dt.astimezone(UTC)

def convert_to_user_tz(dt):
    """Convert any timezone-aware datetime to user timezone"""
    if dt.tzinfo is None:
        # If naive datetime, assume it's in UTC
        dt = UTC.localize(dt)
    return dt.astimezone(USER_TIMEZONE)

def parse_time_string(time_str, reference_time=None):
    """
    Parse time string with consistent timezone handling
    Returns UTC datetime object
    """
    if reference_time is None:
        reference_time = get_current_time_in_user_tz()
    
    # Parse relative to user timezone
    parsed_dt = dateparser.parse(
        time_str,
        settings={
            'TIMEZONE': 'Asia/Kolkata',
            'RETURN_AS_TIMEZONE_AWARE': True,
            'RELATIVE_BASE': reference_time
        }
    )
    
    if parsed_dt:
        return convert_to_utc(parsed_dt)
    return None

# Global database manager
db = DatabaseManager()

def create_app():
    app = Flask(__name__)
    logging.basicConfig(level=logging.INFO)

    BOT_TOKEN = os.getenv("BOT_TOKEN")
    TELEGRAM_URL = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

    # Initialize scheduler
    scheduler = BackgroundScheduler(timezone=UTC)
    scheduler.start()
    
    # Register cleanup function
    atexit.register(lambda: scheduler.shutdown())

    def send_message(chat_id: int, text: str, job_id: str = None):
        """
        Send message via Telegram and mark reminder as sent in database
        """
        try:
            response = requests.post(TELEGRAM_URL, json={"chat_id": chat_id, "text": text})
            response.raise_for_status()
            logging.info(f"✅ Message sent to {chat_id}: {text}")
            
            # Mark reminder as sent in database
            if job_id:
                db.mark_reminder_sent(job_id)
                logging.info(f"✅ Reminder {job_id} marked as sent in database")
                
        except Exception as e:
            logging.error(f"🔥 Failed to send message to {chat_id}: {e}")

    def restore_scheduled_jobs():
        """
        Restore all pending reminders from database on startup
        This is crucial for persistence across server restarts
        """
        try:
            pending_reminders = db.get_pending_reminders()
            now_utc = get_current_time_utc()
            restored_count = 0
            
            for reminder in pending_reminders:
                reminder_time_utc = dateparser.parse(reminder['reminder_time_utc'])
                
                # Skip past reminders
                if reminder_time_utc <= now_utc:
                    logging.info(f"Skipping past reminder: {reminder['job_id']}")
                    continue
                
                try:
                    trigger = DateTrigger(run_date=reminder_time_utc)
                    scheduler.add_job(
                        func=send_message,
                        trigger=trigger,
                        args=[reminder['chat_id'], reminder['message'], reminder['job_id']],
                        id=reminder['job_id']
                    )
                    restored_count += 1
                    logging.info(f"✅ Restored job: {reminder['job_id']}")
                    
                except Exception as e:
                    logging.error(f"Failed to restore job {reminder['job_id']}: {e}")
            
            logging.info(f"🔄 Restored {restored_count} scheduled reminders from database")
            
        except Exception as e:
            logging.error(f"Failed to restore jobs from database: {e}")

    # Restore jobs on startup
    restore_scheduled_jobs()

    @app.route("/", methods=["GET"])
    def home():
        stats = db.get_database_stats()
        return f"TaskNova is running! Database stats: {stats}"

    @app.route("/webhook", methods=["POST"])
    def webhook():
        try:
            data = request.get_json(force=True)
            logging.info("Webhook received: %s", data)
            
            if "message" not in data:
                return jsonify(ok=True)

            chat_id = data["message"]["chat"]["id"]
            text = data["message"].get("text", "")
            
            # Handle special commands
            if text.lower() in ['/start', '/help']:
                help_msg = (
                    "🤖 Welcome to TaskNova!\n\n"
                    "I'm your AI-powered reminder assistant. Just tell me what you need to remember:\n\n"
                    "Examples:\n"
                    "• 'Remind me to submit assignment by 8 PM'\n"
                    "• 'Call mom in 30 minutes'\n"
                    "• 'Meeting preparation tomorrow at 2 PM'\n\n"
                    "I'll create smart multiple reminders to keep you on track! 🎯"
                )
                send_message(chat_id, help_msg)
                return jsonify(ok=True)
            
            if text.lower() == '/mystasks':
                user_tasks = db.get_user_tasks(chat_id, limit=5)
                if not user_tasks:
                    send_message(chat_id, "📋 You have no active tasks.")
                else:
                    msg = "📋 Your Recent Tasks:\n\n"
                    for task in user_tasks:
                        base_time = dateparser.parse(task['base_time'])
                        if base_time:
                            base_time_user = convert_to_user_tz(base_time)
                            time_str = base_time_user.strftime('%Y-%m-%d %I:%M %p IST')
                        else:
                            time_str = "Time not available"
                        
                        msg += f"• {task['task_description']}\n"
                        msg += f"  ⏰ Due: {time_str}\n"
                        msg += f"  📊 Reminders: {task['sent_reminders']}/{task['total_reminders']} sent\n\n"
                    
                send_message(chat_id, msg)
                return jsonify(ok=True)
            
            # Get current time in user timezone for context
            now_user_tz = get_current_time_in_user_tz()
            now_utc = get_current_time_utc()
            
            # Pass user timezone time to Gemini for better context
            parsed = extract_task_plan(text, now_user_tz)
            task = parsed.get("task")
            base_time_str = parsed.get("base_time")
            reminders = parsed.get("reminders", [])

            if not task or not base_time_str or not reminders:
                send_message(chat_id, "⚠️ Sorry, I couldn't understand your task/time. Try: 'Remind me to ... at ...'.")
                return jsonify(ok=True)

            task_entries = []

            for idx, reminder in enumerate(reminders):
                time_str = reminder.get("time")
                message = reminder.get("message")
                
                # Parse reminder time consistently
                dt_utc = parse_time_string(time_str, now_user_tz)
                
                if not dt_utc or dt_utc < now_utc:
                    logging.warning(f"Skipping past reminder: {time_str}")
                    continue  # Skip past reminders

                try:
                    job_id = f"{chat_id}_{int(now_utc.timestamp())}_{idx}"
                    trigger = DateTrigger(run_date=dt_utc)  # Schedule in UTC
                    
                    scheduler.add_job(
                        func=send_message,
                        trigger=trigger,
                        args=[chat_id, message, job_id],
                        id=job_id
                    )
                    
                    task_entries.append({
                        "id": job_id, 
                        "task": task, 
                        "time_utc": dt_utc.isoformat(), 
                        "time_user": convert_to_user_tz(dt_utc).isoformat(),
                        "message": message
                    })
                    
                except Exception as e:
                    logging.error(f"Failed to schedule job {job_id}: {e}")
                    continue

            if task_entries:
                # Save to database BEFORE sending confirmation
                try:
                    task_id = db.save_task_with_reminders(
                        chat_id=chat_id,
                        task_description=task,
                        base_time=base_time_str,
                        reminder_entries=task_entries
                    )
                    logging.info(f"✅ Task {task_id} saved to database with {len(task_entries)} reminders")
                except Exception as e:
                    logging.error(f"Failed to save task to database: {e}")
                    send_message(chat_id, "⚠️ Task scheduled but couldn't save to database. Reminders may not persist across restarts.")
                
                # Show confirmation to user
                first_reminder_utc = dateparser.parse(task_entries[0]["time_utc"])
                first_reminder_user = convert_to_user_tz(first_reminder_utc)
                
                reminder_times = []
                for entry in task_entries:
                    entry_utc = dateparser.parse(entry["time_utc"])
                    entry_user = convert_to_user_tz(entry_utc)
                    reminder_times.append(entry_user.strftime('%I:%M %p'))
                
                response_msg = (
                    f"✅ Task scheduled: *{task}*\n"
                    f"🕒 Reminders at: {', '.join(reminder_times)}\n"
                    f"📅 Starting: {first_reminder_user.strftime('%Y-%m-%d %I:%M %p IST')}\n\n"
                    f"💾 Saved to database - will persist across restarts!"
                )
                send_message(chat_id, response_msg)
            else:
                send_message(chat_id, "⚠️ All generated reminders were in the past. Task not scheduled.")

        except Exception as e:
            logging.error(f"Webhook processing error: {e}")
            send_message(chat_id, "🔥 Sorry, something went wrong processing your request.")

        return jsonify(ok=True)

    @app.route("/tasks", methods=["GET"])
    def list_tasks():
        chat_id = int(request.args.get("chat_id", 0))
        user_tasks = db.get_user_tasks(chat_id)
        return jsonify(user_tasks)
    
    @app.route("/stats", methods=["GET"])
    def stats():
        """Database statistics endpoint"""
        return jsonify(db.get_database_stats())
    
    @app.route("/cleanup", methods=["POST"])
    def cleanup_old_tasks():
        """Manual cleanup endpoint"""
        try:
            db.cleanup_old_tasks(days_old=7)
            return jsonify({"status": "success", "message": "Old tasks cleaned up"})
        except Exception as e:
            return jsonify({"status": "error", "message": str(e)})

    @app.teardown_appcontext
    def cleanup(error):
        if error:
            logging.error(f"App context error: {error}")

    return app

# Create the app instance for Gunicorn to find
app = create_app()

if __name__ == "__main__":
    # Only used for local development
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)), debug=False)