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
import uuid

# Timezone strategy:
# - All internal processing and storage of datetimes should be in UTC.
# - User-facing datetimes (e.g., in messages) should be displayed in 'Asia/Kolkata'.
# - `dateparser` is used for parsing, configured to assume UTC for ambiguous inputs
#   and always return UTC datetimes.

# Load environment variables
load_dotenv()

# Flask setup
def create_app():
    app = Flask(__name__)
    logging.basicConfig(level=logging.INFO)

    BOT_TOKEN = os.getenv("BOT_TOKEN")
    TELEGRAM_URL = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

    # In-memory store: {chat_id: [{id, task, run_date, message}...]}
    tasks = {}
    scheduler = BackgroundScheduler()
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
        data = request.get_json(force=True)
        logging.info("Webhook received: %s", data)
        if "message" not in data:
            return jsonify(ok=True)

        chat_id = data["message"]["chat"]["id"]
        text = data["message"].get("text", "")
        # now is in UTC
        now = datetime.now(timezone.utc)

        # Pass UTC time to Gemini
        parsed = extract_task_plan(text, now.isoformat())
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
            # Parse time_str: assume UTC if no timezone info, and return as UTC datetime.
            dt = dateparser.parse(
                time_str,
                settings={
                    'PREFER_DATES_FROM': 'future', # Keep this as it's generally useful
                    'RETURN_AS_TIMEZONE_AWARE': True,
                    'TIMEZONE': 'UTC' # Assume UTC for ambiguous inputs, return UTC
                }
            )
            # dt is now a timezone-aware datetime in UTC if parsing was successful.

            # Compare dt (UTC) with now (UTC)
            if not dt or dt < now:
                continue  # Skip past reminders

            # Generate a unique job_id using UUID
            job_id = f"{chat_id}_{uuid.uuid4()}"
            # APScheduler's DateTrigger should receive the datetime in UTC
            trigger = DateTrigger(run_date=dt.astimezone(timezone.utc))
            scheduler.add_job(
                func=send_message,
                trigger=trigger,
                args=[chat_id, message],
                id=job_id
            )
            task_entries.append({"id": job_id, "task": task, "time": dt.isoformat(), "message": message})

        if task_entries:
            tasks.setdefault(chat_id, []).extend(task_entries)
            # Display reminder time in 'Asia/Kolkata'
            first_dt_utc_str = task_entries[0]["time"] # This is a UTC ISO string
            # Parse the UTC ISO string back to a UTC datetime object
            first_dt_utc = dateparser.parse(first_dt_utc_str, settings={'TIMEZONE': 'UTC', 'RETURN_AS_TIMEZONE_AWARE': True})

            if first_dt_utc:
                # Convert UTC time to 'Asia/Kolkata' for display
                # It's important that dateparser.parser.StaticTzInfo is available and works as expected.
                # If not, an alternative like pytz or ZoneInfo (Python 3.9+) would be needed.
                # For this exercise, we assume StaticTzInfo is fine.
                kolkata_tz = dateparser.parser.StaticTzInfo('Asia/Kolkata')
                first_dt_display = first_dt_utc.astimezone(kolkata_tz)
                display_time_str = first_dt_display.strftime('%Y-%m-%d %H:%M %Z')
                send_message(chat_id, f"✅ Task scheduled: *{task}* starting at {display_time_str}.")
            else:
                # Fallback if parsing the stored UTC string fails for some reason
                send_message(chat_id, f"✅ Task scheduled: *{task}*. Could not parse display time.")
        else:
            send_message(chat_id, "⚠️ All generated reminders were in the past. Task not scheduled.")

        return jsonify(ok=True)

    @app.route("/tasks", methods=["GET"])
    def list_tasks():
        chat_id_str = request.args.get("chat_id")

        if chat_id_str is None:
            return jsonify(error="chat_id parameter is required"), 400

        try:
            chat_id = int(chat_id_str)
        except ValueError:
            return jsonify(error="chat_id parameter must be an integer"), 400

        return jsonify(tasks.get(chat_id, []))

    return app

if __name__ == "__main__":
    app = create_app()
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)))
