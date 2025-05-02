# app/routes/pet_routes.py
from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from ..models import Pet, Role
from .. import db
from ..utils import role_required
import logging # Import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

bp = Blueprint('pets', __name__, url_prefix='/pets')


# Helper Functions
def format_pet(pet):
    """
    Форматирует объект питомца для ответа в формате JSON.
    """
    return {
        'id': pet.id,
        'name': pet.name,
        'species': pet.species,
        'breed': pet.breed,
        'age': pet.age,
        'price': pet.price,
        'description': pet.description,
        'image_url': pet.image_url,
        'seller_id': pet.seller_id
    }


def check_pet_authorization(pet, current_user_identity):
    """
    Проверяет, имеет ли пользователь доступ к питомцу.
    """
    current_user_id = current_user_identity['id']
    current_user_role = Role(current_user_identity['role'])

    if current_user_role not in [Role.ADMIN, Role.OWNER] and pet.seller_id != current_user_id:
        return False
    return True


# Create Pet (Seller or Admin/Owner only)
@bp.route('', methods=['POST'])
@jwt_required()
@role_required(Role.SELLER, Role.ADMIN, Role.OWNER)
def create_pet():
    current_user_identity = get_jwt_identity()
    data = request.get_json()

    if not all(k in data for k in ('name', 'species', 'age', 'price')):
        return jsonify({'message': 'Missing required fields (name, species, age, price)'}), 400

    try:
        new_pet = Pet(
            name=data['name'],
            species=data['species'],
            breed=data.get('breed'),
            age=int(data['age']),
            price=float(data['price']),
            description=data.get('description'),
            image_url=data.get('image_url'),
            seller_id=current_user_identity['id']
        )
        db.session.add(new_pet)
        db.session.commit()
        return jsonify({'message': 'Pet created successfully', 'pet_id': new_pet.id}), 201
    except ValueError:
        return jsonify({'message': 'Invalid data format for age or price'}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': 'Failed to create pet', 'error': str(e)}), 500


# Read All Pets (Public)
@bp.route('', methods=['GET'])
def get_pets():
    try:
        pets = Pet.query.all()
        return jsonify([format_pet(p) for p in pets]), 200
    except Exception as e:
        logger.error(f"Error retrieving pets: {e}", exc_info=True) # Log the full exception
        return jsonify({'message': 'Failed to retrieve pets', 'error': str(e)}), 500



# Read Single Pet (Public)
@bp.route('/<int:pet_id>', methods=['GET'])
def get_pet(pet_id):
    try:
        pet = Pet.query.get_or_404(pet_id)
        return jsonify(format_pet(pet)), 200
    except Exception as e:
        return jsonify({'message': 'Failed to retrieve pet', 'error': str(e)}), 500


# Update Pet (Seller who owns it or Admin/Owner)
@bp.route('/<int:pet_id>', methods=['PUT', 'PATCH'])
@jwt_required()
@role_required(Role.SELLER, Role.ADMIN, Role.OWNER)
def update_pet(pet_id):
    current_user_identity = get_jwt_identity()
    data = request.get_json()

    try:
        pet = Pet.query.get_or_404(pet_id)

        if not check_pet_authorization(pet, current_user_identity):
            return jsonify({'message': 'Permission denied: Not the owner or admin/owner'}), 403

        # Update fields (PATCH semantics)
        if 'name' in data: pet.name = data['name']
        if 'species' in data: pet.species = data['species']
        if 'breed' in data: pet.breed = data['breed']
        if 'age' in data: pet.age = int(data['age'])
        if 'price' in data: pet.price = float(data['price'])
        if 'description' in data: pet.description = data['description']
        if 'image_url' in data: pet.image_url = data['image_url']

        db.session.commit()
        return jsonify({'message': 'Pet updated successfully'}), 200

    except ValueError:
        db.session.rollback()
        return jsonify({'message': 'Invalid data format for age or price'}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': 'Failed to update pet', 'error': str(e)}), 500


# Delete Pet (Seller who owns it or Admin/Owner)
@bp.route('/<int:pet_id>', methods=['DELETE'])
@jwt_required()
@role_required(Role.SELLER, Role.ADMIN, Role.OWNER)
def delete_pet(pet_id):
    current_user_identity = get_jwt_identity()

    try:
        pet = Pet.query.get_or_404(pet_id)

        if not check_pet_authorization(pet, current_user_identity):
            return jsonify({'message': 'Permission denied: Not the owner or admin/owner'}), 403

        db.session.delete(pet)
        db.session.commit()
        return jsonify({'message': 'Pet deleted successfully'}), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'message': 'Failed to delete pet', 'error': str(e)}), 500