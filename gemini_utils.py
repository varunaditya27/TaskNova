import os
import json
import requests
from datetime import datetime, timedelta
import pytz

# Timezone constants
USER_TIMEZONE = pytz.timezone('Asia/Kolkata')

def extract_task_plan(user_input: str, current_time: datetime) -> dict:
    """
    Calls Google Gemini API with an enhanced, legendary prompt for God-tier task planning.
    
    Args:
        user_input: User's reminder request
        current_time: Current time in user's timezone (Asia/Kolkata)
    
    Returns a dict:
    {
        "task": str,
        "base_time": str (ISO 8601),
        "urgency_level": str,
        "task_category": str,
        "estimated_duration": int (minutes),
        "reminders": [
            {"time": str (ISO 8601), "message": str, "type": str, "priority": str},
            ...
        ],
        "motivational_context": str,
        "procrastination_shield": bool
    }
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("ERROR: GEMINI_API_KEY environment variable is required")
        return {
            "task": "", 
            "base_time": "", 
            "urgency_level": "MEDIUM",
            "task_category": "GENERAL",
            "estimated_duration": 30,
            "reminders": [],
            "motivational_context": "",
            "procrastination_shield": False
        }
    url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"
    headers = {
        "Content-Type": "application/json",
        "x-goog-api-key": api_key
    }

    # Format current time for Gemini - include timezone info for clarity
    if current_time.tzinfo is None:
        current_time = USER_TIMEZONE.localize(current_time)
    
    if current_time.tzinfo != USER_TIMEZONE:
        current_time = current_time.astimezone(USER_TIMEZONE)
    
    # Calculate contextual time references
    formatted_time = current_time.strftime("%Y-%m-%d %H:%M:%S IST")
    iso_time = current_time.isoformat()
    weekday = current_time.strftime("%A")
    hour = current_time.hour
    
    # Determine time context for smarter scheduling
    time_context = "morning" if 5 <= hour < 12 else "afternoon" if 12 <= hour < 17 else "evening" if 17 <= hour < 22 else "night"
    
    prompt = {
        "contents": [
            {
                "parts": [
                    {
                        "text": (
                            f"🧠 **LEGENDARY AI PRODUCTIVITY ARCHITECT** 🧠\n"
                            f"You are TaskNova's elite AI brain - the world's most sophisticated task planning system.\n"
                            f"Your mission: Transform chaotic human intentions into bulletproof execution plans.\n\n"
                            
                            f"⏰ **TEMPORAL CONTEXT**\n"
                            f"Current time: {formatted_time} (India Standard Time)\n"
                            f"ISO format: {iso_time}\n"
                            f"Day: {weekday} {time_context}\n"
                            f"Human circadian state: {'Peak focus' if 9 <= hour <= 11 or 14 <= hour <= 16 else 'Moderate focus' if 8 <= hour <= 17 else 'Low energy'}\n\n"
                            
                            f"📝 **USER REQUEST ANALYSIS**\n"
                            f"Raw input: \"{user_input}\"\n\n"
                            
                            f"🎯 **YOUR LEGENDARY CAPABILITIES**\n"
                            f"1. **PSYCHO-LINGUISTIC PARSING**: Decode not just what they said, but what they MEANT\n"
                            f"2. **TEMPORAL INTELLIGENCE**: Master of time perception, deadline psychology, and urgency dynamics\n"
                            f"3. **BEHAVIORAL PREDICTION**: Anticipate procrastination patterns and motivation decay\n"
                            f"4. **CONTEXTUAL AWARENESS**: Factor in time of day, day of week, and human energy cycles\n"
                            f"5. **ADAPTIVE MESSAGING**: Craft messages that evolve in tone, urgency, and psychological impact\n\n"
                            
                            f"🔬 **ANALYSIS FRAMEWORK**\n"
                            f"Step 1: EXTRACT core task with surgical precision\n"
                            f"Step 2: DECODE temporal indicators (explicit and implicit)\n"
                            f"Step 3: ASSESS urgency level and procrastination risk\n"
                            f"Step 4: CATEGORIZE task type for optimal reminder strategy\n"
                            f"Step 5: ESTIMATE realistic completion time\n"
                            f"Step 6: ARCHITECT multi-layer reminder sequence\n\n"
                            
                            f"⚡ **URGENCY CLASSIFICATION SYSTEM**\n"
                            f"• CRITICAL: <2 hours remaining (Code Red)\n"
                            f"• HIGH: 2-8 hours remaining (Alert)\n"
                            f"• MEDIUM: 8-24 hours remaining (Standard)\n"
                            f"• LOW: 1-7 days remaining (Planning)\n"
                            f"• BACKGROUND: >7 days remaining (Strategic)\n\n"
                            
                            f"📚 **TASK CATEGORY INTELLIGENCE**\n"
                            f"• ACADEMIC: assignments, studying, exams, projects\n"
                            f"• WORK: meetings, deadlines, presentations, calls\n"
                            f"• PERSONAL: health, relationships, self-care, hobbies\n"
                            f"• ADMINISTRATIVE: bills, appointments, documentation\n"
                            f"• CREATIVE: writing, design, brainstorming, innovation\n"
                            f"• MAINTENANCE: cleaning, repairs, routine tasks\n\n"
                            
                            f"🧬 **REMINDER DNA SEQUENCES**\n"
                            f"Each reminder type has unique psychological properties:\n"
                            f"• MOTIVATION: Inspiring, energizing, vision-focused\n"
                            f"• PREPARATION: Practical, action-oriented, resource-gathering\n"
                            f"• URGENCY: Time-pressure, consequence-aware, immediate action\n"
                            f"• ACCOUNTABILITY: Social pressure, commitment-based, guilt-free motivation\n"
                            f"• CELEBRATION: Achievement-focused, reward-oriented, completion joy\n\n"
                            
                            f"🎭 **ADAPTIVE MESSAGING PSYCHOLOGY**\n"
                            f"Craft messages that:\n"
                            f"• Start gentle and encouraging (build momentum)\n"
                            f"• Escalate strategically (avoid alarm fatigue)\n"
                            f"• Use power words and emojis for emotional impact\n"
                            f"• Include specific actions, not just reminders\n"
                            f"• Reference benefits and consequences naturally\n"
                            f"• Maintain positive tone even under pressure\n\n"
                            
                            f"🛡️ **PROCRASTINATION SHIELD ACTIVATION**\n"
                            f"Deploy when task shows high procrastination risk:\n"
                            f"• Break large tasks into micro-actions\n"
                            f"• Add 'quick win' reminders before main task\n"
                            f"• Include environment setup reminders\n"
                            f"• Use social accountability language\n"
                            f"• Reference past successes and capabilities\n\n"
                            
                            f"🏗️ **REMINDER ARCHITECTURE PATTERNS**\n"
                            f"CRITICAL (0-2hrs): Every 20-30min, max intensity\n"
                            f"HIGH (2-8hrs): 3-4 reminders, escalating urgency\n"
                            f"MEDIUM (8-24hrs): 3-5 reminders, balanced approach\n"
                            f"LOW (1-7days): 4-6 reminders, preparation-focused\n"
                            f"BACKGROUND (7+days): 2-3 strategic checkpoints\n\n"
                            
                            f"⚗️ **OUTPUT SPECIFICATION**\n"
                            f"Return ONLY a perfectly formatted JSON object:\n"
                            f"{{\n"
                            f"  \"task\": \"Crystal clear task description\",\n"
                            f"  \"base_time\": \"2025-06-14T20:00:00+05:30\",\n"
                            f"  \"urgency_level\": \"HIGH|MEDIUM|LOW|CRITICAL|BACKGROUND\",\n"
                            f"  \"task_category\": \"ACADEMIC|WORK|PERSONAL|etc\",\n"
                            f"  \"estimated_duration\": 45,\n"
                            f"  \"reminders\": [\n"
                            f"    {{\n"
                            f"      \"time\": \"2025-06-14T19:00:00+05:30\",\n"
                            f"      \"message\": \"🎯 Power Hour Alert! Your DBMS revision session starts in 60 minutes. Grab your notes, find your focus zone, and prepare to dominate this material! 💪\",\n"
                            f"      \"type\": \"PREPARATION\",\n"
                            f"      \"priority\": \"medium\"\n"
                            f"    }},\n"
                            f"    {{\n"
                            f"      \"time\": \"2025-06-14T19:30:00+05:30\",\n"
                            f"      \"message\": \"⚡ Final 30 Minutes! Time to activate study mode. Clear your desk, silence distractions, and channel that inner academic warrior. You've got this! 🧠✨\",\n"
                            f"      \"type\": \"MOTIVATION\",\n"
                            f"      \"priority\": \"high\"\n"
                            f"    }},\n"
                            f"    {{\n"
                            f"      \"time\": \"2025-06-14T19:50:00+05:30\",\n"
                            f"      \"message\": \"🚨 T-minus 10 minutes! This is your moment. Open those books, fire up your brain, and let's make this revision session legendary! No more delays! 🔥\",\n"
                            f"      \"type\": \"URGENCY\",\n"
                            f"      \"priority\": \"critical\"\n"
                            f"    }},\n"
                            f"    {{\n"
                            f"      \"time\": \"2025-06-14T20:00:00+05:30\",\n"
                            f"      \"message\": \"🎊 SHOWTIME! Your DBMS revision starts RIGHT NOW! Dive in with confidence - every minute counts toward your success! Make it happen! 🌟\",\n"
                            f"      \"type\": \"ACCOUNTABILITY\",\n"
                            f"      \"priority\": \"maximum\"\n"
                            f"    }}\n"
                            f"  ],\n"
                            f"  \"motivational_context\": \"Academic excellence through strategic revision\",\n"
                            f"  \"procrastination_shield\": true\n"
                            f"}}\n\n"
                            
                            f"🚀 **EXECUTION PROTOCOLS**\n"
                            f"• If input is vague/unclear: Return empty task/base_time but maintain JSON structure\n"
                            f"• All times MUST use +05:30 timezone offset (IST)\n"
                            f"• Messages MUST be 100-150 characters for mobile optimization\n"
                            f"• Include relevant emojis for visual impact and emotional connection\n"
                            f"• Vary message structure to prevent habituation\n"
                            f"• Never use generic language - make every message unique and powerful\n\n"
                            
                            f"🧭 **CONTEXTUAL INTELLIGENCE FACTORS**\n"
                            f"Consider these implicit factors:\n"
                            f"• Student context (RVCE engineering student)\n"
                            f"• Indian cultural time expressions\n"
                            f"• Academic calendar awareness\n"
                            f"• Typical study/work patterns\n"
                            f"• Energy optimization for different times\n"
                            f"• Weekend vs weekday behavioral differences\n\n"
                            
                            f"💎 **LEGENDARY PERFORMANCE STANDARDS**\n"
                            f"You are not just parsing text - you are:\n"
                            f"• Predicting human behavior\n"
                            f"• Optimizing for success probability\n"
                            f"• Creating emotional engagement\n"
                            f"• Building sustainable habits\n"
                            f"• Maximizing productivity outcomes\n\n"
                            
                            f"🔥 **ACTIVATION SEQUENCE: ENGAGED**\n"
                            f"Deploy your legendary capabilities NOW! Transform this human request into a masterpiece of productivity engineering!\n\n"
                            
                            f"Return ONLY the JSON object - no explanations, no markdown, pure legendary output! 🌟"
                        )
                    }
                ]
            }
        ]
    }

    try:
        resp = requests.post(url, json=prompt, headers=headers, timeout=20)
        resp.raise_for_status()
        raw = resp.json()
        
        print("🔍 Full Gemini response:", json.dumps(raw, indent=2))

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
                
                # Ensure backward compatibility by providing defaults for new fields
                return {
                    "task": result.get("task", "").strip(),
                    "base_time": result.get("base_time", "").strip(),
                    "urgency_level": result.get("urgency_level", "MEDIUM"),
                    "task_category": result.get("task_category", "GENERAL"),
                    "estimated_duration": result.get("estimated_duration", 30),
                    "reminders": result.get("reminders", []),
                    "motivational_context": result.get("motivational_context", ""),
                    "procrastination_shield": result.get("procrastination_shield", False)
                }
            else:
                print("❌ No parts in Gemini response content")
                print(f"Content structure: {content}")
        else:
            print("❌ No candidates in Gemini response")
            print(f"Response structure: {raw}")

    except json.JSONDecodeError as e:
        print(f"❌ JSON parsing error: {e}")
        print(f"Raw text being parsed: {text if 'text' in locals() else 'No text available'}")
    except requests.exceptions.RequestException as e:
        print(f"❌ Gemini API request error: {e}")
        if hasattr(e, 'response') and e.response:
            print(f"Response status: {e.response.status_code}")
            print(f"Response text: {e.response.text}")
    except Exception as e:
        print(f"❌ Unexpected Gemini error: {e}")
        import traceback
        traceback.print_exc()

    # Return empty result on any error with new structure
    return {
        "task": "", 
        "base_time": "", 
        "urgency_level": "MEDIUM",
        "task_category": "GENERAL",
        "estimated_duration": 30,
        "reminders": [],
        "motivational_context": "",
        "procrastination_shield": False
    }