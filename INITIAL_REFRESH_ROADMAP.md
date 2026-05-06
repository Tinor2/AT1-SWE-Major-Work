# Pomodoro App — Refactor Roadmap

Each phase is self-contained and leaves the app fully working before you move to the next one.
Complete phases in order. Check off each task as you go.

---

## Phase 1 — Delete Dead Files

> **Goal:** Remove noise from the repo. No code changes, no risk.

- [ ] Delete `pomodoro/static/js/unified-drag-controller-OLD.js`
- [ ] Delete `pomodoro/static/js/task-reorder.js`
- [ ] Delete `pomodoro/static/js/hierarchical-tasks.js`
- [ ] Delete `pomodoro/templates/home/index-OLD.html`
- [ ] Delete `schema-backup.sql`
- [ ] Delete `cookies.txt`
- [ ] Delete `pomodoro/templates/auth/__init__.py` (Python file in a templates folder)
- [ ] Move `OUTLINE.md` → `docs/OUTLINE.md` (create `docs/` folder)

**Verify:** Run `flask run` and confirm the home page, lists page, and login all load correctly.

---

## Phase 2 — Fix the Schema / Migration Mess

> **Goal:** One single source of truth for the database schema. No duplicate column-creation logic.

### 2a — Create a migrations runner

Create a new file `pomodoro/migrations.py`:

```python
# pomodoro/migrations.py
import os
import sqlite3

MIGRATIONS_DIR = os.path.join(os.path.dirname(__file__), '..', 'migrations')

def run_pending_migrations(db: sqlite3.Connection):
    """Apply any migration SQL files that have not been run yet."""
    db.execute("""
        CREATE TABLE IF NOT EXISTS schema_migrations (
            filename TEXT PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    db.commit()

    applied = {row[0] for row in db.execute("SELECT filename FROM schema_migrations")}

    migration_files = sorted(
        f for f in os.listdir(MIGRATIONS_DIR)
        if f.endswith('.sql') and f not in applied
    )

    for filename in migration_files:
        path = os.path.join(MIGRATIONS_DIR, filename)
        with open(path) as f:
            sql = f.read()
        try:
            db.executescript(sql)
            db.execute("INSERT INTO schema_migrations (filename) VALUES (?)", (filename,))
            db.commit()
            print(f"Applied migration: {filename}")
        except sqlite3.Error as e:
            print(f"Migration failed ({filename}): {e}")
            raise
```

### 2b — Delete `_ensure_schema()` from `db.py`

- [ ] Remove the entire `_ensure_schema()` function from `pomodoro/db.py`
- [ ] Remove the call `_ensure_schema(g.db)` inside `get_db()`
- [ ] Add this import and call inside `get_db()` instead:
  ```python
  from .migrations import run_pending_migrations
  run_pending_migrations(g.db)
  ```

### 2c — Rename and order the existing migration files

Rename the files in `migrations/` so they run in a guaranteed order:

| Old filename | New filename |
|---|---|
| `001_add_hierarchy.sql` | `001_add_hierarchy.sql` ✓ already correct |
| `002_add_timer_state.sql` | `002_add_timer_state.sql` ✓ already correct |
| `003_add_current_phase.sql` | `003_add_current_phase.sql` ✓ already correct |
| `004_add_profile_picture.sql` | `004_add_profile_picture.sql` ✓ already correct |
| `add_user_tags.sql` | rename → `005_add_user_tags.sql` |

- [ ] Rename `migrations/add_user_tags.sql` → `migrations/005_add_user_tags.sql`

**Verify:** Drop your dev database (`instance/pomodoro.sqlite`), run `flask init-db`, then `flask run`. All tables should be created and migrations applied cleanly.

---

## Phase 3 — Add `routes/__init__.py`

> **Goal:** Make the routes package explicit so imports don't work by accident.

- [ ] Create `pomodoro/routes/__init__.py` with contents:

```python
# pomodoro/routes/__init__.py
```

