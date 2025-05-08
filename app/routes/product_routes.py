from flask_restx import Namespace, Resource, fields, reqparse
from flask import request, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from werkzeug.utils import secure_filename
import os
import uuid
import logging
from app.models import db, Product, Role
from app.utils import role_required

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

product_ns = Namespace('products', description='Operations related to products', path='/products')

# Swagger model
product_model = product_ns.model('Product', {
    'name': fields.String(required=True, description='Product name'),
    'price': fields.Float(required=True, description='Product price'),
    'description': fields.String(description='Product description'),
    'category_id': fields.Integer(required=True, description='Category ID'),
})

# Parser
product_parser = reqparse.RequestParser()
product_parser.add_argument('name', type=str, required=True, help='Product name is required')
product_parser.add_argument('price', type=float, required=True, help='Product price is required')
product_parser.add_argument('description', type=str)
product_parser.add_argument('category_id', type=int, required=True, help='Category ID is required')
product_parser.add_argument('image', type=reqparse.FileStorage, location='files', required=False)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def format_product(product):
    return {
        'id': product.id,
        'name': product.name,
        'price': product.price,
        'description': product.description,
        'image': product.image,
        'category_id': product.category_id,
    }

@product_ns.route('/')
class ProductList(Resource):
    @product_ns.doc('list_products')
    def get(self):
        """Get all products"""
        try:
            category = request.args.get('category')
            search = request.args.get('search')

            query = Product.query
            if category:
                query = query.filter_by(category_id=category)
            if search:
                query = query.filter(Product.name.ilike(f'%{search}%'))

            products = query.all()
            return [format_product(p) for p in products], 200
        except Exception as e:
            logger.error(f"Error fetching products: {e}")
            return {'message': 'Error fetching products', 'error': str(e)}, 500

    @jwt_required()
    @role_required(Role.SELLER, Role.ADMIN, Role.OWNER)
    @product_ns.expect(product_parser)
    @product_ns.doc('create_product', security='BearerAuth')
    def post(self):
        """Create a new product"""
        current_user = get_jwt_identity()
        args = product_parser.parse_args()
        image = args['image']

        try:
            filename = 'default.jpg'
            if image and allowed_file(image.filename):
                unique_filename = f"{uuid.uuid4().hex}_{secure_filename(image.filename)}"
                upload_path = os.path.join(current_app.config['UPLOAD_FOLDER'], unique_filename)
                os.makedirs(current_app.config['UPLOAD_FOLDER'], exist_ok=True)
                image.save(upload_path)
                filename = unique_filename

            new_product = Product(
                name=args['name'],
                price=args['price'],
                description=args['description'],
                category_id=args['category_id'],
                image=filename
            )
            db.session.add(new_product)
            db.session.commit()
            return {'message': 'Product created', 'product': format_product(new_product)}, 201
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error creating product: {e}")
            return {'message': 'Error creating product', 'error': str(e)}, 500

@product_ns.route('/<int:product_id>')
class ProductResource(Resource):
    @product_ns.doc('get_product')
    def get(self, product_id):
        """Get product by ID"""
        try:
            product = Product.query.get_or_404(product_id)
            return format_product(product), 200
        except Exception as e:
            logger.error(f"Error fetching product {product_id}: {e}")
            return {'message': 'Error fetching product', 'error': str(e)}, 500

    @jwt_required()
    @role_required(Role.SELLER, Role.ADMIN, Role.OWNER)
    @product_ns.expect(product_parser)
    @product_ns.doc('update_product', security='BearerAuth')
    def put(self, product_id):
        """Update a product"""
        args = product_parser.parse_args()
        image = args['image']

        try:
            product = Product.query.get_or_404(product_id)
            product.name = args['name']
            product.price = args['price']
            product.description = args['description']
            product.category_id = args['category_id']

            if image and allowed_file(image.filename):
                if product.image and product.image != 'default.jpg':
                    old_path = os.path.join(current_app.root_path, product.image.lstrip("/"))
                    if os.path.exists(old_path):
                        os.remove(old_path)
                filename = f"{uuid.uuid4().hex}_{secure_filename(image.filename)}"
                upload_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
                os.makedirs(current_app.config['UPLOAD_FOLDER'], exist_ok=True)
                image.save(upload_path)
                product.image = filename

            db.session.commit()
            return {'message': 'Product updated', 'product': format_product(product)}, 200
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error updating product {product_id}: {e}")
            return {'message': 'Error updating product', 'error': str(e)}, 500

    @jwt_required()
    @role_required(Role.SELLER, Role.ADMIN, Role.OWNER)
    @product_ns.doc('delete_product', security='BearerAuth')
    def delete(self, product_id):
        """Delete a product"""
        try:
            product = Product.query.get_or_404(product_id)
            if product.image and product.image != 'default.jpg':
                old_path = os.path.join(current_app.root_path, product.image.lstrip("/"))
                if os.path.exists(old_path):
                    os.remove(old_path)
            db.session.delete(product)
            db.session.commit()
            return {'message': 'Product deleted'}, 200
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error deleting product {product_id}: {e}")
            return {'message': 'Error deleting product', 'error': str(e)}, 500

