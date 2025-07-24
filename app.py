import os
import logging
from flask import Flask, request, jsonify
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.date import DateTrigger
from dotenv import load_dotenv
from gemini_utils import extract_task_plan
from database import DatabaseManager
import requests
from datetime import datetime, timezone
import dateparser
import pytz
import atexit

# Load environment variables
load_dotenv()

# Timezone constants - Single source of truth
USER_TIMEZONE = pytz.timezone('Asia/Kolkata')
UTC = pytz.UTC

def get_current_time_in_user_tz():
    """Get current time in user's timezone (Asia/Kolkata)"""
    return datetime.now(USER_TIMEZONE)

def get_current_time_utc():
    """Get current time in UTC"""
    return datetime.now(UTC)

def convert_to_utc(dt):
    """Convert any timezone-aware datetime to UTC"""
    if dt.tzinfo is None:
        # If naive datetime, assume it's in user timezone
        dt = USER_TIMEZONE.localize(dt)
    return dt.astimezone(UTC)

def convert_to_user_tz(dt):
    """Convert any timezone-aware datetime to user timezone"""
    if dt.tzinfo is None:
        # If naive datetime, assume it's in UTC
        dt = UTC.localize(dt)
    return dt.astimezone(USER_TIMEZONE)

def parse_time_string(time_str, reference_time=None):
    """
    Parse time string with consistent timezone handling
    Returns UTC datetime object
    """
    if reference_time is None:
        reference_time = get_current_time_in_user_tz()
    
    # Parse relative to user timezone
    parsed_dt = dateparser.parse(
        time_str,
        settings={
            'TIMEZONE': 'Asia/Kolkata',
            'RETURN_AS_TIMEZONE_AWARE': True,
            'RELATIVE_BASE': reference_time
        }
    )
    
    if parsed_dt:
        return convert_to_utc(parsed_dt)
    return None

# Global database manager
db = DatabaseManager()

