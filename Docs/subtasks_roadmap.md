# Hierarchical Subtasks Implementation Roadmap

## Overview

This document outlines the comprehensive plan for implementing hierarchical subtasks with drag-and-drop functionality in the Pomodoro + To-Do application. The feature will allow users to create parent-child task relationships and organize tasks in a hierarchical structure.

## Current State Analysis

### Existing Infrastructure
- ✅ **Database**: SQLite with `tasks`, `lists`, and `users` tables
- ✅ **Basic Drag-and-Drop**: Task reordering already implemented with `position` field
- ✅ **Task Management**: CRUD operations for tasks
- ✅ **Frontend**: Modern UI with CSS variables and responsive design
- ✅ **Authentication**: User-based task isolation

### Current Task Schema
```sql
CREATE TABLE tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    list_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    content TEXT NOT NULL,
    is_done BOOLEAN DEFAULT 0,
    tags TEXT DEFAULT '',
    position INTEGER DEFAULT 0,  -- Already exists for reordering
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (list_id) REFERENCES lists (id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
);
```

## Backend Database Changes

### Phase 1: Schema Modifications

#### 1.1 Add Hierarchical Fields to Tasks Table
```sql
-- Add parent-child relationship fields
ALTER TABLE tasks ADD COLUMN parent_id INTEGER DEFAULT NULL;
ALTER TABLE tasks ADD COLUMN level INTEGER DEFAULT 0;
ALTER TABLE tasks ADD COLUMN path TEXT DEFAULT NULL;  -- Materialized path for efficient queries

-- Add indexes for performance
CREATE INDEX idx_tasks_parent_id ON tasks(parent_id);
CREATE INDEX idx_tasks_level ON tasks(level);
CREATE INDEX idx_tasks_path ON tasks(path);

-- Add foreign key constraint
ALTER TABLE tasks ADD CONSTRAINT fk_tasks_parent 
    FOREIGN KEY (parent_id) REFERENCES tasks(id) ON DELETE CASCADE;
```

#### 1.2 Migration Strategy
```sql
-- Set initial values for existing tasks (all become root-level)
UPDATE tasks SET level = 0, path = CAST(id AS TEXT) WHERE parent_id IS NULL;

-- Ensure all existing tasks have proper path
UPDATE tasks SET path = CAST(id AS TEXT) WHERE path IS NULL;
```

### Phase 2: Backend API Changes

#### 2.1 New Endpoints in `home.py`

**Create Subtask Endpoint**
```python
@bp.route('/task/<int:parent_id>/subtask', methods=['POST'])
@login_required
def create_subtask(parent_id):
    # Validate parent task ownership
    # Create subtask with parent_id, level = parent.level + 1
    # Update path = parent.path + '/' + new_id
    # Insert at appropriate position within parent's children
```

**Move Task Endpoint (for drag-and-drop hierarchy changes)**
```python
@bp.route('/task/<int:id>/move', methods=['POST'])
@login_required
def move_task(id):
    # Handle moving task to new parent or reordering within same level
    # Update parent_id, level, path, and position
    # Recursively update all children paths and levels
```

**Get Task Tree Endpoint**
```python
@bp.route('/tasks/tree', methods=['GET'])
@login_required
def get_task_tree():
    # Return hierarchical structure for frontend rendering
    # Use materialized path for efficient tree queries
```

#### 2.2 Enhanced Query Methods

**Hierarchical Task Retrieval**
```python
def get_tasks_with_hierarchy(list_id, user_id):
    """Get tasks ordered hierarchically with proper nesting"""
    query = '''
    WITH RECURSIVE task_tree AS (
        SELECT id, content, is_done, tags, position, parent_id, level, path, 0 as depth
        FROM tasks 
        WHERE list_id = ? AND user_id = ? AND parent_id IS NULL
        
        UNION ALL
        
        SELECT t.id, t.content, t.is_done, t.tags, t.position, 
               t.parent_id, t.level, t.path, tt.depth + 1
        FROM tasks t
        JOIN task_tree tt ON t.parent_id = tt.id
        WHERE t.list_id = ? AND t.user_id = ?
    )
    SELECT * FROM task_tree ORDER BY path, position;
    '''
```

## Frontend Changes

### Phase 3: UI/UX Enhancements

#### 3.1 Visual Hierarchy Design

