🧭 Project Overview: Pomodoro + To-Do Web App
🌐 Goal

A Flask-based web app that combines:

A Pomodoro timer (linked to specific To-Do lists)

A To-Do list manager

A List selection page to manage multiple lists (each with its own Pomodoro settings and tasks)

🧩 Core Features Breakdown
1. Home Page (/)

Displays two main panels side-by-side:

Left panel: Pomodoro timer (for now just a placeholder with no timer logic yet)

Right panel: To-Do list for the currently active list.

The layout fills the screen width (minus small padding), so it feels clean and spacious.

Changing which list is active updates both:

The tasks shown

The Pomodoro settings (like session length, short break, long break, etc.)

2. List Selection Page (/lists)

Displays all lists (To-Do boards) in a responsive grid layout.

Each list shows:

Name

Optional description

Buttons for:

Select — activates this list on the homepage

Edit — opens a future settings page to modify Pomodoro and list values (placeholder for now)

Delete — removes the list from the database

You can also create a new list, which automatically creates:

A new entry in the lists table

A corresponding tasks table (or a linked set of rows in a shared tasks table)

🧱 Database Structure

We’ll use SQLite (as before), managed via db.py.

Tables
1. lists

Stores metadata and Pomodoro settings for each To-Do list.

CREATE TABLE lists (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    description TEXT,
    is_active BOOLEAN DEFAULT 0,
    pomo_session INTEGER DEFAULT 25,
    pomo_short_break INTEGER DEFAULT 5,
    pomo_long_break INTEGER DEFAULT 15,
    pomo_current_time INTEGER DEFAULT 0
);

2. tasks

Stores individual To-Do items linked to a list.

CREATE TABLE tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    list_id INTEGER NOT NULL,
    content TEXT NOT NULL,
    is_done BOOLEAN DEFAULT 0,
    FOREIGN KEY (list_id) REFERENCES lists (id) ON DELETE CASCADE
);


This structure allows:

Each list to have its own Pomodoro settings

Each list to hold multiple tasks

Switching the active list to automatically change the linked Pomodoro data

🗂️ Directory Structure

A clean organization helps avoid confusion later. Here’s how your new project might look:

pomodoro_app/
│
├── app.py                   # Main Flask entry point
│
├── pomodoro/                # Package for all app modules
│   ├── __init__.py          # Creates Flask app, registers blueprints
│   ├── db.py                # Database connection + init logic
│   ├── models.py            # (Optional) Helpers for interacting with DB tables
│   ├── routes/
│   │   ├── home.py          # Handles home page (timer + tasks)
│   │   └── lists.py         # Handles list selection and management
│   │
│   ├── templates/
│   │   ├── base.html        # Shared layout (navbar, CSS includes)
│   │   ├── home.html        # Home page (Pomodoro + To-Do)
│   │   └── lists.html       # List selection grid
│   │
│   ├── static/
│   │   ├── css/
│   │   │   ├── style.css    # Global styles (grid, layout, colors)
│   │   └── js/
│   │       ├── home.js      # Handles tasks and timer linkage
│   │       └── lists.js     # Handles list creation, selection, deletion
│   │
│   └── schema.sql           # SQL setup for lists and tasks tables
│
├── instance/
│   └── pomodoro.sqlite      # SQLite DB file
│
└── README.md

💡 Implementation Flow (Step-by-Step Roadmap)
Phase 1 – Base Setup

Initialize Flask app (app.py, __init__.py, db.py)

Create schema.sql with lists + tasks tables

Run flask init-db to initialize database

Phase 2 – Pages & Routing

/ → home.html (shows active list and blank Pomodoro)

/lists → lists.html (grid of all lists)

Create basic navigation bar between pages

Phase 3 – Link Database

Add logic in /lists page to:

Show all lists

Mark one as active

In / page, query:

The active list’s tasks

The Pomodoro settings for that list

Phase 4 – To-Do & Pomodoro Integration

When switching active list:

Update active list flag in DB

Reload / with new list’s tasks and Pomodoro settings

(Later) Add Pomodoro timer logic and controls

Phase 5 – UI Enhancements

Add edit/delete buttons for lists

Add add/edit/delete for tasks

Add clean CSS grid layout (similar to your screenshot)

🎨 Design Summary

Color palette: inspired by your uploaded image — red/orange accent, minimalist white background, black text.

Layout: two main panels filling screen width with small padding.

Font: clean sans-serif (e.g., Inter, Roboto).

Grid system: CSS Grid for the list selection page; Flexbox for the home layout.

🧠 Next Steps (Recommended)

✅ Set up the directory and schema.sql

✅ Configure Flask and db.py

🧩 Add home.py and lists.py routes (with templates)

🎨 Add basic front-end layout with placeholders

🔗 Connect database logic to display lists and tasks dynamically

Would you like me to generate the base Flask project (with folders, routes, and templates) exactly as described — ready for you to run flask run and see both / and /lists pages?
That would give you a clean, working foundation to start coding on top of.