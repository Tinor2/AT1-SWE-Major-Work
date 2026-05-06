from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, abort, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import check_password_hash
from werkzeug.utils import secure_filename
import os
import uuid
from ..models.user import User

bp = Blueprint('auth', __name__, url_prefix='/auth')

@bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        remember = bool(request.form.get('remember'))
        
        if not username or not password:
            flash('Please enter both username and password.', 'error')
            return render_template('auth/login.html')
        
        user = User.get_by_username(username)
        if user and user.check_password(password):
            login_user(user, remember=remember)
            user.update_last_login()
            next_page = request.args.get('next')
            if next_page and next_page.startswith('/'):
                return redirect(next_page)
            return redirect(url_for('home.index'))
        else:
            flash('Invalid username or password.', 'error')
    
    return render_template('auth/login.html')

@bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        
        # Basic validation
        errors = []
        if not username:
            errors.append('Username is required.')
        elif len(username) < 3:
            errors.append('Username must be at least 3 characters long.')
        elif not username.replace('_', '').replace('-', '').isalnum():
            errors.append('Username can only contain letters, numbers, underscores, and hyphens.')
        
        if not email:
            errors.append('Email is required.')
        elif '@' not in email or '.' not in email.split('@')[-1]:
            errors.append('Please enter a valid email address.')
        
        if not password:
            errors.append('Password is required.')
        elif len(password) < 6:
            errors.append('Password must be at least 6 characters long.')
        
        if password != confirm_password:
            errors.append('Passwords do not match.')
        
        # Check if user already exists
        if User.get_by_username(username):
            errors.append('Username already exists.')
        
        if User.get_by_email(email):
            errors.append('Email already registered.')
        
        if errors:
            for error in errors:
                flash(error, 'error')
            return render_template('auth/register.html')
        
        # Create new user
        try:
            user = User.create(username, email, password)
            login_user(user)
            flash('Account created successfully! Welcome to Pomodoro Timer!', 'success')
            return redirect(url_for('home.index'))
        except Exception as e:
            current_app.logger.error(f"Error creating user: {e}")
            flash('An error occurred while creating your account. Please try again.', 'error')
    
    return render_template('auth/register.html')

@bp.route('/logout', methods=['POST'])
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('auth.login'))

@bp.route('/profile')
@login_required
def profile():
    return render_template('auth/profile.html', user=current_user)

@bp.route('/upload_profile_picture', methods=['POST'])
@login_required
def upload_profile_picture():
    if 'profile_picture' not in request.files:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': False, 'message': 'No file selected.'})
        flash('No file selected.', 'error')
        return redirect(url_for('auth.profile'))
    
    file = request.files['profile_picture']
    if file.filename == '':
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': False, 'message': 'No file selected.'})
        flash('No file selected.', 'error')
        return redirect(url_for('auth.profile'))
    
    # Check file extension
    allowed_extensions = {'png', 'jpg', 'jpeg', 'gif'}
    filename = secure_filename(file.filename)
    if not filename or '.' not in filename or filename.rsplit('.', 1)[1].lower() not in allowed_extensions:
        error_msg = 'Invalid file type. Please upload PNG, JPG, JPEG, or GIF.'
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': False, 'message': error_msg})
        flash(error_msg, 'error')
        return redirect(url_for('auth.profile'))
    
    # Generate unique filename
    file_extension = filename.rsplit('.', 1)[1].lower()
    unique_filename = f"{uuid.uuid4().hex}.{file_extension}"
    
    # Create upload directory if it doesn't exist
    upload_dir = os.path.join(current_app.static_folder, 'uploads', 'profile_pictures')
    os.makedirs(upload_dir, exist_ok=True)
    
    # Save file
    file_path = os.path.join(upload_dir, unique_filename)
    file.save(file_path)
    
    # Update user profile picture in database
    relative_path = os.path.join('uploads', 'profile_pictures', unique_filename).replace('\\', '/')
    current_user.update_profile_picture(relative_path)
    
    success_msg = 'Profile picture updated successfully!'
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({'success': True, 'message': success_msg, 'profile_picture': relative_path})
    
    flash(success_msg, 'success')
    return redirect(url_for('auth.profile'))
