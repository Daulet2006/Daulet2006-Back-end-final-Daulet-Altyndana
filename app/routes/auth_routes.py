import datetime
from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity, set_access_cookies, \
    unset_jwt_cookies
from ..models import User, Role
from .. import db, bcrypt  # Import bcrypt
from ..role_utils import get_user_data_with_permissions  # Импорт утилит для работы с ролями

bp = Blueprint('auth', __name__, url_prefix='/auth')


@bp.route('/register', methods=['POST'])
def register():
    data = request.get_json()

    # Check if all required fields are in the request
    if not all(k in data for k in ('username', 'email', 'password', 'role')):
        return jsonify({'message': 'Invalid data. Ensure you provide username, email, password, and role.'}), 400

    # Check if the email is already registered
    if User.query.filter_by(email=data['email']).first():
        return jsonify({'message': 'Email already registered. Please try logging in or use a different email.'}), 400

    
    # Преобразуем строковое значение роли в объект перечисления Role
    role_value = data['role']
    role_enum = None
    
    # Находим соответствующее значение в перечислении Role
    for role in Role:
        if role.value == role_value:
            role_enum = role
            break
    
    if not role_enum:
        return jsonify({'message': f'Недопустимое значение роли: {role_value}. Допустимые значения: {[r.value for r in Role]}'}), 400
    
    new_user = User(
        username=data['username'],
        email=data['email'],
        password=bcrypt.generate_password_hash(data['password']).decode('utf-8'),  # Hash the password using bcrypt
        role=role_enum
    )

    # Add the new user to the database
    db.session.add(new_user)
    db.session.commit()

    # Create the access token for the newly registered user
    access_token = create_access_token(identity={
        'id': new_user.id,
        'username': new_user.username,
        'role': new_user.role.value  # Используем строковое значение роли для сериализации
    }, expires_delta=datetime.timedelta(days=1))

    # Получаем данные пользователя с разрешениями для интерфейса
    user_data = get_user_data_with_permissions(new_user)
    
    return jsonify({
        'message': 'User registered and logged in successfully.',
        'access_token': access_token,
        'user': user_data
    }), 201



@bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()

    # Fetch user by email
    user = User.query.filter_by(email=data['email']).first()

    # Check if user exists and password matches
    if user and bcrypt.check_password_hash(user.password, data['password']):
        access_token = create_access_token(identity={
            'id': user.id,
            'username': user.username,
            'role': user.role.value  # Используем строковое значение роли для сериализации
        }, expires_delta=datetime.timedelta(days=1))

        # Получаем данные пользователя с разрешениями для интерфейса
        user_data = get_user_data_with_permissions(user)
        
        return jsonify({
            'message': 'Login successful.',
            'access_token': access_token,
            'user': user_data
        }), 200

    # Invalid credentials
    return jsonify({'message': 'Invalid credentials. Please check your email and password.'}), 401


@bp.route('/logout', methods=['POST'])
@jwt_required()
def logout():
    response = jsonify({'message': 'Successfully logged out.'})
    unset_jwt_cookies(response)
    return response