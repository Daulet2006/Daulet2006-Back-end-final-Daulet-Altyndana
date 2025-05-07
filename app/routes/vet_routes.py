from flask import Blueprint, jsonify, request
from ..models import User, Role
from .. import db
from ..utils import role_required

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
        return jsonify([format_vet(v) for v in vets]), 200  # Возвращаем отформатированный список
    except Exception as e:
        # Log the error for debugging
        print(f"Error fetching vets: {e}")  # Added basic logging
        return jsonify({'message': 'Failed to retrieve vets', 'error': str(e)}), 500


# Получить одного ветеринара
@bp.route('/<int:vet_id>', methods=['GET'])
def get_vet(vet_id):
    try:
        vet = User.query.get_or_404(vet_id)
        if vet.role != Role.VETERINARIAN:
            return jsonify({'message': 'Not a veterinarian'}), 400
        return jsonify(format_vet(vet)), 200
    except Exception as e:
        return jsonify({'message': 'Failed to retrieve vet', 'error': str(e)}), 500


# Обновить информацию о ветеринаре
@bp.route('/<int:vet_id>', methods=['PUT'])
def update_vet(vet_id):
    data = request.get_json()

    try:
        vet = User.query.get_or_404(vet_id)
        if vet.role != Role.VETERINARIAN:
            return jsonify({'message': 'Not a veterinarian'}), 400

        # Обновление данных (например, email)
        if 'email' in data:
            vet.email = data['email']
        if 'username' in data:
            vet.username = data['username']

        db.session.commit()
        return jsonify({'message': 'Vet information updated'}), 200
    except Exception as e:
        return jsonify({'message': 'Failed to update vet', 'error': str(e)}), 500


# Удалить ветеринара
@bp.route('/<int:vet_id>', methods=['DELETE'])
@role_required(Role.ADMIN)  # Только администратор может удалить ветеринара
def delete_vet(vet_id):
    try:
        vet = User.query.get_or_404(vet_id)
        if vet.role != Role.VETERINARIAN:
            return jsonify({'message': 'Not a veterinarian'}), 400

        db.session.delete(vet)
        db.session.commit()
        return jsonify({'message': 'Vet deleted'}), 200
    except Exception as e:
        return jsonify({'message': 'Failed to delete vet', 'error': str(e)}), 500
