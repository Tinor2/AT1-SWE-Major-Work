"""Real ML prediction + retraining endpoints for Phase 3."""

from flask import Blueprint, jsonify
from flask_login import login_required, current_user

routine_bp = Blueprint('routine_suggestion', __name__, url_prefix='/api/productivity')


@routine_bp.route('/prediction', methods=['GET'])
@login_required
def get_prediction():
    from pomodoro.db import get_db
    from pomodoro.ml.predictor import predict_for_user
    try:
        result = predict_for_user(current_user.id, get_db())
        return jsonify(result), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@routine_bp.route('/retrain', methods=['POST'])
@login_required
def retrain():
    from pomodoro.db import get_db
    from pomodoro.ml.trainer import train_for_user
    from pomodoro.ml.predictor import predict_for_user
    try:
        train_for_user(current_user.id, get_db())
        result = predict_for_user(current_user.id, get_db())
        return jsonify(result), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
