# app/routes/users_routes.py
from flask_restx import Namespace, Resource, fields
from flask import request
from flask_jwt_extended import jwt_required, get_jwt_identity
from .auth_routes import PASSWORD_REGEX, EMAIL_REGEX
from app.models.user_model import User, Role
from .. import db, bcrypt
from app.utils.util import role_required
from app.utils.role_utils import get_user_data_with_permissions

users_ns = Namespace('users', description='Operations related to users')

# Swagger model
user_model = users_ns.model('User', {
    'username': fields.String(description='User username'),
    'email': fields.String(description='User email'),
    'password': fields.String(description='User password'),
    'role': fields.String(description='User role')
})
@users_ns.route('/clients')
class ClientList(Resource):
    @jwt_required()
    @role_required( Role.ADMIN, Role.OWNER)
    def get(self):
        """Get all clients"""
        try:
            clients = User.query.filter_by(role=Role.CLIENT).all()
            return [get_user_data_with_permissions(c) for c in clients], 200
        except Exception as e:
            return {'message': 'Ошибка получения клиентов', 'error': str(e)}, 500
@users_ns.route('')
class UserList(Resource):
    @jwt_required()
    @role_required(Role.ADMIN, Role.OWNER)
    @users_ns.expect(user_model)
    def post(self):
        """Create a new user"""
        try:
            data = request.get_json()
            if not data:
                return {'message': 'No data provided'}, 400

            # Проверка обязательных полей
            required_fields = ['username', 'email', 'password', 'role']
            if not all(field in data for field in required_fields):
                return {'message': f'Missing required fields: {required_fields}'}, 400


            if User.query.filter_by(email=data['email']).first():
                return {'message': 'Email already taken'}, 400

            # Валидация email
            if not EMAIL_REGEX.match(data['email']):
                return {'message': 'Invalid email format'}, 400

            # Валидация пароля
            if not PASSWORD_REGEX.match(data['password']):
                return {'message': 'Password must be at least 6 characters and contain at least one letter and one number'}, 400

            # Валидация роли
            role_value = data.get('role')
            if not role_value or not isinstance(role_value, str):
                return {'message': f'Role is required and must be a string. Received: {role_value}'}, 400

            try:
                role = Role(role_value.upper())
            except ValueError:
                return {'message': f'Invalid role. Valid user_model.py: {[r.value for r in Role]}'}, 400

            # Создание нового пользователя
            new_user = User(
                username=data['username'],
                email=data['email'],
                password=bcrypt.generate_password_hash(data['password']).decode('utf-8'),
                role=role
            )

            db.session.add(new_user)
            db.session.commit()

            return {
                'message': 'User created successfully',
                'user': get_user_data_with_permissions(new_user)
            }, 201

        except Exception as e:
            db.session.rollback()
            return {'message': 'Error creating user', 'error': str(e)}, 500

    @jwt_required()
    @role_required(Role.ADMIN, Role.OWNER, Role.SELLER, Role.CLIENT)
    def get(self):
        """Get all users"""
        users = User.query.all()
        return [get_user_data_with_permissions(u) for u in users], 200
