#!/usr/bin/env python3
"""
Frontend integration tests for task selection system.
Tests the complete user flow.
"""

import sys
import os
sys.path.append('.')

from pomodoro import create_app
from pomodoro.db import get_db
import json

def test_frontend_flow():
    """Test complete frontend integration flow."""
    app = create_app()
    
    with app.test_client() as client:
        with app.app_context():
            # Setup test data
            from test_task_selection import setup_test_data
            user_id, list_id, parent_task_id = setup_test_data()
            
            print("🧪 Testing Frontend Integration Flow")
            print("=" * 50)
            
            # Simulate login
            with client.session_transaction() as sess:
                sess['_user_id'] = str(user_id)
            
            # Test 1: Load initial state
            print("\n1️⃣ Testing initial page load")
            response = client.get('/timer/status')
            print(f"Timer status: {response.status_code}")
            
            response = client.get('/timer/current-task')
            data = json.loads(response.data)
            print(f"Current task: {data['selected_task']}")
            assert data['selected_task'] is None
            print("✅ PASSED: Initial state loaded correctly")
            
            # Test 2: Simulate frontend task selection
            print("\n2️⃣ Testing frontend task selection")
            response = client.post('/timer/select-task',
                               json={'task_id': parent_task_id},
                               content_type='application/json')
            data = json.loads(response.data)
            print(f"Selection response: {data}")
            assert data['success'] == True
            assert data['selected_task']['id'] == parent_task_id
            print("✅ PASSED: Frontend task selection works")
            
            # Reset timer to session state first
            print("\n3️⃣ Resetting timer to session state")
            response = client.post('/timer/reset-sets', content_type='application/json')
            data = json.loads(response.data)
            print(f"Timer reset: {data['timer_state']}")
            print(f"Current phase: {data['current_phase']}")
            
            # Test 3: Start timer (should begin tracking)
            print("\n4️⃣ Testing timer start with task selected")
            response = client.post('/timer/start', content_type='application/json')
            data = json.loads(response.data)
            print(f"Timer started: {data['timer_state']}")
            assert data['timer_state'] == 'session'
            
            # Verify time session created
            db = get_db()
            session = db.execute('SELECT * FROM task_time_sessions WHERE ended_at IS NULL').fetchone()
            assert session is not None
            assert session['task_id'] == parent_task_id
            print("✅ PASSED: Time tracking started with timer")
            
            # Test 4: Pause timer (should stop tracking)
            print("\n4️⃣ Testing timer pause")
            response = client.post('/timer/pause', content_type='application/json')
            data = json.loads(response.data)
            print(f"Timer paused: {data['timer_state']}")
            assert data['timer_state'] == 'paused'
            
            # Verify session ended
            db = get_db()
            session = db.execute('SELECT * FROM task_time_sessions WHERE task_id = ? ORDER BY id DESC LIMIT 1', 
                              (parent_task_id,)).fetchone()
            assert session['ended_at'] is not None
            print(f"✅ PASSED: Time tracking stopped (duration: {session['duration_seconds']}s)")
            
            # Test 5: Skip to break (should not track)
            print("\n5️⃣ Testing skip to break")
            initial_time = db.execute('SELECT total_time_seconds FROM tasks WHERE id = ?', 
                                  (parent_task_id,)).fetchone()['total_time_seconds']
            
            response = client.post('/timer/skip', content_type='application/json')
            data = json.loads(response.data)
            print(f"Skipped to: {data['current_phase']}")
            assert data['current_phase'] in ['short_break', 'long_break']
            
            # Start break timer
            response = client.post('/timer/start', content_type='application/json')
            data = json.loads(response.data)
            print(f"Break timer: {data['timer_state']}")
            
            # Verify no new time session created for break
            db = get_db()
            active_sessions = db.execute('SELECT COUNT(*) as count FROM task_time_sessions WHERE ended_at IS NULL').fetchone()['count']
            assert active_sessions == 0  # Should be no active sessions during break
            
            final_time = db.execute('SELECT total_time_seconds FROM tasks WHERE id = ?', 
                                  (parent_task_id,)).fetchone()['total_time_seconds']
            assert final_time == initial_time
            print("✅ PASSED: Break time not tracked")
            
            # Test 6: Return to work session
            print("\n6️⃣ Testing return to work session")
            response = client.post('/timer/skip', content_type='application/json')  # Skip back to work
            response = client.post('/timer/start', content_type='application/json')
            data = json.loads(response.data)
            print(f"Work resumed: {data['timer_state']}")
            assert data['timer_state'] == 'session'
            
            # Verify new time session created
            db = get_db()
            session = db.execute('SELECT * FROM task_time_sessions WHERE ended_at IS NULL').fetchone()
            assert session is not None
            assert session['task_id'] == parent_task_id
            print("✅ PASSED: Work session tracking resumed")

def test_edge_cases():
    """Test edge cases and error conditions."""
    app = create_app()
    
    with app.test_client() as client:
        with app.app_context():
            # Clear database to start fresh
            from test_task_selection import setup_test_data
            from pomodoro.db import init_db
            import os
            if os.path.exists('instance/pomodoro.sqlite'):
                os.remove('instance/pomodoro.sqlite')
            init_db()  # Reinitialize clean database
            user_id, list_id, parent_task_id = setup_test_data()
            
            print("\n🧪 Testing Edge Cases")
            print("=" * 50)
            
            # Simulate login
            with client.session_transaction() as sess:
                sess['_user_id'] = str(user_id)
            
            # Test 1: Timer operations without selected task
            print("\n1️⃣ Testing timer without selected task")
            response = client.post('/timer/start', content_type='application/json')
            data = json.loads(response.data)
            print(f"Timer started without task: {data['timer_state']}")
            assert data['timer_state'] == 'session'
            
            # Verify no time session created
            db = get_db()
            sessions = db.execute('SELECT COUNT(*) as count FROM task_time_sessions').fetchone()['count']
            assert sessions == 0
            print("✅ PASSED: Timer works without selected task")
            
            # Test 2: Select task while timer running
            print("\n2️⃣ Testing task selection while timer running")
            client.post('/timer/pause', content_type='application/json')
            client.post('/timer/select-task', json={'task_id': parent_task_id}, content_type='application/json')
            client.post('/timer/start', content_type='application/json')
            
            # Try to select different task while running
            db = get_db()
            other_task = db.execute('SELECT id FROM tasks WHERE id != ? LIMIT 1', (parent_task_id,)).fetchone()
            
            response = client.post('/timer/select-task',
                               json={'task_id': other_task['id']},
                               content_type='application/json')
            data = json.loads(response.data)
            print(f"Task selection while running: {data['success']}")
            assert data['success'] == True  # Should allow selection change
            print("✅ PASSED: Can change task selection")
            
            # Test 3: Deselect task while timer running
            print("\n3️⃣ Testing task deselection while timer running")
            response = client.post('/timer/deselect-task', content_type='application/json')
            data = json.loads(response.data)
            print(f"Task deselection: {data['success']}")
            assert data['success'] == True
            
            # Verify tracking stopped
            db = get_db()
            active_sessions = db.execute('SELECT COUNT(*) as count FROM task_time_sessions WHERE ended_at IS NULL').fetchone()['count']
            assert active_sessions == 0
            print("✅ PASSED: Deselection stops tracking")

if __name__ == '__main__':
    print("🚀 Starting Frontend Integration Tests")
    print("=" * 60)
    
    try:
        test_frontend_flow()
        test_edge_cases()
        
        print("\n" + "=" * 60)
        print("🎉 ALL FRONTEND TESTS PASSED! System fully functional.")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ FRONTEND TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
