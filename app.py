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
        now = datetime.now(timezone.utc).astimezone()

        parsed = extract_task_plan(text, now)
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
            dt = dateparser.parse(
                time_str,
                settings={
                    'TIMEZONE': 'Asia/Kolkata',
                    'RETURN_AS_TIMEZONE_AWARE': True
                }
            )
            if dt:
                dt = dt.astimezone()
            if not dt or dt < now:
                continue  # Skip past reminders

            job_id = f"{chat_id}_{len(tasks.get(chat_id, [])) + idx + 1}"
            trigger = DateTrigger(run_date=dt)
            scheduler.add_job(
                func=send_message,
                trigger=trigger,
                args=[chat_id, message],
                id=job_id
            )
            task_entries.append({"id": job_id, "task": task, "time": dt.isoformat(), "message": message})

        if task_entries:
            tasks.setdefault(chat_id, []).extend(task_entries)
            first_dt = dateparser.parse(task_entries[0]["time"], settings={'TIMEZONE': 'UTC', 'TO_TIMEZONE': 'Asia/Kolkata'})
            send_message(chat_id, f"✅ Task scheduled: *{task}* starting at {first_dt.strftime('%Y-%m-%d %H:%M')}.")
        else:
            send_message(chat_id, "⚠️ All generated reminders were in the past. Task not scheduled.")

        return jsonify(ok=True)

    @app.route("/tasks", methods=["GET"])
    def list_tasks():
        chat_id = int(request.args.get("chat_id", 0))
        return jsonify(tasks.get(chat_id, []))

    return app

if __name__ == "__main__":
    app = create_app()
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)))
