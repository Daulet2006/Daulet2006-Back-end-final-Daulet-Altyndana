# app/routes/users_routes.py
from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required
from ..models import User
from .. import db
from ..utils import role_required, get_user_data_with_permissions
from ..role_utils import Role

bp = Blueprint('users', __name__, url_prefix='/users')

@bp.route('', methods=['GET'])
@jwt_required()
@role_required(Role.OWNER)
def get_all_users():
    users = User.query.all()
    return jsonify([get_user_data_with_permissions(u) for u in users]), 200

@bp.route('/<int:user_id>', methods=['PUT'])
@jwt_required()
@role_required(Role.OWNER)
def update_user(user_id):
    user = User.query.get_or_404(user_id)
    # Реализация обновления данных пользователя
    return jsonify(get_user_data_with_permissions(user)), 200

@bp.route('/<int:user_id>', methods=['DELETE'])
@jwt_required()
@role_required(Role.OWNER)
def delete_user(user_id):
    user = User.query.get_or_404(user_id)
    db.session.delete(user)
    db.session.commit()
    return jsonify({'message': 'User deleted'}), 200