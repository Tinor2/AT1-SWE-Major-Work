# Hierarchical View Order Fix Plan

## 🎯 Problem Statement
When tasks are reorganized into hierarchies, the view order becomes incorrect. Tasks don't maintain their logical sequence when parent-child relationships are created.

## 📋 Current Issues & Examples

### **Issue 1: Incorrect Order After Hierarchy Creation**
**Expected Behavior**: `{A,B,C,D}` → `{A,B,C:{D}}` should display as `A,B,C,D`
**Actual Behavior**: Displays as `A,C,B,D`

**Expected Behavior**: `{A,B,C,D}` → `{A:{B},C:{D}}` should display as `A,B,C,D`  
**Actual Behavior**: Displays as `A,C,B,D`

### **Issue 2: Correct Behavior on Deletion**
- When parent `C` is deleted, child `D` is correctly deleted
- Remaining tasks display in correct order: `A,B`

## 🔍 Root Cause Analysis

### **Database Schema**
```sql
CREATE TABLE tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    position INTEGER DEFAULT 0,           -- For ordering within same level
    parent_id INTEGER DEFAULT NULL,        -- For hierarchy
    level INTEGER DEFAULT 0,               -- Hierarchy depth
    path TEXT DEFAULT NULL,                -- Materialized path (e.g., "1/5/12")
    list_id INTEGER NOT NULL,              -- List grouping
    -- ... other fields
);
```

### **Current Query Logic**
The current query likely orders by `position` only, without considering hierarchical relationships:

```sql
-- PROBLEMATIC: Only orders by position, ignores hierarchy
SELECT * FROM tasks 
WHERE list_id = ? AND user_id = ? 
ORDER BY position ASC;
```

### **Why This Fails**
1. **Position is relative to parent**: Each parent has its own position sequence
2. **Cross-level ordering**: Tasks at different levels shouldn't be compared by position
3. **Missing hierarchical context**: Query doesn't know about parent-child relationships

## 🛠️ Solution Strategy

### **Approach 1: Hierarchical Ordering with Path-Based Sorting**
Use the materialized `path` field to maintain proper hierarchical ordering.

#### **Phase 1: Update Position Management**
When creating hierarchy relationships, update positions to maintain logical order:

```python
def update_positions_for_hierarchy(task_id, new_parent_id, db):
    """Update positions when task becomes a subtask"""
    
    # 1. Get current positions
    dragged_task = db.execute('SELECT * FROM tasks WHERE id = ?', (task_id,)).fetchone()
    siblings = db.execute(
        'SELECT * FROM tasks WHERE parent_id = ? AND list_id = ? ORDER BY position',
        (new_parent_id, dragged_task['list_id'])
    ).fetchall()
    
    # 2. Update dragged task position to be after all siblings
    new_position = len(siblings) if siblings else 0
    
    # 3. Update dragged task
    db.execute(
        'UPDATE tasks SET parent_id = ?, position = ?, level = ?, path = ? WHERE id = ?',
        (new_parent_id, new_position, new_level, new_path, task_id)
    )
    
    # 4. Update positions of old siblings (fill the gap)
    db.execute(
        'UPDATE tasks SET position = position - 1 WHERE parent_id = ? AND position > ?',
        (dragged_task['parent_id'], dragged_task['position'])
    )
```

#### **Phase 2: Implement Hierarchical Ordering Query**
Create a query that respects both hierarchy and position:

```sql
-- SOLUTION: Order by path for hierarchical context, then by position within level
WITH RECURSIVE ordered_tasks AS (
    -- Base case: root level tasks
    SELECT id, content, parent_id, level, path, position, list_id, user_id
    FROM tasks 
    WHERE parent_id IS NULL AND list_id = ? AND user_id = ?
    
    UNION ALL
    
    -- Recursive case: get children in order
    SELECT t.id, t.content, t.parent_id, t.level, t.path, t.position, t.list_id, t.user_id
    FROM tasks t
    JOIN ordered_tasks ot ON t.parent_id = ot.id
    WHERE t.list_id = ? AND t.user_id = ?
)
SELECT * FROM ordered_tasks 
ORDER BY path, position;
```

### **Approach 2: Dual Ordering System**
Maintain both hierarchical position and global display order:

#### **Phase 1: Add Global Position Field**
```sql
ALTER TABLE tasks ADD COLUMN global_position INTEGER DEFAULT 0;
```

