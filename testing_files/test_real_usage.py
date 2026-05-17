#!/usr/bin/env python3
"""
Test real usage scenario to verify time tracking works correctly.
"""

import sys
import os
import time
sys.path.append('.')

from pomodoro import create_app
from pomodoro.db import get_db

def test_real_usage():
    """Test a realistic usage scenario."""
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
            
            print("🎯 Real Usage Test: Task Selection & Time Tracking")
            print("=" * 60)
            
            # Login
            with client.session_transaction() as sess:
                sess['_user_id'] = str(user_id)
            
            # Select task
            print("\n1️⃣ Selecting task...")
            response = client.post('/timer/select-task',
                               json={'task_id': parent_task_id},
                               content_type='application/json')
            data = json.loads(response.data)
            print(f"   Selected: {data['selected_task']['content']}")
            
            # Start work session
            print("\n2️⃣ Starting work session...")
            response = client.post('/timer/start', content_type='application/json')
            data = json.loads(response.data)
            print(f"   Timer state: {data['timer_state']}")
            
            # Work for 3 seconds
            print("\n3️⃣ Working for 3 seconds...")
            time.sleep(3)
            
            # Check current task time (should still be 0 since session is active)
            response = client.get('/timer/current-task')
            data = json.loads(response.data)
            print(f"   Current task time (while active): {data['selected_task']['total_time_seconds']}s")
            
            # Pause timer
            print("\n4️⃣ Pausing timer...")
            response = client.post('/timer/pause', content_type='application/json')
            data = json.loads(response.data)
            print(f"   Timer state: {data['timer_state']}")
            
            # Check task time after pause
            response = client.get('/timer/current-task')
            data = json.loads(response.data)
            print(f"   Task time after pause: {data['selected_task']['total_time_seconds']}s")
            
            # Resume work
            print("\n5️⃣ Resuming work...")
            response = client.post('/timer/start', content_type='application/json')
            data = json.loads(response.data)
            print(f"   Timer state: {data['timer_state']}")
            
            # Work for 2 more seconds
            print("\n6️⃣ Working for 2 more seconds...")
            time.sleep(2)
            
            # Final pause
            print("\n7️⃣ Final pause...")
            response = client.post('/timer/pause', content_type='application/json')
            
            # Check final task time
            response = client.get('/timer/current-task')
            data = json.loads(response.data)
            final_time = data['selected_task']['total_time_seconds']
            print(f"   Final task time: {final_time}s")
            
            # Verify database state
            db = get_db()
            sessions = db.execute('SELECT * FROM task_time_sessions WHERE task_id = ? ORDER BY id', 
                              (parent_task_id,)).fetchall()
            total_db_time = sum(s['duration_seconds'] for s in sessions)
            
            print(f"\n📊 Summary:")
            print(f"   Sessions: {len(sessions)}")
            print(f"   Session durations: {[s['duration_seconds'] for s in sessions]}")
            print(f"   Total from sessions: {total_db_time}s")
            print(f"   Task total_time_seconds: {final_time}s")
            
            # Verify consistency
            assert total_db_time == final_time, "Session total doesn't match task total"
            assert final_time >= 5, f"Expected at least 5 seconds, got {final_time}"
            assert final_time <= 7, f"Expected at most 7 seconds, got {final_time}"
            
            print(f"\n✅ SUCCESS: Time tracking working correctly!")
            print(f"   Total work time tracked: {final_time}s")
            
            return True

if __name__ == '__main__':
    import json
    
    try:
        test_real_usage()
        print("\n🎉 Real usage test passed!")
    except Exception as e:
        print(f"\n❌ Real usage test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
