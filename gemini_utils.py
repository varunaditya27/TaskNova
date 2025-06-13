import os
import json
import requests

def extract_task_and_time(user_input: str) -> dict:
    """
    Calls Google Gemini API to extract task and time from user input.
    Returns a dict: {"task": str, "time": str}.
    """
    api_key = os.getenv("GEMINI_API_KEY")
    url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"
    headers = {
        "Content-Type": "application/json",
        "x-goog-api-key": api_key
    }
    prompt = {
        "contents": [{
            "parts": [{
                "text": (
                    f"Extract the task and time from this message and reply ONLY with valid JSON.\n"
                    f"Return JSON with keys 'task' and 'time'.\n"
                    f"If unable to parse, return {{'task': '', 'time': ''}}.\n\n"
                    f"Message: '{user_input}'"
                )
            }]
        }]
    }
    try:
        resp = requests.post(url, json=prompt, headers=headers, timeout=10)
        resp.raise_for_status()
        text = resp.json()["candidates"][0]["content"]["parts"][0]
        # Parse JSON safely
        data = text.get("text") if isinstance(text, dict) else text
        result = json.loads(data)
        return {
            "task": result.get("task", "").strip(),
            "time": result.get("time", "").strip()
        }
    except Exception as e:
        print("Gemini parsing error:", e)
        return {"task": "", "time": ""}