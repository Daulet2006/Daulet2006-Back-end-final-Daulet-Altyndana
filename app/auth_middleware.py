from functools import wraps
from flask import request, g, jsonify, current_app
from flask_jwt_extended import decode_token
from .models import User
from .role_utils import get_user_data_with_permissions

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        if 'Authorization' in request.headers:
            auth_header = request.headers['Authorization']
            if auth_header.startswith('Bearer '):
                token = auth_header.split(' ')[1]

        if not token:
            return jsonify({'message': 'Токен отсутствует!'}), 401

        try:
            data = decode_token(token)
            current_user = User.query.filter_by(id=data['sub']['id']).first()
            if not current_user:
                return jsonify({'message': 'Пользователь не найден!'}), 401
            g.user = current_user
            g.user_permissions = get_user_data_with_permissions(current_user)['permissions']
        except Exception as e:
            return jsonify({'message': f'Ошибка: {str(e)}'}), 401

        return f(*args, **kwargs)
    return decorated

def setup_auth_middleware(app):
    @app.before_request
    def before_request():
        public_routes = [
            '/auth/login',
            '/auth/register',
            '/products',
            '/pets',
            '/categories'
        ]
        if request.path in public_routes or request.path.startswith('/static/') or request.path == '/docs':
            return None

        token = None
        if 'Authorization' in request.headers:
            auth_header = request.headers['Authorization']
            if auth_header.startswith('Bearer '):
                token = auth_header.split(' ')[1]

        if not token:
            return None

        try:
            data = decode_token(token)
            current_user = User.query.filter_by(id=data['sub']['id']).first()
            if current_user:
                g.user = current_user
                g.user_permissions = get_user_data_with_permissions(current_user)['permissions']
        except Exception as e:
            return jsonify({'message': f'Ошибка: {str(e)}'}), 401
        return None