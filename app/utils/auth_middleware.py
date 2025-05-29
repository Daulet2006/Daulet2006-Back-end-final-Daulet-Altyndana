from functools import wraps
from flask import request, g, jsonify
from flask_jwt_extended import  jwt_required, get_jwt_identity
from .role_utils import get_user_data_with_permissions
from ..models.user_model import User


def token_required(f):
    @wraps(f)
    @jwt_required()
    def decorated(*args, **kwargs):
        identity = get_jwt_identity()
        current_user = User.query.filter_by(id=identity['id']).first()
        if not current_user:
            return jsonify({'message': 'Пользователь не найден!'}), 401
        g.user = current_user
        g.user_permissions = get_user_data_with_permissions(current_user)['permissions']
        return f(*args, **kwargs)
    return decorated

def setup_auth_middleware(app):
    @app.before_request
    def before_request():
        public_routes = [
            '/auth/login',
            '/auth/register',
            '/auth/verify',
            '/products',
            '/pets',
            '/categories'
        ]
        if request.path in public_routes or request.path.startswith('/static/') or request.path == '/docs':
            return None
        # Не проверяем токен здесь, полагаемся на @token_required или @jwt_required
        return None