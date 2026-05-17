#!/usr/bin/env python3
"""
Debug time tracking to find why duration is always 0.
"""

import sys
import os
import time
sys.path.append('.')

from pomodoro import create_app
from pomodoro.db import get_db
from pomodoro.models.time_tracking import end_current_session

app = create_app()
with app.app_context():
    db = get_db()
    
    print('=== Testing Time Tracking Logic ===')
    
    # Start a session manually
    start_time = int(time.time())
    cursor = db.execute(
        'INSERT INTO task_time_sessions (task_id, user_id, started_at) VALUES (?, ?, ?)',
        (1, 1, start_time)
    )
    session_id = cursor.lastrowid
    db.commit()
    
    print(f'Created session {session_id} with start_time {start_time}')
    
    # Wait a bit
    print('Waiting 2 seconds...')
    time.sleep(2)
    
    # Check current time
    current_time = int(time.time())
    expected_duration = current_time - start_time
    print(f'Current time: {current_time}')
    print(f'Expected duration: {expected_duration}')
    
    # End the session using our function
    duration = end_current_session(1)
    print(f'Function returned duration: {duration}')
    
    # Check what was actually stored
    session = db.execute('SELECT * FROM task_time_sessions WHERE id = ?', (session_id,)).fetchone()
    print(f'Stored session:')
    print(f'  started_at: {session["started_at"]}')
    print(f'  ended_at: {session["ended_at"]}')
    print(f'  duration_seconds: {session["duration_seconds"]}')
    
    # Check task time
    task = db.execute('SELECT total_time_seconds FROM tasks WHERE id = 1').fetchone()
    print(f'Task total_time_seconds: {task["total_time_seconds"]}')
    
    # Manual verification
    manual_duration = session['ended_at'] - session['started_at']
    print(f'Manual calculated duration: {manual_duration}')
