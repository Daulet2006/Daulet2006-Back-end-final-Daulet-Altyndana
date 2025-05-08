# Role service module for business logic
from ..models import User, Role
from ..role_utils import update_user_role, get_user_data_with_permissions

def get_user_permissions(user):
    return get_user_data_with_permissions(user)

def update_role(user_id, new_role, current_user):
    target_user = User.query.get(user_id)
    if not target_user:
        return None, {'message': 'User not found'}, 404
    if (target_user.role == Role.OWNER or new_role.upper() == 'OWNER') and current_user.role != Role.OWNER:
        return None, {'message': 'Insufficient rights to manage owners'}, 403
    updated_user, error = update_user_role(user_id, new_role)
    if error:
        return None, {'message': error}, 400
    return updated_user, None, 200

def get_all_roles():
    return [role.value for role in Role]

def get_users_with_roles():
    users = User.query.all()
    return [{
        'id': user.id,
        'username': user.username,
        'email': user.email,
        'role': user.role.value
    } for user in users]