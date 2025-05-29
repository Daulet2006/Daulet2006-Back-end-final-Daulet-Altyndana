from flask_restx import Namespace, Resource, fields, reqparse
from flask import request, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from app import db
from app.models.pet_model import Pet, PetStatus
from app.utils.util import role_required
import logging
import os
import uuid
from werkzeug.utils import secure_filename
from app.models.user_model import User, Role

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

pet_ns = Namespace('pets', description='Pet operations', path='/pets')

pet_model = pet_ns.model('Pet', {
    'id': fields.Integer(readonly=True),
    'name': fields.String(required=True),
    'species': fields.String(required=True),
    'breed': fields.String(),
    'age': fields.Integer(required=True),
    'description': fields.String(),
    'price': fields.Float(required=True),
    'image_url': fields.String(),
    'seller_id': fields.Integer(),
    'category_id': fields.Integer(),
    'status': fields.String(),
    'owner_id': fields.Integer(),
    'owner': fields.Nested(pet_ns.model('Owner', {
        'id': fields.Integer(),
        'username': fields.String()
    }), allow_null=True)
})

status_parser = reqparse.RequestParser()
status_parser.add_argument('status', type=str, required=True, help='Pet status (AVAILABLE, RESERVED, SOLD)')
status_parser.add_argument('owner_id', type=int, help='Owner ID for SOLD status')

pet_parser = reqparse.RequestParser()
pet_parser.add_argument('name', type=str, required=True, help='Pet name cannot be blank', location='form')
pet_parser.add_argument('species', type=str, required=True, help='Species cannot be blank', location='form')
pet_parser.add_argument('breed', type=str, help='Pet breed', location='form')
pet_parser.add_argument('age', type=int, required=True, help='Age cannot be blank', location='form')
pet_parser.add_argument('description', type=str, help='Pet description', location='form')
pet_parser.add_argument('price', type=float, required=True, help='Price cannot be blank', location='form')
pet_parser.add_argument('image', type=reqparse.FileStorage, location='files', help='Pet image')
pet_parser.add_argument('category_id', type=int, help='Category ID', location='form')

owner_parser = reqparse.RequestParser()
owner_parser.add_argument('owner_id', type=int, help='User ID to set as owner')

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def format_pet(pet, for_vet=False):
    owner = User.query.get(pet.owner_id) if pet.owner_id else None
    result = {
        'id': pet.id,
        'name': pet.name,
        'species': pet.species,
        'breed': pet.breed,
        'age': pet.age,
        'description': pet.description,
        'image_url': pet.image_url,
        'seller_id': pet.seller_id,
        'category_id': pet.category_id,
        'status': pet.status,
        'owner_id': pet.owner_id,
        'owner': {'id': owner.id, 'username': owner.username} if owner else None
    }
    if not for_vet:
        result['price'] = float(pet.price)
    return result

def check_pet_authorization(pet, current_user_identity):
    current_user_id = current_user_identity['id']
    role_str = current_user_identity.get('role', '')
    try:
        current_user_role = Role(role_str)
    except ValueError:
        logger.error(f"Invalid role: {role_str}")
        return False, "Недопустимая роль"
    if current_user_role in [Role.ADMIN, Role.OWNER] or pet.seller_id == current_user_id:
        return True, None
    return False, "Нет прав для изменения питомца"

