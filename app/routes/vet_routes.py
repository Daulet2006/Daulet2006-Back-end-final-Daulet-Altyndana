# app/routes/vet_routes.py
from flask import Blueprint, jsonify
from ..models import User, Role # Import User and Role
from .. import db

bp = Blueprint('vets', __name__, url_prefix='/vets')

# Helper function
def format_vet(vet):
    """
    Форматирует объект пользователя-ветеринара для ответа в формате JSON.
    """
    return {
        'id': vet.id,
        'username': vet.username,
        'email': vet.email
        # Добавьте другие поля ветеринара по мере необходимости
    }

# Read All Vets
@bp.route('/', methods=['GET'])
def get_vets():
    try:
        # Запрашиваем пользователей с ролью VETERINARIAN
        vets = User.query.filter_by(role=Role.VETERINARIAN).all()
        return jsonify([format_vet(v) for v in vets]), 200 # Возвращаем отформатированный список
    except Exception as e:
        # Log the error for debugging
        print(f"Error fetching vets: {e}") # Added basic logging
        return jsonify({'message': 'Failed to retrieve vets', 'error': str(e)}), 500

# Placeholder for other vet-related routes (e.g., get single vet)
# @bp.route('/<int:vet_id>', methods=['GET'])
# def get_vet(vet_id):
#     # ... implementation ...
#     pass