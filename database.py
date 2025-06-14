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
        """Initialize database with required tables"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Tasks table to store task information
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    chat_id INTEGER NOT NULL,
                    task_description TEXT NOT NULL,
                    base_time TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    status TEXT DEFAULT 'active'
                )
            ''')
            
            # Reminders table to store individual reminders for each task
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS reminders (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id INTEGER NOT NULL,
                    job_id TEXT UNIQUE NOT NULL,
                    reminder_time_utc TEXT NOT NULL,
                    reminder_time_user TEXT NOT NULL,
                    message TEXT NOT NULL,
                    status TEXT DEFAULT 'pending',
                    created_at TEXT NOT NULL,
                    sent_at TEXT NULL,
                    FOREIGN KEY (task_id) REFERENCES tasks (id) ON DELETE CASCADE
                )
            ''')
            
            # Index for faster queries
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_chat_id ON tasks(chat_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_reminder_status ON reminders(status)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_job_id ON reminders(job_id)')
            
            conn.commit()
    
    def save_task_with_reminders(self, chat_id: int, task_description: str, 
                               base_time: str, reminder_entries: List[Dict]) -> int:
        """
        Save a task and its associated reminders to database
        Returns the task_id for reference
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Insert main task
            cursor.execute('''
                INSERT INTO tasks (chat_id, task_description, base_time, created_at)
                VALUES (?, ?, ?, ?)
            ''', (chat_id, task_description, base_time, datetime.utcnow().isoformat()))
            
            task_id = cursor.lastrowid
            
            # Insert all reminders for this task
            for entry in reminder_entries:
                cursor.execute('''
                    INSERT INTO reminders 
                    (task_id, job_id, reminder_time_utc, reminder_time_user, message, created_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    task_id,
                    entry['id'],
                    entry['time_utc'],
                    entry['time_user'],
                    entry['message'],
                    datetime.utcnow().isoformat()
                ))
            
            conn.commit()
            return task_id
    
    def get_pending_reminders(self) -> List[Dict]:
        """Get all reminders that haven't been sent yet"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT r.id, r.job_id, r.reminder_time_utc, r.message, 
                       t.chat_id, t.task_description
                FROM reminders r
                JOIN tasks t ON r.task_id = t.id
                WHERE r.status = 'pending'
                ORDER BY r.reminder_time_utc
            ''')
            
            columns = [desc[0] for desc in cursor.description]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]
    
    def mark_reminder_sent(self, job_id: str):
        """Mark a reminder as sent"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE reminders 
                SET status = 'sent', sent_at = ?
                WHERE job_id = ?
            ''', (datetime.utcnow().isoformat(), job_id))
            conn.commit()
    
    def get_user_tasks(self, chat_id: int, limit: int = 10) -> List[Dict]:
        """Get recent tasks for a user"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT t.id, t.task_description, t.base_time, t.created_at,
                       COUNT(r.id) as total_reminders,
                       COUNT(CASE WHEN r.status = 'sent' THEN 1 END) as sent_reminders
                FROM tasks t
                LEFT JOIN reminders r ON t.id = r.task_id
                WHERE t.chat_id = ? AND t.status = 'active'
                GROUP BY t.id
                ORDER BY t.created_at DESC
                LIMIT ?
            ''', (chat_id, limit))
            
            columns = [desc[0] for desc in cursor.description]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]
    
    def cleanup_old_tasks(self, days_old: int = 7):
        """Clean up completed tasks older than specified days"""
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
            
            # Delete very old completed tasks
            cutoff_date = datetime.utcnow().replace(microsecond=0)
            cutoff_date = cutoff_date.replace(day=cutoff_date.day - days_old)
            
            cursor.execute('''
                DELETE FROM tasks 
                WHERE status = 'completed' AND created_at < ?
            ''', (cutoff_date.isoformat(),))
            
            conn.commit()
    
    def get_database_stats(self) -> Dict:
        """Get database statistics for monitoring"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            stats = {}
            
            # Count tasks by status
            cursor.execute('SELECT status, COUNT(*) FROM tasks GROUP BY status')
            stats['tasks_by_status'] = dict(cursor.fetchall())
            
            # Count reminders by status
            cursor.execute('SELECT status, COUNT(*) FROM reminders GROUP BY status')
            stats['reminders_by_status'] = dict(cursor.fetchall())
            
            # Count unique users
            cursor.execute('SELECT COUNT(DISTINCT chat_id) FROM tasks')
            stats['unique_users'] = cursor.fetchone()[0]
            
            return stats