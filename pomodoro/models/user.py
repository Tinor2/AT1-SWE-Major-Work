from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from .. import db

class User(UserMixin):
    def __init__(self, id=None, username=None, email=None, password_hash=None, created_at=None, last_login=None, profile_picture=None):
        self.id = id
        self.username = username
        self.email = email
        self.password_hash = password_hash
        self.created_at = created_at
        self.last_login = last_login
        self.profile_picture = profile_picture
    
    @staticmethod
    def get_by_id(user_id):
        """Get user by ID."""
        database = db.get_db()
        user_data = database.execute(
            'SELECT * FROM users WHERE id = ?', (user_id,)
        ).fetchone()
        if user_data:
            return User(**user_data)
        return None
    
    @staticmethod
    def get_by_username(username):
        """Get user by username."""
        database = db.get_db()
        user_data = database.execute(
            'SELECT * FROM users WHERE username = ?', (username,)
        ).fetchone()
        if user_data:
            return User(**user_data)
        return None
    
    @staticmethod
    def get_by_email(email):
        """Get user by email."""
        database = db.get_db()
        user_data = database.execute(
            'SELECT * FROM users WHERE email = ?', (email,)
        ).fetchone()
        if user_data:
            return User(**user_data)
        return None
    
    @staticmethod
    def create(username, email, password):
        """Create a new user with default data."""
        password_hash = generate_password_hash(password)
        database = db.get_db()
        cursor = database.execute(
            'INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)',
            (username, email, password_hash)
        )
        database.commit()
        
        # Get the new user ID
        user_id = cursor.lastrowid
        
        # Seed default data for the new user
        try:
            from .. import db as db_module
            db_module.seed_default_data(user_id)
        except Exception as e:
            print(f"Warning: Failed to seed default data for user {user_id}: {e}")
        
        return User.get_by_id(user_id)
    
    def check_password(self, password):
        """Check if the provided password matches the stored hash."""
        return check_password_hash(self.password_hash, password)
    
    def update_last_login(self):
        """Update the last login timestamp."""
        database = db.get_db()
        database.execute(
            'UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE id = ?',
            (self.id,)
        )
        database.commit()
    
    def update_profile_picture(self, profile_picture_path):
        """Update the user's profile picture."""
        database = db.get_db()
        database.execute(
            'UPDATE users SET profile_picture = ? WHERE id = ?',
            (profile_picture_path, self.id)
        )
        database.commit()
        self.profile_picture = profile_picture_path
    
    def to_dict(self):
        """Convert user object to dictionary."""
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'created_at': self.created_at,
            'last_login': self.last_login,
            'profile_picture': self.profile_picture
        }
