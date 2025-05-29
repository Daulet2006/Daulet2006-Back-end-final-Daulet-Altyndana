from flask_restx import Namespace, Resource, fields
from flask import request
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.models.relationship_model import order_product
from .. import db
from datetime import datetime
from app.utils.util import role_required
import logging
from app.models.user_model import User, Role
from app.models.product_model import Product
from app.models.pet_model import Pet, PetStatus
from ..models.order_model import Order

order_ns = Namespace('orders', description='Операции с заказами')

# Настройка логирования
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s %(levelname)s %(name)s: %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# Модели для Swagger
product_order_item = order_ns.model('ProductOrderItem', {
    'id': fields.Integer(required=True, description='ID товара'),
    'quantity': fields.Integer(required=True, description='Количество')
})

order_model = order_ns.model('Order', {
    'products': fields.List(fields.Nested(product_order_item), description='Список товаров с количеством'),
    'pets': fields.List(fields.Integer, description='Список ID питомцев')
})

# Вспомогательные функции
def format_order(order):
    logger.debug(f"Formatting order ID {order.id}")
    products_data = []
    product_associations = db.session.query(order_product).filter_by(order_id=order.id).all()
    for assoc in product_associations:
        product = Product.query.get(assoc.product_id)
        if product:
            products_data.append({
                'id': product.id,
                'name': product.name,
                'quantity': assoc.quantity,
                'price': float(product.price) if product.price is not None else 0.0,
                'sellerId': product.seller_id,
                'type': 'product'
            })

    pets_data = [
        {'id': p.id, 'name': p.name, 'price': float(p.price) if p.price is not None else 0.0, 'type': 'pet', 'quantity': 1}
        for p in order.pets
    ]

    user = User.query.get(order.client_id)
    formatted_order = {
        'id': order.id,
        'userId': order.client_id,
        'date': order.order_date.isoformat(),
        'total': float(order.total_amount) if order.total_amount is not None else 0.0,
        'status': order.status.lower() if order.status else 'unknown',
        'items': products_data + pets_data,
        'user': {
            'username': user.username if user else 'Неизвестно',
            'email': user.email if user else 'Н/Д'
        }
    }
    logger.info(f"Formatted order {order.id}: {formatted_order}")
    return formatted_order

def check_authorization(order, current_user_id, current_user_role):
    logger.debug(f"Checking authorization for order {order.id}, user {current_user_id}, role {current_user_role}")
    # Allow clients to access their own orders
    if current_user_role == Role.CLIENT and order.client_id == current_user_id:
        return True
    # Allow admins and owners to access all orders
    if current_user_role in [Role.ADMIN, Role.OWNER]:
        return True
    # Allow sellers to access orders containing their products
    if current_user_role == Role.SELLER:
        product_associations = db.session.query(order_product).filter_by(order_id=order.id).all()
        for assoc in product_associations:
            product = Product.query.get(assoc.product_id)
            if product and product.seller_id == current_user_id:
                return True
    return False
@order_ns.route('/status-transitions')
class StatusTransitions(Resource):
    def get(self):
        """Получить возможные переходы статусов заказа"""
        return {
            'pending': ['processing', 'cancelled'],
            'processing': ['shipped', 'cancelled'],
            'shipped': ['delivered'],
            'cancelled': [],
            'delivered': []
        }, 200

