import datetime
from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity, set_access_cookies, unset_jwt_cookies
from ..models import User, Role
from .. import db, bcrypt
from ..role_utils import get_user_data_with_permissions
from sqlalchemy.exc import IntegrityError

bp = Blueprint('auth', __name__, url_prefix='/auth')

@bp.route('/register', methods=['POST'])
def register():
    data = request.get_json()

    if not all(k in data for k in ('username', 'email', 'password', 'role')):
        return jsonify({'message': 'Invalid data. Ensure you provide username, email, password, and role.'}), 400

    # Check if the email is already registered
    if User.query.filter_by(email=data['email']).first():
        return jsonify({'message': 'Email already registered. Please try logging in or use a different email.'}), 400

    # Check if the username is already taken
    if User.query.filter_by(username=data['username']).first():
        return jsonify({'message': 'Username already taken. Please choose a different username.'}), 400

    role_value = data['role']
    role_enum = None
    for role in Role:
        if role.value == role_value:
            role_enum = role
            break

    if not role_enum:
        return jsonify({'message': f'Invalid role: {role_value}. Valid roles: {[r.value for r in Role]}'}), 400

    new_user = User(
        username=data['username'],
        email=data['email'],
        password=bcrypt.generate_password_hash(data['password']).decode('utf-8'),
        role=role_enum
    )

    try:
        db.session.add(new_user)
        db.session.commit()
    except IntegrityError as e:
        db.session.rollback()
        error_message = str(e.orig) if e.orig else 'Database integrity error'
        return jsonify({'message': f'Failed to register user: {error_message}. Please try again.'}), 500

    access_token = create_access_token(identity={
        'id': new_user.id,
        'username': new_user.username,
        'role': new_user.role.value  # Keep original case ('Admin')
    }, expires_delta=datetime.timedelta(days=1))

    user_data = get_user_data_with_permissions(new_user)

    return jsonify({
        'message': 'User registered and logged in successfully.',
        'access_token': access_token,
        'user': user_data
    }), 201

@bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()

    user = User.query.filter_by(email=data['email']).first()

    if user and bcrypt.check_password_hash(user.password, data['password']):
        access_token = create_access_token(identity={
            'id': user.id,
            'username': user.username,
            'role': user.role.value  # Keep original case ('Admin')
        }, expires_delta=datetime.timedelta(days=1))

        user_data = get_user_data_with_permissions(user)

        return jsonify({
            'message': 'Login successful.',
            'access_token': access_token,
            'user': user_data
        }), 200

    return jsonify({'message': 'Invalid credentials. Please check your email and password.'}), 401

@bp.route('/logout', methods=['POST'])
@jwt_required()
def logout():
    response = jsonify({'message': 'Successfully logged out.'})
    unset_jwt_cookies(response)
    return response