#!/usr/bin/env python3
"""
Debug timer update and database saving issues.
"""

import sys
import os
import time
import json
sys.path.append('.')

from pomodoro import create_app
from pomodoro.db import get_db

def debug_timer_workflow():
    """Test complete timer workflow to identify issues."""
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
            
            print("🔍 Debug Timer Workflow")
            print("=" * 50)
            
            # Login
            with client.session_transaction() as sess:
                sess['_user_id'] = str(user_id)
            
            # Select task
            print("\n1️⃣ Selecting task...")
            response = client.post('/timer/select-task',
                               json={'task_id': parent_task_id},
                               content_type='application/json')
            data = json.loads(response.data)
            print(f"   Task selected: {data['selected_task']['content']}")
            
            # Start timer
            print("\n2️⃣ Starting timer...")
            response = client.post('/timer/start', content_type='application/json')
            data = json.loads(response.data)
            print(f"   Timer state: {data['timer_state']}")
            print(f"   Timer started_at: {data.get('timer_started_at')}")
            
            # Wait 3 seconds
            print("\n3️⃣ Working for 3 seconds...")
            time.sleep(3)
            
            # Check timer status (this is what JS calls)
            print("\n4️⃣ Checking timer status...")
            response = client.get('/timer/status')
            timer_data = json.loads(response.data)
            print(f"   Timer state: {timer_data['timer_state']}")
            print(f"   Timer started_at: {timer_data.get('timer_started_at')}")
            print(f"   Timer remaining: {timer_data.get('timer_remaining')}")
            
            # Check current task (this is what JS calls)
            print("\n5️⃣ Checking current task...")
            response = client.get('/timer/current-task')
            task_data = json.loads(response.data)
            print(f"   Selected task: {task_data['selected_task']['content']}")
            print(f"   Task total_time_seconds: {task_data['selected_task']['total_time_seconds']}")
            
            # Manual calculation of elapsed time
            if timer_data.get('timer_started_at'):
                started_at = timer_data['timer_started_at']
                current_time = int(time.time())
                elapsed = current_time - int(started_at)
                print(f"   Manual elapsed calculation: {elapsed}s")
                
                # Calculate live total time
                base_time = task_data['selected_task']['total_time_seconds']
                live_total = base_time + elapsed
                print(f"   Live total time: {live_total}s")
            
            # Pause timer (should save time)
            print("\n6️⃣ Pausing timer...")
            response = client.post('/timer/pause', content_type='application/json')
            data = json.loads(response.data)
            print(f"   Timer state: {data['timer_state']}")
            
            # Check database directly
            print("\n7️⃣ Checking database...")
            db = get_db()
            
            # Check task_time_sessions
            sessions = db.execute('SELECT * FROM task_time_sessions WHERE task_id = ? ORDER BY id DESC', 
                              (parent_task_id,)).fetchall()
            print(f"   Total sessions: {len(sessions)}")
            for i, session in enumerate(sessions):
                print(f"   Session {i+1}: started={session['started_at']}, ended={session['ended_at']}, duration={session['duration_seconds']}")
            
            # Check tasks table
            task = db.execute('SELECT total_time_seconds FROM tasks WHERE id = ?', 
                          (parent_task_id,)).fetchone()
            print(f"   Task total_time_seconds: {task['total_time_seconds']}")
            
            # Skip to break (should save session properly)
            print("\n8️⃣ Skipping to break...")
            response = client.post('/timer/skip', content_type='application/json')
            data = json.loads(response.data)
            print(f"   Current phase: {data['current_phase']}")
            print(f"   Timer state: {data['timer_state']}")
            
            # Check database again
            print("\n9️⃣ Checking database after skip...")
            sessions = db.execute('SELECT * FROM task_time_sessions WHERE task_id = ? ORDER BY id DESC', 
                              (parent_task_id,)).fetchall()
            print(f"   Total sessions: {len(sessions)}")
            for i, session in enumerate(sessions):
                print(f"   Session {i+1}: started={session['started_at']}, ended={session['ended_at']}, duration={session['duration_seconds']}")
            
            task = db.execute('SELECT total_time_seconds FROM tasks WHERE id = ?', 
                          (parent_task_id,)).fetchone()
            print(f"   Task total_time_seconds: {task['total_time_seconds']}")
            
            # Start new work session
            print("\n🔟 Starting new work session...")
            response = client.post('/timer/start', content_type='application/json')
            data = json.loads(response.data)
            print(f"   Timer state: {data['timer_state']}")
            print(f"   Timer started_at: {data.get('timer_started_at')}")
            
            time.sleep(2)
            
            # Final database check
            print("\n1️⃣1️⃣ Final database check...")
            sessions = db.execute('SELECT * FROM task_time_sessions WHERE task_id = ? ORDER BY id DESC', 
                              (parent_task_id,)).fetchall()
            print(f"   Total sessions: {len(sessions)}")
            for i, session in enumerate(sessions):
                print(f"   Session {i+1}: started={session['started_at']}, ended={session['ended_at']}, duration={session['duration_seconds']}")
            
            task = db.execute('SELECT total_time_seconds FROM tasks WHERE id = ?', 
                          (parent_task_id,)).fetchone()
            print(f"   Task total_time_seconds: {task['total_time_seconds']}")
            
            return True

if __name__ == '__main__':
    try:
        debug_timer_workflow()
        print("\n✅ Debug completed")
    except Exception as e:
        print(f"\n❌ Debug failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
