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

    # Security (OWASP A08): JSON API blueprints use X-CSRFToken header (not
    # form fields), so they are exempt from form-based CSRF enforcement.
    csrf.exempt(routine_suggestion.routine_bp)

    # Disabled for PythonAnywhere (no daemon thread support).
    # Re-enable locally or use a scheduled task on PA.
    # from .ml.scheduler import start_scheduler
    # start_scheduler(app)

    # Security: harden response headers against common web attacks.
    @app.after_request
    def _add_security_headers(response):
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        return response

    return app
