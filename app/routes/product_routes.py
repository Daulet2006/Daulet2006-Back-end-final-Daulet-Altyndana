# Импорт необходимых модулей
from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from ..models import Product, Role, Category
from .. import db
from ..utils import role_required
import logging
import os
import uuid
from werkzeug.utils import secure_filename

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Разрешённые расширения файлов
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

# Создание Blueprint для маршрутов продуктов
bp = Blueprint('products', __name__, url_prefix='/products')

# Вспомогательная функция для проверки расширения файла
def allowed_file(filename):
   """Проверяет, имеет ли файл допустимое расширение."""
   return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Вспомогательная функция для форматирования данных продукта
def format_product(product):
   """Форматирует объект Product в словарь для ответа API."""
   return {
       'id': str(product.id) if product.id is not None else None,
       'name': product.name,
       'description': product.description,
       'price': float(product.price) if product.price is not None else None,
       'stock': int(product.stock) if product.stock is not None else None,
       'image_url': product.image_url,
       'seller_id': str(product.seller_id) if product.seller_id is not None else None,
       'category_id': str(product.category_id) if product.category_id is not None else None,
       'created_at': product.created_at.isoformat() if product.created_at else None
   }

# Вспомогательная функция для проверки авторизации
def check_product_authorization(product, current_user_identity):
   """Проверяет, имеет ли пользователь право на действия с продуктом."""
   current_user_id = current_user_identity['id']
   role_str = current_user_identity.get('role', '')
   try:
       current_user_role = Role(role_str)
   except ValueError:
       logger.error(f"Недопустимая роль: {role_str}")
       return False

   if current_user_role in [Role.ADMIN, Role.OWNER] or product.seller_id == current_user_id:
       return True
   logger.warning(
       f"Отказано в доступе: user_id={current_user_id} не соответствует seller_id={product.seller_id} и роль={role_str} не ADMIN/OWNER")
   return False

# Создание продукта
@bp.route('', methods=['POST'])
@jwt_required()
@role_required(Role.SELLER, Role.ADMIN, Role.OWNER)
def create_product():
   """Создаёт новый продукт с возможностью загрузки изображения."""
   current_user_identity = get_jwt_identity()

   # Проверка наличия файла изображения
   if 'image' in request.files:
       image = request.files['image']
       if image.filename == '' or not allowed_file(image.filename):
           return jsonify({'message': 'Недопустимый файл изображения'}), 400
       filename = secure_filename(image.filename)
       unique_name = f"{uuid.uuid4().hex}_{filename}"
       save_path = os.path.join(current_app.config['UPLOAD_FOLDER'], unique_name)
       os.makedirs(current_app.config['UPLOAD_FOLDER'], exist_ok=True)
       image.save(save_path)
       image_url = f"/static/uploads/{unique_name}"
   else:
       image_url = None

   # Получение и валидация данных формы
   name = request.form.get('name')
   price = request.form.get('price')
   stock = request.form.get('stock')
   description = request.form.get('description')
   category_id = request.form.get('categoryId')  # Изменено с category_id на categoryId

   if not all([name, price, stock]):
       return jsonify({'message': 'Обязательные поля: name, price, stock'}), 400

   try:
       price = float(price)
       stock = int(stock)
       if price < 0 or stock < 0:
           return jsonify({'message': 'Цена и количество не могут быть отрицательными'}), 400

       new_product = Product(
           name=name,
           description=description,
           price=price,
           stock=stock,
           image_url=image_url,
           seller_id=current_user_identity['id'],
           category_id=category_id if category_id else None
       )

       # Проверка категории, если указана
       if new_product.category_id:
           category = Category.query.get(new_product.category_id)
           if not category:
               return jsonify({'message': f'Категория с ID {new_product.category_id} не найдена'}), 404

       db.session.add(new_product)
       db.session.commit()
       return jsonify({'message': 'Продукт успешно создан', 'product': format_product(new_product)}), 201
   except ValueError as e:
       db.session.rollback()
       logger.error(f"Неверный формат данных: {e}")
       return jsonify({'message': 'Неверный формат данных', 'error': str(e)}), 400
   except Exception as e:
       db.session.rollback()
       logger.error(f"Ошибка при создании продукта: {e}")
       return jsonify({'message': 'Не удалось создать продукт', 'error': str(e)}), 500

# Получение всех продуктов
@bp.route('/', methods=['GET'])
def get_products():
   """Возвращает список продуктов с пагинацией."""
   try:
       page = request.args.get('page', 1, type=int)
       per_page = request.args.get('per_page', 10, type=int)
       products = Product.query.paginate(page=page, per_page=per_page)
       return jsonify({
           'products': [format_product(p) for p in products.items],
           'total': products.total,
           'pages': products.pages,
           'current_page': products.page
       }), 200
   except Exception as e:
       logger.error(f"Ошибка при получении продуктов: {e}")
       return jsonify({'message': 'Не удалось получить продукты', 'error': str(e)}), 500

