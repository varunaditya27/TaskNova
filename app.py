import os
import logging
from flask import Flask, request, jsonify
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.date import DateTrigger
from dotenv import load_dotenv
from gemini_utils import extract_task_and_time
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

    # In-memory store: {chat_id: [{id, task, run_date}...]}
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

        # Extract task and time
        parsed = extract_task_and_time(text)
        task = parsed.get("task")
        time_str = parsed.get("time")

        if not task or not time_str:
            send_message(chat_id, "⚠️ Sorry, I couldn't understand your task/time. Try: 'Remind me to ... at ...'.")
            return jsonify(ok=True)

        # Parse time to datetime
        dt = dateparser.parse(
            time_str,
            settings={
                'TIMEZONE': 'Asia/Kolkata',
                'RETURN_AS_TIMEZONE_AWARE': True
            }
        )
        if dt:
            dt = dt.astimezone()  # Converts from IST to local (UTC on Render)

        if not dt or dt < datetime.now(timezone.utc):
            send_message(chat_id, "⚠️ The time you provided seems invalid or in the past.")
            return jsonify(ok=True)

        # Schedule job
        job_id = f"{chat_id}_{len(tasks.get(chat_id, [])) + 1}"
        trigger = DateTrigger(run_date=dt)
        scheduler.add_job(
            func=send_message,
            trigger=trigger,
            args=[chat_id, f"⏰ Reminder: {task}"],
            id=job_id
        )

        # Store task
        tasks.setdefault(chat_id, []).append({"id": job_id, "task": task, "time": dt.isoformat()})

        ist_datetime = dateparser.parse(str(dt), settings={'TIMEZONE': 'UTC', 'TO_TIMEZONE': 'Asia/Kolkata'})
        send_message(chat_id, f"✅ Task scheduled: *{task}* at {ist_datetime.strftime('%Y-%m-%d %H:%M')}.")
        return jsonify(ok=True)

    @app.route("/tasks", methods=["GET"])
    def list_tasks():
        chat_id = int(request.args.get("chat_id", 0))
        return jsonify(tasks.get(chat_id, []))

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)))