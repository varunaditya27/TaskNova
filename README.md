# 🤖 TaskNova — Your AI-Powered Smart Reminder Agent

**TaskNova** is no longer just a reminder bot — it's your personal productivity agent powered by Google Gemini.
It doesn't just set a timer. It thinks. It plans. It adapts.

Say something like:

> "Remind me to complete my lab report before 8 PM tonight"

...and TaskNova will:

* Figure out what you need to do
* When you need to do it
* And intelligently schedule **multiple reminders** so you don't slack off or forget.

---

## 🧠 What It Does

* Parses natural language using **Gemini Pro**
* Extracts **task**, **deadline**, and plans **smart reminders**
* Schedules and sends reminders through **Telegram**
* Sends multiple nudges depending on task urgency (short/long deadlines)
* Handles vague times like "in 10 minutes" or "tomorrow evening"
* Super simple chat interface — no apps, no clutter

---

## 🛠 Tech Stack

* Python + Flask
* APScheduler for job scheduling
* Telegram Bot API
* Google Gemini Pro API (via Google AI Studio)
* Hosted on [Render](https://render.com/)

---

## 🚀 Getting Started

### 1. Clone the Repo

```bash
git clone https://github.com/<your-username>/tasknova.git
cd tasknova
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Set Environment Variables

Create a `.env` file:

```env
BOT_TOKEN=your_telegram_bot_token
GEMINI_API_KEY=your_gemini_api_key
```

### 4. Run Locally

```bash
python app.py
```

Your Flask server will run at `http://localhost:5000`

---

## 🌐 Deploying on Render

1. Push this repo to GitHub

2. Create a Web Service on Render

3. Connect your GitHub repo

4. Set build/start commands:

   * Build Command: `pip install -r requirements.txt`
   * Start Command: `python app.py`

5. Add environment variables (`BOT_TOKEN`, `GEMINI_API_KEY`) in Render's dashboard

6. Set your Telegram webhook using:

```bash
curl -X POST https://api.telegram.org/bot<YOUR_BOT_TOKEN>/setWebhook \
     -d url=https://your-render-url.onrender.com/webhook
```

---

## 📂 Project Structure

```
tasknova/
├── app.py              # Flask app
├── gemini_utils.py     # Handles Gemini API requests & smart planning
├── requirements.txt    # Python dependencies
├── render.yaml         # Optional: Render deployment config
└── .env                # Secrets (never commit this!)
```

---

## ⚡️ Example Interaction

> You: *"Remind me to revise DBMS unit 2 by 10 PM today"*

> Gemini thinks, calculates: "This is urgent. Let's send 3 reminders: 30 min before, 10 min before, and at the deadline."

> Bot:

```
✅ Task scheduled: Revise DBMS unit 2
🕒 Reminders will be sent at:
- 9:30 PM
- 9:50 PM
- 10:00 PM
```

> You: *"Set a reminder to water plants in 10 minutes"*

> Bot: *"✅ Got it! Smart reminder set."*

---

## 🙌 Author

Crafted with caffeine, memes, and Gemini by [Varun](https://github.com/varunaditya27)

---

## 📜 License

MIT — Use it, fork it, modify it, build something cooler with it. Just give credit where it's due. 😎
