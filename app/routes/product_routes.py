from flask_restx import Namespace, Resource, fields, reqparse
from flask import request, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.models.relationship_model import  db
from app.utils.util import role_required
from werkzeug.utils import secure_filename
import os
import uuid
import logging
from app.models.user_model import User, Role
from app.models.product_model import Product
product_ns = Namespace('products', description='Operations related to products', path='/products')

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

# Swagger model
product_model = product_ns.model('Product', {
    'id': fields.Integer(readonly=True),
    'name': fields.String(required=True),
    'price': fields.Float(required=True),
    'description': fields.String(),
    'stock': fields.Integer(required=True),
    'image_url': fields.String(),
    'category_id': fields.Integer(),
    'seller_id': fields.Integer(),
    'owner_id': fields.Integer(),
    'owner': fields.Nested(product_ns.model('Owner', {
        'id': fields.Integer(),
        'username': fields.String()
    }), allow_null=True)
})

# File upload parser
product_parser = reqparse.RequestParser()
product_parser.add_argument('name', type=str, required=False, help='Название продукта')
product_parser.add_argument('description', type=str, help='Описание продукта')
product_parser.add_argument('price', type=float, required=False, help='Цена продукта')
product_parser.add_argument('stock', type=int, help='Запас продукта')
product_parser.add_argument('category_id', type=int, help='ID категории')
product_parser.add_argument('image', type=reqparse.FileStorage, location='files', help='Изображение продукта')
product_parser.add_argument('owner_id', type=int, help='ID владельца', location='form')

# JSON parser for updates
product_json_parser = reqparse.RequestParser()
product_json_parser.add_argument('name', type=str, help='Название продукта')
product_json_parser.add_argument('description', type=str, help='Описание продукта')
product_json_parser.add_argument('price', type=float, help='Цена продукта')
product_json_parser.add_argument('stock', type=int, help='Запас продукта')
product_json_parser.add_argument('category_id', type=int, help='ID категории')
product_json_parser.add_argument('owner_id', type=int, help='ID владельца')

# Owner parser
owner_parser = reqparse.RequestParser()
owner_parser.add_argument('owner_id', type=int, help='ID пользователя для назначения владельцем')

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def format_product(product):
    owner = User.query.get(product.owner_id) if product.owner_id else None
    return {
        'id': product.id,
        'name': product.name,
        'price': product.price,
        'description': product.description,
        'stock': product.stock,
        'image_url': product.image_url,
        'category_id': product.category_id,
        'seller_id': product.seller_id,
        'owner_id': product.owner_id,
        'owner': {'id': owner.id, 'username': owner.username} if owner else None
    }

def check_product_authorization(product, current_user_identity):
    current_user_id = current_user_identity['id']
    role_str = current_user_identity.get('role', '')
    try:
        current_user_role = Role(role_str)
    except ValueError:
        logger.error(f"Недопустимая роль: {role_str}")
        return False, "Недопустимая роль"
    if current_user_role in [Role.ADMIN, Role.OWNER] or \
       product.seller_id == current_user_id or \
       product.owner_id == current_user_id:
        return True, None
    return False, "Нет прав для изменения продукта"

@product_ns.route('')
class ProductList(Resource):
    @product_ns.doc('list_products')
    @product_ns.marshal_list_with(product_model)
    def get(self):
        """Получить все продукты"""
        try:
            products = Product.query.all()
            logger.debug(f"Retrieved {len(products)} products")
            return [format_product(p) for p in products], 200
        except Exception as e:
            logger.error(f"Ошибка получения продуктов: {str(e)}")
            return {'message': 'Ошибка получения продуктов', 'error': str(e)}, 500

    @jwt_required()
    @role_required(Role.SELLER, Role.ADMIN, Role.OWNER)
    @product_ns.expect(product_parser)
    @product_ns.doc('create_product', security='BearerAuth')
    @product_ns.marshal_with(product_model, code=201)
    def post(self):
        """Создать новый продукт"""
        current_user_identity = get_jwt_identity()
        logger.info(f"Request form data: {request.form}")
        logger.info(f"Request files: {request.files}")
        try:
            args = product_parser.parse_args()
            logger.info(f"Parsed args: {args}")
            image = args['image']

            if not args['name'] or not args['price'] or not args['stock']:
                return {'message': 'Поля name, price и stock обязательны'}, 400

            if image and (image.filename == '' or not allowed_file(image.filename)):
                return {'message': 'Недопустимый файл изображения. Допустимые расширения: png, jpg, jpeg, gif'}, 400

            image_url = None
            if image:
                filename = secure_filename(image.filename)
                unique_name = f"{uuid.uuid4().hex}_{filename}"
                # Используем абсолютный путь для UPLOAD_FOLDER
                upload_folder = os.path.abspath(current_app.config['UPLOAD_FOLDER'])
                save_path = os.path.join(upload_folder, unique_name)
                try:
                    os.makedirs(upload_folder, exist_ok=True)
                    image.save(save_path)
                    image_url = unique_name
                    logger.info(f"Image saved successfully: {save_path}")
                except Exception as e:
                    logger.error(f"Failed to save image: {str(e)}")
                    return {'message': 'Не удалось сохранить изображение', 'error': str(e)}, 500

            new_product = Product(
                name=args['name'],
                price=args['price'],
                description=args['description'] or '',
                stock=args['stock'],
                image_url=image_url,
                category_id=args['category_id'],
                seller_id=current_user_identity['id']
            )
            db.session.add(new_product)
            db.session.commit()
            logger.info(f"Product created successfully: ID {new_product.id}")
            return format_product(new_product), 201
        except Exception as e:
            db.session.rollback()
            logger.error(f"Ошибка создания продукта: {str(e)}")
            return {'message': 'Ошибка создания продукта', 'error': str(e)}, 500

