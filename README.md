# 🤖 TaskNova — Your AI-Powered Telegram Task Reminder Bot

**TaskNova** is your smart, snappy task companion that turns your casual thoughts like:

> "Remind me to revise Unit 3 before 6 PM tomorrow"

...into actionable, scheduled tasks with a little help from Google Gemini.

Talk like a human, get reminded like a boss.

---

## 🧠 What It Does

* Understands natural task instructions (LLM-powered)
* Extracts the **task** and **time**
* Confirms with the user
* \[Coming Soon] Sends reminder notifications
* Works right inside Telegram

---

## 🛠 Tech Stack

* Python + Flask
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
5. Add environment variables (`BOT_TOKEN`, `GEMINI_API_KEY`) in the dashboard
6. Set webhook using:

```bash
curl -X POST https://api.telegram.org/bot<YOUR_BOT_TOKEN>/setWebhook \
     -d url=https://your-render-url.onrender.com/webhook
```

---

## 📂 Project Structure

```
tasknova/
├── app.py            # Flask app
├── gemini_utils.py   # Gemini LLM logic
├── requirements.txt  # Python deps
├── render.yaml       # Render config (optional)
└── .env              # Your secret sauce
```

---

## 🙌 Author

Made with ☕ and late-night chaos by [Varun](https://github.com/<your-username>)

---

## 📜 License

MIT — Use it, fork it, enhance it. Just don’t forget to give credit if it helps.
