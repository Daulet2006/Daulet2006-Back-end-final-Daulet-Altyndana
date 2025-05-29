# app/routes/role_routes.py
from flask_restx import Namespace, Resource, fields
from flask import request, g
from flask_jwt_extended import jwt_required
from app.models.user_model import User, Role
from app.utils.role_utils import update_user_role, get_user_data_with_permissions
from app.utils.util import role_required

role_ns = Namespace('role', description='Operations related to user user_model.py')

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
        """Get all available user_model.py"""
        roles = [role.value for role in Role]
        return {'user_model.py': roles}, 200

@role_ns.route('/users/roles')
class UsersWithRoles(Resource):
    @jwt_required()
    @role_required(Role.OWNER, Role.ADMIN)
    def get(self):
        """Get all users with their user_model.py"""
        users = User.query.all()
        result = [{
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'role': user.role.value
        } for user in users]
        return {'users': result}, 200

