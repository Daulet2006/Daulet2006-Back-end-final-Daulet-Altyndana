# app/role_functions.py
from functools import wraps
from flask import jsonify, request, g, current_app
import jwt
from .models import User, Role


# Функции для роли CLIENT
class ClientFunctions:
    @staticmethod
    def can_view_products():
        return True
    
    @staticmethod
    def can_view_pets():
        return True
    
    @staticmethod
    def can_create_order():
        return True
    
    @staticmethod
    def can_view_own_orders(user_id, order_id=None):
        return True
    
    @staticmethod
    def can_book_appointment():
        return True
    
    @staticmethod
    def can_view_own_appointments(user_id, appointment_id=None):
        return True
    
    @staticmethod
    def can_send_message():
        return True

# Функции для роли SELLER
class SellerFunctions:
    @staticmethod
    def can_view_products():
        return True
    
    @staticmethod
    def can_create_product():
        return True
    
    @staticmethod
    def can_update_product(user_id, product_id):
        # Проверка, является ли пользователь владельцем продукта
        from .models import Product
        product = Product.query.get(product_id)
        return product and product.seller_id == user_id
    
    @staticmethod
    def can_delete_product(user_id, product_id):
        # Проверка, является ли пользователь владельцем продукта
        from .models import Product
        product = Product.query.get(product_id)
        return product and product.seller_id == user_id
    
    @staticmethod
    def can_view_pets():
        return True
    
    @staticmethod
    def can_create_pet():
        return True
    
    @staticmethod
    def can_update_pet(user_id, pet_id):
        # Проверка, является ли пользователь владельцем питомца
        from .models import Pet
        pet = Pet.query.get(pet_id)
        return pet and pet.seller_id == user_id
    
    @staticmethod
    def can_delete_pet(user_id, pet_id):
        # Проверка, является ли пользователь владельцем питомца
        from .models import Pet
        pet = Pet.query.get(pet_id)
        return pet and pet.seller_id == user_id
    
    @staticmethod
    def can_view_own_sales(user_id):
        return True
    
    @staticmethod
    def can_send_message():
        return True

# Функции для роли VETERINARIAN
class VeterinarianFunctions:
    @staticmethod
    def can_view_appointments():
        return True
    
    @staticmethod
    def can_update_appointment(user_id, appointment_id):
        # Проверка, является ли пользователь ветеринаром для данной записи
        from .models import VetAppointment
        appointment = VetAppointment.query.get(appointment_id)
        return appointment and appointment.vet_id == user_id
    
    @staticmethod
    def can_view_pets():
        return True
    
    @staticmethod
    def can_send_message():
        return True

# Функции для роли ADMIN
class AdminFunctions:
    @staticmethod
    def can_view_all_users():
        return True
    
    @staticmethod
    def can_update_user(user_id=None):
        return True
    
    @staticmethod
    def can_delete_user(user_id=None):
        return True
    
    @staticmethod
    def can_view_all_products():
        return True
    
    @staticmethod
    def can_update_any_product(product_id=None):
        return True
    
    @staticmethod
    def can_delete_any_product(product_id=None):
        return True
    
    @staticmethod
    def can_view_all_pets():
        return True
    
    @staticmethod
    def can_update_any_pet(pet_id=None):
        return True
    
    @staticmethod
    def can_delete_any_pet(pet_id=None):
        return True
    
    @staticmethod
    def can_view_all_orders():
        return True
    
    @staticmethod
    def can_update_any_order(order_id=None):
        return True
    
    @staticmethod
    def can_view_all_appointments():
        return True
    
    @staticmethod
    def can_update_any_appointment(appointment_id=None):
        return True
    
    @staticmethod
    def can_manage_categories():
        return True
    
    @staticmethod
    def can_send_message():
        return True

# Функции для роли OWNER
class OwnerFunctions(AdminFunctions):
    # Владелец имеет все права администратора плюс дополнительные
    
    @staticmethod
    def can_manage_admins():
        return True
    
    @staticmethod
    def can_view_system_stats():
        return True
    
    @staticmethod
    def can_configure_system():
        return True

# Функция для получения класса функций по роли
def get_role_functions(role):
    role_map = {
        Role.CLIENT: ClientFunctions,
        Role.SELLER: SellerFunctions,
        Role.VETERINARIAN: VeterinarianFunctions,
        Role.ADMIN: AdminFunctions,
        Role.OWNER: OwnerFunctions
    }
    return role_map.get(role, ClientFunctions)  # По умолчанию возвращаем функции клиента