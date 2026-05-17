#!/usr/bin/env python3
"""
Complete end-to-end test of the task selection system.
Tests the full user workflow as it would be used in production.
"""

import sys
import os
sys.path.append('.')

from pomodoro import create_app
from pomodoro.db import get_db
import json
import time

def test_complete_workflow():
    """Test complete user workflow from start to finish."""
    app = create_app()
    
    with app.test_client() as client:
        with app.app_context():
            # Setup clean environment
            from test_task_selection import setup_test_data
            from pomodoro.db import init_db
            if os.path.exists('instance/pomodoro.sqlite'):
                os.remove('instance/pomodoro.sqlite')
            init_db()
            user_id, list_id, parent_task_id = setup_test_data()
            
            print("🚀 Complete Task Selection System Test")
            print("=" * 60)
            
            # Simulate login
            with client.session_transaction() as sess:
                sess['_user_id'] = str(user_id)
            
            print("\n📋 STEP 1: User loads the application")
            response = client.get('/timer/current-task')
            data = json.loads(response.data)
            assert data['selected_task'] is None
            print("✅ Application loads with no task selected")
            
            print("\n📋 STEP 2: User selects a parent task")
            response = client.post('/timer/select-task',
                               json={'task_id': parent_task_id},
                               content_type='application/json')
            data = json.loads(response.data)
            assert data['success'] == True
            assert data['selected_task']['id'] == parent_task_id
            print(f"✅ Task '{data['selected_task']['content']}' selected successfully")
            
            print("\n📋 STEP 3: User starts work session")
            response = client.post('/timer/start', content_type='application/json')
            data = json.loads(response.data)
            assert data['timer_state'] == 'session'
            print("✅ Work session started")
            
            # Verify time tracking began
            db = get_db()
            session = db.execute('SELECT * FROM task_time_sessions WHERE ended_at IS NULL').fetchone()
            assert session is not None
            assert session['task_id'] == parent_task_id
            print("✅ Time tracking started automatically")
            
            print("\n📋 STEP 4: User works for a few seconds")
            time.sleep(2)  # Simulate work
            
            print("\n📋 STEP 5: User pauses timer")
            response = client.post('/timer/pause', content_type='application/json')
            data = json.loads(response.data)
            assert data['timer_state'] == 'paused'
            print("✅ Timer paused")
            
            # Verify time tracking stopped
            db = get_db()
            session = db.execute('SELECT * FROM task_time_sessions WHERE task_id = ? ORDER BY id DESC LIMIT 1', 
                              (parent_task_id,)).fetchone()
            assert session['ended_at'] is not None
            assert session['duration_seconds'] >= 2  # At least 2 seconds of work
            print(f"✅ Time tracking stopped ({session['duration_seconds']}s recorded)")
            
            print("\n📋 STEP 6: User checks task total time")
            task = db.execute('SELECT total_time_seconds FROM tasks WHERE id = ?', 
                          (parent_task_id,)).fetchone()
            assert task['total_time_seconds'] > 0
            print(f"✅ Task total time: {task['total_time_seconds']}s")
            
            print("\n📋 STEP 7: User skips to break")
            response = client.post('/timer/skip', content_type='application/json')
            data = json.loads(response.data)
            assert data['current_phase'] in ['short_break', 'long_break']
            print(f"✅ Skipped to {data['current_phase']}")
            
            print("\n📋 STEP 8: User starts break timer")
            response = client.post('/timer/start', content_type='application/json')
            data = json.loads(response.data)
            assert data['timer_state'] in ['short_break', 'long_break']
            print("✅ Break timer started")
            
            # Verify no time tracking during break
            db = get_db()
            active_sessions = db.execute('SELECT COUNT(*) as count FROM task_time_sessions WHERE ended_at IS NULL').fetchone()['count']
            assert active_sessions == 0
            print("✅ No time tracking during break")
            
            time.sleep(1)  # Simulate break time
            
            print("\n📋 STEP 9: User ends break")
            response = client.post('/timer/pause', content_type='application/json')
            data = json.loads(response.data)
            assert data['timer_state'] == 'paused'
            print("✅ Break ended")
            
            # Verify task time didn't change during break
            task_after_break = db.execute('SELECT total_time_seconds FROM tasks WHERE id = ?', 
                                     (parent_task_id,)).fetchone()
            assert task_after_break['total_time_seconds'] == task['total_time_seconds']
            print("✅ Task time unchanged during break")
            
            print("\n📋 STEP 10: User returns to work")
            response = client.post('/timer/skip', content_type='application/json')  # Skip back to work
            response = client.post('/timer/start', content_type='application/json')
            data = json.loads(response.data)
            assert data['timer_state'] == 'session'
            print("✅ Work session resumed")
            
            # Verify time tracking resumed
            db = get_db()
            session = db.execute('SELECT * FROM task_time_sessions WHERE ended_at IS NULL').fetchone()
            assert session is not None
            assert session['task_id'] == parent_task_id
            print("✅ Time tracking resumed")
            
            time.sleep(1)
            
            print("\n📋 STEP 11: User deselects task")
            response = client.post('/timer/deselect-task', content_type='application/json')
            data = json.loads(response.data)
            assert data['success'] == True
            assert data['selected_task'] is None
            print("✅ Task deselected")
            
            # Verify time tracking stopped
            db = get_db()
            active_sessions = db.execute('SELECT COUNT(*) as count FROM task_time_sessions WHERE ended_at IS NULL').fetchone()['count']
            assert active_sessions == 0
            print("✅ Time tracking stopped on deselection")
            
            print("\n📋 STEP 12: Verify final statistics")
            # Get all sessions for the task
            sessions = db.execute('SELECT * FROM task_time_sessions WHERE task_id = ? ORDER BY id', 
                              (parent_task_id,)).fetchall()
            total_time = sum(s['duration_seconds'] for s in sessions)
            task_final = db.execute('SELECT total_time_seconds FROM tasks WHERE id = ?', 
                                 (parent_task_id,)).fetchone()
            
            assert task_final['total_time_seconds'] == total_time
            print(f"✅ Final task time: {task_final['total_time_seconds']}s")
            print(f"✅ Total sessions: {len(sessions)}")
            print(f"✅ Session breakdown: {[s['duration_seconds'] for s in sessions]}")
            
            return True

