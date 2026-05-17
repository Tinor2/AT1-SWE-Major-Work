#!/usr/bin/env python3
"""
Comprehensive test script for task selection system.
Tests all endpoints and functionality.
"""

import sys
import os
sys.path.append('.')

from pomodoro import create_app
from pomodoro.db import get_db
import json
import time

def setup_test_data():
    """Create test user and tasks for testing."""
    db = get_db()
    
    # Create test user
    cursor = db.execute(
        'INSERT OR IGNORE INTO users (username, email, password_hash) VALUES (?, ?, ?)',
        ('testuser', 'test@example.com', 'hashed_password')
    )
    user_id = cursor.lastrowid if cursor.lastrowid else db.execute('SELECT id FROM users WHERE username = ?', ('testuser',)).fetchone()['id']
    
    # Create test list
    cursor = db.execute(
        'INSERT OR IGNORE INTO lists (user_id, name, description, is_active) VALUES (?, ?, ?, ?)',
        (user_id, 'Test List', 'Test list for task selection', 1)
    )
    list_id = cursor.lastrowid if cursor.lastrowid else db.execute('SELECT id FROM lists WHERE user_id = ? AND name = ?', (user_id, 'Test List')).fetchone()['id']
    
    # Create parent task
    cursor = db.execute(
        'INSERT INTO tasks (list_id, user_id, content, level, position) VALUES (?, ?, ?, ?, ?)',
        (list_id, user_id, 'Parent Task 1', 0, 0)
    )
    parent_task_id = cursor.lastrowid
    
    # Create child task
    db.execute(
        'INSERT INTO tasks (list_id, user_id, content, level, position, parent_id) VALUES (?, ?, ?, ?, ?, ?)',
        (list_id, user_id, 'Child Task 1', 1, 0, parent_task_id)
    )
    
    # Create another parent task
    db.execute(
        'INSERT INTO tasks (list_id, user_id, content, level, position) VALUES (?, ?, ?, ?, ?)',
        (list_id, user_id, 'Parent Task 2', 0, 1)
    )
    
    db.commit()
    return user_id, list_id, parent_task_id

def test_endpoints():
    """Test all task selection endpoints."""
    app = create_app()
    
    with app.test_client() as client:
        with app.app_context():
            user_id, list_id, parent_task_id = setup_test_data()
            
            print("🧪 Testing Task Selection Endpoints")
            print("=" * 50)
            
            # Simulate login by setting session
            with client.session_transaction() as sess:
                sess['_user_id'] = str(user_id)
            
            # Test 1: Get current task (should be None initially)
            print("\n1️⃣ Testing GET /timer/current-task (initial state)")
            response = client.get('/timer/current-task')
            print(f"Status: {response.status_code}")
            data = json.loads(response.data)
            print(f"Response: {data}")
            assert data['success'] == True
            assert data['selected_task'] is None
            print("✅ PASSED: No task selected initially")
            
            # Test 2: Try to select a child task (should fail)
            print("\n2️⃣ Testing POST /timer/select-task with child task (should fail)")
            child_task_id = get_db().execute('SELECT id FROM tasks WHERE level = 1').fetchone()['id']
            response = client.post('/timer/select-task', 
                               json={'task_id': child_task_id},
                               content_type='application/json')
            print(f"Status: {response.status_code}")
            data = json.loads(response.data)
            print(f"Response: {data}")
            assert response.status_code == 400
            assert 'Only parent tasks can be selected' in data['error']
            print("✅ PASSED: Child task selection correctly rejected")
            
            # Test 3: Select a parent task (should succeed)
            print("\n3️⃣ Testing POST /timer/select-task with parent task (should succeed)")
            response = client.post('/timer/select-task',
                               json={'task_id': parent_task_id},
                               content_type='application/json')
            print(f"Status: {response.status_code}")
            data = json.loads(response.data)
            print(f"Response: {data}")
            assert response.status_code == 200
            assert data['success'] == True
            assert data['selected_task']['id'] == parent_task_id
            print("✅ PASSED: Parent task selection successful")
            
            # Test 4: Get current task (should return selected task)
            print("\n4️⃣ Testing GET /timer/current-task (after selection)")
            response = client.get('/timer/current-task')
            print(f"Status: {response.status_code}")
            data = json.loads(response.data)
            print(f"Response: {data}")
            assert data['success'] == True
            assert data['selected_task']['id'] == parent_task_id
            print("✅ PASSED: Selected task retrieved correctly")
            
            # Test 5: Deselect task
            print("\n5️⃣ Testing POST /timer/deselect-task")
            response = client.post('/timer/deselect-task',
                               content_type='application/json')
            print(f"Status: {response.status_code}")
            data = json.loads(response.data)
            print(f"Response: {data}")
            assert response.status_code == 200
            assert data['success'] == True
            assert data['selected_task'] is None
            print("✅ PASSED: Task deselection successful")
            
            # Test 6: Invalid task ID
            print("\n6️⃣ Testing POST /timer/select-task with invalid task ID")
            response = client.post('/timer/select-task',
                               json={'task_id': 99999},
                               content_type='application/json')
            print(f"Status: {response.status_code}")
            data = json.loads(response.data)
            print(f"Response: {data}")
            assert response.status_code == 404
            assert 'Task not found' in data['error']
            print("✅ PASSED: Invalid task ID correctly rejected")
            
            # Test 7: Missing task_id parameter
            print("\n7️⃣ Testing POST /timer/select-task without task_id")
            response = client.post('/timer/select-task',
                               json={},
                               content_type='application/json')
            print(f"Status: {response.status_code}")
            data = json.loads(response.data)
            print(f"Response: {data}")
            assert response.status_code == 400
            assert 'task_id required' in data['error']
            print("✅ PASSED: Missing task_id correctly rejected")

