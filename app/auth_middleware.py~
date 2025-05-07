# app/auth_middleware.py
from functools import wraps
from flask import request, g, jsonify
import jwt
from .models import User
from .role_utils import get_user_data_with_permissions

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        
        # Проверяем наличие токена в заголовке
        if 'Authorization' in request.headers:
            auth_header = request.headers['Authorization']
            if auth_header.startswith('Bearer '):
                token = auth_header.split(' ')[1]
        
        # Если токен отсутствует
        if not token:
            return jsonify({'message': 'Токен отсутствует!'}), 401
        
        try:
            # Декодируем токен
            from flask import current_app
            data = jwt.decode(token, current_app.config['SECRET_KEY'], algorithms=['HS256'])
            current_user = User.query.filter_by(id=data['user_id']).first()
            
            if not current_user:
                return jsonify({'message': 'Пользователь не найден!'}), 401
            
            # Сохраняем пользователя в g для использования в маршрутах
            g.user = current_user
            
            # Добавляем информацию о разрешениях пользователя
            g.user_permissions = get_user_data_with_permissions(current_user)['permissions']
            
        except jwt.ExpiredSignatureError:
            return jsonify({'message': 'Токен истек!'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'message': 'Недействительный токен!'}), 401
        except Exception as e:
            return jsonify({'message': f'Ошибка: {str(e)}'}), 500
        
        return f(*args, **kwargs)
    
    return decorated

# Функция для применения middleware к приложению
def setup_auth_middleware(app):
    @app.before_request
    def before_request():
        # Пропускаем проверку для маршрутов аутентификации и некоторых публичных маршрутов
        public_routes = [
            '/api/auth/login',
            '/api/auth/register',
            '/api/products',  # Публичный доступ к просмотру товаров
            '/api/pets',      # Публичный доступ к просмотру питомцев
            '/api/categories' # Публичный доступ к просмотру категорий
        ]
        
        # Проверяем, является ли текущий маршрут публичным
        if request.path in public_routes or request.path.startswith('/static/'):
            return None
        
        # Для всех остальных маршрутов проверяем токен
        token = None
        if 'Authorization' in request.headers:
            auth_header = request.headers['Authorization']
            if auth_header.startswith('Bearer '):
                token = auth_header.split(' ')[1]
        
        # Если токен отсутствует, пропускаем (будет обработано в маршруте)
        if not token:
            return None
        
        try:
            # Декодируем токен
            data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
            current_user = User.query.filter_by(id=data['user_id']).first()
            
            if current_user:
                # Сохраняем пользователя в g для использования в маршрутах
                g.user = current_user
                
                # Добавляем информацию о разрешениях пользователя
                g.user_permissions = get_user_data_with_permissions(current_user)['permissions']
        except:
            # В случае ошибки просто продолжаем выполнение запроса
            # Конкретный маршрут решит, требуется ли аутентификация
            pass
        
        return None