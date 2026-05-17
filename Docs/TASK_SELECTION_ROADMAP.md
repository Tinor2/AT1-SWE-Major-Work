# Task Selection System Rebuild Roadmap

## Current Issues
- `POST /timer/select-task` endpoint returns 404
- Task selection logic needs to be rebuilt
- Time tracking should only count for work sessions, not breaks
- Child tasks should not be selectable (only parent tasks)

## Requirements
1. Every task has an associated time column for study timer duration
2. Only parent tasks can be selected (child tasks are not selectable)
3. Break timer does NOT count toward task time
4. Work timer DOES count toward selected task time

## Implementation Plan

### Phase 1: Analysis & Backend Foundation
- [ ] Analyze current task selection and time tracking implementation
- [ ] Examine database schema for task hierarchy and time tracking
- [ ] Review existing timer routes and JavaScript

### Phase 2: Backend Updates
- [ ] Update backend to prevent child task selection
- [ ] Create/fix `/timer/select-task` endpoint
- [ ] Ensure task time only increments during work sessions
- [ ] Add validation for task selection (parent tasks only)

### Phase 3: Frontend Updates
- [ ] Update frontend task selection logic
- [ ] Modify UI to show only selectable tasks
- [ ] Update JavaScript to handle new endpoint
- [ ] Add visual feedback for selected task

### Phase 4: Integration & Testing
- [ ] Test complete task selection and time tracking flow
- [ ] Verify time only counts during work sessions
- [ ] Test parent/child task selection rules
- [ ] Ensure data persistence across sessions

## Technical Details

### Database Schema Considerations
- `tasks` table already has `total_time_seconds` column
- `task_time_sessions` table tracks individual work sessions
- Need to ensure parent/child relationship is respected

### API Endpoints
- `POST /timer/select-task` - Select a task for time tracking
- `GET /timer/current-task` - Get currently selected task
- Time should only be tracked when timer is in 'session' state

### Frontend Integration
- Update task list to show selection state
- Prevent clicks on child tasks
- Show visual indication of selected task
- Sync with timer state changes

## Edge Cases to Handle
1. No task selected - timer runs without tracking time
2. Task completed while selected - handle time tracking
3. Timer paused/stopped - handle session time recording
4. Multiple browser tabs - prevent conflicting selections
5. Parent task with all children completed - allow selection

## Success Criteria
- Task selection works without 404 errors
- Only parent tasks are selectable
- Time only accumulates during work sessions
- Selected task persists across page refreshes
- UI clearly shows selected task state
