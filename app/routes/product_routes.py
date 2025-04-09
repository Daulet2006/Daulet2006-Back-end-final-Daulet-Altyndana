from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from ..models import Product, User
from .. import db
from ..utils import role_required

bp = Blueprint('products', __name__, url_prefix='/products')

# Получение всех продуктов
@bp.route('/', methods=['GET'])
def get_products():
    products = Product.query.all()
    return jsonify([{
        'id': p.id,
        'name': p.name,
        'description': p.description,
        'price': p.price,
        'stock': p.stock,
        'seller_id': p.seller_id
    } for p in products])

# Фильтрация продуктов по имени
@bp.route('/filter', methods=['GET'])
def filter_products():
    name = request.args.get('name', '')
    products = Product.query.filter(Product.name.ilike(f'%{name}%')).all()
    return jsonify([{
        'id': p.id,
        'name': p.name,
        'description': p.description,
        'price': p.price,
        'stock': p.stock,
        'seller_id': p.seller_id
    } for p in products])

# Добавление нового продукта (для seller)
@bp.route('/', methods=['POST'])
@role_required('seller')
def add_product():
    data = request.get_json()
    current_user = get_jwt_identity()
    new_product = Product(
        name=data['name'],
        description=data['description'],
        price=data['price'],
        stock=data['stock'],
        seller_id=current_user['id']
    )
    db.session.add(new_product)
    db.session.commit()
    return jsonify({'message': 'Product added'}), 201

# Обновление продукта (для seller или admin)
@bp.route('/<int:id>', methods=['PUT'])
@role_required('seller', 'admin')
def update_product(id):
    product = Product.query.get_or_404(id)
    data = request.get_json()
    current_user = get_jwt_identity()

    if current_user['role'] == 'admin' or product.seller_id == current_user['id']:
        product.name = data['name']
        product.description = data['description']
        product.price = data['price']
        product.stock = data['stock']
        db.session.commit()
        return jsonify({'message': 'Product updated'}), 200
    return jsonify({'message': 'Access denied'}), 403

# Удаление продукта (для seller или admin)
@bp.route('/<int:id>', methods=['DELETE'])
@role_required('seller', 'admin')
def delete_product(id):
    product = Product.query.get_or_404(id)
    current_user = get_jwt_identity()

    if current_user['role'] == 'admin' or product.seller_id == current_user['id']:
        db.session.delete(product)
        db.session.commit()
        return jsonify({'message': 'Product deleted'}), 200

    return jsonify({'message': 'Access denied'}), 403

# Покупка продукта (для customer)
@bp.route('/buy/<int:product_id>', methods=['POST'])
@role_required('customer')
def buy_product(product_id):
    product = Product.query.get_or_404(product_id)
    if product.stock <= 0:
        return jsonify({'message': 'Product out of stock'}), 400
    current_user = get_jwt_identity()
    user = User.query.get(current_user['id'])
    user.products.append(product)
    product.stock -= 1
    db.session.commit()
    return jsonify({'message': 'Product purchased'}), 200
