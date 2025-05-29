# app/util.py
from flask_jwt_extended import jwt_required, get_jwt_identity
from flask import jsonify

def role_required(*roles):
    def wrapper(fn):
        @jwt_required()
        def decorator(*args, **kwargs):
            current_user = get_jwt_identity()
            if current_user['role'] not in [role.value for role in roles]:
                return jsonify({'message': 'Доступ запрещен'}), 403
            return fn(*args, **kwargs)
        decorator.__name__ = fn.__name__
        return decorator
    return wrapper