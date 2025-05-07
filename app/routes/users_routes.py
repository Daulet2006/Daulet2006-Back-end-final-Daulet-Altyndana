# app/routes/users_routes.py

from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from ..models import User
from .. import db
from ..utils import role_required
from ..role_utils import Role, get_user_data_with_permissions

bp = Blueprint('users', __name__, url_prefix='/users')

@bp.route('', methods=['GET'])
@jwt_required()
@role_required(Role.OWNER)
def get_all_users():
    users = User.query.all()
    return jsonify([get_user_data_with_permissions(u) for u in users]), 200

@bp.route('/<int:user_id>', methods=['GET'])
@jwt_required()
@role_required(Role.OWNER)
def get_user(user_id):
    user = User.query.get_or_404(user_id)
    return jsonify(get_user_data_with_permissions(user)), 200

@bp.route('/<int:user_id>', methods=['PUT'])
@jwt_required()
@role_required(Role.OWNER)
def update_user(user_id):
    user = User.query.get_or_404(user_id)
    data = request.get_json()

    allowed_fields = ['username', 'email', 'role']
    updated = False

    if not data:
        return jsonify({'message': 'No data provided'}), 400

    if 'username' in data:
        user.username = data['username']
        updated = True
    if 'email' in data:
        user.email = data['email']
        updated = True
    if 'role' in data:
        try:
            from ..models import Role as RoleEnum
            user.role = RoleEnum(data['role'])
            updated = True
        except ValueError:
            return jsonify({'message': f'Invalid role. Valid roles: {[r.value for r in RoleEnum]}'}), 400

    if not updated:
        return jsonify({'message': 'No valid fields to update'}), 400

    db.session.commit()
    return jsonify({'message': 'User updated successfully', 'user': get_user_data_with_permissions(user)}), 200

@bp.route('/<int:user_id>', methods=['DELETE'])
@jwt_required()
@role_required(Role.OWNER)
def delete_user(user_id):
    current_user_id = get_jwt_identity().get('id')
    if user_id == current_user_id:
        return jsonify({'message': 'You cannot delete your own account.'}), 400

    user = User.query.get_or_404(user_id)
    db.session.delete(user)
    db.session.commit()
    return jsonify({'message': 'User deleted successfully'}), 200
