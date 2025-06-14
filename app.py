import os
import logging
from flask import Flask, request, jsonify
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.date import DateTrigger
from dotenv import load_dotenv
from gemini_utils import extract_task_plan
import requests
from datetime import datetime, timezone
import dateparser
import pytz

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

# Flask setup
def create_app():
    app = Flask(__name__)
    logging.basicConfig(level=logging.INFO)

    BOT_TOKEN = os.getenv("BOT_TOKEN")
    TELEGRAM_URL = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

    # In-memory store: {chat_id: [{id, task, run_date_utc, message}...]}
    tasks = {}
    scheduler = BackgroundScheduler(timezone=UTC)  # Scheduler runs in UTC
    scheduler.start()

    def send_message(chat_id: int, text: str):
        try:
            response = requests.post(TELEGRAM_URL, json={"chat_id": chat_id, "text": text})
            response.raise_for_status()
            logging.info(f"✅ Message sent to {chat_id}: {text}")
        except Exception as e:
            logging.error(f"🔥 Failed to send message to {chat_id}: {e}")

    @app.route("/", methods=["GET"])
    def home():
        return "TaskNova is running!"

    @app.route("/webhook", methods=["POST"])
    def webhook():
        try:
            data = request.get_json(force=True)
            logging.info("Webhook received: %s", data)
            
            if "message" not in data:
                return jsonify(ok=True)

            chat_id = data["message"]["chat"]["id"]
            text = data["message"].get("text", "")
            
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
                    job_id = f"{chat_id}_{len(tasks.get(chat_id, [])) + idx + 1}"
                    trigger = DateTrigger(run_date=dt_utc)  # Schedule in UTC
                    
                    scheduler.add_job(
                        func=send_message,
                        trigger=trigger,
                        args=[chat_id, message],
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
                tasks.setdefault(chat_id, []).extend(task_entries)
                
                # Show first reminder time in user timezone
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
                    f"📅 Starting: {first_reminder_user.strftime('%Y-%m-%d %I:%M %p IST')}"
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
        user_tasks = tasks.get(chat_id, [])
        
        # Convert times to user timezone for display
        display_tasks = []
        for task in user_tasks:
            task_copy = task.copy()
            if 'time_utc' in task_copy:
                utc_time = dateparser.parse(task_copy['time_utc'])
                user_time = convert_to_user_tz(utc_time)
                task_copy['time_display'] = user_time.strftime('%Y-%m-%d %I:%M %p IST')
            display_tasks.append(task_copy)
            
        return jsonify(display_tasks)

    @app.teardown_appcontext
    def cleanup(error):
        if error:
            logging.error(f"App context error: {error}")

    return app

if __name__ == "__main__":
    app = create_app()
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)))