# app/routes/order_routes.py
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from ..models import Order, Product, Pet, User, Role, order_product, order_pet
from .. import db
from datetime import datetime
from ..utils import role_required

bp = Blueprint('orders', __name__, url_prefix='/orders')


# Helper functions
def format_order(order):
    """
    Форматирует объект заказа для ответа в JSON.
    """
    # Получение продуктов в заказе
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

    # Получение питомцев в заказе
    pets_data = [{
        'id': p.id,
        'name': p.name,
        'species': p.species,
        'price': p.price
    } for p in order.pets]

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
    """
    Проверяет, имеет ли пользователь доступ к указанному заказу.
    """
    if current_user_role == Role.CLIENT and order.client_id != current_user_id:
        return False
    # Добавьте дополнительные проверки для продавцов/администраторов при необходимости
    return True


# Create Order (Client only)
@bp.route('', methods=['POST'])
@jwt_required()
@role_required(Role.CLIENT)
def create_order():
    current_user_identity = get_jwt_identity()
    client_id = current_user_identity['id']

    data = request.get_json()
    product_ids_with_quantity = data.get('products', [])
    pet_ids = data.get('pets', [])

    if not product_ids_with_quantity and not pet_ids:
        return jsonify({'message': 'Order must contain at least one product or pet'}), 400

    total_amount = 0
    products_in_order = []
    pets_in_order = []

    try:
        # Process products in the order
        for item in product_ids_with_quantity:
            product_id = item.get('id')
            quantity = item.get('quantity', 1)
            if not isinstance(product_id, int) or not isinstance(quantity, int) or quantity <= 0:
                return jsonify({'message': f'Invalid product data: {item}'}), 400

            product = Product.query.get(product_id)
            if not product:
                return jsonify({'message': f'Product with ID {product_id} not found'}), 404
            if product.stock < quantity:
                return jsonify({
                                   'message': f'Insufficient stock for product {product.name} (ID: {product_id}). Available: {product.stock}'}), 400

            products_in_order.append({'product': product, 'quantity': quantity})
            total_amount += product.price * quantity
            product.stock -= quantity  # Decrease stock

        # Process pets in the order
        for pet_id in pet_ids:
            if not isinstance(pet_id, int):
                return jsonify({'message': f'Invalid pet ID: {pet_id}'}), 400

            pet = Pet.query.get(pet_id)
            if not pet:
                return jsonify({'message': f'Pet with ID {pet_id} not found'}), 404

            # Check if pet is already linked to another order
            existing_order_link = db.session.query(order_pet).filter_by(pet_id=pet.id).first()
            if existing_order_link:
                return jsonify({'message': f'Pet {pet.name} (ID: {pet_id}) is already part of an order or sold.'}), 400

            pets_in_order.append(pet)
            total_amount += pet.price

        # Create the new order
        new_order = Order(
            client_id=client_id,
            order_date=datetime.utcnow(),
            total_amount=total_amount,
            status='Pending'
        )
        db.session.add(new_order)
        db.session.flush()  # To get order ID

        # Add products to the order
        for item in products_in_order:
            stmt = order_product.insert().values(
                order_id=new_order.id,
                product_id=item['product'].id,
                quantity=item['quantity']
            )
            db.session.execute(stmt)

        # Add pets to the order
        new_order.pets.extend(pets_in_order)

        db.session.commit()
        return jsonify({'message': 'Order created successfully', 'order_id': new_order.id}), 201

    except Exception as e:
        db.session.rollback()
        print(f"Error creating order: {e}")
        return jsonify({'message': 'Failed to create order', 'error': str(e)}), 500


# Get All Orders
@bp.route('', methods=['GET'])
@jwt_required()
def get_orders():
    current_user_identity = get_jwt_identity()
    current_user_id = current_user_identity['id']
    current_user_role = Role(current_user_identity['role'])

    try:
        query = Order.query
        if current_user_role == Role.CLIENT:
            query = query.filter_by(client_id=current_user_id)

        orders = query.order_by(Order.order_date.desc()).all()
        return jsonify([format_order(order) for order in orders]), 200
    except Exception as e:
        return jsonify({'message': 'Failed to retrieve orders', 'error': str(e)}), 500


# Get Single Order
@bp.route('/<int:order_id>', methods=['GET'])
@jwt_required()
def get_order(order_id):
    current_user_identity = get_jwt_identity()
    current_user_id = current_user_identity['id']
    current_user_role = Role(current_user_identity['role'])

    try:
        order = Order.query.get_or_404(order_id)
        if not check_authorization(order, current_user_id, current_user_role):
            return jsonify({'message': 'Permission denied'}), 403
        return jsonify(format_order(order)), 200
    except Exception as e:
        return jsonify({'message': 'Failed to retrieve order', 'error': str(e)}), 500


# Update Order Status (Admin/Owner only)
@bp.route('/<int:order_id>', methods=['PUT', 'PATCH'])
@jwt_required()
@role_required(Role.ADMIN, Role.OWNER)
def update_order(order_id):
    data = request.get_json()

    try:
        order = Order.query.get_or_404(order_id)
        if 'status' in data:
            allowed_statuses = ['Pending', 'Completed', 'Cancelled']
            if data['status'] not in allowed_statuses:
                return jsonify({'message': f'Invalid status. Allowed: {", ".join(allowed_statuses)}'}), 400
            order.status = data['status']

        db.session.commit()
        return jsonify({'message': 'Order updated successfully'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': 'Failed to update order', 'error': str(e)}), 500


# Delete Order (Admin/Owner only)
@bp.route('/<int:order_id>', methods=['DELETE'])
@jwt_required()
@role_required(Role.ADMIN, Role.OWNER)
def delete_order(order_id):
    try:
        order = Order.query.get_or_404(order_id)
        db.session.delete(order)
        db.session.commit()
        return jsonify({'message': 'Order deleted successfully'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': 'Failed to delete order', 'error': str(e)}), 500