def create_app():
    app = Flask(__name__)
    logging.basicConfig(level=logging.INFO)

    BOT_TOKEN = os.getenv("BOT_TOKEN")
    TELEGRAM_URL = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

    # Initialize scheduler
    scheduler = BackgroundScheduler(timezone=UTC)
    scheduler.start()
    
    # Register cleanup function
    atexit.register(lambda: scheduler.shutdown())

    def send_message(chat_id: int, text: str, job_id: str = None):
        """
        Send message via Telegram and mark reminder as sent in database
        Enhanced with better formatting and error handling
        """
        try:
            response = requests.post(TELEGRAM_URL, json={
                "chat_id": chat_id, 
                "text": text,
                "parse_mode": "Markdown"  # Enable markdown for better formatting
            })
            response.raise_for_status()
            logging.info(f"✅ Message sent to {chat_id}: {text[:50]}...")
            
            # Mark reminder as sent in database
            if job_id:
                db.mark_reminder_sent(job_id)
                logging.info(f"✅ Reminder {job_id} marked as sent in database")
                
        except Exception as e:
            logging.error(f"🔥 Failed to send message to {chat_id}: {e}")
            # Try sending without markdown as fallback
            try:
                fallback_response = requests.post(TELEGRAM_URL, json={
                    "chat_id": chat_id, 
                    "text": text
                })
                fallback_response.raise_for_status()
                logging.info(f"✅ Fallback message sent to {chat_id}")
                if job_id:
                    db.mark_reminder_sent(job_id)
            except Exception as fallback_error:
                logging.error(f"🔥 Fallback message also failed: {fallback_error}")

    def restore_scheduled_jobs():
        """
        Restore all pending reminders from database on startup
        Enhanced with better logging and error handling
        """
        try:
            pending_reminders = db.get_pending_reminders()
            now_utc = get_current_time_utc()
            restored_count = 0
            skipped_count = 0
            
            for reminder in pending_reminders:
                reminder_time_utc = dateparser.parse(reminder['reminder_time_utc'])
                
                # Skip past reminders
                if reminder_time_utc <= now_utc:
                    logging.info(f"Skipping past reminder: {reminder['job_id']} ({reminder.get('reminder_type', 'STANDARD')})")
                    skipped_count += 1
                    continue
                
                try:
                    trigger = DateTrigger(run_date=reminder_time_utc)
                    scheduler.add_job(
                        func=send_message,
                        trigger=trigger,
                        args=[reminder['chat_id'], reminder['message'], reminder['job_id']],
                        id=reminder['job_id']
                    )
                    restored_count += 1
                    logging.info(f"✅ Restored {reminder.get('reminder_type', 'STANDARD')} job: {reminder['job_id']}")
                    
                except Exception as e:
                    logging.error(f"Failed to restore job {reminder['job_id']}: {e}")
            
            logging.info(f"🔄 Restored {restored_count} scheduled reminders, skipped {skipped_count} past reminders")
            
        except Exception as e:
            logging.error(f"Failed to restore jobs from database: {e}")

    # Restore jobs on startup
    restore_scheduled_jobs()

    @app.route("/", methods=["GET"])
    def home():
        """Enhanced home page with comprehensive stats"""
        try:
            stats = db.get_database_stats()
            return f"""
            🤖 <b>TaskNova - God-Tier AI Productivity System</b> 🤖
            
            📊 <b>System Stats:</b>
            • Active Users: {stats.get('unique_users', 0)}
            • Tasks by Status: {stats.get('tasks_by_status', {})}
            • Tasks by Urgency: {stats.get('tasks_by_urgency', {})}
            • Tasks by Category: {stats.get('tasks_by_category', {})}
            • Reminders by Type: {stats.get('reminders_by_type', {})}
            • Avg Task Duration: {stats.get('average_task_duration', 0)} minutes
            • Procrastination Shield Activations: {stats.get('procrastination_shield_activations', 0)}
            • 30-Day Completion Rate: {stats.get('30_day_completion_rate', 0)}%
            
            🚀 System Status: <b>LEGENDARY OPERATIONAL</b>
            """
        except Exception as e:
            return f"TaskNova is running! (Stats error: {e})"

    @app.route("/webhook", methods=["POST"])
    def webhook():
        """Enhanced webhook handler with God-tier AI integration"""
        try:
            data = request.get_json(force=True)
            logging.info("Webhook received: %s", data)
            
            if "message" not in data:
                return jsonify(ok=True)

            chat_id = data["message"]["chat"]["id"]
            text = data["message"].get("text", "")
            
            # Handle special commands
            if text.lower() in ['/start', '/help']:
                help_msg = (
                    "🤖 *Welcome to TaskNova - God-Tier AI Assistant!*\n\n"
                    "I'm your legendary productivity architect powered by advanced AI. "
                    "I don't just set reminders—I craft psychological masterpieces that "
                    "motivate, prepare, and optimize you for peak performance!\n\n"
                    "*🎯 What I Do:*\n"
                    "• Parse your natural language with psycho-linguistic intelligence\n"
                    "• Predict procrastination patterns and deploy countermeasures\n"
                    "• Create adaptive reminders that evolve in urgency and tone\n"
                    "• Optimize for your circadian rhythms and energy cycles\n\n"
                    "*📝 Examples:*\n"
                    "• 'Remind me to submit DBMS assignment by 8 PM tonight'\n"
                    "• 'Call mom in 30 minutes'\n"
                    "• 'Prepare for data structures exam tomorrow morning'\n"
                    "• 'Complete lab report by Friday evening'\n\n"
                    "*🎮 Commands:*\n"
                    "• `/mytasks` - View your recent tasks with AI insights\n"
                    "• `/analytics` - Get your productivity analytics\n"
                    "• `/insights` - Personalized productivity insights\n\n"
                    "Ready to achieve legendary productivity? Just tell me what you need to remember! 🚀"
                )
                send_message(chat_id, help_msg)
                return jsonify(ok=True)
            
            if text.lower() == '/mytasks':
                user_tasks = db.get_user_tasks(chat_id, limit=5)
                if not user_tasks:
                    send_message(chat_id, "📋 You have no active tasks. Ready to create something legendary?")
                else:
                    msg = "📋 *Your Recent Tasks (AI-Enhanced):*\n\n"
                    for task in user_tasks:
                        base_time = dateparser.parse(task['base_time'])
                        if base_time:
                            base_time_user = convert_to_user_tz(base_time)
                            time_str = base_time_user.strftime('%Y-%m-%d %I:%M %p IST')
                        else:
                            time_str = "Time not available"
                        
                        # Enhanced task display with AI metadata
                        urgency_emoji = {
                            'CRITICAL': '🚨', 'HIGH': '⚡', 'MEDIUM': '⏰', 
                            'LOW': '📅', 'BACKGROUND': '🌱'
                        }.get(task['urgency_level'], '⏰')
                        
                        category_emoji = {
                            'ACADEMIC': '📚', 'WORK': '💼', 'PERSONAL': '🏠',
                            'ADMINISTRATIVE': '📋', 'CREATIVE': '🎨', 'MAINTENANCE': '🔧'
                        }.get(task['task_category'], '📝')
                        
                        shield_indicator = '🛡️' if task['procrastination_shield'] else ''
                        
                        msg += f"{urgency_emoji} {category_emoji} *{task['task_description']}* {shield_indicator}\n"
                        msg += f"   ⏰ Due: {time_str}\n"
                        msg += f"   📊 Progress: {task['sent_reminders']}/{task['total_reminders']} reminders sent\n"
                        msg += f"   🎯 Category: {task['task_category']} | Duration: {task['estimated_duration']}min\n"
                        if task['motivational_context']:
                            msg += f"   💭 Context: _{task['motivational_context']}_\n"
                        msg += "\n"
                    
                send_message(chat_id, msg)
                return jsonify(ok=True)
            
            if text.lower() == '/analytics':
                analytics = db.get_task_analytics(chat_id)
                if not any(analytics.values()):
                    send_message(chat_id, "📊 No analytics data available yet. Create some tasks to see your patterns!")
                else:
                    msg = "📊 *Your Productivity Analytics (Last 30 Days):*\n\n"
                    
                    if analytics.get('category_distribution'):
                        msg += "*📚 Task Categories:*\n"
                        for category, count in analytics['category_distribution'].items():
                            msg += f"  • {category}: {count} tasks\n"
                        msg += "\n"
                    
                    if analytics.get('urgency_patterns'):
                        msg += "*⚡ Urgency Patterns:*\n"
                        for urgency, count in analytics['urgency_patterns'].items():
                            msg += f"  • {urgency}: {count} tasks\n"
                        msg += "\n"
                    
                    if analytics.get('completion_rate_by_urgency'):
                        msg += "*✅ Completion Rates by Urgency:*\n"
                        for urgency, rate in analytics['completion_rate_by_urgency'].items():
                            msg += f"  • {urgency}: {rate:.1f}%\n"
                        msg += "\n"
                    
                    shield_usage = analytics.get('procrastination_shield_usage', {})
                    if shield_usage.get(True, 0) > 0:
                        total_tasks = sum(shield_usage.values())
                        shield_rate = (shield_usage.get(True, 0) / total_tasks) * 100
                        msg += f"*🛡️ Procrastination Shield Usage:* {shield_rate:.1f}%\n\n"
                    
                    msg += "Keep up the legendary work! 🚀"
                    
                send_message(chat_id, msg)
                return jsonify(ok=True)
            
            if text.lower() == '/insights':
                insights = db.get_user_productivity_insights(chat_id)
                if not any(insights.values()):
                    send_message(chat_id, "🔮 Not enough data for personalized insights yet. Complete a few more tasks to unlock your productivity patterns!")
                else:
                    msg = "🔮 *Your Personalized Productivity Insights:*\n\n"
                    
                    # Peak productivity hours
                    if insights.get('peak_productivity_hours'):
                        msg += "*🌟 Your Peak Performance Hours:*\n"
                        for hour_data in insights['peak_productivity_hours']:
                            hour = int(hour_data[0])
                            success_rate = hour_data[2] * 100 if hour_data[2] else 0
                            time_label = f"{hour:02d}:00" if hour < 12 else f"{hour:02d}:00"
                            msg += f"  • {time_label} - {success_rate:.0f}% success rate\n"
                        msg += "\n"
                    
                    # Preferred categories
                    if insights.get('preferred_categories'):
                        msg += "*📊 Your Favorite Task Types:*\n"
                        for category, frequency in insights['preferred_categories']:
                            msg += f"  • {category}: {frequency} tasks\n"
                        msg += "\n"
                    
                    # Procrastination patterns
                    if insights.get('procrastination_patterns'):
                        msg += "*🛡️ Procrastination Shield Patterns:*\n"
                        for urgency, shield_rate in insights['procrastination_patterns']:
                            shield_percentage = shield_rate * 100 if shield_rate else 0
                            msg += f"  • {urgency} tasks: {shield_percentage:.0f}% shield usage\n"
                        msg += "\n"
                    
                    msg += "*💡 AI Recommendation:* Schedule important tasks during your peak hours for maximum success! 🚀"
                    
                send_message(chat_id, msg)
                return jsonify(ok=True)
            
            # Get current time in user timezone for context
            now_user_tz = get_current_time_in_user_tz()
            now_utc = get_current_time_utc()
            
            # Enhanced AI processing with legendary prompt
            parsed = extract_task_plan(text, now_user_tz)
            task = parsed.get("task")
            base_time_str = parsed.get("base_time")
            reminders = parsed.get("reminders", [])
            
            # Extract enhanced AI metadata
            urgency_level = parsed.get("urgency_level", "MEDIUM")
            task_category = parsed.get("task_category", "GENERAL")
            estimated_duration = parsed.get("estimated_duration", 30)
            motivational_context = parsed.get("motivational_context", "")
            procrastination_shield = parsed.get("procrastination_shield", False)

            if not task or not base_time_str or not reminders:
                error_msg = (
                    "⚠️ I couldn't quite understand your request. Let me help you!\n\n"
                    "*Try these formats:*\n"
                    "• 'Remind me to [task] by [time]'\n"
                    "• '[Task] in [duration]'\n"
                    "• '[Task] at [specific time]'\n\n"
                    "*Examples:*\n"
                    "• 'Submit assignment by 8 PM tonight'\n"
                    "• 'Call mom in 30 minutes'\n"
                    "• 'Study for exam tomorrow at 2 PM'\n\n"
                    "I'm ready to create something legendary! 🚀"
                )
                send_message(chat_id, error_msg)
                return jsonify(ok=True)

            task_entries = []

            for idx, reminder in enumerate(reminders):
                time_str = reminder.get("time")
                message = reminder.get("message")
                reminder_type = reminder.get("type", "STANDARD")
                priority = reminder.get("priority", "medium")
                
                # Parse reminder time consistently
                dt_utc = parse_time_string(time_str, now_user_tz)
                
                if not dt_utc or dt_utc < now_utc:
                    logging.warning(f"Skipping past reminder: {time_str}")
                    continue  # Skip past reminders

                try:
                    job_id = f"{chat_id}_{int(now_utc.timestamp())}_{idx}"
                    trigger = DateTrigger(run_date=dt_utc)  # Schedule in UTC
                    
                    scheduler.add_job(
                        func=send_message,
                        trigger=trigger,
                        args=[chat_id, message, job_id],
                        id=job_id
                    )
                    
                    task_entries.append({
                        "id": job_id, 
                        "task": task, 
                        "time_utc": dt_utc.isoformat(), 
                        "time_user": convert_to_user_tz(dt_utc).isoformat(),
                        "message": message,
                        "type": reminder_type,
                        "priority": priority
                    })
                    
                except Exception as e:
                    logging.error(f"Failed to schedule job {job_id}: {e}")
                    continue

            if task_entries:
                # Save to database with enhanced AI metadata
                try:
                    task_id = db.save_task_with_reminders(
                        chat_id=chat_id,
                        task_description=task,
                        base_time=base_time_str,
                        reminder_entries=task_entries,
                        urgency_level=urgency_level,
                        task_category=task_category,
                        estimated_duration=estimated_duration,
                        motivational_context=motivational_context,
                        procrastination_shield=procrastination_shield
                    )
                    logging.info(f"✅ Enhanced task {task_id} saved with {len(task_entries)} AI-powered reminders")
                except Exception as e:
                    logging.error(f"Failed to save task to database: {e}")
                    send_message(chat_id, "⚠️ Task scheduled but couldn't save to database. Reminders may not persist across restarts.")
                
                # Enhanced confirmation message with AI insights
                first_reminder_utc = dateparser.parse(task_entries[0]["time_utc"])
                first_reminder_user = convert_to_user_tz(first_reminder_utc)
                
                reminder_times = []
                reminder_types = []
                for entry in task_entries:
                    entry_utc = dateparser.parse(entry["time_utc"])
                    entry_user = convert_to_user_tz(entry_utc)
                    reminder_times.append(entry_user.strftime('%I:%M %p'))
                    reminder_types.append(entry.get('type', 'STANDARD'))
                
                # Build enhanced confirmation with AI metadata
                urgency_emoji = {
                    'CRITICAL': '🚨', 'HIGH': '⚡', 'MEDIUM': '⏰', 
                    'LOW': '📅', 'BACKGROUND': '🌱'
                }.get(urgency_level, '⏰')
                
                category_emoji = {
                    'ACADEMIC': '📚', 'WORK': '💼', 'PERSONAL': '🏠',
                    'ADMINISTRATIVE': '📋', 'CREATIVE': '🎨', 'MAINTENANCE': '🔧'
                }.get(task_category, '📝')
                
                response_msg = (
                    f"✅ *LEGENDARY TASK SCHEDULED* ✅\n\n"
                    f"{urgency_emoji} {category_emoji} *Task:* {task}\n"
                    f"🎯 *Category:* {task_category}\n"
                    f"⚡ *Urgency:* {urgency_level}\n"
                    f"⏱️ *Duration:* {estimated_duration} minutes\n"
                )
                
                if procrastination_shield:
                    response_msg += f"🛡️ *Procrastination Shield:* ACTIVATED\n"
                
                if motivational_context:
                    response_msg += f"💭 *Context:* _{motivational_context}_\n"
                
                response_msg += (
                    f"\n🕒 *AI-Crafted Reminders:*\n"
                    f"📅 Starting: {first_reminder_user.strftime('%Y-%m-%d %I:%M %p IST')}\n"
                    f"⏰ Times: {', '.join(reminder_times)}\n"
                    f"🎭 Types: {', '.join(set(reminder_types))}\n\n"
                    f"💾 *Secured in quantum database* - will persist across universe resets! 🌌\n\n"
                    f"🚀 Get ready for productivity at *legendary levels*! Your AI assistant has crafted the perfect reminder sequence to ensure your success! 💫"
                )
                
                send_message(chat_id, response_msg)
            else:
                send_message(chat_id, "⚠️ All generated reminders were in the past. Please specify a future time for your legendary task!")

        except Exception as e:
            logging.error(f"Webhook processing error: {e}")
            chat_id = data.get("message", {}).get("chat", {}).get("id", 0)
            if chat_id:
                send_message(chat_id, "🔥 Something went wrong in the AI matrix! Please try again with a clearer request.")

        return jsonify(ok=True)

    @app.route("/tasks", methods=["GET"])
    def list_tasks():
        """Enhanced task listing with AI metadata"""
        chat_id = int(request.args.get("chat_id", 0))
        limit = int(request.args.get("limit", 10))
        user_tasks = db.get_user_tasks(chat_id, limit)
        
        # Enhance response with AI metadata
        enhanced_tasks = []
        for task in user_tasks:
            enhanced_task = dict(task)
            enhanced_task['ai_enhanced'] = True
            enhanced_task['has_procrastination_shield'] = bool(task['procrastination_shield'])
            enhanced_tasks.append(enhanced_task)
        
        return jsonify({
            "tasks": enhanced_tasks,
            "total": len(enhanced_tasks),
            "ai_powered": True
        })
    
    @app.route("/stats", methods=["GET"])
    def stats():
        """Enhanced database statistics endpoint with AI metrics"""
        stats = db.get_database_stats()
        stats['ai_enhanced'] = True
        stats['legendary_mode'] = True
        return jsonify(stats)
    
    @app.route("/analytics/<int:chat_id>", methods=["GET"])
    def user_analytics(chat_id):
        """Get user analytics via API"""
        analytics = db.get_task_analytics(chat_id)
        return jsonify({
            "chat_id": chat_id,
            "analytics": analytics,
            "ai_powered": True
        })
    
    @app.route("/insights/<int:chat_id>", methods=["GET"])
    def user_insights(chat_id):
        """Get user productivity insights via API"""
        insights = db.get_user_productivity_insights(chat_id)
        return jsonify({
            "chat_id": chat_id,
            "insights": insights,
            "ai_powered": True
        })
    
    @app.route("/cleanup", methods=["POST"])
    def cleanup_old_tasks():
        """Enhanced cleanup endpoint with better reporting"""
        try:
            days_old = int(request.json.get("days_old", 7))
            deleted_count = db.cleanup_old_tasks(days_old=days_old)
            return jsonify({
                "status": "success", 
                "message": f"Cleaned up {deleted_count} old tasks",
                "deleted_tasks": deleted_count,
                "ai_optimized": True
            })
        except Exception as e:
            return jsonify({
                "status": "error", 
                "message": str(e),
                "ai_error_analysis": "Database cleanup failed"
            })

    @app.route("/health", methods=["GET"])
    def health_check():
        """Enhanced health check with system status"""
        try:
            stats = db.get_database_stats()
            pending_jobs = len(scheduler.get_jobs())
            
            return jsonify({
                "status": "LEGENDARY",
                "database": "Connected",
                "scheduler": f"{pending_jobs} jobs pending",
                "ai_system": "Fully Operational",
                "unique_users": stats.get('unique_users', 0),
                "total_tasks": sum(stats.get('tasks_by_status', {}).values()),
                "system_mode": "God-Tier Productivity Engine"
            })
        except Exception as e:
            return jsonify({
                "status": "ERROR",
                "message": str(e),
                "ai_diagnosis": "System requires attention"
            }), 500

    @app.teardown_appcontext
    def cleanup(error):
        if error:
            logging.error(f"App context error: {error}")

    return app

# Create the app instance for Gunicorn to find
app = create_app()

if __name__ == "__main__":
    # Only used for local development
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)), debug=False)