@pet_ns.route('')
class PetList(Resource):
    @pet_ns.doc('list_pets')
    @pet_ns.marshal_list_with(pet_model)
    def get(self):
        logger.debug("Entering get method for PetList")
        try:
            pets = Pet.query.all()
            logger.debug(f"Retrieved {len(pets)} pets")
            formatted_pets = []
            for pet in pets:
                try:
                    formatted_pet = format_pet(pet)
                    formatted_pets.append(formatted_pet)
                except Exception as e:
                    logger.warning(f"Failed to format pet ID {pet.id}: {str(e)}")
                    continue
            logger.debug("Formatted pets successfully")
            return formatted_pets, 200
        except Exception as e:
            logger.exception(f"Error fetching pets: {str(e)}")
            return {'message': 'Ошибка получения питомцев', 'error': str(e)}, 500

    @jwt_required()
    @role_required(Role.SELLER, Role.ADMIN, Role.OWNER)
    @pet_ns.expect(pet_parser)
    @pet_ns.doc('create_pet', security='BearerAuth')
    @pet_ns.marshal_with(pet_model, code=201)
    def post(self):
        current_user_identity = get_jwt_identity()
        logger.info(f"Request form data: {request.form}")
        logger.info(f"Request files: {request.files}")
        try:
            args = pet_parser.parse_args()
            logger.info(f"Parsed args: {args}")
            image = args['image']

            if image and (image.filename == '' or not allowed_file(image.filename)):
                return {'message': 'Недопустимый файл изображения. Допустимые расширения: png, jpg, jpeg, gif'}, 400

            image_url = None
            if image:
                filename = secure_filename(image.filename)
                unique_name = f"{uuid.uuid4().hex}_{filename}"
                save_path = os.path.join(current_app.config['UPLOAD_FOLDER'], unique_name)
                try:
                    os.makedirs(current_app.config['UPLOAD_FOLDER'], exist_ok=True)
                    image.save(save_path)
                    image_url = unique_name
                except Exception as e:
                    logger.error(f"Failed to save image: {str(e)}")
                    return {'message': 'Не удалось сохранить изображение', 'error': str(e)}, 500

            new_pet = Pet(
                name=args['name'],
                species=args['species'],
                breed=args['breed'],
                age=args['age'],
                price=args['price'],
                description=args['description'] or '',
                image_url=image_url,
                seller_id=current_user_identity['id'],
                category_id=args['category_id'],
                status=PetStatus.AVAILABLE.value
            )
            db.session.add(new_pet)
            db.session.commit()
            return format_pet(new_pet), 201
        except Exception as e:
            db.session.rollback()
            logger.error(f"Ошибка создания питомца: {str(e)}")
            return {'message': 'Ошибка создания питомца', 'error': str(e)}, 500

@pet_ns.route('/<int:pet_id>')
class PetResource(Resource):
    @pet_ns.doc('get_pet')
    @pet_ns.marshal_with(pet_model)
    def get(self, pet_id):
        """Получить питомца по ID"""
        try:
            pet = Pet.query.get_or_404(pet_id)
            return format_pet(pet), 200
        except Exception as e:
            return {'message': 'Ошибка получения питомца', 'error': str(e)}, 500

    @jwt_required()
    @role_required(Role.SELLER, Role.ADMIN, Role.OWNER)
    @pet_ns.expect(pet_parser)
    @pet_ns.doc('update_pet', security='BearerAuth')
    @pet_ns.marshal_with(pet_model)
    def put(self, pet_id):
        """Обновить питомца"""
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
                return {'message': 'Недопустимый файл изображения. Допустимые расширения: png, jpg, jpeg, gif'}, 400
            if image:
                if pet.image_url:
                    old_path = os.path.join(current_app.config['UPLOAD_FOLDER'], pet.image_url.strip("/"))
                    if os.path.exists(old_path):
                        try:
                            os.remove(old_path)
                        except Exception:
                            pass
                filename = f"{uuid.uuid4().hex}_{secure_filename(image.filename)}"
                upload_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
                os.makedirs(current_app.config['UPLOAD_FOLDER'], exist_ok=True)
                try:
                    image.save(upload_path)
                    pet.image_url = filename
                except Exception as e:
                    return {'message': 'Не удалось сохранить изображение', 'error': str(e)}, 500

            db.session.commit()
            return format_pet(pet), 200
        except Exception as e:
            db.session.rollback()
            return {'message': 'Ошибка обновления питомца', 'error': str(e)}, 500

    @jwt_required()
    @role_required(Role.SELLER, Role.ADMIN, Role.OWNER)
    @pet_ns.doc('delete_pet', security='BearerAuth')
    def delete(self, pet_id):
        """Удалить питомца"""
        current_user_identity = get_jwt_identity()
        try:
            pet = Pet.query.get_or_404(pet_id)
            authorized, error_message = check_pet_authorization(pet, current_user_identity)
            if not authorized:
                return {'message': error_message}, 403
            if pet.image_url:
                old_path = os.path.join(current_app.config['UPLOAD_FOLDER'], pet.image_url.strip("/"))
                if os.path.exists(old_path):
                    try:
                        os.remove(old_path)
                    except Exception:
                        pass
            db.session.delete(pet)
            db.session.commit()
            return {'message': 'Питомец успешно удалён'}, 200
        except Exception as e:
            db.session.rollback()
            return {'message': 'Ошибка удаления питомца', 'error': str(e)}, 500

@pet_ns.route('/owned')
class OwnedPets(Resource):
    @jwt_required()
    @pet_ns.doc('list_owned_pets', security='BearerAuth')
    @pet_ns.marshal_list_with(pet_model)
    def get(self):
        """Получить питомцев, принадлежащих текущему пользователю"""
        current_user_identity = get_jwt_identity()
        current_user_id = current_user_identity['id']
        try:
            pets = Pet.query.filter_by(owner_id=current_user_id).all()
            return [format_pet(p) for p in pets], 200
        except Exception as e:
            logger.error(f"Ошибка получения питомцев владельца {current_user_id}: {e}")
            return {'message': 'Ошибка получения питомцев', 'error': str(e)}, 500