#### **Phase 2: Update Global Positions on Hierarchy Changes**
```python
def update_global_positions(list_id, db):
    """Recalculate global positions based on hierarchy"""
    
    # Get all tasks ordered hierarchically
    tasks = get_tasks_hierarchical_order(list_id, db)
    
    # Update global positions
    for i, task in enumerate(tasks):
        db.execute(
            'UPDATE tasks SET global_position = ? WHERE id = ?',
            (i, task['id'])
        )
```

#### **Phase 3: Use Global Position for Display**
```sql
-- Simple ordering by global position
SELECT * FROM tasks 
WHERE list_id = ? AND user_id = ? 
ORDER BY global_position ASC;
```

## 📅 Implementation Plan

### **Step 1: Fix Move Task Backend (Priority: High)**
- [ ] Update `move_task()` function to recalculate positions
- [ ] Ensure proper position updates for both old and new siblings
- [ ] Add global position recalculation

### **Step 2: Update Frontend Query (Priority: High)**
- [ ] Modify `get_tasks_with_hierarchy()` to use proper ordering
- [ ] Ensure hierarchical display respects logical order
- [ ] Test with various hierarchy scenarios

### **Step 3: Handle Edge Cases (Priority: Medium)**
- [ ] Multiple levels of nesting
- [ ] Moving tasks between different parents
- [ ] Moving subtasks to root level
- [ ] Circular reference prevention

### **Step 4: Performance Optimization (Priority: Low)**
- [ ] Add indexes for ordering queries
- [ ] Optimize recursive CTE performance
- [ ] Cache hierarchical order when possible

## 🧪 Edge Cases & Test Scenarios

### **Edge Case 1: Multi-Level Nesting**
**Scenario**: `{A,B,C,D}` → `{A:{B:{C}},D}`
**Expected**: Display as `A,B,C,D`
**Issues**: 
- Position updates across multiple levels
- Path recalculation for all descendants

### **Edge Case 2: Moving Between Parents**
**Scenario**: `{A:{B},C:{D}}` → Move `B` to be child of `C` → `{A,C:{D:{B}}}`
**Expected**: Display as `A,C,D,B`
**Issues**:
- Update old parent's sibling positions
- Update new parent's sibling positions
- Maintain global order

### **Edge Case 3: Moving to Root Level**
**Scenario**: `{A:{B},C:{D}}` → Move `B` to root → `{A,B,C:{D}}`
**Expected**: Display as `A,B,C,D`
**Issues**:
- Assign new root-level position
- Update old parent's positions
- Path recalculation

### **Edge Case 4: Reordering Within Hierarchy**
**Scenario**: `{A:{B,C},D}` → Reorder `B` and `C` → `{A:{C,B},D}`
**Expected**: Display as `A,C,B,D`
**Issues**:
- Position updates within same parent
- No global position changes needed

### **Edge Case 5: Complex Rearrangement**
**Scenario**: `{A,B,C,D}` → `{A:{D},B:{C}}`
**Expected**: Display as `A,D,B,C`
**Issues**:
- Multiple parent-child relationships
- Complex position calculations

## 🔧 Technical Implementation Details

### **Backend Changes Required**

#### **1. Update `move_task()` Function**
```python
@bp.route('/task/<int:id>/move', methods=['POST'])
@login_required
def move_task(id):
    # ... existing validation ...
    
    try:
        if operation == 'make_subtask' and new_parent_id:
            # Get current positions
            old_parent_id = task['parent_id']
            old_position = task['position']
            
            # Calculate new position (after existing siblings)
            max_sibling_position = db.execute(
                'SELECT COALESCE(MAX(position), -1) FROM tasks WHERE parent_id = ?',
                (new_parent_id,)
            ).fetchone()[0]
            new_position = max_sibling_position + 1
            
            # Update task hierarchy
            new_level = new_parent['level'] + 1
            new_path = f"{new_parent['path']}/{id}"
            
            db.execute(
                'UPDATE tasks SET parent_id = ?, level = ?, path = ?, position = ? WHERE id = ?',
                (new_parent_id, new_level, new_path, new_position, id)
            )
            
            # Update old siblings' positions (fill the gap)
            if old_parent_id is not None:
                db.execute(
                    'UPDATE tasks SET position = position - 1 WHERE parent_id = ? AND position > ?',
                    (old_parent_id, old_position)
                )
            
            # Update descendants' paths
            update_descendants_paths(id, new_path, new_level, db)
            
        # Recalculate global positions for the entire list
        recalculate_global_positions(task['list_id'], db)
        
        db.commit()
        return jsonify({'success': True})
        
    except Exception as e:
        db.rollback()
        return jsonify({'error': str(e)}), 500
```

