import os
import json
import requests
from datetime import datetime


def extract_task_plan(user_input: str, now: datetime) -> dict:
    """
    Calls Google Gemini API to extract a smart reminder plan from user input and current time.
    Returns a dict:
    {
        "task": str,
        "base_time": str (ISO 8601),
        "reminders": [
            {"time": str (ISO 8601), "message": str},
            ...
        ]
    }
    """
    api_key = os.getenv("GEMINI_API_KEY")
    url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"
    headers = {
        "Content-Type": "application/json",
        "x-goog-api-key": api_key
    }

    iso_now = now.strftime("%Y-%m-%dT%H:%M:%SZ")
    prompt = {
        "contents": [
            {
                "parts": [
                    {
                        "text": (
                            f"You are a productivity assistant that creates smart reminder plans.\\n"
                            f"Current time is: {iso_now}\\n\\n"
                            f"User just sent a reminder request: \"{user_input}\"\\n\\n"
                            f"You must:\n"
                            f"1. Extract the task.\n"
                            f"2. Determine base_time (when task is due).\n"
                            f"3. Create 2-5 appropriate reminders (depending on urgency).\n"
                            f"Reminders must be smart: early ones gentle, later ones assertive.\\n"
                            f"Return ONLY a JSON like this:\n"
                            f"{{\\n  \"task\": \"...\",\n  \"base_time\": \"...\",\n  \"reminders\": [\n    {{\"time\": \"...\", \"message\": \"...\"}},\n    ...\n  ]\n}}\\n"
                            f"All times should be in ISO 8601 format with 'Z' for UTC.\\n"
                            f"If task or time is unclear, return empty values. Do not explain anything."
                        )
                    }
                ]
            }
        ]
    }

    try:
        resp = requests.post(url, json=prompt, headers=headers, timeout=10)
        resp.raise_for_status()
        raw = resp.json()

        text_block = raw["candidates"][0]["content"]["parts"][0]
        text = text_block["text"] if isinstance(text_block, dict) else text_block
        print("🔍 Gemini returned text:", text)

        result = json.loads(text)

        return {
            "task": result.get("task", "").strip(),
            "base_time": result.get("base_time", "").strip(),
            "reminders": result.get("reminders", [])
        }

    except Exception as e:
        print("Gemini smart planning error:", e)
        return {"task": "", "base_time": "", "reminders": []}
