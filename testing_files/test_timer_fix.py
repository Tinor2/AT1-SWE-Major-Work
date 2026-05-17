#!/usr/bin/env python3
"""
Test timer fix and database saving.
"""

import sys
import os
import time
import json
sys.path.append('.')

from pomodoro import create_app
from pomodoro.db import get_db

def test_timer_fix():
    """Test timer fix and database saving."""
    app = create_app()
    
    with app.test_client() as client:
        with app.app_context():
            # Clean setup
            from test_task_selection import setup_test_data
            from pomodoro.db import init_db
            if os.path.exists('instance/pomodoro.sqlite'):
                os.remove('instance/pomodoro.sqlite')
            init_db()
            user_id, list_id, parent_task_id = setup_test_data()
            
            print("🧪 Testing Timer Fix")
            print("=" * 40)
            
            # Login
            with client.session_transaction() as sess:
                sess['_user_id'] = str(user_id)
            
            # Select task and start timer
            client.post('/timer/select-task', json={'task_id': parent_task_id}, content_type='application/json')
            client.post('/timer/start', content_type='application/json')
            
            # Wait and check status
            time.sleep(2)
            
            response = client.get('/timer/status')
            timer_data = json.loads(response.data)
            print(f"Timer started_at: {timer_data.get('timer_started_at')}")
            print(f"Timer state: {timer_data.get('timer_state')}")
            
            # Pause to save time
            client.post('/timer/pause', content_type='application/json')
            
            # Check database
            db = get_db()
            sessions = db.execute('SELECT * FROM task_time_sessions WHERE task_id = ? ORDER BY id DESC', 
                              (parent_task_id,)).fetchall()
            task = db.execute('SELECT total_time_seconds FROM tasks WHERE id = ?', 
                          (parent_task_id,)).fetchone()
            
            print(f"Sessions: {len(sessions)}")
            for session in sessions:
                print(f"  Session: started={session['started_at']}, ended={session['ended_at']}, duration={session['duration_seconds']}")
            print(f"Task total_time_seconds: {task['total_time_seconds']}")
            
            # Skip to break
            client.post('/timer/skip', content_type='application/json')
            
            # Check database after skip
            sessions_after = db.execute('SELECT * FROM task_time_sessions WHERE task_id = ? ORDER BY id DESC', 
                                   (parent_task_id,)).fetchall()
            task_after = db.execute('SELECT total_time_seconds FROM tasks WHERE id = ?', 
                                 (parent_task_id,)).fetchone()
            
            print(f"\nAfter skip:")
            print(f"Sessions: {len(sessions_after)}")
            for session in sessions_after:
                print(f"  Session: started={session['started_at']}, ended={session['ended_at']}, duration={session['duration_seconds']}")
            print(f"Task total_time_seconds: {task_after['total_time_seconds']}")
            
            # Start new session
            client.post('/timer/start', content_type='application/json')
            time.sleep(1)
            client.post('/timer/pause', content_type='application/json')
            
            # Final check
            sessions_final = db.execute('SELECT * FROM task_time_sessions WHERE task_id = ? ORDER BY id DESC', 
                                   (parent_task_id,)).fetchall()
            task_final = db.execute('SELECT total_time_seconds FROM tasks WHERE id = ?', 
                                 (parent_task_id,)).fetchone()
            
            print(f"\nFinal:")
            print(f"Sessions: {len(sessions_final)}")
            for session in sessions_final:
                print(f"  Session: started={session['started_at']}, ended={session['ended_at']}, duration={session['duration_seconds']}")
            print(f"Task total_time_seconds: {task_final['total_time_seconds']}")
            
            total_duration = sum(s['duration_seconds'] for s in sessions_final)
            print(f"Sum of session durations: {total_duration}")
            print(f"Task total_time_seconds: {task_final['total_time_seconds']}")
            
            assert total_duration == task_final['total_time_seconds'], "Database doesn't match sessions!"
            print("✅ Database saving correctly!")

if __name__ == '__main__':
    test_timer_fix()
