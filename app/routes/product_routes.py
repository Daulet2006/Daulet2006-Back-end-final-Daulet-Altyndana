# app/routes/product_routes.py
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from ..models import Product, Role, Category # Import Category
from .. import db
from ..utils import role_required
import logging # Import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

bp = Blueprint('products', __name__, url_prefix='/products')


# Helper function
def format_product(product):
    """
    Форматирует объект продукта для ответа в формате JSON.
    """
    return {
        'id': product.id,
        'name': product.name,
        'description': product.description,
        'price': product.price,
        'stock': product.stock,
        'image_url': product.image_url,
        'seller_id': product.seller_id,
        'category_id': product.category_id if product.category_id else None # Handle None category_id
    }


def check_product_authorization(product, current_user_identity):
    """
    Проверяет, имеет ли пользователь доступ к продукту (действует ли он как продавец или администратор).
    """
    current_user_id = current_user_identity['id']
    current_user_role = Role(current_user_identity['role'])

    if current_user_role not in [Role.ADMIN, Role.OWNER] and product.seller_id != current_user_id:
        return False
    return True


# Read All Products (Public)
@bp.route('/', methods=['GET'])
def get_products():
    try:
        products = Product.query.all()
        return jsonify([format_product(p) for p in products]), 200
    except Exception as e:
        logger.error(f"Error retrieving products: {e}", exc_info=True) # Log the full exception
        return jsonify({'message': 'Failed to retrieve products', 'error': str(e)}), 500


# Filter Products by Name
@bp.route('/filter', methods=['GET'])
def filter_products():
    name_query = request.args.get('name', '')
    try:
        if not name_query:
            return jsonify({'message': 'Name parameter is required for filtering'}), 400

        products = Product.query.filter(Product.name.ilike(f'%{name_query}%')).all()
        return jsonify([format_product(p) for p in products]), 200
    except Exception as e:
        return jsonify({'message': 'Failed to filter products', 'error': str(e)}), 500


# Create Product (Seller or Admin/Owner Only)
@bp.route('', methods=['POST'])
@jwt_required()
@role_required(Role.SELLER, Role.ADMIN, Role.OWNER)
def create_product():
    current_user_identity = get_jwt_identity()
    data = request.get_json()

    if not all(k in data for k in ('name', 'price', 'stock')):
        return jsonify({'message': 'Missing required fields (name, price, stock)'}), 400

    try:
        new_product = Product(
            name=data['name'],
            description=data.get('description'),
            price=float(data['price']),
            stock=int(data['stock']),
            image_url=data.get('image_url'),
            seller_id=current_user_identity['id'],
            category_id=data.get('category_id') # Get optional category_id
        )

        # Validate category_id if provided
        if new_product.category_id:
            category = Category.query.get(new_product.category_id)
            if not category:
                return jsonify({'message': f'Category with ID {new_product.category_id} not found'}), 404
        db.session.add(new_product)
        db.session.commit()
        return jsonify({'message': 'Product created successfully', 'product_id': new_product.id}), 201
    except ValueError:
        return jsonify({'message': 'Invalid data format for price or stock'}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': 'Failed to create product', 'error': str(e)}), 500


# Read Single Product (Public)
@bp.route('/<int:product_id>', methods=['GET'])
def get_product(product_id):
    try:
        product = Product.query.get_or_404(product_id)
        return jsonify(format_product(product)), 200
    except Exception as e:
        return jsonify({'message': 'Failed to retrieve product', 'error': str(e)}), 500


# Update Product (Seller who owns it or Admin/Owner)
@bp.route('/<int:product_id>', methods=['PUT', 'PATCH'])
@jwt_required()
@role_required(Role.SELLER, Role.ADMIN, Role.OWNER)
def update_product(product_id):
    current_user_identity = get_jwt_identity()
    data = request.get_json()

    try:
        product = Product.query.get_or_404(product_id)

        if not check_product_authorization(product, current_user_identity):
            return jsonify({'message': 'Permission denied: Not owner or admin/owner'}), 403

        # Update only provided fields
        if 'name' in data: product.name = data['name']
        if 'description' in data: product.description = data['description']
        if 'price' in data: product.price = float(data['price'])
        if 'stock' in data: product.stock = int(data['stock'])
        if 'image_url' in data: product.image_url = data['image_url']
        if 'category_id' in data:
            category_id = data['category_id']
            if category_id:
                category = Category.query.get(category_id)
                if not category:
                    return jsonify({'message': f'Category with ID {category_id} not found'}), 404
                product.category_id = category_id
            else:
                product.category_id = None # Allow setting category to null

        db.session.commit()
        return jsonify({'message': 'Product updated successfully'}), 200

    except ValueError:
        db.session.rollback()
        return jsonify({'message': 'Invalid data format for price or stock'}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': 'Failed to update product', 'error': str(e)}), 500


# Delete Product (Seller who owns it or Admin/Owner)
@bp.route('/<int:product_id>', methods=['DELETE'])
@jwt_required()
@role_required(Role.SELLER, Role.ADMIN, Role.OWNER)
def delete_product(product_id):
    current_user_identity = get_jwt_identity()

    try:
        product = Product.query.get_or_404(product_id)

        if not check_product_authorization(product, current_user_identity):
            return jsonify({'message': 'Permission denied: Not owner or admin/owner'}), 403

        db.session.delete(product)
        db.session.commit()
        return jsonify({'message': 'Product deleted successfully'}), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'message': 'Failed to delete product', 'error': str(e)}), 500