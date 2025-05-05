# app/routes/role_routes.py
from flask import Blueprint, request, jsonify, g
from ..models import User, Role
from ..role_utils import update_user_role, get_user_data_with_permissions
from ..role_functions import role_required

role_bp = Blueprint('role', __name__)

# Получение информации о текущем пользователе с его разрешениями
@role_bp.route('/api/user/permissions', methods=['GET'])
def get_current_user_permissions():
    # Получаем текущего пользователя из g (должен быть установлен middleware аутентификации)
    if not hasattr(g, 'user'):
        return jsonify({'message': 'Пользователь не аутентифицирован'}), 401
    
    user_data = get_user_data_with_permissions(g.user)
    return jsonify(user_data), 200

# Обновление роли пользователя (только для админов и владельцев)
@role_bp.route('/api/user/<int:user_id>/role', methods=['PUT'])
@role_required([Role.OWNER])
def update_role(user_id):
    data = request.get_json()
    
    if not data or 'role' not in data:
        return jsonify({'message': 'Необходимо указать новую роль'}), 400
    
    new_role = data['role']
    
    # Проверка, что владелец не может быть понижен другим администратором
    target_user = User.query.get(user_id)
    if not target_user:
        return jsonify({'message': 'Пользователь не найден'}), 404
    
    # Только владелец может управлять другими владельцами
    if (target_user.role == Role.OWNER or new_role.upper() == 'OWNER') and g.user.role != Role.OWNER:
        return jsonify({'message': 'Недостаточно прав для управления владельцами'}), 403
    
    # Обновляем роль пользователя
    updated_user, error = update_user_role(user_id, new_role)
    
    if error:
        return jsonify({'message': error}), 400
    
    return jsonify({
        'message': f'Роль пользователя успешно обновлена на {new_role}',
        'user': updated_user
    }), 200

# Получение списка всех доступных ролей
@role_bp.route('/api/roles', methods=['GET'])
@role_required([Role.OWNER])
def get_roles():
    roles = [role.value for role in Role]
    return jsonify({'roles': roles}), 200

# Получение списка пользователей с их ролями (только для админов и владельцев)
@role_bp.route('/api/users/roles', methods=['GET'])
@role_required([Role.OWNER])
def get_users_with_roles():
    users = User.query.all()
    result = [{
        'id': user.id,
        'username': user.username,
        'email': user.email,
        'role': user.role.value
    } for user in users]
    
    return jsonify({'users': result}), 200