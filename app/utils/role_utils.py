# app/role_utils.py
from app import db
from app.models.user_model import Role, User

# Dictionary with permissions for each role
ROLE_PERMISSIONS = {
    Role.CLIENT: {
        'interface_sections': [
            'profile', 'products', 'pets', 'orders', 'appointments', 'chat'
        ],
        'actions': [
            'view_products', 'view_pets', 'create_order', 'view_own_orders',
            'book_appointment', 'view_own_appointments', 'send_message'
        ]
    },
    Role.SELLER: {
        'interface_sections': [
            'profile', 'products', 'pets', 'sales', 'chat'
        ],
        'actions': [
            'view_products', 'create_product', 'update_own_product', 'delete_own_product',
            'view_pets', 'create_pet', 'update_own_pet', 'delete_own_pet',
            'view_own_sales', 'send_message'
        ]
    },
    Role.ADMIN: {
        'interface_sections': [
            'profile', 'users', 'products', 'pets', 'orders', 'appointments',
            'categories', 'chat'
        ],
        'actions': [
            'view_all_users', 'update_user', 'delete_user', 'view_all_products',
            'update_any_product', 'delete_any_product', 'view_all_pets',
            'update_any_pet', 'delete_any_pet', 'view_all_orders', 'update_any_order',
            'view_all_appointments', 'update_any_appointment', 'manage_categories',
            'send_message'
        ]
    },
    Role.OWNER: {
        'interface_sections': [
            'profile', 'users', 'products', 'pets', 'orders', 'appointments',
            'categories', 'system', 'stats', 'chat'
        ],
        'actions': [
            'view_all_users', 'update_user', 'delete_user', 'view_all_products',
            'update_any_product', 'delete_any_product', 'view_all_pets',
            'update_any_pet', 'delete_any_pet', 'view_all_orders', 'update_any_order',
            'view_all_appointments', 'update_any_appointment', 'manage_categories',
            'manage_roles', 'view_system_stats', 'configure_system', 'send_message'
        ]
    }
}

def get_user_permissions(user):
    """Get user permissions based on their role"""
    if not user or not user.role:
        return {
            'interface_sections': ['login', 'register', 'products', 'pets'],
            'actions': ['view_products', 'view_pets']
        }
    return ROLE_PERMISSIONS.get(user.role, ROLE_PERMISSIONS[Role.CLIENT])

def can_access_section(user, section):
    """Check if user can access a specific interface section"""
    permissions = get_user_permissions(user)
    return section in permissions['interface_sections']

def can_perform_action(user, action):
    """Check if user can perform a specific action"""
    permissions = get_user_permissions(user)
    return action in permissions['actions']

def get_user_data_with_permissions(user):
    """Return user data with their permissions"""
    if not user:
        return None
    permissions = get_user_permissions(user)
    return {
        'id': user.id,
        'username': user.username,
        'email': user.email,
        'role': user.role.value,
        'permissions': permissions,
        'isBanned': user.isBanned
    }

def update_user_role(user_id, new_role):
    """Update a user's role and return updated data"""
    user = User.query.get(user_id)
    if not user:
        return None, 'Пользователь не найден'
    try:
        role = Role[new_role.upper()]
    except (KeyError, AttributeError):
        return None, f'Недопустимая роль: {new_role}'
    user.role = role
    db.session.commit()
    return get_user_data_with_permissions(user), None