# Получение одного продукта
@bp.route('/<int:product_id>', methods=['GET'])
def get_product(product_id):
   """Возвращает данные одного продукта по ID."""
   try:
       product = Product.query.get_or_404(product_id)
       return jsonify(format_product(product)), 200
   except Exception as e:
       logger.error(f"Ошибка при получении продукта {product_id}: {e}")
       return jsonify({'message': 'Не удалось получить продукт', 'error': str(e)}), 500

# Обновление продукта
@bp.route('/<int:product_id>', methods=['PUT', 'PATCH'])
@jwt_required()
@role_required(Role.SELLER, Role.ADMIN, Role.OWNER)
def update_product(product_id):
   """Обновляет данные продукта, включая возможность замены изображения."""
   current_user_identity = get_jwt_identity()

   try:
       product = Product.query.get_or_404(product_id)
       if not check_product_authorization(product, current_user_identity):
           return jsonify({'message': 'Доступ запрещён'}), 403

       # Получение данных формы
       name = request.form.get('name')
       description = request.form.get('description')
       price = request.form.get('price')
       stock = request.form.get('stock')
       category_id = request.form.get('categoryId')  # Изменено с category_id на categoryId
       image = request.files.get('image')

       # Обновление полей, если предоставлены
       if name:
           product.name = name
       if description:
           product.description = description
       if price:
           product.price = float(price)
       if stock:
           product.stock = int(stock)
       if product.price < 0 or product.stock < 0:
           return jsonify({'message': 'Цена и количество не могут быть отрицательными'}), 400

       if category_id:
           if category_id:
               category = Category.query.get(category_id)
               if not category:
                   return jsonify({'message': f'Категория с ID {category_id} не найдена'}), 404
               product.category_id = category_id
           else:
               product.category_id = None

       # Обработка нового изображения
       if image:
           if image.filename == '' or not allowed_file(image.filename):
               return jsonify({'message': 'Недопустимый файл изображения'}), 400
           if product.image_url:
               old_path = os.path.join(current_app.root_path, product.image_url.strip("/"))
               if os.path.exists(old_path):
                   os.remove(old_path)
           filename = f"{uuid.uuid4().hex}_{secure_filename(image.filename)}"
           upload_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
           os.makedirs(current_app.config['UPLOAD_FOLDER'], exist_ok=True)
           image.save(upload_path)
           product.image_url = f"/static/uploads/{filename}"

       db.session.commit()
       return jsonify({'message': 'Продукт успешно обновлён', 'product': format_product(product)}), 200
   except ValueError as e:
       db.session.rollback()
       logger.error(f"Неверный формат данных для продукта {product_id}: {e}")
       return jsonify({'message': 'Неверный формат данных', 'error': str(e)}), 400
   except Exception as e:
       db.session.rollback()
       logger.error(f"Ошибка при обновлении продукта {product_id}: {e}")
       return jsonify({'message': 'Не удалось обновить продукт', 'error': str(e)}), 500

# Удаление продукта
@bp.route('/<int:product_id>', methods=['DELETE'])
@jwt_required()
@role_required(Role.SELLER, Role.ADMIN, Role.OWNER)
def delete_product(product_id):
   """Удаляет продукт по ID."""
   current_user_identity = get_jwt_identity()
   try:
       product = Product.query.get_or_404(product_id)
       if not check_product_authorization(product, current_user_identity):
           return jsonify({'message': 'Доступ запрещён'}), 403
       db.session.delete(product)
       db.session.commit()
       return jsonify({'message': 'Продукт успешно удалён'}), 200
   except Exception as e:
       db.session.rollback()
       logger.error(f"Ошибка при удалении продукта {product_id}: {e}")
       return jsonify({'message': 'Не удалось удалить продукт', 'error': str(e)}), 500

# Фильтрация продуктов по имени
@bp.route('/filter', methods=['GET'])
def filter_products():
   """Фильтрует продукты по частичному совпадению имени."""
   name_query = request.args.get('name', '')
   try:
       if not name_query:
           return jsonify({'message': 'Параметр name обязателен для фильтрации'}), 400
       products = Product.query.filter(Product.name.ilike(f'%{name_query}%')).all()
       return jsonify([format_product(p) for p in products]), 200
   except Exception as e:
       logger.error(f"Ошибка при фильтрации продуктов: {e}")
       return jsonify({'message': 'Не удалось отфильтровать продукты', 'error': str(e)}), 500

# Получение продуктов по категории
@bp.route('/by_category/<int:category_id>', methods=['GET'])
def get_products_by_category(category_id):
   """Возвращает продукты, относящиеся к указанной категории."""
   try:
       products = Product.query.filter_by(category_id=category_id).all()
       return jsonify([format_product(p) for p in products]), 200
   except Exception as e:
       logger.error(f"Ошибка при фильтрации по категории: {e}")
       return jsonify({'message': 'Не удалось получить продукты по категории', 'error': str(e)}), 500