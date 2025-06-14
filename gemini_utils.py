import os
import json
import requests
from datetime import datetime
import pytz

# Timezone constants
USER_TIMEZONE = pytz.timezone('Asia/Kolkata')

def extract_task_plan(user_input: str, current_time: datetime) -> dict:
    """
    Calls Google Gemini API to extract a smart reminder plan from user input and current time.
    
    Args:
        user_input: User's reminder request
        current_time: Current time in user's timezone (Asia/Kolkata)
    
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

    # Format current time for Gemini - include timezone info for clarity
    if current_time.tzinfo is None:
        # If naive datetime, assume it's in user timezone
        current_time = USER_TIMEZONE.localize(current_time)
    
    # Convert to user timezone if not already
    if current_time.tzinfo != USER_TIMEZONE:
        current_time = current_time.astimezone(USER_TIMEZONE)
    
    # Format time with timezone info for Gemini
    formatted_time = current_time.strftime("%Y-%m-%d %H:%M:%S IST")
    iso_time = current_time.isoformat()
    
    prompt = {
        "contents": [
            {
                "parts": [
                    {
                        "text": (
                            f"You are a productivity assistant that creates smart reminder plans.\n"
                            f"Current time is: {formatted_time} (India Standard Time)\n"
                            f"Current time ISO: {iso_time}\n\n"
                            f"User just sent a reminder request: \"{user_input}\"\n\n"
                            f"IMPORTANT INSTRUCTIONS:\n"
                            f"1. All times should be interpreted relative to India Standard Time (IST/Asia/Kolkata)\n"
                            f"2. When user says 'tonight', 'tomorrow', 'today', calculate relative to IST\n"
                            f"3. Extract the task clearly\n"
                            f"4. Determine base_time (when task is due) in ISO 8601 format with +05:30 timezone\n"
                            f"5. Create 2-5 appropriate reminders based on urgency:\n"
                            f"   - For tasks due within 2 hours: 2-3 reminders (30min, 10min before)\n"
                            f"   - For tasks due within 24 hours: 3-4 reminders (4hr, 1hr, 15min before)\n"
                            f"   - For tasks due later: 4-5 reminders (1day, 3hr, 30min before)\n"
                            f"6. Make reminders progressively more urgent in tone\n"
                            f"7. All reminder times must be in ISO 8601 format with +05:30 timezone offset\n\n"
                            f"Return ONLY a JSON object like this:\n"
                            f"{{\n"
                            f"  \"task\": \"Complete assignment\",\n"
                            f"  \"base_time\": \"2025-06-14T20:00:00+05:30\",\n"
                            f"  \"reminders\": [\n"
                            f"    {{\"time\": \"2025-06-14T19:30:00+05:30\", \"message\": \"📝 Gentle reminder: Complete assignment in 30 minutes\"}},\n"
                            f"    {{\"time\": \"2025-06-14T19:50:00+05:30\", \"message\": \"⏰ Time's running out! Complete assignment in 10 minutes\"}},\n"
                            f"    {{\"time\": \"2025-06-14T20:00:00+05:30\", \"message\": \"🚨 DEADLINE NOW! Time to complete assignment!\"}}\n"
                            f"  ]\n"
                            f"}}\n\n"
                            f"If task or time is unclear, return empty values. Do not explain anything."
                        )
                    }
                ]
            }
        ]
    }

    try:
        resp = requests.post(url, json=prompt, headers=headers, timeout=15)
        resp.raise_for_status()
        raw = resp.json()

        # Handle Gemini response format
        if "candidates" in raw and len(raw["candidates"]) > 0:
            content = raw["candidates"][0]["content"]
            if "parts" in content and len(content["parts"]) > 0:
                text_block = content["parts"][0]
                text = text_block.get("text", "") if isinstance(text_block, dict) else str(text_block)
                
                # Clean up the text (remove markdown code blocks if present)
                text = text.strip()
                if text.startswith("```json"):
                    text = text[7:]
                if text.endswith("```"):
                    text = text[:-3]
                text = text.strip()
                
                print("🔍 Gemini returned text:", text)
                
                # Parse JSON response
                result = json.loads(text)
                
                return {
                    "task": result.get("task", "").strip(),
                    "base_time": result.get("base_time", "").strip(),
                    "reminders": result.get("reminders", [])
                }
            else:
                print("No parts in Gemini response content")
        else:
            print("No candidates in Gemini response")

    except json.JSONDecodeError as e:
        print(f"JSON parsing error: {e}")
        print(f"Raw text: {text if 'text' in locals() else 'No text available'}")
    except requests.exceptions.RequestException as e:
        print(f"Gemini API request error: {e}")
    except Exception as e:
        print(f"Gemini smart planning error: {e}")

    # Return empty result on any error
    return {"task": "", "base_time": "", "reminders": []}