@product_ns.route('/<int:product_id>')
class ProductResource(Resource):
    @product_ns.doc('get_product')
    @product_ns.marshal_with(product_model)
    def get(self, product_id):
        """Получить продукт по ID"""
        try:
            product = Product.query.get_or_404(product_id)
            return format_product(product), 200
        except Exception as e:
            logger.error(f"Ошибка получения продукта {product_id}: {str(e)}")
            return {'message': 'Ошибка получения продукта', 'error': str(e)}, 500

    @jwt_required()
    @role_required(Role.SELLER, Role.ADMIN, Role.OWNER)
    @product_ns.expect(product_json_parser, product_parser)
    @product_ns.doc('update_product', security='BearerAuth')
    @product_ns.marshal_with(product_model)
    def put(self, product_id):
        """Обновить продукт"""
        current_user_identity = get_jwt_identity()
        content_type = request.content_type
        logger.info(f"Request form antigos data: {request.form}")
        logger.info(f"Request files: {request.files}")

        try:
            product = Product.query.get_or_404(product_id)
            authorized, error_message = check_product_authorization(product, current_user_identity)
            if not authorized:
                return {'message': error_message}, 403

            if content_type.startswith('multipart/form-data'):
                args = product_parser.parse_args()
                logger.info(f"Parsed args: {args}")
                image = args['image']
                if image and (image.filename == '' or not allowed_file(image.filename)):
                    return {'message': 'Недопустимый файл изображения. Допустимые расширения: png, jpg, jpeg, gif'}, 400
                if image:
                    if product.image_url:
                        old_path = os.path.join(os.path.abspath(current_app.config['UPLOAD_FOLDER']), product.image_url.strip("/"))
                        if os.path.exists(old_path):
                            try:
                                os.remove(old_path)
                                logger.info(f"Old image deleted: {old_path}")
                            except Exception:
                                logger.warning(f"Failed to delete old image: {old_path}")
                                pass
                    filename = f"{uuid.uuid4().hex}_{secure_filename(image.filename)}"
                    upload_folder = os.path.abspath(current_app.config['UPLOAD_FOLDER'])
                    upload_path = os.path.join(upload_folder, filename)
                    try:
                        os.makedirs(upload_folder, exist_ok=True)
                        image.save(upload_path)
                        product.image_url = filename
                        logger.info(f"New image saved: {upload_path}")
                    except Exception as e:
                        logger.error(f"Failed to save image: {str(e)}")
                        return {'message': 'Не удалось сохранить изображение', 'error': str(e)}, 500
            else:
                args = product_json_parser.parse_args()
                logger.info(f"Parsed args (JSON): {args}")

            # Обновляем только предоставленные поля
            if args['name'] is not None:
                product.name = args['name']
            if args['price'] is not None:
                product.price = args['price']
            if args['stock'] is not None:
                product.stock = args['stock']
            if args['description'] is not None:
                product.description = args['description'] or ''
            if args['category_id'] is not None:
                product.category_id = args['category_id']
            if args['owner_id'] is not None:
                if args['owner_id']:
                    owner = User.query.get(args['owner_id'])
                    if not owner:
                        return {'message': f'Пользователь с ID {args["owner_id"]} не найден'}, 404
                    if owner.isBanned:
                        return {'message': 'Нельзя назначить заблокированного пользователя владельцем'}, 400
                    product.owner_id = args['owner_id']
                else:
                    product.owner_id = None

            db.session.commit()
            logger.info(f"Product updated successfully: ID {product_id}")
            return format_product(product), 200
        except Exception as e:
            db.session.rollback()
            logger.error(f"Ошибка обновления продукта {product_id}: {str(e)}")
            return {'message': 'Ошибка обновления продукта', 'error': str(e)}, 500

    @jwt_required()
    @role_required(Role.SELLER, Role.ADMIN, Role.OWNER)
    @product_ns.doc('delete_product', security='BearerAuth')
    def delete(self, product_id):
        """Удалить продукт"""
        current_user_identity = get_jwt_identity()
        try:
            product = Product.query.get_or_404(product_id)
            authorized, error_message = check_product_authorization(product, current_user_identity)
            if not authorized:
                return {'message': error_message}, 403

            if product.image_url:
                old_path = os.path.join(os.path.abspath(current_app.config['UPLOAD_FOLDER']), product.image_url.strip("/"))
                if os.path.exists(old_path):
                    try:
                        os.remove(old_path)
                        logger.info(f"Image deleted: {old_path}")
                    except Exception:
                        logger.warning(f"Failed to delete image: {old_path}")
                        pass

            db.session.delete(product)
            db.session.commit()
            logger.info(f"Product deleted successfully: ID {product_id}")
            return {'message': 'Продукт успешно удалён'}, 200
        except Exception as e:
            db.session.rollback()
            logger.error(f"Ошибка удаления продукта {product_id}: {str(e)}")
            return {'message': 'Ошибка удаления продукта', 'error': str(e)}, 500

