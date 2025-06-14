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
                    "Extract the task and time from the message below. "
                    "Reply ONLY with a JSON object like this:\n"
                    "{\"task\": \"...\", \"time\": \"...\"}\n"
                    "If not possible, reply with: {\"task\": \"\", \"time\": \"\"}\n"
                    "DO NOT include any explanation or formatting.\n\n"
                    f"Message: '{user_input}'"
                )
            }]
        }]
    }
    try:
        resp = requests.post(url, json=prompt, headers=headers, timeout=10)
        resp.raise_for_status()
        raw = resp.json()
        try:
            text_block = raw["candidates"][0]["content"]["parts"][0]
            text = text_block["text"] if isinstance(text_block, dict) else text_block
            print("🔍 Gemini returned text:", text)
            result = json.loads(text)
        except (json.JSONDecodeError, KeyError) as e:
            print("⚠️ Error decoding Gemini response:", e)
            return {"task": "", "time": ""}

        return {
            "task": result.get("task", "").strip(),
            "time": result.get("time", "").strip()
        }

    except Exception as e:
        print("Gemini parsing error:", e)
        return {"task": "", "time": ""}