@order_ns.route('')
class OrderList(Resource):
    @jwt_required()
    @order_ns.doc('list_orders', security='BearerAuth')
    def get(self):
        """Получить все заказы"""
        current_user_identity = get_jwt_identity()
        current_user_id = current_user_identity['id']
        try:
            current_user_role = Role(current_user_identity['role'])
        except ValueError as e:
            logger.error(f"Invalid role in JWT: {current_user_identity['role']}")
            return {'message': 'Недопустимая роль пользователя'}, 403

        try:
            query = Order.query
            if current_user_role == Role.CLIENT:
                query = query.filter_by(client_id=current_user_id)
            orders = query.order_by(Order.order_date.desc()).all()
            logger.info(f"Returning {len(orders)} orders for user {current_user_id}, role: {current_user_role}")
            return [format_order(order) for order in orders], 200
        except Exception as e:
            logger.error(f"Ошибка получения заказов: {str(e)}")
            return {'message': 'Не удалось получить заказы', 'error': str(e)}, 500

    @jwt_required()
    @role_required(Role.CLIENT)
    @order_ns.expect(order_model)
    @order_ns.doc('create_order', security='BearerAuth')
    def post(self):
        """Создать новый заказ"""
        current_user_identity = get_jwt_identity()
        client_id = current_user_identity['id']
        data = request.get_json()

        if not data or 'products' not in data or 'pets' not in data:
            return {'message': 'Неверный формат запроса'}, 400

        product_ids_with_quantity = data.get('products', [])
        pet_ids = data.get('pets', [])

        if not isinstance(product_ids_with_quantity, list) or not isinstance(pet_ids, list):
            return {'message': 'Товары и питомцы должны быть списками'}, 400

        if not product_ids_with_quantity and not pet_ids:
            return {'message': 'Заказ должен содержать хотя бы один товар или питомца'}, 400

        total_amount = 0
        products_in_order = []
        pets_in_order = []

        try:
            for index, item in enumerate(product_ids_with_quantity):
                if not isinstance(item, dict) or 'id' not in item or 'quantity' not in item:
                    return {'message': f'Неверный формат товара на позиции {index}'}, 400
                product_id = item['id']
                quantity = item['quantity']
                product = Product.query.get(product_id)
                if not product:
                    return {'message': f'Товар с ID {product_id} не найден'}, 404
                if product.stock < quantity:
                    return {'message': f'Недостаточно запасов для товара {product.name} (ID: {product_id}). Доступно: {product.stock}'}, 400
                products_in_order.append({'product': product, 'quantity': quantity})
                total_amount += product.price * quantity

            for index, pet_id in enumerate(pet_ids):
                pet = Pet.query.get(pet_id)
                if not pet:
                    return {'message': f'Питомец с ID {pet_id} не найден'}, 404
                logger.debug(f"Checking pet ID {pet_id}, status: {pet.status}, type: {type(pet.status)}")
                pet_status = pet.status if isinstance(pet.status, str) else pet.status.value
                if pet_status != PetStatus.AVAILABLE.value:
                    return {'message': f'Питомец {pet.name} (ID: {pet_id}) недоступен. Статус: {pet_status}'}, 400
                pets_in_order.append(pet)
                total_amount += pet.price

            new_order = Order(
                client_id=client_id,
                order_date=datetime.utcnow(),
                total_amount=total_amount,
                status='pending'
            )
            db.session.add(new_order)
            db.session.flush()

            for item in products_in_order:
                stmt = order_product.insert().values(
                    order_id=new_order.id,
                    product_id=item['product'].id,
                    quantity=item['quantity']
                )
                db.session.execute(stmt)
                item['product'].stock -= item['quantity']

            for pet in pets_in_order:
                pet.status = PetStatus.RESERVED.value
                new_order.pets.append(pet)

            db.session.commit()
            logger.info(f"Создан заказ {new_order.id} для клиента {client_id}, сумма: {total_amount}")
            return format_order(new_order), 201
        except Exception as e:
            db.session.rollback()
            logger.error(f"Ошибка создания заказа: {str(e)}")
            return {'message': 'Не удалось создать заказ', 'error': str(e)}, 500

