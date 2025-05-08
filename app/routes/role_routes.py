from flask_restx import Namespace, Resource, fields
from flask import request, jsonify, g
from flask_jwt_extended import jwt_required
from ..models import User, Role
from ..role_utils import update_user_role, get_user_data_with_permissions
from ..utils import role_required

role_ns = Namespace('role', description='Operations related to user roles')

# Swagger model
role_update_model = role_ns.model('RoleUpdate', {
    'role': fields.String(required=True, description='New role for the user')
})

@role_ns.route('/user/permissions')
class UserPermissions(Resource):
    @jwt_required()
    def get(self):
        """Get current user permissions"""
        if not hasattr(g, 'user'):
            return {'message': 'Пользователь не аутентифицирован'}, 401
        user_data = get_user_data_with_permissions(g.user)
        return user_data, 200

@role_ns.route('/user/<int:user_id>/role')
class UserRole(Resource):
    @jwt_required()
    @role_required(Role.OWNER, Role.ADMIN)
    @role_ns.expect(role_update_model)
    def put(self, user_id):
        """Update user role"""
        data = request.get_json()
        if not data or 'role' not in data:
            return {'message': 'Необходимо указать новую роль'}, 400

        new_role = data['role']
        target_user = User.query.get(user_id)
        if not target_user:
            return {'message': 'Пользователь не найден'}, 404

        if (target_user.role == Role.OWNER or new_role.upper() == 'OWNER') and g.user.role != Role.OWNER:
            return {'message': 'Недостаточно прав для управления владельцами'}, 403

        updated_user, error = update_user_role(user_id, new_role)
        if error:
            return {'message': error}, 400

        return {
            'message': f'Роль пользователя успешно обновлена на {new_role}',
            'user': updated_user
        }, 200

@role_ns.route('/roles')
class RolesList(Resource):
    @jwt_required()
    @role_required(Role.OWNER)
    def get(self):
        """Get all available roles"""
        roles = [role.value for role in Role]
        return {'roles': roles}, 200

@role_ns.route('/users/roles')
class UsersWithRoles(Resource):
    @jwt_required()
    @role_required(Role.OWNER, Role.ADMIN)
    def get(self):
        """Get all users with their roles"""
        users = User.query.all()
        result = [{
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'role': user.role.value
        } for user in users]
        return {'users': result}, 200

