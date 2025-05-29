from flask_restx import Namespace, Resource, fields
from flask import request, jsonify
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity, unset_jwt_cookies
from sqlalchemy import func
from .. import db, bcrypt
from app.utils.role_utils import get_user_data_with_permissions
from sqlalchemy.exc import IntegrityError
import datetime
import re
from app.models.user_model import User, Role

auth_ns = Namespace('auth', description='Операции аутентификации', tags=['Аутентификация'])

register_model = auth_ns.model('Register', {
    'username': fields.String(required=True, description='Имя пользователя'),
    'email': fields.String(required=True, description='Электронная почта'),
    'password': fields.String(required=True, description='Пароль')
})

login_model = auth_ns.model('Login', {
    'email': fields.String(required=True, description='Электронная почта'),
    'password': fields.String(required=True, description='Пароль')
})

PASSWORD_REGEX = re.compile(r'^(?=.*[A-Za-z])(?=.*\d).{6,}$')
EMAIL_REGEX = re.compile(r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$')

@auth_ns.route('/roles')
class Roles(Resource):
    def get(self):
        roles = [role.value for role in Role]
        return {'user_model.py': roles}, 200

def get_next_user_id():
    max_id = db.session.query(func.max(User.id)).scalar()  # Получаем максимальный id
    if max_id is None:  # Если пользователей нет, начинаем с 1
        return 1
    return max_id + 1  # Увеличиваем максимальный id на 1

@auth_ns.route('/register')
class Register(Resource):
    @auth_ns.expect(register_model)
    def post(self):
        """Регистрация нового пользователя (по умолчанию роль CLIENT)"""
        data = request.get_json()
        if not all(k in data for k in ('username', 'email', 'password')):
            return {'message': 'Отсутствуют обязательные поля: username, email, password.'}, 400

        if not EMAIL_REGEX.match(data['email']):
            return {'message': 'Неверный формат email.'}, 400

        if not PASSWORD_REGEX.match(data['password']):
            return {'message': 'Пароль должен быть минимум 6 символов, содержать хотя бы одну букву и одну цифру.'}, 400

        if User.query.filter_by(email=data['email']).first():
            return {'message': 'Email уже зарегистрирован.'}, 400
        if User.query.filter_by(username=data['username']).first():
            return {'message': 'Имя пользователя занято.'}, 400

        # Генерация следующего уникального ID
        new_user_id = get_next_user_id()

        new_user = User(
            id=new_user_id,  # Явно указываем id
            username=data['username'],
            email=data['email'],
            password=bcrypt.generate_password_hash(data['password']).decode('utf-8'),
            role=Role.CLIENT.value
        )

        try:
            db.session.add(new_user)
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            return {'message': 'Ошибка базы данных: невозможно зарегистрировать пользователя.'}, 500

        access_token = create_access_token(identity={
            'id': new_user.id,
            'username': new_user.username,
            'role': new_user.role.value
        }, expires_delta=datetime.timedelta(minutes=30))

        user_data = get_user_data_with_permissions(new_user)

        return {
            'message': 'Пользователь успешно зарегистрирован.',
            'access_token': access_token,
            'user': user_data
        }, 201

@auth_ns.route('/login')
class Login(Resource):
    @auth_ns.expect(login_model)
    def post(self):
        """Вход пользователя"""
        data = request.get_json()
        if not all(k in data for k in ('email', 'password')):
            return {'message': 'Отсутствуют обязательные поля: email, password.'}, 400

        if not EMAIL_REGEX.match(data['email']):
            return {'message': 'Неверный формат email.'}, 400

        user = User.query.filter_by(email=data['email']).first()

        if not user:
            return {'message': 'Пользователь не найден.'}, 404

        if user.isBanned:
            return {'message': 'Ваш аккаунт заблокирован. Обратитесь в поддержку.'}, 403

        if bcrypt.check_password_hash(user.password, data['password']):
            access_token = create_access_token(identity={
                'id': user.id,
                'username': user.username,
                'role': user.role.value
            }, expires_delta=datetime.timedelta(minutes=30))

            user_data = get_user_data_with_permissions(user)

            return {
                'message': 'Вход выполнен успешно.',
                'access_token': access_token,
                'user': user_data
            }, 200

        return {'message': 'Неверный пароль.'}, 401

@auth_ns.route('/logout')
class Logout(Resource):
    @jwt_required()
    def post(self):
        """Выход пользователя"""
        response = jsonify({'message': 'Выход выполнен успешно.'})
        unset_jwt_cookies(response)
        return response

@auth_ns.route('/verify')
class VerifyToken(Resource):
    @jwt_required()
    def get(self):
        """Проверка валидности токена"""
        identity = get_jwt_identity()
        user = User.query.get(identity['id'])
        if not user:
            return {'message': 'Пользователь не найден.'}, 404
        return {
            'message': 'Токен действителен.',
            'user': get_user_data_with_permissions(user)
        }, 200