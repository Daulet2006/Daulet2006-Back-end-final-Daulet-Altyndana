from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from ..models import Pet, User
from .. import db
from ..utils import role_required

bp = Blueprint('pets', __name__, url_prefix='/pets')

# Добавление питомца (для seller)
@bp.route('/', methods=['POST'])
@role_required('seller')
def add_pet():
    data = request.get_json()
    current_user = get_jwt_identity()
    new_pet = Pet(
        name=data['name'],
        species=data['species'],
        age=data['age'],
        seller_id=current_user['id']
    )
    db.session.add(new_pet)
    db.session.commit()
    return jsonify({'message': 'Pet added'}), 201

# Покупка питомца (для customer)
@bp.route('/buy/<int:pet_id>', methods=['POST'])
@role_required('customer')
def buy_pet(pet_id):
    pet = Pet.query.get_or_404(pet_id)
    current_user = get_jwt_identity()
    user = User.query.get(current_user['id'])
    if pet in user.pets:
        return jsonify({'message': 'You already own this pet'}), 400
    user.pets.append(pet)
    db.session.commit()
    return jsonify({'message': 'Pet purchased'}), 200
