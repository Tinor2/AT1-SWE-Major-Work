# ML Model: Optimal Routine Suggestion

## Overview

The Optimal Routine Suggestion model uses Linear Regression to predict the ideal Pomodoro session duration for each user based on their productivity patterns, break habits, and task completion metrics.

## Architecture

```
pomodoro/ml/
├── feature_engineering.py      # Feature computation from user_statistics
├── models/
│   ├── routine_suggestion.pkl   # Trained Linear Regression model
│   ├── scaler.pkl               # MinMaxScaler for feature normalization
│   └── poly_features.pkl        # (Optional) PolynomialFeatures transformer

pomodoro/routes/
└── routine_suggestion.py        # API endpoint: GET /api/productivity/routine-suggestion

scripts/
└── train_routine_model.py       # Model training script
```

## Feature Engineering

The model uses **13 features** organized into 4 categories:

### 1. Productivity-Based Features (6 features)
- **avg_task_completion_time_seconds**: Average time spent on completed tasks
  - Source: `user_statistics.task_completion_time_seconds`
  - Interpretation: Users with short task completion times need shorter sessions; longer times need longer sessions
  
- **task_completion_rate** (0-1): Fraction of created tasks that are completed
  - Calculation: `completed_tasks / (created_tasks + completed_tasks)`
  - High rate → user is productive with current setup
  
- **break_completion_rate** (0-1): Fraction of breaks that are completed (not skipped)
  - Calculation: `completed_breaks / (completed_breaks + skipped_breaks)`
  - High rate → user can handle longer sessions
  
- **session_completion_rate** (0-1): Fraction of started sessions that are completed
  - Calculation: `session_end_events / session_start_events`
  - Low rate → sessions may be too long
  
- **avg_daily_focus_time_seconds**: Average total focus time per day
  - Calculation: Sum session durations by day, then average across days
  - Tells us the user's sustainable work volume
  
- **consistency_score** (0-1): Measure of how consistently the user works
  - Calculation: `1.0 / (1.0 + variance_of_daily_focus_times / 10000)`
  - Low variance → consistent user can handle longer/more sessions
  - High variance → inconsistent user needs flexible, shorter sessions

### 2. Temporal Features (2 features)
- **preferred_hour** (0-23): Hour of day when user starts most sessions
  - Source: Grouped query on session_start events by hour
  - Feature type: Categorical (encoded as hour number)
  - Use case: Some users are more productive at specific times

- **preferred_weekday** (0-6, where 0=Monday): Day of week with most sessions
  - Source: Grouped query on session_start events by weekday
  - Feature type: Categorical
  - Use case: Weekday vs. weekend productivity differences

### 3. Current Settings (3 features)
- **current_session_duration**: User's current Pomodoro session setting (minutes)
  - Source: `lists.pomo_session`
  - Use case: Model learns from current settings as baseline
  
- **current_short_break_duration**: User's current short break setting (minutes)
  - Source: `lists.pomo_short_break`
  
- **current_long_break_duration**: User's current long break setting (minutes)
  - Source: `lists.pomo_long_break`

### 4. Engagement Features (2 features)
- **avg_sessions_per_day**: Average number of sessions per day
  - Calculation: Count session_start events per day, then average
  - Use case: Users with many short sessions vs. few long sessions

- **break_skip_streak**: Count of consecutive breaks skipped recently
  - Calculation: Count recent break_skip events in last 7 days
  - Use case: High skip rate indicates user skips breaks or works through them

## Training Pipeline

### Step 1: Data Collection
```python
from scripts.train_routine_model import collect_training_data

user_ids, X, y = collect_training_data(
    min_history_events=20,  # Minimum tracked events for inclusion
    days_window=60          # Only use data from last 60 days
)
```

Selects users with sufficient history to ensure representative training data.

### Step 2: Feature Normalization
Features are normalized to 0-1 range using MinMaxScaler:
- Ensures all features contribute equally to model
- Handles features with different scales (e.g., 0-23 for hours, 0-86400 for seconds)

### Step 3: Model Training
```python
from scripts.train_routine_model import train_model

results = train_model(
    X, y,
    test_size=0.2,           # 20% test set
    use_polynomial=False     # Use linear regression (set True for polynomial)
)
```

**Output metrics:**
- R² on train/test sets: Indicates model fit quality (0-1, where 1 is perfect)
- MAE (Mean Absolute Error): Typical prediction error in minutes
- Residuals: Used to compute prediction confidence

### Step 4: Model Persistence
Models are saved as pickle files:
```python
pomodoro/ml/models/
  ├── routine_suggestion.pkl    # Trained model
  ├── scaler.pkl                 # Feature scaler
  └── poly_features.pkl          # (Optional) Polynomial transformer
```

## Model: Linear Regression

**Why Linear Regression?**
- Session duration is a continuous numeric output (15-45 minutes)
- Relationship between features and duration is approximately linear
- Interpretable coefficients show which features increase/decrease duration
- Fast inference, no overfitting with regularization
- Baseline for comparison with more complex models

**Model coefficients** indicate how each feature affects session duration:
- Positive coefficient: Feature increases optimal duration
- Negative coefficient: Feature decreases optimal duration
- Magnitude: Strength of the effect (in minutes per unit feature change)

### Alternative: Polynomial Regression
If the model underfits (R² < 0.5), try Polynomial Regression:
```python
from sklearn.preprocessing import PolynomialFeatures

poly = PolynomialFeatures(degree=2, include_bias=False)
X_poly = poly.fit_transform(X_scaled)
# Train on X_poly
```

