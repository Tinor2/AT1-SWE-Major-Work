# Custom Error Pages

This application includes custom error pages to provide a better user experience when something goes wrong.

## Error Pages Included

### 404 - Page Not Found
- **Path**: `templates/errors/404.html`
- **Trigger**: When a user tries to access a non-existent URL
- **Features**: 
  - Animated pomodoro timer illustration
  - Clear messaging with a touch of humor
  - Navigation options to get back on track
  - Mobile responsive design

### 403 - Access Denied
- **Path**: `templates/errors/403.html`
- **Trigger**: When a user tries to access a page they don't have permission for
- **Features**:
  - Lock illustration
  - Contextual help based on authentication status
  - Links to login/register or return to safe areas
  - Clear explanation of access restrictions

### 500 - Internal Server Error
- **Path**: `templates/errors/500.html`
- **Features**:
  - Warning illustration with shimmer effect
  - Reassuring message that data is safe
  - Auto-refresh option after 30 seconds
  - Database rollback on error
  - Detailed error information

### Generic Error Page
- **Path**: `templates/errors/error.html`
- **Trigger**: For other HTTP errors (410, etc.)
- **Features**:
  - Animated wrench illustration
  - Customizable error code and message
  - Standard navigation options

## Implementation

### Error Handlers
The error handlers are registered in `pomodoro/__init__.py`:

```python
@app.errorhandler(404)
def not_found_error(error):
    return render_template('errors/404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    db_session = db.get_db()
    if db_session:
        db_session.rollback()
    return render_template('errors/500.html'), 500

@app.errorhandler(403)
def forbidden_error(error):
    return render_template('errors/403.html'), 403

@app.errorhandler(Exception)
def handle_exception(error):
    app.logger.error(f"Unhandled exception: {error}")
    if app.debug:
        return error
    return render_template('errors/error.html', error_code=500, error_message="An unexpected error occurred."), 500
```

### Features

1. **Responsive Design**: All error pages work on mobile and desktop
2. **Accessibility**: Proper semantic HTML and ARIA labels
3. **Animations**: Subtle CSS animations for better UX
4. **Navigation**: Clear paths to get users back to productive areas
5. **Context Awareness**: Different options for authenticated vs anonymous users
6. **Error Logging**: Proper error logging for debugging
7. **Database Safety**: Automatic rollback on 500 errors

### Testing

Use the `test_errors.py` script to verify error pages are working:

```bash
python test_errors.py
```

Or manually test by visiting:
- `http://localhost:5000/nonexistent` (404)
- Protected routes while logged out (403)
- Trigger a server error (500)

### Customization

To customize error pages:

1. **Colors**: Modify CSS variables in `static/css/style.css`
2. **Content**: Edit the HTML templates in `templates/errors/`
3. **Animations**: Adjust CSS animations in each template's `<style>` block
4. **Behavior**: Modify error handlers in `pomodoro/__init__.py`

### Best Practices Followed

- ✅ User-friendly messaging
- ✅ Clear navigation options
- ✅ Mobile responsive
- ✅ Accessible design
- ✅ Error logging
- ✅ Database safety
- ✅ Contextual help
- ✅ Professional appearance