@order_ns.route('/<int:order_id>')
class OrderResource(Resource):
    @role_required(Role.ADMIN, Role.OWNER, Role.SELLER, Role.CLIENT)
    @jwt_required()
    @order_ns.doc('get_order', security='BearerAuth')
    def get(self, order_id):
        """Получить один заказ"""
        current_user_identity = get_jwt_identity()
        current_user_id = current_user_identity['id']
        try:
            current_user_role = Role(current_user_identity['role'])
        except ValueError as e:
            logger.error(f"Invalid role in JWT: {current_user_identity['role']}")
            return {'message': 'Недопустимая роль пользователя'}, 403

        try:
            order = Order.query.get_or_404(order_id)
            if not check_authorization(order, current_user_id, current_user_role):
                return {'message': 'Доступ запрещен'}, 403
            return format_order(order), 200
        except Exception as e:
            logger.error(f"Ошибка получения заказа {order_id}: {str(e)}")
            return {'message': 'Не удалось получить заказ', 'error': str(e)}, 500

    @jwt_required()
    @role_required(Role.ADMIN, Role.OWNER, Role.SELLER)
    @order_ns.doc('update_order', security='BearerAuth')
    def put(self, order_id):
        """Обновить статус заказа"""
        current_user_identity = get_jwt_identity()
        current_user_id = current_user_identity['id']
        try:
            current_user_role = Role(current_user_identity['role'])
        except ValueError as e:
            logger.error(f"Invalid role in JWT: {current_user_identity['role']}")
            return {'message': 'Недопустимая роль пользователя'}, 403
        data = request.get_json()

        try:
            order = Order.query.get_or_404(order_id)
            if not check_authorization(order, current_user_id, current_user_role):
                return {'message': 'Доступ запрещен'}, 403

            new_status = data.get('status')
            if not new_status:
                return {'message': 'Отсутствует поле статуса'}, 400

            # Все допустимые статусы
            valid_statuses = ['pending', 'processing', 'shipped', 'delivered', 'cancelled']
            if new_status.lower() not in valid_statuses:
                return {'message': f'Недопустимый статус: {new_status}'}, 400

            # Проверка переходов статусов только для SELLER
            if current_user_role == Role.SELLER:
                allowed_transitions = {
                    'pending': ['processing', 'cancelled'],
                    'processing': ['shipped', 'cancelled'],
                    'shipped': ['delivered'],
                    'cancelled': [],
                    'delivered': []
                }
                if new_status not in allowed_transitions.get(order.status.lower(), []):
                    return {'message': f'Недопустимый переход статуса с {order.status} на {new_status}'}, 400

            if new_status == 'cancelled':
                for pet in order.pets:
                    pet.status = PetStatus.AVAILABLE.value
                    pet.owner_id = None
                order_products = db.session.query(order_product).filter_by(order_id=order.id).all()
                for assoc in order_products:
                    product = Product.query.get(assoc.product_id)
                    if product:
                        product.stock += assoc.quantity
                        product.owner_id = None

            elif new_status == 'delivered':
                for pet in order.pets:
                    pet.status = PetStatus.SOLD.value
                    pet.owner_id = order.client_id
                order_products = db.session.query(order_product).filter_by(order_id=order.id).all()
                for assoc in order_products:
                    product = Product.query.get(assoc.product_id)
                    if product:
                        product.owner_id = order.client_id

            order.status = new_status
            db.session.commit()
            logger.info(f"Обновлен статус заказа {order_id} на {new_status} пользователем {current_user_id} ({current_user_role})")
            return format_order(order), 200
        except Exception as e:
            db.session.rollback()
            logger.error(f"Ошибка обновления заказа {order_id}: {str(e)}")
            return {'message': 'Не удалось обновить заказ', 'error': str(e)}, 500

    @jwt_required()
    @role_required(Role.ADMIN, Role.OWNER, Role.SELLER)
    @order_ns.doc('delete_order', security='BearerAuth')
    def delete(self, order_id):
        """Удалить заказ"""
        try:
            order = Order.query.get_or_404(order_id)
            for pet in order.pets:
                pet.status = PetStatus.AVAILABLE.value
                pet.owner_id = None
            order_products = db.session.query(order_product).filter_by(order_id=order.id).all()
            for assoc in order_products:
                product = Product.query.get(assoc.product_id)
                if product:
                    product.stock += assoc.quantity
                    product.owner_id = None
            db.session.delete(order)
            db.session.commit()
            logger.info(f"Удален заказ {order_id}")
            return {'message': 'Заказ успешно удален'}, 200
        except Exception as e:
            db.session.rollback()
            logger.error(f"Ошибка удаления заказа {order_id}: {str(e)}")
            return {'message': 'Не удалось удалить заказ', 'error': str(e)}, 500