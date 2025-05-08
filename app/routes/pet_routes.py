from flask_restx import Namespace, Resource, fields, reqparse
from flask import request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.models import Pet, Role, db
from app.utils import role_required
import logging
import os
import uuid
from werkzeug.utils import secure_filename

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

pet_ns = Namespace('pets', description='Operations related to pets', path='/pets')

# Swagger models
pet_model = pet_ns.model('Pet', {
    'name': fields.String(required=True, description='Pet name'),
    'species': fields.String(required=True, description='Pet species'),
    'breed': fields.String(description='Pet breed'),
    'age': fields.Integer(required=True, description='Pet age'),
    'price': fields.Float(required=True, description='Pet price'),
    'description': fields.String(description='Pet description'),
    'category_id': fields.Integer(description='Category ID'),
})

# Request parser for file uploads
pet_parser = reqparse.RequestParser()
pet_parser.add_argument('name', type=str, required=True, help='Pet name')
pet_parser.add_argument('species', type=str, required=True, help='Pet species')
pet_parser.add_argument('breed', type=str, help='Pet breed')
pet_parser.add_argument('age', type=int, required=True, help='Pet age')
pet_parser.add_argument('price', type=float, required=True, help='Pet price')
pet_parser.add_argument('description', type=str, help='Pet description')
pet_parser.add_argument('category_id', type=int, help='Category ID')
pet_parser.add_argument('image', type=reqparse.FileStorage, location='files', required=True, help='Pet image')

# Helper functions
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def format_pet(pet):
    return {
        'id': str(pet.id) if pet.id is not None else None,
        'name': pet.name,
        'species': pet.species,
        'breed': pet.breed,
        'age': int(pet.age) if pet.age is not None else None,
        'price': float(pet.price) if pet.price is not None else None,
        'description': pet.description,
        'image_url': pet.image_url,
        'seller_id': str(pet.seller_id) if pet.seller_id is not None else None,
        'category_id': pet.category_id
    }

def check_pet_authorization(pet, current_user_identity):
    current_user_id = current_user_identity['id']
    role_str = current_user_identity.get('role', '')
    try:
        current_user_role = Role(role_str)
    except ValueError:
        logger.error(f"Недопустимая роль: {role_str}")
        return False, "Недопустимая роль"
    if current_user_role in [Role.ADMIN, Role.OWNER] or pet.seller_id == current_user_id:
        return True, None
    return False, "Нет прав для изменения питомца"

@pet_ns.route('')
class PetList(Resource):
    @pet_ns.doc('list_pets')
    def get(self):
        """Get all pets"""
        try:
            pets = Pet.query.all()
            return [format_pet(p) for p in pets], 200
        except Exception as e:
            logger.error(f"Ошибка получения питомцев: {e}")
            return {'message': 'Ошибка получения питомцев', 'error': str(e)}, 500

    @jwt_required()
    @role_required(Role.SELLER, Role.ADMIN, Role.OWNER)
    @pet_ns.expect(pet_parser)
    @pet_ns.doc('create_pet', security='BearerAuth')
    def post(self):
        """Create a new pet"""
        current_user_identity = get_jwt_identity()
        args = pet_parser.parse_args()
        image = args['image']

        if image.filename == '' or not allowed_file(image.filename):
            return {'message': 'Недопустимый файл'}, 400

        filename = secure_filename(image.filename)
        unique_name = f"{uuid.uuid4().hex}_{filename}"
        save_path = os.path.join(current_app.config['UPLOAD_FOLDER'], unique_name)
        os.makedirs(current_app.config['UPLOAD_FOLDER'], exist_ok=True)
        image.save(save_path)
        image_url = unique_name

        try:
            new_pet = Pet(
                name=args['name'],
                species=args['species'],
                breed=args['breed'],
                age=args['age'],
                price=args['price'],
                description=args['description'] or '',
                image_url=image_url,
                seller_id=current_user_identity['id'],
                category_id=args['category_id']
            )
            db.session.add(new_pet)
            db.session.commit()
            return {'message': 'Питомец создан', 'pet': format_pet(new_pet)}, 201
        except Exception as e:
            db.session.rollback()
            logger.error(f"Ошибка создания питомца: {e}")
            return {'message': 'Ошибка создания питомца', 'error': str(e)}, 500

@pet_ns.route('/<int:pet_id>')
class PetResource(Resource):
    @pet_ns.doc('get_pet')
    def get(self, pet_id):
        """Get a pet by ID"""
        try:
            pet = Pet.query.get_or_404(pet_id)
            return format_pet(pet), 200
        except Exception as e:
            logger.error(f"Ошибка получения питомца {pet_id}: {e}")
            return {'message': 'Ошибка получения питомца', 'error': str(e)}, 500

    @jwt_required()
    @role_required(Role.SELLER, Role.ADMIN, Role.OWNER)
    @pet_ns.expect(pet_parser)
    @pet_ns.doc('update_pet', security='BearerAuth')
    def put(self, pet_id):
        """Update a pet"""
        current_user_identity = get_jwt_identity()
        args = pet_parser.parse_args()
        image = args['image']

        try:
            pet = Pet.query.get_or_404(pet_id)
            authorized, error_message = check_pet_authorization(pet, current_user_identity)
            if not authorized:
                return {'message': error_message}, 403

            pet.name = args['name']
            pet.species = args['species']
            pet.breed = args['breed']
            pet.age = args['age']
            pet.price = args['price']
            pet.description = args['description'] or ''
            pet.category_id = args['category_id']

            if image and (image.filename == '' or not allowed_file(image.filename)):
                return {'message': 'Недопустимый файл'}, 400
            if image:
                if pet.image_url:
                    old_path = os.path.join(current_app.root_path, pet.image_url.strip("/"))
                    if os.path.exists(old_path):
                        os.remove(old_path)
                filename = f"{uuid.uuid4().hex}_{secure_filename(image.filename)}"
                upload_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
                os.makedirs(current_app.config['UPLOAD_FOLDER'], exist_ok=True)
                image.save(upload_path)
                pet.image_url = filename

            db.session.commit()
            return {'message': 'Питомец обновлён', 'pet': format_pet(pet)}, 200
        except Exception as e:
            db.session.rollback()
            logger.error(f"Ошибка обновления питомца {pet_id}: {e}")
            return {'message': 'Ошибка обновления питомца', 'error': str(e)}, 500

    @jwt_required()
    @role_required(Role.SELLER, Role.ADMIN, Role.OWNER)
    @pet_ns.doc('delete_pet', security='BearerAuth')
    def delete(self, pet_id):
        """Delete a pet"""
        current_user_identity = get_jwt_identity()
        try:
            pet = Pet.query.get_or_404(pet_id)
            authorized, error_message = check_pet_authorization(pet, current_user_identity)
            if not authorized:
                return {'message': error_message}, 403
            if pet.image_url:
                old_path = os.path.join(current_app.root_path, pet.image_url.strip("/"))
                if os.path.exists(old_path):
                    os.remove(old_path)
            db.session.delete(pet)
            db.session.commit()
            return {'message': 'Питомец удалён'}, 200
        except Exception as e:
            db.session.rollback()
            logger.error(f"Ошибка удаления питомца {pet_id}: {e}")
            return {'message': 'Ошибка удаления питомца', 'error': str(e)}, 500