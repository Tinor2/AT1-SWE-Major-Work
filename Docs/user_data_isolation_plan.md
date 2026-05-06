# User Data Isolation Implementation Plan

## Overview
This document outlines the approach for implementing user-specific data isolation to ensure each user can only see their own lists and tasks.

## Current State Analysis
- Database has been updated with `user_id` columns in `lists` and `tasks` tables
- Migration has been completed - all existing data assigned to user ID 1
- Authentication system is in place with Flask-Login
- Current routes may not be filtering data by user

## Implementation Plan

### Phase 1: Database Verification
- [ ] Verify foreign key constraints are properly set up
- [ ] Ensure all lists and tasks have valid user_id values
- [ ] Add database-level constraints for data integrity

### Phase 2: Route Protection
- [ ] Update all routes to require authentication
- [ ] Add `@login_required` decorator to protected endpoints
- [ ] Implement proper access control checks

### Phase 3: Data Filtering in Routes
- [ ] Update home.py routes to filter lists by current_user.id
- [ ] Update lists.py routes to filter tasks by current_user.id
- [ ] Update all database queries to include user_id filtering

### Phase 4: Template Updates
- [ ] Update templates to handle user-specific data
- [ ] Add user context to templates where needed
- [ ] Update navigation for authenticated users

### Phase 5: Error Handling
- [ ] Handle cases where user has no lists
- [ ] Add proper error messages for unauthorized access
- [ ] Implement graceful fallbacks

## Detailed Implementation Steps

### Database Structure Changes
The current database structure is already correct:
```sql
CREATE TABLE lists (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    -- other fields...
    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
);

CREATE TABLE tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    list_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    content TEXT NOT NULL,
    -- other fields...
    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
);
```

### Route Updates Required

#### home.py
- Update index route to show only user's active list
- Update all database queries to filter by `current_user.id`

#### lists.py
- Update index route to show only user's lists
- Update create route to associate lists with current_user
- Update all task operations to filter by user_id
- Add `@login_required` to all routes

### Query Pattern Changes

**Before (current):**
```python
lists = db.execute('SELECT * FROM lists').fetchall()
tasks = db.execute('SELECT * FROM tasks WHERE list_id = ?', (list_id,)).fetchall()
```

**After (user-specific):**
```python
lists = db.execute('SELECT * FROM lists WHERE user_id = ?', (current_user.id,)).fetchall()
tasks = db.execute('SELECT * FROM tasks WHERE list_id = ? AND user_id = ?', (list_id, current_user.id)).fetchall()
```

### Security Considerations
- All database queries must include user_id filtering
- Routes must validate user ownership before allowing modifications
- Session security to prevent user switching
- Proper error handling for unauthorized access attempts

### Future Enhancements (for later implementation)
- Guest mode: Allow unauthenticated users to use the app with temporary data
- Session-based temporary storage for guest users
- Option to convert guest session to permanent account
- Data export/import functionality
- Sharing capabilities between users

## Files to Modify

### Core Routes
- `pomodoro/routes/home.py` - Update for user-specific data
- `pomodoro/routes/lists.py` - Update for user-specific data

### Database
- `pomodoro/db.py` - Add user filtering helpers (optional)
- Database constraints verification

### Templates
- Update any templates that assume global data access

## Testing Strategy
- Create multiple test users
- Verify data isolation between users
- Test edge cases (no lists, empty tasks)
- Verify authentication requirements
- Test error handling

## Implementation Order
1. Add authentication decorators to routes
2. Update database queries with user_id filtering
3. Test data isolation
4. Update templates if needed
5. Add error handling
6. Comprehensive testing

## Success Criteria
- ✅ Users can only see their own lists
- ✅ Users can only see their own tasks
- ✅ Authentication required for all data access
- ✅ Proper error handling for unauthorized access
- ✅ Existing user (ID 1) retains their migrated data
