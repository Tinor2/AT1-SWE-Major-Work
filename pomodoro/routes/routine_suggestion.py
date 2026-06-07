"""
API endpoints for optimal routine suggestions.

GET /api/productivity/routine-suggestion
Returns optimal session duration recommendation for the logged-in user.
"""

from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user
import pickle
import os
import numpy as np

from pomodoro.ml.feature_engineering import (
    compute_features_for_user,
    normalize_features,
    compute_productivity_score,
)

routine_bp = Blueprint('routine_suggestion', __name__, url_prefix='/api/productivity')

# Model paths
MODEL_DIR = os.path.join(os.path.dirname(__file__), '..', 'ml', 'models')
MODEL_PATH = os.path.join(MODEL_DIR, 'routine_suggestion.pkl')
SCALER_PATH = os.path.join(MODEL_DIR, 'scaler.pkl')
POLY_PATH = os.path.join(MODEL_DIR, 'poly_features.pkl')

# Global model cache
_model = None
_scaler = None
_poly = None


def load_model():
    """Load model from disk (lazy load)."""
    global _model, _scaler, _poly
    
    if _model is None:
        if not os.path.exists(MODEL_PATH):
            return None, None, None
        
        with open(MODEL_PATH, 'rb') as f:
            _model = pickle.load(f)
        
        with open(SCALER_PATH, 'rb') as f:
            _scaler = pickle.load(f)
        
        if os.path.exists(POLY_PATH):
            with open(POLY_PATH, 'rb') as f:
                _poly = pickle.load(f)
    
    return _model, _scaler, _poly


def calculate_prediction_confidence(residual_std, typical_duration=25):
    """
    Calculate confidence in prediction (0-1 scale).
    
    Based on residual standard error: higher residuals = lower confidence.
    """
    if residual_std == 0:
        return 1.0
    confidence = 1.0 / (1.0 + (residual_std / typical_duration))
    return np.clip(confidence, 0, 1)


@routine_bp.route('/routine-suggestion', methods=['GET'])
@login_required
def get_routine_suggestion():
    """
    Return recommended session duration for the current user.
    
    Response:
    {
        "optimal_session_duration_minutes": 28,
        "confidence": 0.78,
        "rationale": "Your break completion rate is high...",
        "alternatives": [
            {"duration": 25, "productivity_gain": "-2%"},
            {"duration": 30, "productivity_gain": "+1%"}
        ]
    }
    """
    # Load model
    model, scaler, poly = load_model()
    
    if model is None:
        return jsonify({
            'error': 'Model not yet trained',
            'message': 'Routine suggestion model is still being trained. Try again later.'
        }), 503
    
    try:
        # Compute features for user
        features_dict = compute_features_for_user(current_user.id)
        
        # TODO: Extract features in correct order and normalize
        # features_list = [f1, f2, f3, ...] in same order as training
        # features_scaled = scaler.transform([features_list])
        # if poly:
        #     features_scaled = poly.transform(features_scaled)
        
        # Predict (placeholder)
        predicted_duration = 25.0
        
        # Clamp and round
        optimal_duration = max(15, min(45, round(predicted_duration / 5) * 5))
        
        # Confidence (placeholder)
        confidence = 0.7
        
        # Generate rationale
        rationale = generate_rationale(features_dict)
        
        # Generate alternatives
        alternatives = generate_alternatives(optimal_duration)
        
        return jsonify({
            'optimal_session_duration_minutes': int(optimal_duration),
            'confidence': round(confidence, 2),
            'rationale': rationale,
            'alternatives': alternatives,
        }), 200
        
    except Exception as e:
        return jsonify({
            'error': 'Prediction failed',
            'message': str(e)
        }), 500


def generate_rationale(features):
    """
    Generate human-readable rationale for recommendation.
    
    Lists top 3 factors influencing the recommendation.
    """
    factors = []
    
    if features.get('break_completion_rate', 0) > 0.8:
        factors.append('Your break completion rate is high ({}%)'.format(
            int(features['break_completion_rate'] * 100)
        ))
    
    if features.get('consistency_score', 0) > 0.7:
        factors.append('You have consistent daily focus habits')
    
    if features.get('preferred_hour') is not None:
        hour = features['preferred_hour']
        factors.append('You\'re most productive at {} AM/PM'.format(hour))
    
    if not factors:
        factors = ['Based on your productivity history']
    
    return '. '.join(factors[:3]) + '.'


def generate_alternatives(optimal_duration):
    """
    Generate alternative durations for A/B testing.
    
    Returns 2-3 alternatives around the optimal duration.
    """
    alternatives = []
    
    # Current duration (baseline)
    if optimal_duration != 25:
        alternatives.append({
            'duration': 25,
            'productivity_gain': '-2%'  # TODO: Calculate from model
        })
    
    # +5 min alternative
    alt_duration = min(45, optimal_duration + 5)
    alternatives.append({
        'duration': int(alt_duration),
        'productivity_gain': '+1%'  # TODO: Calculate from model
    })
    
    # -5 min alternative
    alt_duration = max(15, optimal_duration - 5)
    alternatives.append({
        'duration': int(alt_duration),
        'productivity_gain': '-1%'  # TODO: Calculate from model
    })
    
    return alternatives[:3]