**Task Item Structure**
```html
<li class="task-item" data-task-id="{{ task.id }}" data-level="{{ task.level }}" 
    data-parent-id="{{ task.parent_id }}" draggable="true">
    
    <!-- Hierarchy Controls -->
    <div class="hierarchy-controls">
        <button class="collapse-btn" aria-label="Collapse subtasks">
            <svg>▼</svg>
        </button>
        <div class="level-indicator" style="padding-left: {{ task.level * 20 }}px;"></div>
    </div>
    
    <!-- Existing Task Content -->
    <div class="drag-handle">⋮⋮</div>
    <form method="post" action="{{ url_for('home.toggle_task', id=task.id) }}">
        <input type="checkbox" {% if task.is_done %}checked{% endif %} 
               onchange="this.form.submit()">
    </form>
    <span class="task-content">{{ task.content }}</span>
    
    <!-- Add Subtask Button -->
    <button class="add-subtask-btn" data-parent-id="{{ task.id }}">
        <span>+</span> Add Subtask
    </button>
</li>
```

#### 3.2 CSS Styling for Hierarchy

**Hierarchy Visual Indicators**
```css
/* Level-based indentation */
.task-item[data-level="1"] { padding-left: 20px; }
.task-item[data-level="2"] { padding-left: 40px; }
.task-item[data-level="3"] { padding-left: 60px; }

/* Hierarchy connection lines */
.task-item::before {
    content: '';
    position: absolute;
    left: 10px;
    top: 0;
    bottom: 0;
    width: 1px;
    background: var(--border-color);
}

.task-item[data-level="0"]::before {
    display: none;
}

/* Collapse/Expand animations */
.task-children {
    max-height: 0;
    overflow: hidden;
    transition: max-height 0.3s ease-out;
}

.task-children.expanded {
    max-height: 2000px;
    transition: max-height 0.3s ease-in;
}

/* Drag-and-drop zones for hierarchy */
.task-item.drag-over-parent {
    background: var(--bg-tertiary);
    border: 2px dashed var(--primary-color);
}
```

#### 3.3 Enhanced Drag-and-Drop JavaScript

**Extend Existing TaskReordering Class**
The new hierarchical functionality should extend the existing `TaskReordering` class approach rather than replace it. The current implementation uses:

- Class-based structure with clear separation of concerns
- Placeholder element for visual feedback
- Smooth animations with `animateDrop()` method
- Proper error handling with flash messages
- CSRF token management
- Loading states during API calls

