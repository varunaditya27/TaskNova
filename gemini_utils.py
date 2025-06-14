import os
import json
import logging
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
    if not api_key:
        logging.critical("GEMINI_API_KEY is not set or empty.")
        return {"task": "", "base_time": "", "reminders": []}

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

        # Validate response structure
        if not raw.get("candidates"):
            logging.error("Invalid API response: Missing 'candidates' key.")
            return {"task": "", "base_time": "", "reminders": []}

        candidates = raw["candidates"]
        if not isinstance(candidates, list) or len(candidates) == 0:
            logging.error("Invalid API response: 'candidates' is not a list or is empty.")
            return {"task": "", "base_time": "", "reminders": []}

        candidate = candidates[0]
        if not candidate.get("content"):
            logging.error("Invalid API response: Missing 'content' key in candidate.")
            return {"task": "", "base_time": "", "reminders": []}

        content = candidate["content"]
        if not content.get("parts"):
            logging.error("Invalid API response: Missing 'parts' key in content.")
            return {"task": "", "base_time": "", "reminders": []}

        parts = content["parts"]
        if not isinstance(parts, list) or len(parts) == 0: # This check is from previous implementation
            logging.error("Invalid API response: 'parts' is not a list or is empty.")
            return {"task": "", "base_time": "", "reminders": []}

        # New text extraction logic from requirement
        extracted_text = []
        for part in parts:
            if isinstance(part, dict) and "text" in part:
                extracted_text.append(part["text"])
            elif isinstance(part, str): # Fallback if a part is just a string
                extracted_text.append(part)

        if not extracted_text:
            logging.error("Gemini API response: No text found in 'parts'.")
            return {"task": "", "base_time": "", "reminders": []}

        # Assuming the relevant JSON content is in the first text block if multiple exist,
        # or they are concatenated if that's the desired behavior.
        # For this specific use case, the JSON block is expected to be the primary content.
        text = "".join(extracted_text)

        print("🔍 Gemini returned text:", text)

        result = json.loads(text)

        return {
            "task": result.get("task", "").strip(),
            "base_time": result.get("base_time", "").strip(),
            "reminders": result.get("reminders", [])
        }

    except requests.exceptions.RequestException as e:
        logging.error(f"API request failed: {type(e).__name__} - {e}")
        return {"task": "", "base_time": "", "reminders": []}
    except json.JSONDecodeError as e:
        logging.error(f"Failed to decode JSON response: {type(e).__name__} - {e}")
        return {"task": "", "base_time": "", "reminders": []}
    except Exception as e:
        logging.error(f"An unexpected error occurred: {type(e).__name__} - {e}")
        return {"task": "", "base_time": "", "reminders": []}
