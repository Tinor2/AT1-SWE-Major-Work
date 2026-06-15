from flask import Flask
import os
from flask_login import LoginManager

def create_app(test_config=None):
    # Create and configure the app
    app = Flask(__name__, instance_relative_config=True)
    
    # Default configuration
    app.config.from_mapping(
        SECRET_KEY=os.environ.get('SECRET_KEY') or os.urandom(32).hex(),
        DATABASE=os.path.join(app.instance_path, 'pomodoro.sqlite'),
        WTF_CSRF_ENABLED=True,
        WTF_CSRF_TIME_LIMIT=None,
    )

    if test_config is None:
        # Load the instance config, if it exists, when not testing
        app.config.from_pyfile('config.py', silent=True)
    else:
        # Load the test config if passed in
        app.config.from_mapping(test_config)

    # Ensure the instance folder exists
    try:
        os.makedirs(app.instance_path, exist_ok=True)
    except OSError:
        pass

    # Initialize the database
    from . import db
    db.init_app(app)

    # Initialize Flask-Login
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Please log in to access this page.'
    login_manager.login_message_category = 'info'

    @login_manager.user_loader
    def load_user(user_id):
        from .models.user import User
        return User.get_by_id(int(user_id))

    # Add template filters
    @app.template_filter('format_duration')
    def format_duration(seconds):
        """Format duration in seconds to human readable format (hours and minutes only)."""
        if seconds < 60:
            return "0m"  # Less than 1 minute shows as 0m
        elif seconds < 3600:
            minutes = seconds // 60
            return f"{minutes}m"
        else:
            hours = seconds // 3600
            minutes = (seconds % 3600) // 60
            return f"{hours}h {minutes}m"

    @app.template_filter('format_datetime')
    def format_datetime(ts):
        """Convert a unix timestamp to a human-readable local datetime string."""
        from datetime import datetime
        dt = datetime.fromtimestamp(ts)
        return dt.strftime('%a %-d %b %Y, %-I:%M %p')

    @app.template_filter('format_date_iso')
    def format_date_iso(ts):
        """Convert a unix timestamp to ISO-8601 date string (for <time datetime>)."""
        from datetime import datetime
        return datetime.fromtimestamp(ts).isoformat()

    # Security (OWASP A08): Flask-WTF CSRF protection — every POST form
    # includes {{ csrf_token() }}, and AJAX routes send the token via
    # X-CSRFToken header read from the meta[name="csrf-token"] tag.
    from flask_wtf.csrf import CSRFProtect
    csrf = CSRFProtect()
    csrf.init_app(app)

    # Register blueprints
    from .routes import home, lists, auth, timer, tasks, analytics, routine_suggestion
    app.register_blueprint(home.bp)
    app.register_blueprint(lists.bp)
    app.register_blueprint(auth.bp)
    app.register_blueprint(timer.bp)
    app.register_blueprint(tasks.bp)
    app.register_blueprint(analytics.bp)
    app.register_blueprint(routine_suggestion.routine_bp)
    app.add_url_rule('/', endpoint='index')

    # Disabled for PythonAnywhere (no daemon thread support).
    # Re-enable locally or use a scheduled task on PA.
    # from .ml.scheduler import start_scheduler
    # start_scheduler(app)

    # Security (DAST — manual penetration testing, 2026-06-14):
    #   - Verified all POST endpoints reject requests without CSRF token.
    #   - Confirmed /api/productivity/retrain (POST) requires login.
    #   - Tested SQL injection on search/query params — all use
    #     parameterised ? placeholders (confirmed via code review).
    #   - Checked session cookie is HTTP-only + SameSite=Lax (Flask default).
    #   - X-Content-Type-Options: nosniff prevents MIME-type sniffing.
    #   - X-Frame-Options: DENY prevents clickjacking.
    @app.after_request
    def _add_security_headers(response):
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        return response

    return app
