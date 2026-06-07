"""
Training script for optimal routine suggestion model.

This script:
1. Collects training data from users with sufficient history
2. Engineers features for each user
3. Trains a Linear Regression model
4. Saves model and scaler to disk
5. Reports performance metrics (R², MAE)
"""

import pickle
import numpy as np
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import MinMaxScaler
from sklearn.model_selection import train_test_split
from sklearn.metrics import r2_score, mean_absolute_error

import sys
import os

# Add parent directory to path so we can import pomodoro
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from pomodoro.db import get_db
from pomodoro.ml.feature_engineering import (
    compute_features_for_user,
    compute_target_variable,
    compute_productivity_score,
)


def collect_training_data(min_history_events=20, days_window=60):
    """
    Collect training data from users with sufficient history.
    
    Args:
        min_history_events: Minimum number of tracked events for inclusion
        days_window: Only consider events from last N days
        
    Returns:
        tuple: (user_ids, X_features, y_targets)
    """
    db = get_db()
    cutoff_timestamp = int(__import__('time').time()) - (days_window * 86400)
    
    # Find users with sufficient history
    users_with_history = db.execute(
        """
        SELECT user_id, COUNT(*) as event_count
        FROM user_statistics
        WHERE timestamp >= ?
        GROUP BY user_id
        HAVING COUNT(*) >= ?
        ORDER BY event_count DESC
        """,
        (cutoff_timestamp, min_history_events)
    ).fetchall()
    
    if not users_with_history:
        print("  ⚠ No users found with sufficient history")
        return [], np.array([]), np.array([])
    
    user_ids = []
    X_features = []
    y_targets = []
    
    for user_row in users_with_history:
        user_id = user_row['user_id']
        
        try:
            features = compute_features_for_user(user_id, days_window)
            target = compute_target_variable(db, user_id, days_window)
            
            # Extract and normalize features
            feature_order = [
                'avg_task_completion_time_seconds',
                'task_completion_rate',
                'break_completion_rate',
                'session_completion_rate',
                'avg_daily_focus_time_seconds',
                'consistency_score',
                'preferred_hour',
                'preferred_weekday',
                'current_session_duration',
                'current_short_break_duration',
                'current_long_break_duration',
                'avg_sessions_per_day',
                'break_skip_streak',
            ]
            
            feature_vector = [features.get(key, 0.0) for key in feature_order]
            
            X_features.append(feature_vector)
            y_targets.append(target)
            user_ids.append(user_id)
            
        except Exception as e:
            print(f"  ⚠ Error processing user {user_id}: {str(e)}")
            continue
    
    return user_ids, np.array(X_features), np.array(y_targets)


def train_model(X, y, test_size=0.2, use_polynomial=False):
    """
    Train Linear Regression (or Polynomial Regression) model.
    
    Args:
        X: Feature matrix (n_samples, n_features)
        y: Target vector (n_samples,)
        test_size: Fraction of data to use for testing
        use_polynomial: If True, use PolynomialFeatures (degree=2)
        
    Returns:
        dict: Model, scaler, metrics, and predictions
    """
    # Split data
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=test_size, random_state=42
    )
    
    # Normalize features
    scaler = MinMaxScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)
    
    # Optionally create polynomial features
    if use_polynomial:
        from sklearn.preprocessing import PolynomialFeatures
        poly = PolynomialFeatures(degree=2, include_bias=False)
        X_train_scaled = poly.fit_transform(X_train_scaled)
        X_test_scaled = poly.fit_transform(X_test_scaled)
    else:
        poly = None
    
    # Train model
    model = LinearRegression()
    model.fit(X_train_scaled, y_train)
    
    # Evaluate
    y_pred_train = model.predict(X_train_scaled)
    y_pred_test = model.predict(X_test_scaled)
    
    r2_train = r2_score(y_train, y_pred_train)
    r2_test = r2_score(y_test, y_pred_test)
    mae_train = mean_absolute_error(y_train, y_pred_train)
    mae_test = mean_absolute_error(y_test, y_pred_test)
    
    return {
        'model': model,
        'scaler': scaler,
        'poly': poly,
        'r2_train': r2_train,
        'r2_test': r2_test,
        'mae_train': mae_train,
        'mae_test': mae_test,
        'residuals': y_test - y_pred_test,
    }


def save_model(results, output_dir='pomodoro/ml/models'):
    """
    Save trained model and scaler to disk.
    
    Args:
        results: dict returned from train_model()
        output_dir: Directory to save files
    """
    os.makedirs(output_dir, exist_ok=True)
    
    # Save model
    with open(f'{output_dir}/routine_suggestion.pkl', 'wb') as f:
        pickle.dump(results['model'], f)
    
    # Save scaler
    with open(f'{output_dir}/scaler.pkl', 'wb') as f:
        pickle.dump(results['scaler'], f)
    
    # Save poly transformer if used
    if results['poly']:
        with open(f'{output_dir}/poly_features.pkl', 'wb') as f:
            pickle.dump(results['poly'], f)
    
    print(f"✓ Model saved to {output_dir}/")


def main():
    """Main training pipeline."""
    print("=" * 60)
    print("Optimal Routine Suggestion Model - Training")
    print("=" * 60)
    
    # Collect training data
    print("\n1. Collecting training data...")
    user_ids, X, y = collect_training_data(min_history_events=20, days_window=60)
    
    if len(X) == 0:
        print("✗ No training data available. Ensure user_statistics has data.")
        return
    
    print(f"   Found {len(user_ids)} users with sufficient history")
    print(f"   Feature matrix shape: {X.shape}")
    print(f"   Target shape: {y.shape}")
    
    # Train model
    print("\n2. Training Linear Regression model...")
    results = train_model(X, y, test_size=0.2, use_polynomial=False)
    
    print(f"   R² (train): {results['r2_train']:.4f}")
    print(f"   R² (test):  {results['r2_test']:.4f}")
    print(f"   MAE (train): {results['mae_train']:.2f} minutes")
    print(f"   MAE (test):  {results['mae_test']:.2f} minutes")
    print(f"   Residual Std Dev: {np.std(results['residuals']):.2f} minutes")
    
    # Save model
    print("\n3. Saving model...")
    save_model(results)
    
    print("\n" + "=" * 60)
    print("✓ Training complete!")
    print("=" * 60)


if __name__ == '__main__':
    main()