@users_ns.route('/<int:user_id>')
class UserResource(Resource):
    @jwt_required()
    def get(self, user_id):
        """Get a user by ID"""
        current_user_identity = get_jwt_identity()
        current_user_id_from_token = current_user_identity['id']
        current_user_role = Role(current_user_identity['role'])

        user = User.query.get_or_404(user_id)

        if current_user_role in [Role.ADMIN, Role.OWNER] or \
           (user.id == current_user_id_from_token): # Allow user to get their own info
            return get_user_data_with_permissions(user), 200
        else:
            return {'message': 'Permission denied'}, 403

    @jwt_required()
    @users_ns.expect(user_model)
    def put(self, user_id):
        """Update a user"""
        current_user_identity = get_jwt_identity()
        current_user_id_from_token = current_user_identity['id']
        current_user_role = Role(current_user_identity['role'])

        user_to_update = User.query.get_or_404(user_id)
        data = request.get_json()
        updated = False

        if not data:
            return {'message': 'No data provided'}, 400

        # Handle username update
        if 'username' in data:
            if data['username'] != user_to_update.username: # Only check if username is actually changing
                existing_user_by_username = User.query.filter(User.username == data['username'], User.id != user_to_update.id).first()
                if existing_user_by_username:
                    return {'message': 'Username already taken.'}, 400
            user_to_update.username = data['username']
            updated = True

        # Handle email update
        if 'email' in data:
            if data['email'] != user_to_update.email: # Only check if email is actually changing
                existing_user_by_email = User.query.filter(User.email == data['email'], User.id != user_to_update.id).first()
                if existing_user_by_email:
                    return {'message': 'Email already taken.'}, 400
            user_to_update.email = data['email']
            updated = True

        # Role update logic
        if 'role' in data:
            new_role_str = data['role']
            try:
                new_role_enum = Role(new_role_str)
            except ValueError:
                return {'message': f'Invalid role. Valid user_model.py: {[r.value for r in Role]}'}, 400

            if new_role_enum != user_to_update.role: # Actual role change requested
                if current_user_role == Role.CLIENT:
                    return {'message': 'Clients cannot change user_model.py.'}, 403

                elif current_user_role == Role.ADMIN:
                    if user_to_update.id == current_user_id_from_token:
                        return {'message': 'Admins cannot change their own role.'}, 403
                    if user_to_update.role == Role.OWNER:
                        return {'message': "Admins cannot change an Owner's role."}, 403
                    if user_to_update.role == Role.ADMIN:
                        return {'message': 'Admins cannot change the role of other Admin users.'}, 403
                    if new_role_enum == Role.ADMIN:
                        return {'message': 'Admins cannot assign the Admin role to other users.'}, 403
                    
                    user_to_update.role = new_role_enum
                    updated = True

                elif current_user_role == Role.OWNER:
                    if user_to_update.id == current_user_id_from_token and new_role_enum != Role.OWNER:
                        return {'message': 'Owners cannot change their own role to a non-Owner role.'}, 403
                    user_to_update.role = new_role_enum
                    updated = True
                else:
                    return {'message': 'Permission denied for role change due to unrecognized current user role.'}, 403
        
        # Final check for Client trying to update another user's profile (even if no role change was attempted)
        if current_user_role == Role.CLIENT and user_to_update.id != current_user_id_from_token:
            return {'message': 'Clients can only update their own profile.'}, 403

        if not updated:
            return {'message': 'No valid fields to update or no changes made'}, 400

        db.session.commit()
        return {'message': 'User updated successfully', 'user': get_user_data_with_permissions(user_to_update)}, 200

    @jwt_required()
    @role_required(Role.OWNER)
    def delete(self, user_id):
        """Delete a user"""
        current_user_id = get_jwt_identity().get('id')
        if user_id == current_user_id:
            return {'message': 'You cannot delete your own account.'}, 400
        user = User.query.get_or_404(user_id)
        db.session.delete(user)
        db.session.commit()
        return {'message': 'User deleted successfully'}, 200
# Swagger model для бана/разбана
ban_model = users_ns.model('BanUser', {
    'isBanned': fields.Boolean(required=True, description='True чтобы забанить, False чтобы разбанить')
})

@users_ns.route('/<int:user_id>/ban')
class BanUser(Resource):
    @jwt_required()
    @role_required(Role.ADMIN, Role.OWNER)
    @users_ns.expect(ban_model)
    def put(self, user_id):
        """Забанить или разбанить пользователя"""
        user = User.query.get_or_404(user_id)
        data = request.get_json()

        if 'isBanned' not in data:
            return {'message': 'Поле isBanned обязательно'}, 400

        if user.id == get_jwt_identity().get('id'):
            return {'message': 'Вы не можете забанить самого себя'}, 400

        user.isBanned = data['isBanned']
        db.session.commit()
        # status = 'забанен' if user.isBanned else 'разбанен' # Old message
        return {'message': f'User ban status updated successfully', 'user': get_user_data_with_permissions(user)}, 200

