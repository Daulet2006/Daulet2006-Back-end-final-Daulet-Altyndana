# app/role_utils.py
from flask import jsonify, g
from .models import Role, User

# Словарь с доступными функциями и разделами интерфейса для каждой роли
ROLE_PERMISSIONS = {
    Role.CLIENT: {
        'interface_sections': [
            'profile',          # Профиль пользователя
            'products',         # Просмотр товаров
            'pets',             # Просмотр питомцев
            'orders',           # Мои заказы
            'appointments',     # Мои записи к ветеринару
            'chat'              # Чат поддержки
        ],
        'actions': [
            'view_products',     # Просмотр товаров
            'view_pets',        # Просмотр питомцев
            'create_order',     # Создание заказа
            'view_own_orders',  # Просмотр своих заказов
            'book_appointment', # Запись к ветеринару
            'view_own_appointments', # Просмотр своих записей
            'send_message'      # Отправка сообщений в чат
        ]
    },
    Role.SELLER: {
        'interface_sections': [
            'profile',          # Профиль пользователя
            'products',         # Управление товарами
            'pets',             # Управление питомцами
            'sales',            # Мои продажи
            'chat'              # Чат поддержки
        ],
        'actions': [
            'view_products',     # Просмотр товаров
            'create_product',   # Создание товара
            'update_own_product', # Обновление своего товара
            'delete_own_product', # Удаление своего товара
            'view_pets',        # Просмотр питомцев
            'create_pet',       # Создание питомца
            'update_own_pet',   # Обновление своего питомца
            'delete_own_pet',   # Удаление своего питомца
            'view_own_sales',   # Просмотр своих продаж
            'send_message'      # Отправка сообщений в чат
        ]
    },
    Role.VETERINARIAN: {
        'interface_sections': [
            'profile',          # Профиль пользователя
            'appointments',     # Управление записями
            'pets',             # Просмотр питомцев
            'chat'              # Чат поддержки
        ],
        'actions': [
            'view_appointments', # Просмотр записей
            'update_appointment', # Обновление записи
            'view_pets',        # Просмотр питомцев
            'send_message'      # Отправка сообщений в чат
        ]
    },
    Role.ADMIN: {
        'interface_sections': [
            'profile',          # Профиль пользователя
            'users',            # Управление пользователями
            'products',         # Управление товарами
            'pets',             # Управление питомцами
            'orders',           # Управление заказами
            'appointments',     # Управление записями
            'categories',       # Управление категориями
            'chat'              # Чат поддержки
        ],
        'actions': [
            'view_all_users',    # Просмотр всех пользователей
            'update_user',      # Обновление пользователя
            'delete_user',      # Удаление пользователя
            'view_all_products', # Просмотр всех товаров
            'update_any_product', # Обновление любого товара
            'delete_any_product', # Удаление любого товара
            'view_all_pets',    # Просмотр всех питомцев
            'update_any_pet',   # Обновление любого питомца
            'delete_any_pet',   # Удаление любого питомца
            'view_all_orders',  # Просмотр всех заказов
            'update_any_order', # Обновление любого заказа
            'view_all_appointments', # Просмотр всех записей
            'update_any_appointment', # Обновление любой записи
            'manage_categories', # Управление категориями
            'send_message'      # Отправка сообщений в чат
        ]
    },
    Role.OWNER: {
        'interface_sections': [
            'profile',          # Профиль пользователя
            'users',            # Управление пользователями
            'products',         # Управление товарами
            'pets',             # Управление питомцами
            'orders',           # Управление заказами
            'appointments',     # Управление записями
            'categories',       # Управление категориями
            'system',           # Системные настройки
            'stats',            # Статистика
            'chat'              # Чат поддержки
        ],
        'actions': [
            'view_all_users',    # Просмотр всех пользователей
            'update_user',      # Обновление пользователя
            'delete_user',      # Удаление пользователя
            'view_all_products', # Просмотр всех товаров
            'update_any_product', # Обновление любого товара
            'delete_any_product', # Удаление любого товара
            'view_all_pets',    # Просмотр всех питомцев
            'update_any_pet',   # Обновление любого питомца
            'delete_any_pet',   # Удаление любого питомца
            'view_all_orders',  # Просмотр всех заказов
            'update_any_order', # Обновление любого заказа
            'view_all_appointments', # Просмотр всех записей
            'update_any_appointment', # Обновление любой записи
            'manage_categories', # Управление категориями
            'manage_roles',     # Изменение ролей пользователей
            'view_system_stats', # Просмотр системной статистики
            'configure_system', # Настройка системы
            'send_message'      # Отправка сообщений в чат
        ]
    }
}

# Функция для получения разрешений пользователя по его роли
def get_user_permissions(user):
    """Получает разрешения пользователя на основе его роли"""
    if not user or not user.role:
        # Если пользователь не авторизован или роль не указана, возвращаем базовые разрешения
        return {
            'interface_sections': ['login', 'register', 'products', 'pets'],
            'actions': ['view_products', 'view_pets']
        }
    
    return ROLE_PERMISSIONS.get(user.role, ROLE_PERMISSIONS[Role.CLIENT])

# Функция для проверки доступа к разделу интерфейса
def can_access_section(user, section):
    """Проверяет, имеет ли пользователь доступ к указанному разделу интерфейса"""
    permissions = get_user_permissions(user)
    return section in permissions['interface_sections']

# Функция для проверки возможности выполнения действия
def can_perform_action(user, action):
    """Проверяет, может ли пользователь выполнить указанное действие"""
    permissions = get_user_permissions(user)
    return action in permissions['actions']

# Функция для получения данных о пользователе с его разрешениями
def get_user_data_with_permissions(user):
    """Возвращает данные о пользователе вместе с его разрешениями"""
    if not user:
        return None
    
    permissions = get_user_permissions(user)
    
    return {
        'id': user.id,
        'username': user.username,
        'email': user.email,
        'role': user.role.value,
        'permissions': permissions
    }

# Функция для обновления роли пользователя
def update_user_role(user_id, new_role):
    """Обновляет роль пользователя и возвращает обновленные данные"""
    user = User.query.get(user_id)
    if not user:
        return None, 'Пользователь не найден'
    
    # Проверяем, существует ли такая роль
    try:
        role = Role[new_role.upper()]
    except (KeyError, AttributeError):
        return None, f'Недопустимая роль: {new_role}'
    
    # Обновляем роль пользователя
    user.role = role
    from . import db
    db.session.commit()
    
    # Возвращаем обновленные данные пользователя
    return get_user_data_with_permissions(user), None