def test_time_tracking():
    """Test time tracking integration."""
    app = create_app()
    
    with app.test_client() as client:
        with app.app_context():
            # Clear database to start fresh
            from pomodoro.db import init_db
            import os
            if os.path.exists('instance/pomodoro.sqlite'):
                os.remove('instance/pomodoro.sqlite')
            init_db()
            user_id, list_id, parent_task_id = setup_test_data()
            
            print("\n🧪 Testing Time Tracking Integration")
            print("=" * 50)
            
            # Simulate login
            with client.session_transaction() as sess:
                sess['_user_id'] = str(user_id)
            
            # Select a task first
            client.post('/timer/select-task', json={'task_id': parent_task_id}, content_type='application/json')
            
            # Test 1: Start timer (should start tracking)
            print("\n1️⃣ Testing timer start with selected task")
            response = client.post('/timer/start', content_type='application/json')
            print(f"Status: {response.status_code}")
            data = json.loads(response.data)
            print(f"Timer state: {data['timer_state']}")
            assert data['timer_state'] == 'session'
            
            # Check if time session was created
            db = get_db()
            session = db.execute('SELECT * FROM task_time_sessions WHERE ended_at IS NULL').fetchone()
            assert session is not None
            assert session['task_id'] == parent_task_id
            print("✅ PASSED: Time session started when timer began")
            
            # Test 2: Pause timer (should stop tracking)
            print("\n2️⃣ Testing timer pause (should stop tracking)")
            time.sleep(1)  # Wait a bit to create some duration
            response = client.post('/timer/pause', content_type='application/json')
            print(f"Status: {response.status_code}")
            data = json.loads(response.data)
            print(f"Timer state: {data['timer_state']}")
            assert data['timer_state'] == 'paused'
            
            # Check if session was ended
            db = get_db()
            session = db.execute('SELECT * FROM task_time_sessions WHERE task_id = ? ORDER BY id DESC LIMIT 1', 
                              (parent_task_id,)).fetchone()
            assert session is not None
            assert session['ended_at'] is not None
            assert session['duration_seconds'] > 0
            print(f"✅ PASSED: Time session ended with duration {session['duration_seconds']}s")
            
            # Test 3: Check task total time updated
            print("\n3️⃣ Testing task total time update")
            task = db.execute('SELECT total_time_seconds FROM tasks WHERE id = ?', (parent_task_id,)).fetchone()
            assert task['total_time_seconds'] > 0
            print(f"✅ PASSED: Task total time updated to {task['total_time_seconds']}s")

def test_break_time_tracking():
    """Test that breaks don't count toward task time."""
    app = create_app()
    
    with app.test_client() as client:
        with app.app_context():
            user_id, list_id, parent_task_id = setup_test_data()
            
            print("\n🧪 Testing Break Time Tracking")
            print("=" * 50)
            
            # Simulate login and select task
            with client.session_transaction() as sess:
                sess['_user_id'] = str(user_id)
            
            client.post('/timer/select-task', json={'task_id': parent_task_id}, content_type='application/json')
            
            # Start work session
            client.post('/timer/start', content_type='application/json')
            time.sleep(1)
            client.post('/timer/pause', content_type='application/json')
            
            # Get initial time
            db = get_db()
            initial_time = db.execute('SELECT total_time_seconds FROM tasks WHERE id = ?', 
                                  (parent_task_id,)).fetchone()['total_time_seconds']
            
            # Skip to break
            print("\n1️⃣ Testing skip to break (should not track time)")
            response = client.post('/timer/skip', content_type='application/json')
            data = json.loads(response.data)
            print(f"Current phase: {data['current_phase']}")
            assert data['current_phase'] in ['short_break', 'long_break']
            
            # Start break timer
            client.post('/timer/start', content_type='application/json')
            time.sleep(1)
            client.post('/timer/pause', content_type='application/json')
            
            # Check time didn't increase during break
            final_time = db.execute('SELECT total_time_seconds FROM tasks WHERE id = ?', 
                                (parent_task_id,)).fetchone()['total_time_seconds']
            assert final_time == initial_time
            print(f"✅ PASSED: Task time unchanged during break (still {final_time}s)")

if __name__ == '__main__':
    print("🚀 Starting Task Selection System Tests")
    print("=" * 60)
    
    try:
        test_endpoints()
        test_time_tracking()
        test_break_time_tracking()
        
        print("\n" + "=" * 60)
        print("🎉 ALL TESTS PASSED! Task selection system working correctly.")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
