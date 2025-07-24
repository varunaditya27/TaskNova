import sqlite3
import json
from datetime import datetime
from typing import List, Dict, Optional
import os

class DatabaseManager:
    def __init__(self, db_path: str = "tasknova.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Initialize database with enhanced tables for God-tier features"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Enhanced tasks table with new AI-powered fields
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    chat_id INTEGER NOT NULL,
                    task_description TEXT NOT NULL,
                    base_time TEXT NOT NULL,
                    urgency_level TEXT DEFAULT 'MEDIUM',
                    task_category TEXT DEFAULT 'GENERAL',
                    estimated_duration INTEGER DEFAULT 30,
                    motivational_context TEXT DEFAULT '',
                    procrastination_shield BOOLEAN DEFAULT FALSE,
                    created_at TEXT NOT NULL,
                    status TEXT DEFAULT 'active'
                )
            ''')
            
            # Enhanced reminders table with psychological messaging data
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS reminders (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id INTEGER NOT NULL,
                    job_id TEXT UNIQUE NOT NULL,
                    reminder_time_utc TEXT NOT NULL,
                    reminder_time_user TEXT NOT NULL,
                    message TEXT NOT NULL,
                    reminder_type TEXT DEFAULT 'STANDARD',
                    priority_level TEXT DEFAULT 'medium',
                    status TEXT DEFAULT 'pending',
                    created_at TEXT NOT NULL,
                    sent_at TEXT NULL,
                    FOREIGN KEY (task_id) REFERENCES tasks (id) ON DELETE CASCADE
                )
            ''')
            
            # Add new columns to existing tables if they don't exist (migration support)
            self._migrate_database(cursor)
            
            # Enhanced indexes for optimal performance
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_chat_id ON tasks(chat_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_urgency_level ON tasks(urgency_level)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_task_category ON tasks(task_category)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_reminder_status ON reminders(status)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_reminder_type ON reminders(reminder_type)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_priority_level ON reminders(priority_level)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_job_id ON reminders(job_id)')
            
            conn.commit()
    
    def _migrate_database(self, cursor):
        """Handle database migrations for existing installations"""
        try:
            # Check if new columns exist, add them if they don't
            cursor.execute("PRAGMA table_info(tasks)")
            task_columns = [column[1] for column in cursor.fetchall()]
            
            if 'urgency_level' not in task_columns:
                cursor.execute('ALTER TABLE tasks ADD COLUMN urgency_level TEXT DEFAULT "MEDIUM"')
            if 'task_category' not in task_columns:
                cursor.execute('ALTER TABLE tasks ADD COLUMN task_category TEXT DEFAULT "GENERAL"')
            if 'estimated_duration' not in task_columns:
                cursor.execute('ALTER TABLE tasks ADD COLUMN estimated_duration INTEGER DEFAULT 30')
            if 'motivational_context' not in task_columns:
                cursor.execute('ALTER TABLE tasks ADD COLUMN motivational_context TEXT DEFAULT ""')
            if 'procrastination_shield' not in task_columns:
                cursor.execute('ALTER TABLE tasks ADD COLUMN procrastination_shield BOOLEAN DEFAULT FALSE')
            
            # Check reminders table
            cursor.execute("PRAGMA table_info(reminders)")
            reminder_columns = [column[1] for column in cursor.fetchall()]
            
            if 'reminder_type' not in reminder_columns:
                cursor.execute('ALTER TABLE reminders ADD COLUMN reminder_type TEXT DEFAULT "STANDARD"')
            if 'priority_level' not in reminder_columns:
                cursor.execute('ALTER TABLE reminders ADD COLUMN priority_level TEXT DEFAULT "medium"')
                
        except sqlite3.OperationalError as e:
            print(f"Migration warning: {e}")
    
    def save_task_with_reminders(self, chat_id: int, task_description: str, 
                               base_time: str, reminder_entries: List[Dict],
                               urgency_level: str = "MEDIUM", task_category: str = "GENERAL",
                               estimated_duration: int = 30, motivational_context: str = "",
                               procrastination_shield: bool = False) -> int:
        """
        Save a task and its associated reminders with enhanced AI metadata
        Returns the task_id for reference
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Insert enhanced task with AI-powered metadata
            cursor.execute('''
                INSERT INTO tasks 
                (chat_id, task_description, base_time, urgency_level, task_category, 
                 estimated_duration, motivational_context, procrastination_shield, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (chat_id, task_description, base_time, urgency_level, task_category, 
                  estimated_duration, motivational_context, procrastination_shield,
                  datetime.utcnow().isoformat()))
            
            task_id = cursor.lastrowid
            
            # Insert all enhanced reminders for this task
            for entry in reminder_entries:
                cursor.execute('''
                    INSERT INTO reminders 
                    (task_id, job_id, reminder_time_utc, reminder_time_user, message, 
                     reminder_type, priority_level, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    task_id,
                    entry['id'],
                    entry['time_utc'],
                    entry['time_user'],
                    entry['message'],
                    entry.get('type', 'STANDARD'),
                    entry.get('priority', 'medium'),
                    datetime.utcnow().isoformat()
                ))
            
            conn.commit()
            return task_id
    
    def get_pending_reminders(self) -> List[Dict]:
        """Get all reminders that haven't been sent yet with enhanced metadata"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT r.id, r.job_id, r.reminder_time_utc, r.message, r.reminder_type, 
                       r.priority_level, t.chat_id, t.task_description, t.urgency_level,
                       t.task_category, t.procrastination_shield
                FROM reminders r
                JOIN tasks t ON r.task_id = t.id
                WHERE r.status = 'pending'
                ORDER BY r.reminder_time_utc
            ''')
            
            columns = [desc[0] for desc in cursor.description]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]
    
    def mark_reminder_sent(self, job_id: str):
        """Mark a reminder as sent with timestamp"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE reminders 
                SET status = 'sent', sent_at = ?
                WHERE job_id = ?
            ''', (datetime.utcnow().isoformat(), job_id))
            conn.commit()
    
    def get_user_tasks(self, chat_id: int, limit: int = 10) -> List[Dict]:
        """Get recent tasks for a user with enhanced AI metadata"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT t.id, t.task_description, t.base_time, t.urgency_level, 
                       t.task_category, t.estimated_duration, t.motivational_context,
                       t.procrastination_shield, t.created_at,
                       COUNT(r.id) as total_reminders,
                       COUNT(CASE WHEN r.status = 'sent' THEN 1 END) as sent_reminders,
                       COUNT(CASE WHEN r.reminder_type = 'CRITICAL' THEN 1 END) as critical_reminders,
                       COUNT(CASE WHEN r.reminder_type = 'MOTIVATION' THEN 1 END) as motivation_reminders
                FROM tasks t
                LEFT JOIN reminders r ON t.id = r.task_id
                WHERE t.chat_id = ? AND t.status = 'active'
                GROUP BY t.id
                ORDER BY t.created_at DESC
                LIMIT ?
            ''', (chat_id, limit))
            
            columns = [desc[0] for desc in cursor.description]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]
    
    def get_task_analytics(self, chat_id: int) -> Dict:
        """Get advanced analytics for user's task patterns"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            analytics = {}
            
            # Task category distribution
            cursor.execute('''
                SELECT task_category, COUNT(*) as count
                FROM tasks 
                WHERE chat_id = ? AND created_at > datetime('now', '-30 days')
                GROUP BY task_category
                ORDER BY count DESC
            ''', (chat_id,))
            analytics['category_distribution'] = dict(cursor.fetchall())
            
            # Urgency level patterns
            cursor.execute('''
                SELECT urgency_level, COUNT(*) as count
                FROM tasks 
                WHERE chat_id = ? AND created_at > datetime('now', '-30 days')
                GROUP BY urgency_level
                ORDER BY count DESC
            ''', (chat_id,))
            analytics['urgency_patterns'] = dict(cursor.fetchall())
            
            # Procrastination shield usage
            cursor.execute('''
                SELECT procrastination_shield, COUNT(*) as count
                FROM tasks 
                WHERE chat_id = ? AND created_at > datetime('now', '-30 days')
                GROUP BY procrastination_shield
            ''', (chat_id,))
            analytics['procrastination_shield_usage'] = dict(cursor.fetchall())
            
            # Average estimated duration by category
            cursor.execute('''
                SELECT task_category, AVG(estimated_duration) as avg_duration
                FROM tasks 
                WHERE chat_id = ? AND created_at > datetime('now', '-30 days')
                GROUP BY task_category
            ''', (chat_id,))
            analytics['avg_duration_by_category'] = dict(cursor.fetchall())
            
            # Reminder effectiveness (completion rate)
            cursor.execute('''
                SELECT 
                    t.urgency_level,
                    COUNT(CASE WHEN t.status = 'completed' THEN 1 END) * 100.0 / COUNT(*) as completion_rate
                FROM tasks t
                WHERE t.chat_id = ? AND t.created_at > datetime('now', '-30 days')
                GROUP BY t.urgency_level
            ''', (chat_id,))
            analytics['completion_rate_by_urgency'] = dict(cursor.fetchall())
            
            return analytics
    
    def cleanup_old_tasks(self, days_old: int = 7):
        """Clean up completed tasks older than specified days with enhanced logic"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Mark tasks as completed where all reminders are sent
            cursor.execute('''
                UPDATE tasks 
                SET status = 'completed'
                WHERE id IN (
                    SELECT t.id FROM tasks t
                    LEFT JOIN reminders r ON t.id = r.task_id
                    WHERE t.status = 'active'
                    GROUP BY t.id
                    HAVING COUNT(r.id) > 0 AND COUNT(CASE WHEN r.status = 'pending' THEN 1 END) = 0
                )
            ''')
            
            # Delete very old completed tasks (preserve analytics data for recent tasks)
            cutoff_date = datetime.utcnow().replace(microsecond=0)
            cutoff_date = cutoff_date.replace(day=cutoff_date.day - days_old)
            
            cursor.execute('''
                DELETE FROM tasks 
                WHERE status = 'completed' AND created_at < ?
            ''', (cutoff_date.isoformat(),))
            
            deleted_count = cursor.rowcount
            conn.commit()
            return deleted_count
    
    def get_database_stats(self) -> Dict:
        """Get comprehensive database statistics for monitoring"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            stats = {}
            
            # Basic counts
            cursor.execute('SELECT status, COUNT(*) FROM tasks GROUP BY status')
            stats['tasks_by_status'] = dict(cursor.fetchall())
            
            cursor.execute('SELECT status, COUNT(*) FROM reminders GROUP BY status')
            stats['reminders_by_status'] = dict(cursor.fetchall())
            
            cursor.execute('SELECT COUNT(DISTINCT chat_id) FROM tasks')
            stats['unique_users'] = cursor.fetchone()[0]
            
            # Enhanced AI-powered stats
            cursor.execute('SELECT urgency_level, COUNT(*) FROM tasks GROUP BY urgency_level')
            stats['tasks_by_urgency'] = dict(cursor.fetchall())
            
            cursor.execute('SELECT task_category, COUNT(*) FROM tasks GROUP BY task_category')
            stats['tasks_by_category'] = dict(cursor.fetchall())
            
            cursor.execute('SELECT reminder_type, COUNT(*) FROM reminders GROUP BY reminder_type')
            stats['reminders_by_type'] = dict(cursor.fetchall())
            
            cursor.execute('SELECT priority_level, COUNT(*) FROM reminders GROUP BY priority_level')
            stats['reminders_by_priority'] = dict(cursor.fetchall())
            
            cursor.execute('SELECT AVG(estimated_duration) FROM tasks WHERE estimated_duration > 0')
            avg_duration = cursor.fetchone()[0]
            stats['average_task_duration'] = round(avg_duration, 2) if avg_duration else 0
            
            cursor.execute('SELECT COUNT(*) FROM tasks WHERE procrastination_shield = 1')
            stats['procrastination_shield_activations'] = cursor.fetchone()[0]
            
            # Performance metrics
            cursor.execute('''
                SELECT AVG(
                    CASE WHEN t.status = 'completed' THEN 1.0 ELSE 0.0 END
                ) * 100 as completion_rate
                FROM tasks t
                WHERE t.created_at > datetime('now', '-30 days')
            ''')
            completion_rate = cursor.fetchone()[0]
            stats['30_day_completion_rate'] = round(completion_rate, 2) if completion_rate else 0
            
            return stats
    
    def get_user_productivity_insights(self, chat_id: int) -> Dict:
        """Generate personalized productivity insights for a user"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            insights = {}
            
            # Most productive time patterns
            cursor.execute('''
                SELECT 
                    strftime('%H', datetime(base_time)) as hour,
                    COUNT(*) as task_count,
                    AVG(CASE WHEN status = 'completed' THEN 1.0 ELSE 0.0 END) as success_rate
                FROM tasks 
                WHERE chat_id = ? AND created_at > datetime('now', '-30 days')
                GROUP BY hour
                ORDER BY success_rate DESC, task_count DESC
                LIMIT 3
            ''', (chat_id,))
            insights['peak_productivity_hours'] = cursor.fetchall()
            
            # Preferred task categories
            cursor.execute('''
                SELECT task_category, COUNT(*) as frequency
                FROM tasks 
                WHERE chat_id = ? AND created_at > datetime('now', '-30 days')
                GROUP BY task_category
                ORDER BY frequency DESC
                LIMIT 5
            ''', (chat_id,))
            insights['preferred_categories'] = cursor.fetchall()
            
            # Procrastination patterns
            cursor.execute('''
                SELECT 
                    urgency_level,
                    AVG(CASE WHEN procrastination_shield = 1 THEN 1.0 ELSE 0.0 END) as shield_usage_rate
                FROM tasks 
                WHERE chat_id = ? AND created_at > datetime('now', '-30 days')
                GROUP BY urgency_level
            ''', (chat_id,))
            insights['procrastination_patterns'] = cursor.fetchall()
            
            return insights