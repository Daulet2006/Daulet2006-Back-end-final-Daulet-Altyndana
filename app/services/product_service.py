# Product service module for business logic
from ..models import Product
from .. import db

def format_product(product):
    return {
        'id': product.id,
        'name': product.name,
        'description': product.description,
        'price': product.price,
        'stock': product.stock,
        'seller_id': product.seller_id,
        'category_id': product.category_id
    }

def get_all_products():
    products = Product.query.all()
    return [format_product(p) for p in products]

def get_product_by_id(product_id):
    product = Product.query.get_or_404(product_id)
    return format_product(product)

def create_product(data, seller_id):
    try:
        new_product = Product(
            name=data['name'],
            description=data.get('description'),
            price=data['price'],
            stock=data['stock'],
            seller_id=seller_id,
            category_id=data.get('category_id')
        )
        db.session.add(new_product)
        db.session.commit()
        return format_product(new_product), None, 201
    except Exception as e:
        db.session.rollback()
        return None, {'message': 'Error creating product', 'error': str(e)}, 500

def update_product(product_id, data, seller_id):
    try:
        product = Product.query.get_or_404(product_id)
        if product.seller_id != seller_id:
            return None, {'message': 'No permission to update this product'}, 403
        product.name = data.get('name', product.name)
        product.description = data.get('description', product.description)
        product.price = data.get('price', product.price)
        product.stock = data.get('stock', product.stock)
        product.category_id = data.get('category_id', product.category_id)
        db.session.commit()
        return format_product(product), None, 200
    except Exception as e:
        db.session.rollback()
        return None, {'message': 'Error updating product', 'error': str(e)}, 500

def delete_product(product_id, seller_id):
    try:
        product = Product.query.get_or_404(product_id)
        if product.seller_id != seller_id:
            return {'message': 'No permission to delete this product'}, 403
        db.session.delete(product)
        db.session.commit()
        return {'message': 'Product deleted'}, 200
    except Exception as e:
        db.session.rollback()
        return {'message': 'Error deleting product', 'error': str(e)}, 500