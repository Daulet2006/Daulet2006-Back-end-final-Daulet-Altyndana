from flask_restx import Namespace, Resource, fields
from flask import request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from ..models import Order, Product, Pet, User, Role, order_product, order_pet
from .. import db
from datetime import datetime
from ..utils import role_required

order_ns = Namespace('orders', description='Operations related to orders')

# Swagger models
product_order_item = order_ns.model('ProductOrderItem', {
    'id': fields.Integer(required=True, description='Product ID'),
    'quantity': fields.Integer(required=True, description='Quantity')
})

order_model = order_ns.model('Order', {
    'products': fields.List(fields.Nested(product_order_item), description='List of products with quantities'),
    'pets': fields.List(fields.Integer, description='List of pet IDs')
})

# Helper functions
def format_order(order):
    products_data = []
    product_associations = db.session.query(order_product).filter_by(order_id=order.id).all()
    for assoc in product_associations:
        product = Product.query.get(assoc.product_id)
        if product:
            products_data.append({
                'id': product.id,
                'name': product.name,
                'quantity': assoc.quantity,
                'price': product.price
            })

    pets_data = [{'id': p.id, 'name': p.name, 'species': p.species, 'price': p.price} for p in order.pets]

    return {
        'id': order.id,
        'client_id': order.client_id,
        'order_date': order.order_date.isoformat(),
        'total_amount': order.total_amount,
        'status': order.status,
        'products': products_data,
        'pets': pets_data
    }

def check_authorization(order, current_user_id, current_user_role):
    if current_user_role == Role.CLIENT:
        return order.client_id == current_user_id
    if current_user_role in [Role.ADMIN, Role.OWNER]:
        return True
    if current_user_role == Role.SELLER:
        order_products = db.session.query(order_product).filter_by(order_id=order.id).all()
        seller_products = Product.query.filter_by(seller_id=current_user_id).all()
        seller_product_ids = {p.id for p in seller_products}
        return any(assoc.product_id in seller_product_ids for assoc in order_products)
    return False

@order_ns.route('')
class OrderList(Resource):
    @jwt_required()
    def get(self):
        """Get all orders"""
        current_user_identity = get_jwt_identity()
        current_user_id = current_user_identity['id']
        current_user_role = Role(current_user_identity['role'])

        try:
            query = Order.query
            if current_user_role == Role.CLIENT:
                query = query.filter_by(client_id=current_user_id)
            orders = query.order_by(Order.order_date.desc()).all()
            return [format_order(order) for order in orders], 200
        except Exception as e:
            return {'message': 'Failed to retrieve orders', 'error': str(e)}, 500

    @jwt_required()
    @role_required(Role.CLIENT)
    @order_ns.expect(order_model)
    def post(self):
        """Create a new order"""
        current_user_identity = get_jwt_identity()
        client_id = current_user_identity['id']
        data = request.get_json()

        if not data or 'products' not in data or 'pets' not in data:
            return {'message': 'Invalid request format'}, 400

        product_ids_with_quantity = data.get('products', [])
        pet_ids = data.get('pets', [])

        if not isinstance(product_ids_with_quantity, list) or not isinstance(pet_ids, list):
            return {'message': 'Products and pets must be lists'}, 400

        if not product_ids_with_quantity and not pet_ids:
            return {'message': 'Order must contain at least one product or pet'}, 400

        total_amount = 0
        products_in_order = []
        pets_in_order = []

        try:
            for index, item in enumerate(product_ids_with_quantity):
                if not isinstance(item, dict) or 'id' not in item or 'quantity' not in item:
                    return {'message': f'Invalid product format at index {index}'}, 400
                product_id = item['id']
                quantity = item['quantity']
                product = Product.query.get(product_id)
                if not product:
                    return {'message': f'Product with ID {product_id} not found'}, 404
                if product.stock < quantity:
                    return {'message': f'Insufficient stock for product {product.name} (ID: {product_id}). Available: {product.stock}'}, 400
                products_in_order.append({'product': product, 'quantity': quantity})
                total_amount += product.price * quantity

            for index, pet_id in enumerate(pet_ids):
                pet = Pet.query.get(pet_id)
                if not pet:
                    return {'message': f'Pet with ID {pet_id} not found'}, 404
                existing_order_link = db.session.query(order_pet).filter_by(pet_id=pet.id).first()
                if existing_order_link or pet.status != 'available':
                    return {'message': f'Pet {pet.name} (ID: {pet_id}) недоступен для заказа. Статус: {pet.status}'}, 400
                pets_in_order.append(pet)
                total_amount += pet.price

            new_order = Order(
                client_id=client_id,
                order_date=datetime.utcnow(),
                total_amount=total_amount,
                status='Pending'
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
                pet.status = 'reserved'
                new_order.pets.append(pet)

            db.session.commit()
            return {'message': 'Order created successfully', 'order_id': new_order.id}, 201
        except Exception as e:
            db.session.rollback()
            return {'message': 'Failed to create order', 'error': str(e)}, 500

@order_ns.route('/<int:order_id>')
class OrderResource(Resource):
    @jwt_required()
    def get(self, order_id):
        """Get a single order"""
        current_user_identity = get_jwt_identity()
        current_user_id = current_user_identity['id']
        current_user_role = Role(current_user_identity['role'])

        try:
            order = Order.query.get_or_404(order_id)
            if not check_authorization(order, current_user_id, current_user_role):
                return {'message': 'Permission denied'}, 403
            return format_order(order), 200
        except Exception as e:
            return {'message': 'Failed to retrieve order', 'error': str(e)}, 500

    @jwt_required()
    @role_required(Role.ADMIN, Role.OWNER, Role.SELLER)
    def put(self, order_id):
        """Update order status"""
        current_user_identity = get_jwt_identity()
        current_user_id = current_user_identity['id']
        current_user_role = Role(current_user_identity['role'])
        data = request.get_json()

        try:
            order = Order.query.get_or_404(order_id)
            if not check_authorization(order, current_user_id, current_user_role):
                return {'message': 'Permission denied'}, 403

            new_status = data.get('status')
            if not new_status:
                return {'message': 'Missing status field'}, 400

            allowed_transitions = {
                'Pending': ['Processing', 'Cancelled'],
                'Processing': ['Shipped', 'Cancelled'],
                'Shipped': ['Completed'],
                'Cancelled': [],
                'Completed': []
            }

            if new_status not in allowed_transitions.get(order.status, []):
                return {'message': f'Invalid status transition from {order.status} to {new_status}'}, 400

            if new_status == 'Cancelled':
                for pet in order.pets:
                    pet.status = 'available'
            elif new_status == 'Completed':
                for pet in order.pets:
                    pet.status = 'sold'

            order.status = new_status
            db.session.commit()
            return {'message': 'Order updated successfully'}, 200
        except Exception as e:
            db.session.rollback()
            return {'message': 'Failed to update order', 'error': str(e)}, 500

    @jwt_required()
    @role_required(Role.ADMIN, Role.OWNER)
    def delete(self, order_id):
        """Delete an order"""
        try:
            order = Order.query.get_or_404(order_id)
            for pet in order.pets:
                pet.status = 'available'
            db.session.delete(order)
            db.session.commit()
            return {'message': 'Order deleted successfully'}, 200
        except Exception as e:
            db.session.rollback()
            return {'message': 'Failed to delete order', 'error': str(e)}, 500