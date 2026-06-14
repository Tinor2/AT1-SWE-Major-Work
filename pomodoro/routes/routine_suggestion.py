"""Real ML prediction + retraining endpoints for Phase 3."""

from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user

routine_bp = Blueprint('routine_suggestion', __name__, url_prefix='/api/productivity')


@routine_bp.route('/prediction', methods=['GET'])
@login_required
def get_prediction():
    from pomodoro.db import get_db
    from pomodoro.ml.predictor import predict_for_user
    days = request.args.get("days", default=60, type=int)
    if days < 1:
        days = 60
    try:
        result = predict_for_user(current_user.id, get_db(), days=days)
        return jsonify(result), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@routine_bp.route('/retrain', methods=['POST'])
@login_required
def retrain():
    from pomodoro.db import get_db
    from pomodoro.ml.trainer import train_for_user
    from pomodoro.ml.predictor import predict_for_user
    days = request.args.get("days", default=60, type=int)
    if days < 1:
        days = 60
    try:
        train_for_user(current_user.id, get_db())
        result = predict_for_user(current_user.id, get_db(), days=days)
        return jsonify(result), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