This captures non-linear interactions (e.g., longer sessions require higher break completion rate).

## API Endpoint

### GET `/api/productivity/routine-suggestion`

**Authentication:** Required (login_required)

**Response (200 OK):**
```json
{
  "optimal_session_duration_minutes": 28,
  "confidence": 0.78,
  "rationale": "Your break completion rate is high (85%), and you're most productive at 2 PM. We recommend 28-minute sessions.",
  "alternatives": [
    {"duration": 25, "productivity_gain": "-2%"},
    {"duration": 30, "productivity_gain": "+1%"}
  ]
}
```

**Response (503 Service Unavailable):**
```json
{
  "error": "Model not yet trained",
  "message": "Routine suggestion model is still being trained. Try again later."
}
```

**Fields:**
- `optimal_session_duration_minutes`: Recommended session length (15-45 minutes, rounded to nearest 5)
- `confidence`: Model confidence in prediction (0-1 scale)
- `rationale`: Human-readable explanation of top 3 factors
- `alternatives`: 2-3 alternative durations for A/B testing

## Usage Examples

### Training the Model

```bash
source venv/bin/activate
python scripts/train_routine_model.py
```

Output:
```
============================================================
Optimal Routine Suggestion Model - Training
============================================================

1. Collecting training data...
   Found 150 users with sufficient history
   Feature matrix shape: (150, 13)
   Target shape: (150,)

2. Training Linear Regression model...
   R² (train): 0.6523
   R² (test):  0.6201
   MAE (train): 2.45 minutes
   MAE (test):  2.78 minutes
   Residual Std Dev: 2.94 minutes

3. Saving model...
✓ Model saved to pomodoro/ml/models/

============================================================
✓ Training complete!
============================================================
```

### Making Predictions

```python
from pomodoro.ml.feature_engineering import compute_features_for_user, normalize_features
import pickle

# Load model
with open('pomodoro/ml/models/routine_suggestion.pkl', 'rb') as f:
    model = pickle.load(f)

with open('pomodoro/ml/models/scaler.pkl', 'rb') as f:
    scaler = pickle.load(f)

# Get features for user
user_id = 42
features = compute_features_for_user(user_id)

# Normalize and predict
normalized, _ = normalize_features(features, scaler)
predicted_duration = model.predict([normalized])[0]

# Clamp and round
optimal = max(15, min(45, round(predicted_duration / 5) * 5))
print(f"Recommended session: {optimal} minutes")
```

## Retraining Schedule

**Initial training:** Week 5 (after 2+ weeks of fresh user data)
**Retraining frequency:** Every 2 weeks during user testing
**Final deployment:** Week 7 (model frozen for evaluation)

## Monitoring & Metrics

Track during retraining:
- **R² score on test set**: Overall model quality (target > 0.6)
- **MAE (Mean Absolute Error)**: Typical prediction error (target < 3 minutes)
- **Feature importance**: Which features drive recommendations most

```python
# Feature importance (coefficients)
import matplotlib.pyplot as plt

feature_names = [
    'task_time', 'task_rate', 'break_rate', 'session_rate', 
    'daily_focus', 'consistency', 'hour', 'weekday',
    'session_dur', 'short_break', 'long_break', 'sessions_per_day', 'skip_streak'
]

plt.barh(feature_names, model.coef_)
plt.xlabel('Coefficient (effect on session duration)')
plt.title('Feature Importance')
plt.show()
```

## Testing

Run the ML pipeline tests:
```bash
source venv/bin/activate
python test_ml_pipeline.py
```

This verifies:
1. Feature engineering computes all 13 features correctly
2. Training pipeline collects data and trains model
3. Model achieves reasonable accuracy on test data

## Future Enhancements

1. **Multi-output model**: Predict break durations and sessions-per-day separately
2. **Personalized confidence**: Per-user confidence intervals based on feature relevance
3. **Online learning**: Continuously update model as new data arrives
4. **Ensemble methods**: Combine Linear Regression with Random Forest for better accuracy
5. **Explainability**: SHAP values to explain individual predictions
6. **A/B testing framework**: Track user adoption of recommendations vs. actual improvements

## File Locations

- **Model files**: `pomodoro/ml/models/`
- **Feature engineering**: `pomodoro/ml/feature_engineering.py`
- **Training script**: `scripts/train_routine_model.py`
- **API endpoint**: `pomodoro/routes/routine_suggestion.py`
- **Tests**: `test_ml_pipeline.py`

## Database Schema

Features are sourced from two main tables:

### user_statistics
Tracks all productivity events:
- `event_type`: 'task_completion', 'break_completion', 'break_skip', 'session_start', 'session_end', etc.
- `timestamp`: Unix timestamp
- `duration_seconds`: Event duration (for sessions, breaks)
- `task_completion_time_seconds`: Time spent on task
- Indexes on (user_id, event_type), (user_id, timestamp)

### lists
User settings:
- `pomo_session`: Session duration in minutes
- `pomo_short_break`: Short break duration
- `pomo_long_break`: Long break duration
- `is_active`: Whether list is active

## Troubleshooting

**Issue:** Model file not found
- Solution: Run `python scripts/train_routine_model.py` to train

**Issue:** Feature engineering returns zeros
- Solution: Check that `user_statistics` has data for the user (min 20 events)

**Issue:** Model R² too low (< 0.5)
- Solution: Try PolynomialFeatures for degree-2 interactions

**Issue:** Predictions outside 15-45 minute range
- Solution: Clamping is applied in API endpoint (line ensures 15-45 range)