@pet_ns.route('/<int:pet_id>/owner')
class PetOwner(Resource):
    @jwt_required()
    @role_required(Role.SELLER, Role.ADMIN, Role.OWNER)
    @pet_ns.expect(owner_parser)
    @pet_ns.doc('set_pet_owner', security='BearerAuth')
    @pet_ns.marshal_with(pet_model)
    def put(self, pet_id):
        """Назначить или обновить владельца питомца"""
        current_user_identity = get_jwt_identity()
        args = owner_parser.parse_args()
        owner_id = args['owner_id']

        try:
            pet = Pet.query.get_or_404(pet_id)
            authorized, error_message = check_pet_authorization(pet, current_user_identity)
            if not authorized:
                return {'message': error_message}, 403

            if owner_id:
                owner = User.query.get(owner_id)
                if not owner:
                    return {'message': f'Пользователь с ID {owner_id} не найден'}, 404
                if owner.isBanned:
                    return {'message': 'Нельзя назначить заблокированного пользователя владельцем'}, 400
                pet.owner_id = owner_id
                pet.status = PetStatus.SOLD.value
            else:
                pet.owner_id = None
                pet.status = PetStatus.AVAILABLE.value

            db.session.commit()
            return format_pet(pet), 200
        except Exception as e:
            db.session.rollback()
            logger.error(f"Ошибка назначения владельца для питомца {pet_id}: {e}")
            return {'message': 'Ошибка назначения владельца', 'error': str(e)}, 500

    @jwt_required()
    @role_required(Role.SELLER, Role.ADMIN, Role.OWNER)
    @pet_ns.doc('remove_pet_owner', security='BearerAuth')
    @pet_ns.marshal_with(pet_model)
    def delete(self, pet_id):
        """Удалить владельца питомца"""
        current_user_identity = get_jwt_identity()
        try:
            pet = Pet.query.get_or_404(pet_id)
            authorized, error_message = check_pet_authorization(pet, current_user_identity)
            if not authorized:
                return {'message': error_message}, 403

            pet.owner_id = None
            pet.status = PetStatus.AVAILABLE.value
            db.session.commit()
            return format_pet(pet), 200
        except Exception as e:
            db.session.rollback()
            logger.error(f"Ошибка удаления владельца для питомца {pet_id}: {e}")
            return {'message': 'Ошибка удаления владельца', 'error': str(e)}, 500

@pet_ns.route('/<int:pet_id>/status')
class PetStatusResource(Resource):
    @jwt_required()
    @role_required(Role.ADMIN, Role.OWNER)
    @pet_ns.expect(status_parser)
    @pet_ns.doc('update_pet_status', security='BearerAuth')
    @pet_ns.marshal_with(pet_model)
    def put(self, pet_id):
        """Обновить статус питомца (только для ADMIN и OWNER)"""
        current_user_identity = get_jwt_identity()
        args = status_parser.parse_args()
        new_status = args['status']
        owner_id = args['owner_id']

        try:
            pet = Pet.query.get_or_404(pet_id)
            authorized, error_message = check_pet_authorization(pet, current_user_identity)
            if not authorized:
                return {'message': error_message}, 403

            valid_statuses = [status.value for status in PetStatus]
            if new_status not in valid_statuses:
                return {'message': f'Недопустимый статус: {new_status}. Допустимые значения: {", ".join(valid_statuses)}'}, 400

            pet.status = new_status
            if new_status == PetStatus.SOLD.value:
                if not owner_id:
                    return {'message': 'Для статуса SOLD требуется указать owner_id'}, 400
                owner = User.query.get(owner_id)
                if not owner:
                    return {'message': f'Пользователь с ID {owner_id} не найден'}, 404
                if owner.isBanned:
                    return {'message': 'Нельзя назначить заблокированного пользователя владельцем'}, 400
                pet.owner_id = owner_id
            elif new_status == PetStatus.AVAILABLE.value:
                pet.owner_id = None

            db.session.commit()
            logger.info(f"Обновлен статус питомца {pet_id} на {new_status} пользователем {current_user_identity['id']}")
            return format_pet(pet), 200
        except Exception as e:
            db.session.rollback()
            logger.error(f"Ошибка обновления статуса питомца {pet_id}: {str(e)}")
            return {'message': 'Ошибка обновления статуса питомца', 'error': str(e)}, 500