**Hierarchical Enhancement Strategy**
```javascript
// Extend the existing TaskReordering class
class HierarchicalTaskReordering extends TaskReordering {
    constructor() {
        super();
        this.dragMode = null; // 'reorder' or 'hierarchy'
        this.dropTarget = null;
        this.initHierarchyFeatures();
    }
    
    initHierarchyFeatures() {
        this.setupHierarchyControls();
        this.setupAddSubtaskButtons();
        // Override drag detection to handle hierarchy creation
    }
    
    // Override handleListDragOver to detect hierarchy vs reorder
    handleListDragOver(e) {
        e.preventDefault();
        e.dataTransfer.dropEffect = 'move';
        
        if (!this.draggedElement) return;
        
        const taskList = e.currentTarget;
        const targetElement = e.target.closest('.task-item');
        
        if (targetElement && targetElement !== this.draggedElement) {
            // Detect if we're creating a subtask or reordering
            const rect = targetElement.getBoundingClientRect();
            const dropZone = this.detectDropZone(targetElement, e.clientX, e.clientY);
            
            if (dropZone.type === 'subtask' && this.canBecomeSubtask(targetElement)) {
                this.showSubtaskDropZone(targetElement);
                this.dragMode = 'hierarchy';
            } else {
                // Use existing reorder logic from parent class
                super.handleListDragOver(e);
                this.dragMode = 'reorder';
            }
        } else {
            // Use existing reorder logic
            super.handleListDragOver(e);
        }
    }
    
    // Override handleListDrop to handle both operations
    handleListDrop(e) {
        e.preventDefault();
        
        if (this.dragMode === 'hierarchy' && this.dropTarget) {
            this.createSubtaskRelationship();
        } else {
            // Use existing reorder logic from parent class
            super.handleListDrop(e);
        }
    }
    
    // New method for hierarchy creation
    createSubtaskRelationship() {
        const parentId = this.dropTarget.dataset.taskId;
        const taskId = this.draggedElement.dataset.taskId;
        
        // Use similar error handling pattern as saveNewOrder()
        this.showLoadingState();
        
        fetch(`/task/${taskId}/move`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': this.getCsrfToken() // Reuse existing method
            },
            body: JSON.stringify({ 
                new_parent_id: parentId,
                operation: 'make_subtask'
            })
        })
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            if (!data.success) {
                console.error('Failed to create subtask:', data.error);
                this.showError('Failed to create subtask');
                setTimeout(() => location.reload(), 2000);
            } else {
                this.updateUIHierarchy(data.updated_tasks);
                this.showSuccess('Subtask created successfully');
            }
        })
        .catch(error => {
            console.error('Error creating subtask:', error);
            this.showError('Error creating subtask');
            setTimeout(() => location.reload(), 2000);
        })
        .finally(() => {
            this.hideLoadingState();
        });
    }
    
    // Reuse existing animation and error handling patterns
    showLoadingState() {
        document.querySelectorAll('.task-item').forEach(el => el.style.opacity = '0.7');
    }
    
    hideLoadingState() {
        document.querySelectorAll('.task-item').forEach(el => el.style.opacity = '1');
    }
    
    // Visual feedback for subtask drop zones
    showSubtaskDropZone(targetElement) {
        // Clear existing drop zones
        document.querySelectorAll('.drag-over-parent').forEach(el => {
            el.classList.remove('drag-over-parent');
        });
        
        targetElement.classList.add('drag-over-parent');
        this.dropTarget = targetElement;
    }
    
    detectDropZone(targetElement, x, y) {
        const rect = targetElement.getBoundingClientRect();
        const centerX = rect.left + rect.width / 2;
        const topThird = rect.top + rect.height / 3;
        
        // If dropped in top third and slightly to the right, create subtask
        if (y < topThird && x > centerX + 20) {
            return { type: 'subtask', element: targetElement };
        }
        
        return { type: 'reorder', element: targetElement };
    }
    
    canBecomeSubtask(targetElement) {
        const targetId = targetElement.dataset.taskId;
        const draggedId = this.draggedElement.dataset.taskId;
        
        // Prevent creating circular references
        return !this.isDescendant(draggedId, targetId);
    }
    
    isDescendant(potentialDescendant, potentialAncestor) {
        // Check if potentialDescendant is already a descendant of potentialAncestor
        const descendantElement = document.querySelector(`[data-task-id="${potentialDescendant}"]`);
        if (!descendantElement) return false;
        
        let current = descendantElement.parentElement;
        while (current && current.classList.contains('task-children')) {
            const parentTask = current.previousElementSibling;
            if (parentTask && parentTask.dataset.taskId === potentialAncestor) {
                return true;
            }
            current = current.parentElement?.parentElement;
        }
        return false;
    }
    
    // Setup hierarchy controls (collapse/expand)
    setupHierarchyControls() {
        document.querySelectorAll('.collapse-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const taskId = e.target.closest('.task-item').dataset.taskId;
                this.toggleSubtasks(taskId);
            });
        });
    }
    
    toggleSubtasks(parentId) {
        const childrenContainer = document.querySelector(`[data-children-of="${parentId}"]`);
        const parentElement = document.querySelector(`[data-task-id="${parentId}"]`);
        const collapseBtn = parentElement.querySelector('.collapse-btn');
        
        if (childrenContainer) {
            childrenContainer.classList.toggle('collapsed');
            collapseBtn.classList.toggle('collapsed');
        }
    }
    
    setupAddSubtaskButtons() {
        document.querySelectorAll('.add-subtask-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const parentId = btn.dataset.parentId;
                this.showSubtaskInput(parentId);
            });
        });
    }
    
    showSubtaskInput(parentId) {
        // Implementation for inline subtask creation
        // Follow similar patterns to existing task creation
    }
}

// Initialize the enhanced class
document.addEventListener('DOMContentLoaded', () => {
    new HierarchicalTaskReordering();
});
```

**Key Compatibility Points:**
1. **Inheritance**: Extends existing `TaskReordering` class to preserve all current functionality
2. **Error Handling**: Reuses existing `showError()`, `showSuccess()`, and CSRF token methods
3. **Animation**: Leverages existing `animateDrop()` method for smooth transitions
4. **Loading States**: Uses same opacity pattern during API calls
5. **API Pattern**: Follows same fetch/error handling structure as `saveNewOrder()`
6. **Placeholder System**: Integrates with existing placeholder creation and management
```

### Phase 4: Advanced Features

#### 4.1 Subtask Progress Tracking
```javascript
// Calculate parent task completion based on subtasks
class TaskProgressTracker {
    calculateParentProgress(parentId) {
        const subtasks = document.querySelectorAll(`[data-parent-id="${parentId}"]`);
        const completed = Array.from(subtasks).filter(task => 
            task.querySelector('input[type="checkbox"]').checked
        ).length;
        
        const progress = subtasks.length > 0 ? (completed / subtasks.length) * 100 : 0;
        this.updateProgressBar(parentId, progress);
    }
    
