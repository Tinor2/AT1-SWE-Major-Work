from flask import Flask
import os
from flask_login import LoginManager

def create_app(test_config=None):
    # Create and configure the app
    app = Flask(__name__, instance_relative_config=True)
    
    # Default configuration
    app.config.from_mapping(
        SECRET_KEY='dev',
        DATABASE=os.path.join(app.instance_path, 'pomodoro.sqlite'),
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

    # Register blueprints
    from .routes import home, lists, auth, timer, tasks
    app.register_blueprint(home.bp)
    app.register_blueprint(lists.bp)
    app.register_blueprint(auth.bp)
    app.register_blueprint(timer.bp)
    app.register_blueprint(tasks.bp)
    app.add_url_rule('/', endpoint='index')

    return app
