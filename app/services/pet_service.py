# Pet service module for business logic
from ..models import Pet, Role
from .. import db
import os
import uuid
from flask import current_app
from werkzeug.utils import secure_filename

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

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
        'seller_id': str(pet.seller_id) if pet.seller_id is not None else None
    }

def check_pet_authorization(pet, current_user_identity):
    current_user_id = current_user_identity['id']
    role_str = current_user_identity.get('role', '')
    try:
        current_user_role = Role(role_str)
    except ValueError:
        return False, "Invalid role"
    if current_user_role in [Role.ADMIN, Role.OWNER] or pet.seller_id == current_user_id:
        return True, None
    return False, "No permission to modify pet"

def get_all_pets():
    pets = Pet.query.all()
    return [format_pet(p) for p in pets]

def create_pet(args, image, current_user_identity):
    if image.filename == '' or not allowed_file(image.filename):
        return None, {'message': 'Invalid file'}, 400
    filename = secure_filename(image.filename)
    unique_name = f"{uuid.uuid4().hex}_{filename}"
    save_path = os.path.join(current_app.config['UPLOAD_FOLDER'], unique_name)
    os.makedirs(current_app.config['UPLOAD_FOLDER'], exist_ok=True)
    image.save(save_path)
    image_url = f"/static/uploads/{unique_name}"
    try:
        new_pet = Pet(
            name=args['name'],
            species=args['species'],
            breed=args['breed'],
            age=args['age'],
            price=args['price'],
            description=args['description'],
            image_url=image_url,
            seller_id=current_user_identity['id']
        )
        db.session.add(new_pet)
        db.session.commit()
        return format_pet(new_pet), None, 201
    except Exception as e:
        db.session.rollback()
        return None, {'message': 'Error creating pet', 'error': str(e)}, 500

def get_pet_by_id(pet_id):
    pet = Pet.query.get_or_404(pet_id)
    return format_pet(pet)

def update_pet(pet_id, args, image, current_user_identity):
    try:
        pet = Pet.query.get_or_404(pet_id)
        authorized, error_message = check_pet_authorization(pet, current_user_identity)
        if not authorized:
            return None, {'message': error_message}, 403
        pet.name = args['name']
        pet.species = args['species']
        pet.breed = args['breed']
        pet.age = args['age']
        pet.price = args['price']
        pet.description = args['description']
        if image and (image.filename == '' or not allowed_file(image.filename)):
            return None, {'message': 'Invalid file'}, 400
        if image:
            if pet.image_url:
                old_path = os.path.join(current_app.root_path, pet.image_url.strip("/"))
                if os.path.exists(old_path):
                    os.remove(old_path)
            filename = f"{uuid.uuid4().hex}_{secure_filename(image.filename)}"
            upload_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
            os.makedirs(current_app.config['UPLOAD_FOLDER'], exist_ok=True)
            image.save(upload_path)
            pet.image_url = f"/static/uploads/{filename}"
        db.session.commit()
        return format_pet(pet), None, 200
    except Exception as e:
        db.session.rollback()
        return None, {'message': 'Error updating pet', 'error': str(e)}, 500

def delete_pet(pet_id, current_user_identity):
    try:
        pet = Pet.query.get_or_404(pet_id)
        authorized, error_message = check_pet_authorization(pet, current_user_identity)
        if not authorized:
            return {'message': error_message}, 403
        db.session.delete(pet)
        db.session.commit()
        return {'message': 'Pet deleted'}, 200
    except Exception as e:
        db.session.rollback()
        return {'message': 'Error deleting pet', 'error': str(e)}, 500