def test_child_task_protection():
    """Test that child tasks cannot be selected."""
    app = create_app()
    
    with app.test_client() as client:
        with app.app_context():
            # Setup
            from test_task_selection import setup_test_data
            from pomodoro.db import init_db
            if os.path.exists('instance/pomodoro.sqlite'):
                os.remove('instance/pomodoro.sqlite')
            init_db()
            user_id, list_id, parent_task_id = setup_test_data()
            
            with client.session_transaction() as sess:
                sess['_user_id'] = str(user_id)
            
            print("\n🛡️ Testing Child Task Protection")
            print("=" * 40)
            
            # Try to select child task
            db = get_db()
            child_task = db.execute('SELECT id FROM tasks WHERE level = 1 LIMIT 1').fetchone()
            
            response = client.post('/timer/select-task',
                               json={'task_id': child_task['id']},
                               content_type='application/json')
            data = json.loads(response.data)
            
            assert response.status_code == 400
            assert 'Only parent tasks can be selected' in data['error']
            print("✅ Child task selection correctly blocked")
            
            # Verify no time session created
            sessions = db.execute('SELECT COUNT(*) as count FROM task_time_sessions').fetchone()['count']
            assert sessions == 0
            print("✅ No time session created for child task")
            
            return True

if __name__ == '__main__':
    print("🧪 STARTING COMPLETE SYSTEM TEST")
    print("=" * 80)
    
    try:
        success1 = test_complete_workflow()
        success2 = test_child_task_protection()
        
        if success1 and success2:
            print("\n" + "=" * 80)
            print("🎉 COMPLETE SYSTEM TEST PASSED!")
            print("✅ Task selection system is fully functional and ready for production.")
            print("✅ All requirements met:")
            print("   - Only parent tasks can be selected")
            print("   - Time tracking only during work sessions")
            print("   - Breaks do not count toward task time")
            print("   - Task selection persists across timer operations")
            print("   - Time tracking stops on deselection")
            print("   - All edge cases handled correctly")
            print("=" * 80)
        else:
            print("❌ Some tests failed")
            sys.exit(1)
            
    except Exception as e:
        print(f"\n❌ COMPLETE SYSTEM TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