That's it — an empty file is enough.

**Verify:** `flask run` still works.

---

## Phase 4 — Extract Timer Routes into Their Own File

> **Goal:** `home.py` currently has ~300 lines of timer API endpoints mixed with page rendering. Split them out.

### 4a — Create `pomodoro/routes/timer.py`

- [ ] Create `pomodoro/routes/timer.py`
- [ ] Move these route functions from `home.py` into `timer.py` (cut, don't copy):
  - `get_timer_status()`
  - `start_timer()`
  - `pause_timer()`
  - `reset_timer()`
  - `skip_timer()`
  - `reset_sets()`
- [ ] Move the helper functions these use (cut from `home.py`):
  - `calculate_remaining_time()`
  - `get_next_phase()`
  - `update_timer_state()`
- [ ] Add the blueprint boilerplate at the top of `timer.py`:

```python
from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from datetime import datetime, timezone

bp = Blueprint('timer', __name__, url_prefix='/timer')

def get_db():
    from .. import db
    return db.get_db()
```

- [ ] Update all route decorators in `timer.py` — change `@bp.route('/timer/...')` to `@bp.route('/...')` since the blueprint already has `url_prefix='/timer'`

### 4b — Register the new blueprint

- [ ] Open `pomodoro/__init__.py`
- [ ] Add `from .routes import home, lists, auth, timer` 
- [ ] Add `app.register_blueprint(timer.bp)` alongside the other blueprint registrations

### 4c — Clean up `home.py`

- [ ] Remove the now-moved functions and their imports from `home.py`
- [ ] `home.py` should now only contain: `index()`, task routes (`add_task`, `toggle_task`, `delete_task`, `update_task`, etc.), tag routes, and the hierarchy helpers

**Verify:** Start the app. Test the timer start/pause/skip buttons. Test adding and deleting tasks.

---

## Phase 5 — Extract Task Routes into Their Own File

> **Goal:** `home.py` is still too large. Task CRUD belongs in `routes/tasks.py`.

### 5a — Create `pomodoro/routes/tasks.py`

- [ ] Create `pomodoro/routes/tasks.py`
- [ ] Move these from `home.py`:
  - `task_detail()`
  - `add_task()`
  - `toggle_task()`
  - `delete_task()`
  - `update_tags()`
  - `update_tags_ajax()`
  - `manage_tags()`
  - `manage_single_tag()`
  - `reorder_tasks()`
  - `update_task_hierarchy()`
  - `update_task()`
  - `create_subtask()`
  - `move_task()`
  - `get_task_tree()`
- [ ] Add blueprint boilerplate at the top:

```python
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user

bp = Blueprint('tasks', __name__)

def get_db():
    from .. import db
    return db.get_db()
```

- [ ] Move the helper functions used by tasks (cut from `home.py`):
  - `get_tasks_with_hierarchy()`
  - `is_descendant()`
  - `update_descendants_paths()`

### 5b — Register the blueprint

- [ ] In `pomodoro/__init__.py`, add `from .routes import home, lists, auth, timer, tasks`
- [ ] Add `app.register_blueprint(tasks.bp)`

### 5c — What remains in `home.py`

After this phase, `home.py` should only contain:
- `index()` — the main page render
- `render_task_hierarchy()`, `render_parent_task()`, `render_subtask()` — temporarily (Phase 6 removes these)

**Verify:** Full smoke test — add task, toggle task, delete task, reorder, add subtask, edit task name inline.

---

## Phase 6 — Replace Python HTML Generation with a Jinja Template

> **Goal:** The three `render_*` functions in `home.py` build raw HTML strings in Python. This is the biggest architectural problem. Replace them with a proper recursive Jinja2 template.

### 6a — Create the task partial template

- [ ] Create folder `pomodoro/templates/home/partials/`
- [ ] Create `pomodoro/templates/home/partials/task_item.html`:

```html
{# Recursive task item partial #}
{# Call with: include 'home/partials/task_item.html' with task=task, all_tasks=all_tasks #}

{% set subtasks = all_tasks | selectattr('parent_id', 'equalto', task.id) | list %}
{% set is_parent = subtasks | length > 0 %}
{% set tags_list = (task.tags or '').split(',') | select | list %}
{% set color_map = {
    '#ff5252': 'red', '#ff9800': 'orange', '#ffeb3b': 'yellow',
    '#4caf50': 'green', '#00bcd4': 'cyan', '#3f51b5': 'indigo',
    '#9c27b0': 'purple', '#795548': 'brown'
} %}

<li class="task-item {% if task.is_done %}completed{% endif %} {% if is_parent %}parent{% endif %} {% if task.parent_id %}subtask{% endif %}"
    data-task-id="{{ task.id }}"
    draggable="true">

    <div class="task-header">
        {% if is_parent %}
            <button type="button" class="collapse-btn" aria-label="Toggle subtasks">▼</button>
        {% endif %}
        <div class="drag-handle">⋮⋮</div>

        <form method="post" action="{{ url_for('tasks.toggle_task', id=task.id) }}" style="display:inline;">
            <input type="checkbox" {% if task.is_done %}checked{% endif %} onchange="this.form.submit()">
        </form>

        <span class="task-content" data-task-id="{{ task.id }}">{{ task.content }}</span>

        {% if tags_list %}
            <div class="task-tags-display">
                {% for color in tags_list %}
                    {% set cc = color_map.get(color) %}
                    {% if cc %}
                        <span class="tag-dot tag-{{ cc }}" title="{{ color }}"></span>
                    {% endif %}
                {% endfor %}
            </div>
        {% endif %}

        <form method="post" action="{{ url_for('tasks.update_tags', id=task.id) }}" class="tag-form" data-task-id="{{ task.id }}">
            <input type="hidden" name="tags" value="{{ task.tags or '' }}">
            <button type="button" class="tag-btn" aria-label="Edit tags">
                <img src="{{ url_for('static', filename='assets/tag.png') }}" alt="Tags" class="tag-icon">
            </button>
            <div class="tag-menu" role="menu" aria-hidden="true">
                <div class="tag-menu-header">
                    <span class="tag-menu-title">Tags</span>
                    <button type="button" class="tag-settings-btn" aria-label="Tag settings" title="Manage tags">
                        <img src="{{ url_for('static', filename='assets/setting.png') }}" alt="Settings" style="height:16px;width:16px;">
                    </button>
                </div>
                <div class="tag-menu-grid">
                    {% for color, cls in color_map.items() %}
                        <button type="button" class="color-choice tag-{{ cls }}" data-color="{{ color }}" title="{{ color }}"></button>
                    {% endfor %}
                </div>
                <div class="tag-menu-actions">
                    <button type="button" class="btn btn-secondary tag-clear">Clear</button>
                    <button type="submit" class="btn btn-primary tag-apply">Apply</button>
                </div>
            </div>
        </form>

        <button type="button" class="delete-btn"
                data-task-id="{{ task.id }}"
                data-task-content="{{ task.content }}"
                aria-label="Delete task">
            <img src="{{ url_for('static', filename='assets/delete.png') }}" alt="Delete" class="delete-icon">
        </button>
    </div>

    {% if subtasks %}
        <ul class="task-children">
            {% for subtask in subtasks %}
                {% include 'home/partials/task_item.html' with context %}
            {% endfor %}
        </ul>
    {% endif %}
</li>
```

### 6b — Update `home/index.html` to use the partial

- [ ] Open `pomodoro/templates/home/index.html`
- [ ] Replace `{{ task_hierarchy_html|safe }}` with:

```html
<ul class="task-list" data-list-id="{{ active_list.id }}">
    {% set root_tasks = tasks | selectattr('parent_id', 'none') | list %}
    {% if root_tasks %}
        {% for task in root_tasks %}
            {% include 'home/partials/task_item.html' with context %}
        {% endfor %}
    {% else %}
        <li class="empty-state">No tasks yet. Add one above!</li>
    {% endif %}
</ul>
```

### 6c — Update the `index()` route in `home.py`

- [ ] Change the route to pass a flat `tasks` list instead of pre-rendered HTML:

```python
@bp.route('/')
@login_required
def index():
    db = get_db()
    active_list = db.execute(
        'SELECT * FROM lists WHERE is_active = 1 AND user_id = ?',
        (current_user.id,)
    ).fetchone()

    tasks = []
    if active_list:
        tasks = db.execute(
            '''SELECT * FROM tasks WHERE list_id = ? AND user_id = ?
               ORDER BY level ASC, position ASC''',
            (active_list['id'], current_user.id)
        ).fetchall()

    return render_template('home/index.html', active_list=active_list, tasks=tasks)
```

### 6d — Delete the now-unused Python HTML functions

- [ ] Delete `render_task_hierarchy()` from `home.py`
- [ ] Delete `render_parent_task()` from `home.py`
- [ ] Delete `render_subtask()` from `home.py`
- [ ] Remove the `task_hierarchy_html` variable and its usages

**Verify:** Full task render test — tasks show, subtasks are indented, tags display, collapse button works, drag handles present.

---

## Phase 7 — Add a Models Layer

> **Goal:** Stop repeating the same DB queries in every route. Add thin model helpers.

### 7a — Create `pomodoro/models/list.py`

- [ ] Create `pomodoro/models/list.py`:

```python
# pomodoro/models/list.py
from ..db import get_db

def get_active_list(user_id):
    db = get_db()
    return db.execute(
        'SELECT * FROM lists WHERE is_active = 1 AND user_id = ?',
        (user_id,)
    ).fetchone()

def get_all_lists(user_id):
    db = get_db()
    return db.execute(
        'SELECT * FROM lists WHERE user_id = ? ORDER BY name',
        (user_id,)
    ).fetchall()

def get_list_by_id(list_id, user_id):
    db = get_db()
    return db.execute(
        'SELECT * FROM lists WHERE id = ? AND user_id = ?',
        (list_id, user_id)
    ).fetchone()

def set_active_list(list_id, user_id):
    db = get_db()
    db.execute('UPDATE lists SET is_active = 0 WHERE user_id = ?', (user_id,))
    db.execute('UPDATE lists SET is_active = 1 WHERE id = ? AND user_id = ?', (list_id, user_id))
    db.commit()
```

### 7b — Create `pomodoro/models/task.py`

- [ ] Create `pomodoro/models/task.py`:

```python
# pomodoro/models/task.py
from ..db import get_db

def get_tasks_for_list(list_id, user_id):
    db = get_db()
    return db.execute(
        '''SELECT * FROM tasks WHERE list_id = ? AND user_id = ?
           ORDER BY level ASC, position ASC''',
        (list_id, user_id)
    ).fetchall()

def get_task_by_id(task_id, user_id):
    db = get_db()
    return db.execute(
        'SELECT * FROM tasks WHERE id = ? AND user_id = ?',
        (task_id, user_id)
    ).fetchone()

def get_next_position(list_id, user_id, parent_id=None):
    db = get_db()
    result = db.execute(
        'SELECT COALESCE(MAX(position), -1) FROM tasks WHERE list_id = ? AND user_id = ? AND parent_id IS ?',
        (list_id, user_id, parent_id)
    ).fetchone()
    return result[0] + 1
```

### 7c — Update routes to use models

- [ ] In `home.py`, replace the `db.execute(... active list ...)` pattern with `from ..models.list import get_active_list`
- [ ] In `timer.py`, replace all `db.execute(... active list ...)` with `get_active_list(current_user.id)`
- [ ] In `lists.py`, replace repeated queries with `get_list_by_id()` and `get_all_lists()`
- [ ] In `tasks.py`, replace `db.execute(... SELECT * FROM tasks ...)` patterns with model functions

**Verify:** Run the full app. All pages should work identically.

---

## Phase 8 — Move Seed Data Out of `db.py`

> **Goal:** `db.py` should only handle connections and schema init. The 100-line `seed_default_data()` function belongs elsewhere.

- [ ] Create `pomodoro/fixtures.py`
- [ ] Cut `seed_default_data()` entirely from `db.py` and paste it into `fixtures.py`
- [ ] Add the import at the top of `fixtures.py`:
  ```python
  from .db import get_db
  ```
- [ ] In `db.py`, update the import inside `seed_data_command()`:
  ```python
  from .fixtures import seed_default_data
  ```
- [ ] In `models/user.py`, update the import:
  ```python
  from ..fixtures import seed_default_data
  ```

**Verify:** Register a new user and confirm the tutorial list and default tasks are created.

---

## Phase 9 — Final Cleanup

> **Goal:** Tidy up remaining small issues.

- [ ] Add `instance/` to `.gitignore` if not already present (the SQLite file shouldn't be committed)
- [ ] Add `pomodoro/static/uploads/` to `.gitignore` (user profile pictures)
- [ ] Review `requirements.txt` — uncomment `Flask-WTF` and add CSRF protection properly, or remove the commented lines
- [ ] Add a `SECRET_KEY` note to `README.md` — the current hardcoded `'dev'` key in `__init__.py` must be overridden via environment variable in production
- [ ] Update `README.md` with the actual commands needed:
  ```bash
  python -m venv venv
  source venv/bin/activate
  pip install -r requirements.txt
  flask init-db
  flask run --port 8000 --debug
  ```
- [ ] Delete the `pomodoro/routes/__init__.py` placeholder comment if it has one (keep it empty or with just a docstring)

---

## Final State Checklist

After all phases are complete, verify the file structure matches this:

```
pomodoro_app/
├── app.py
├── schema.sql
├── requirements.txt
├── docs/
│   └── OUTLINE.md
├── migrations/
│   ├── 001_add_hierarchy.sql
│   ├── 002_add_timer_state.sql
│   ├── 003_add_current_phase.sql
│   ├── 004_add_profile_picture.sql
│   └── 005_add_user_tags.sql
└── pomodoro/
    ├── __init__.py
    ├── db.py
    ├── fixtures.py
    ├── migrations.py
    ├── models/
    │   ├── __init__.py
    │   ├── user.py
    │   ├── list.py
    │   └── task.py
    ├── routes/
    │   ├── __init__.py
    │   ├── auth.py
    │   ├── home.py        ← index() only
    │   ├── tasks.py       ← all task/tag CRUD
    │   ├── timer.py       ← all timer endpoints
    │   └── lists.py
    ├── templates/
    │   ├── base.html
    │   ├── auth/
    │   ├── home/
    │   │   ├── index.html
    │   │   ├── task_detail.html
    │   │   └── partials/
    │   │       └── task_item.html
    │   ├── lists/
    │   └── errors/
    └── static/
        ├── css/
        │   ├── style.css
        │   ├── hierarchy.css
        │   ├── hierarchy-feedback.css
        │   ├── modal.css
        │   └── tag-settings.css
        └── js/
            ├── home.js
            ├── timer.js
            ├── unified-drag-controller.js
            ├── collapsible-tasks.js
            ├── delete-modal.js
            ├── list-delete-modal.js
            ├── lists.js
            ├── logout-modal.js
            └── task-edit.js
```

**Final smoke test:**
- [ ] Register a new user → tutorial list appears
- [ ] Add a task → appears in list
- [ ] Add a subtask → appears indented
- [ ] Start timer → counts down
- [ ] Pause/reset/skip timer → works correctly
- [ ] Switch lists → timer pauses, tasks update
- [ ] Delete a task → confirmation modal, task removed
- [ ] Drag to reorder → order persists on reload