@product_ns.route('/owned')
class OwnedProducts(Resource):
    @jwt_required()
    @product_ns.doc('list_owned_products', security='BearerAuth')
    @product_ns.marshal_list_with(product_model)
    def get(self):
        """Получить продукты, принадлежащие текущему пользователю"""
        current_user_identity = get_jwt_identity()
        current_user_id = current_user_identity['id']
        try:
            products = Product.query.filter_by(owner_id=current_user_id).all()
            logger.debug(f"Retrieved {len(products)} owned products for user {current_user_id}")
            return [format_product(p) for p in products], 200
        except Exception as e:
            logger.error(f"Ошибка получения продуктов владельца {current_user_id}: {str(e)}")
            return {'message': 'Ошибка получения продуктов', 'error': str(e)}, 500

@product_ns.route('/<int:product_id>/owner')
class ProductOwner(Resource):
    @jwt_required()
    @role_required(Role.SELLER, Role.ADMIN, Role.OWNER)
    @product_ns.expect(owner_parser)
    @product_ns.doc('set_product_owner', security='BearerAuth')
    @product_ns.marshal_with(product_model)
    def put(self, product_id):
        """Назначить или обновить владельца продукта"""
        current_user_identity = get_jwt_identity()
        args = owner_parser.parse_args()
        owner_id = args['owner_id']

        try:
            product = Product.query.get_or_404(product_id)
            authorized, error_message = check_product_authorization(product, current_user_identity)
            if not authorized:
                return {'message': error_message}, 403

            if owner_id:
                owner = User.query.get(owner_id)
                if not owner:
                    return {'message': f'Пользователь с ID {owner_id} не найден'}, 404
                if owner.isBanned:
                    return {'message': 'Нельзя назначить заблокированного пользователя владельцем'}, 400
                product.owner_id = owner_id
            else:
                product.owner_id = None

            db.session.commit()
            logger.info(f"Owner updated for product {product_id}: owner_id={owner_id}")
            return format_product(product), 200
        except Exception as e:
            db.session.rollback()
            logger.error(f"Ошибка назначения владельца для продукта {product_id}: {str(e)}")
            return {'message': 'Ошибка назначения владельца', 'error': str(e)}, 500

    @jwt_required()
    @role_required(Role.SELLER, Role.ADMIN, Role.OWNER)
    @product_ns.doc('remove_product_owner', security='BearerAuth')
    @product_ns.marshal_with(product_model)
    def delete(self, product_id):
        """Удалить владельца продукта"""
        current_user_identity = get_jwt_identity()
        try:
            product = Product.query.get_or_404(product_id)
            authorized, error_message = check_product_authorization(product, current_user_identity)
            if not authorized:
                return {'message': error_message}, 403

            product.owner_id = None
            db.session.commit()
            logger.info(f"Owner removed for product {product_id}")
            return format_product(product), 200
        except Exception as e:
            db.session.rollback()
            logger.error(f"Ошибка удаления владельца для продукта {product_id}: {str(e)}")
            return {'message': 'Ошибка удаления владельца', 'error': str(e)}, 500