#### **2. Add Global Position Recalculation**
```python
def recalculate_global_positions(list_id, db):
    """Recalculate global positions based on hierarchical order"""
    
    # Get tasks in hierarchical order
    tasks = db.execute('''
        WITH RECURSIVE task_tree AS (
            SELECT id, content, parent_id, level, path, position, 0 as depth
            FROM tasks WHERE parent_id IS NULL AND list_id = ?
            UNION ALL
            SELECT t.id, t.content, t.parent_id, t.level, t.path, t.position, tt.depth + 1
            FROM tasks t
            JOIN task_tree tt ON t.parent_id = tt.id
            WHERE t.list_id = ?
        )
        SELECT * FROM task_tree ORDER BY path, position
    ''', (list_id, list_id)).fetchall()
    
    # Update global positions
    for i, task in enumerate(tasks):
        db.execute(
            'UPDATE tasks SET global_position = ? WHERE id = ?',
            (i, task['id'])
        )
```

#### **3. Update Task Query**
```python
def get_tasks_with_hierarchy(list_id, user_id):
    """Get tasks ordered hierarchically"""
    db = get_db()
    
    return db.execute('''
        WITH RECURSIVE task_tree AS (
            SELECT id, content, parent_id, level, path, position, global_position
            FROM tasks 
            WHERE parent_id IS NULL AND list_id = ? AND user_id = ?
            
            UNION ALL
            
            SELECT t.id, t.content, t.parent_id, t.level, t.path, t.position, t.global_position
            FROM tasks t
            JOIN task_tree tt ON t.parent_id = tt.id
            WHERE t.list_id = ? AND t.user_id = ?
        )
        SELECT * FROM task_tree 
        ORDER BY global_position ASC
    ''', (list_id, user_id, list_id, user_id)).fetchall()
```

### **Database Migration Required**
```sql
-- Add global_position column
ALTER TABLE tasks ADD COLUMN global_position INTEGER DEFAULT 0;

-- Create index for performance
CREATE INDEX idx_tasks_global_position ON tasks(global_position);
CREATE INDEX idx_tasks_list_global_position ON tasks(list_id, global_position);

-- Update existing tasks
UPDATE tasks SET global_position = position WHERE parent_id IS NULL;
```

## 🎯 Success Criteria

### **Must Have**
- ✅ Tasks maintain logical order when creating hierarchies
- ✅ `{A,B,C,D}` → `{A,B,C:{D}}` displays as `A,B,C,D`
- ✅ `{A,B,C,D}` → `{A:{B},C:{D}}` displays as `A,B,C,D`
- ✅ Deleting parents correctly removes children
- ✅ Moving between parents maintains order

### **Nice to Have**
- ✅ Smooth animations during order changes
- ✅ Undo functionality for hierarchy operations
- ✅ Batch hierarchy operations
- ✅ Performance optimization for large lists

## 📊 Testing Checklist

### **Functional Tests**
- [ ] Create simple hierarchy: `{A,B,C,D}` → `{A,B,C:{D}}`
- [ ] Create complex hierarchy: `{A,B,C,D}` → `{A:{B},C:{D}}`
- [ ] Move between parents: `{A:{B},C:{D}}` → `{A,C:{D:{B}}}`
- [ ] Move to root: `{A:{B},C:{D}}` → `{A,B,C:{D}}`
- [ ] Multi-level nesting: `{A,B,C,D}` → `{A:{B:{C}},D}`
- [ ] Delete parent with children
- [ ] Reorder within same parent

### **Performance Tests**
- [ ] Large task lists (100+ tasks)
- [ ] Deep nesting (5+ levels)
- [ ] Frequent hierarchy changes
- [ ] Concurrent users

### **Edge Case Tests**
- [ ] Circular reference prevention
- [ ] Invalid parent IDs
- [ ] Database constraints
- [ ] Network errors during updates

---

*Plan Created: November 24, 2025*  
*Status: Ready to Implement*  
*Estimated Time: 3-4 hours*  
*Complexity: High*  

## 🚀 Implementation Priority

1. **Fix Backend Position Logic** (1.5 hours)
2. **Add Global Position Field** (0.5 hours)  
3. **Update Query Logic** (1 hour)
4. **Test Edge Cases** (1 hour)
5. **Performance Optimization** (0.5 hours)
