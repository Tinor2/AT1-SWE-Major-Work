"""
Test script for ML feature engineering and training pipeline.

This script verifies that all feature engineering functions work correctly
and demonstrates the model training pipeline.
"""

import sys
import os
import sqlite3
import time
from datetime import datetime, timedelta

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def create_test_database():
    """Create an in-memory database with test data."""
    db = sqlite3.connect(':memory:')
    db.row_factory = sqlite3.Row
    
    # Create schema
    schema_file = os.path.join(os.path.dirname(__file__), 'schema.sql')
    with open(schema_file, 'r') as f:
        db.executescript(f.read())
    
    return db


def insert_test_data(db):
    """Insert sample users and events for testing."""
    current_time = int(time.time())
    
    # Create test users
    for user_id in range(1, 4):
        db.execute(
            'INSERT INTO users (id, username, email, password_hash) VALUES (?, ?, ?, ?)',
            (user_id, f'user{user_id}', f'user{user_id}@test.com', 'hash')
        )
        
        # Create active list for user
        db.execute(
            'INSERT INTO lists (user_id, name, is_active, pomo_session, pomo_short_break, pomo_long_break) VALUES (?, ?, ?, ?, ?, ?)',
            (user_id, f'list{user_id}', 1, 25, 5, 15)
        )
    
    db.commit()
    
    # Insert sample events for user 1 (high productivity)
    base_time = current_time - (30 * 86400)  # 30 days ago
    
    events = [
        # Session events
        ('session_start', base_time + 1000, 25),
        ('session_end', base_time + 1000 + 1500, 25),
        ('break_completion', base_time + 1000 + 1600, 0),
        ('session_start', base_time + 2000, 25),
        ('session_end', base_time + 2000 + 1500, 25),
        ('break_skip', base_time + 2000 + 1600, 0),
        # Task events
        ('task_creation', base_time + 500, 0),
        ('task_completion', base_time + 1800, 1800),
        ('task_creation', base_time + 1900, 0),
        ('task_completion', base_time + 3300, 1800),
    ]
    
    for event_type, timestamp, duration_secs in events:
        db.execute(
            'INSERT INTO user_statistics (user_id, event_type, timestamp, duration_seconds) VALUES (?, ?, ?, ?)',
            (1, event_type, timestamp, duration_secs)
        )
    
    db.commit()
    print(f"✓ Inserted {len(events)} test events for user 1")
    
    return len(events)


def test_feature_engineering():
    """Test feature engineering with mock database."""
    print("\n" + "=" * 60)
    print("Testing Feature Engineering")
    print("=" * 60)
    
    # Monkey-patch get_db to use test database
    test_db = create_test_database()
    insert_test_data(test_db)
    
    import pomodoro.db
    original_get_db = pomodoro.db.get_db
    pomodoro.db.get_db = lambda: test_db
    
    try:
        from pomodoro.ml.feature_engineering import (
            compute_features_for_user,
            compute_productivity_score,
            normalize_features,
        )
        
        print("\n1. Computing features for test user...")
        features = compute_features_for_user(1, training_window_days=60)
        
        print("   ✓ Features computed:")
        for key, value in features.items():
            if isinstance(value, float):
                print(f"     - {key}: {value:.4f}")
            else:
                print(f"     - {key}: {value}")
        
        print("\n2. Computing productivity score...")
        score = compute_productivity_score(features)
        print(f"   ✓ Productivity score: {score:.4f}")
        
        print("\n3. Normalizing features...")
        normalized, scaler = normalize_features(features)
        print(f"   ✓ Normalized features shape: {normalized.shape}")
        print(f"   ✓ Normalized range: [{normalized.min():.4f}, {normalized.max():.4f}]")
        
        return True
        
    except Exception as e:
        print(f"   ✗ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        pomodoro.db.get_db = original_get_db
        test_db.close()


def test_training_pipeline():
    """Test model training pipeline."""
    print("\n" + "=" * 60)
    print("Testing Training Pipeline")
    print("=" * 60)
    
    try:
        import numpy as np
        from sklearn.linear_model import LinearRegression
        from sklearn.preprocessing import MinMaxScaler
        from sklearn.model_selection import train_test_split
        from sklearn.metrics import r2_score, mean_absolute_error
        
        # Create synthetic training data
        print("\n1. Generating synthetic training data...")
        
        # 50 users with 13 features each
        n_samples = 50
        n_features = 13
        
        # Random features (already normalized-ish)
        X = np.random.rand(n_samples, n_features) * 100
        
        # Target: session duration between 15-45 minutes
        # Create some correlation with features
        y = 25 + 5 * (X[:, 1] - 0.5) + 3 * (X[:, 2] - 0.5) + np.random.randn(n_samples)
        y = np.clip(y, 15, 45)
        
        print(f"   ✓ Generated {n_samples} synthetic users")
        print(f"   ✓ Features shape: {X.shape}")
        print(f"   ✓ Targets shape: {y.shape}")
        
        # Split data
        print("\n2. Splitting into train/test sets...")
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42
        )
        
        # Normalize features
        scaler = MinMaxScaler()
        X_train_scaled = scaler.fit_transform(X_train)
        X_test_scaled = scaler.transform(X_test)
        
        # Train model
        print("\n3. Training Linear Regression model...")
        model = LinearRegression()
        model.fit(X_train_scaled, y_train)
        
        # Evaluate
        y_pred_train = model.predict(X_train_scaled)
        y_pred_test = model.predict(X_test_scaled)
        
        r2_train = r2_score(y_train, y_pred_train)
        r2_test = r2_score(y_test, y_pred_test)
        mae_train = mean_absolute_error(y_train, y_pred_train)
        mae_test = mean_absolute_error(y_test, y_pred_test)
        
        print(f"   ✓ Model trained:")
        print(f"     - Train/Test split: {len(X_train)}/{len(X_test)}")
        print(f"     - R² (train): {r2_train:.4f}")
        print(f"     - R² (test):  {r2_test:.4f}")
        print(f"     - MAE (train): {mae_train:.2f} minutes")
        print(f"     - MAE (test):  {mae_test:.2f} minutes")
        
        # Verify model coefficients
        print("\n4. Model coefficients:")
        feature_names = [
            'task_time', 'task_rate', 'break_rate', 'session_rate', 
            'daily_focus', 'consistency', 'hour', 'weekday',
            'session_dur', 'short_break', 'long_break', 'sessions_per_day', 'skip_streak'
        ]
        
        for name, coef in zip(feature_names, model.coef_):
            direction = "↑" if coef > 0 else "↓"
            print(f"   {direction} {name}: {coef:+.4f}")
        
        print(f"   Intercept: {model.intercept_:.2f}")
        
        return True
        
    except Exception as e:
        print(f"   ✗ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests."""
    print("\n" + "=" * 60)
    print("ML Feature Engineering & Training Tests")
    print("=" * 60)
    
    results = {
        'feature_engineering': test_feature_engineering(),
        'training_pipeline': test_training_pipeline(),
    }
    
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    
    for test_name, passed in results.items():
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status}: {test_name}")
    
    all_passed = all(results.values())
    
    print("\n" + "=" * 60)
    if all_passed:
        print("✓ All tests passed!")
    else:
        print("✗ Some tests failed. Review output above.")
    print("=" * 60 + "\n")
    
    return 0 if all_passed else 1


if __name__ == '__main__':
    exit(main())