    updateProgressBar(parentId, progress) {
        const progressBar = document.querySelector(`[data-task-id="${parentId}"] .progress-bar`);
        if (progressBar) {
            progressBar.style.width = `${progress}%`;
            progressBar.setAttribute('aria-valuenow', progress);
        }
    }
}
```

#### 4.2 Bulk Operations
```python
@bp.route('/tasks/bulk', methods=['POST'])
@login_required
def bulk_task_operations():
    """Handle bulk operations on tasks and their subtasks"""
    operation = request.json.get('operation')  # 'delete', 'complete', 'move'
    task_ids = request.json.get('task_ids', [])
    
    if operation == 'delete':
        # Delete task and all subtasks recursively
        for task_id in task_ids:
            delete_task_recursively(task_id)
```

## Implementation Phases

### Phase 1: Foundation (Week 1-2)
- [ ] Database schema updates
- [ ] Migration scripts
- [ ] Basic hierarchical CRUD operations
- [ ] Unit tests for database operations

### Phase 2: Backend API (Week 2-3)
- [ ] New API endpoints
- [ ] Hierarchical query optimization
- [ ] Error handling and validation
- [ ] API documentation

### Phase 3: Frontend UI (Week 3-4)
- [ ] Visual hierarchy implementation
- [ ] Basic drag-and-drop for subtask creation
- [ ] Collapse/expand functionality
- [ ] Responsive design adjustments

### Phase 4: Advanced Features (Week 4-5)
- [ ] Progress tracking
- [ ] Bulk operations
- [ ] Performance optimizations
- [ ] Mobile touch support

### Phase 5: Testing & Polish (Week 5-6)
- [ ] Comprehensive testing
- [ ] Performance testing
- [ ] User experience refinement
- [ ] Documentation updates

## Technical Considerations

### Performance Optimization
1. **Materialized Path**: Using `path` field for efficient tree queries
2. **Lazy Loading**: Load subtasks only when expanded
3. **Caching**: Cache frequently accessed task trees
4. **Database Indexes**: Proper indexing on hierarchical fields

### Edge Cases to Handle
1. **Circular References**: Prevent tasks from becoming their own descendants
2. **Depth Limits**: Set reasonable maximum nesting depth (e.g., 5 levels)
3. **Orphaned Tasks**: Handle parent deletion gracefully
4. **Concurrent Modifications**: Handle simultaneous edits

### Mobile Considerations
1. **Touch Events**: Implement touch-friendly drag-and-drop
2. **Small Screens**: Adaptive UI for hierarchy display
3. **Performance**: Optimize for mobile processors

## Success Metrics

### Functional Requirements
- ✅ Users can create unlimited subtask levels (within reasonable limits)
- ✅ Drag-and-drop creates subtask relationships intuitively
- ✅ Tasks can be reordered within their hierarchy level
- ✅ Subtasks can be converted to parent tasks
- ✅ Progress tracking works correctly

### Performance Requirements
- ✅ Task tree loads in <200ms for 100+ tasks
- ✅ Drag-and-drop responds in <50ms
- ✅ Database queries use indexes efficiently
- ✅ Mobile performance acceptable

### User Experience Requirements
- ✅ Intuitive visual hierarchy
- ✅ Clear drag-and-drop feedback
- ✅ Smooth animations and transitions
- ✅ Accessible design for screen readers

## Files to Modify/Create

### Backend Files
- `schema.sql` - Updated schema
- `pomodoro/routes/home.py` - New endpoints and logic
- `pomodoro/models/task.py` - New task model (if extracting from routes)
- `migrations/001_add_hierarchy.sql` - Database migration

### Frontend Files
- `pomodoro/templates/home/index.html` - Updated task structure
- `pomodoro/static/js/hierarchical-tasks.js` - New JavaScript file
- `pomodoro/static/css/hierarchy.css` - New CSS file
- `pomodoro/static/js/home.js` - Enhanced existing functionality

### Test Files
- `tests/test_task_hierarchy.py` - Backend tests
- `tests/test_hierarchical_ui.py` - Frontend tests
- `tests/test_performance.py` - Performance tests

## Conclusion

This roadmap provides a comprehensive approach to implementing hierarchical subtasks while building upon the existing drag-and-drop infrastructure. The phased approach ensures manageable development cycles and allows for testing and refinement at each stage.

The key success factors will be:
1. **Intuitive UX**: Making hierarchy creation feel natural
2. **Performance**: Ensuring the app remains fast with large task trees
3. **Robustness**: Handling edge cases and errors gracefully
4. **Accessibility**: Maintaining screen reader compatibility

The implementation will transform the flat task list into a powerful hierarchical task management system while preserving the app's simplicity and performance.
