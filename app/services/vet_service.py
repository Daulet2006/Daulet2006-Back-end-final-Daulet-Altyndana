# Vet service module for business logic
from ..models import User, Role
from .. import db

def format_vet(vet):
    return {
        'id': vet.id,
        'username': vet.username,
        'email': vet.email
    }

def get_all_vets():
    vets = User.query.filter_by(role=Role.VETERINARIAN).all()
    return [format_vet(v) for v in vets]

def get_vet_by_id(vet_id):
    vet = User.query.get_or_404(vet_id)
    if vet.role != Role.VETERINARIAN:
        return None, {'message': 'Not a veterinarian'}, 400
    return format_vet(vet), None, 200

def update_vet(vet_id, data):
    try:
        vet = User.query.get_or_404(vet_id)
        if vet.role != Role.VETERINARIAN:
            return None, {'message': 'Not a veterinarian'}, 400
        if 'email' in data:
            vet.email = data['email']
        if 'username' in data:
            vet.username = data['username']
        db.session.commit()
        return {'message': 'Vet information updated'}, None, 200
    except Exception as e:
        db.session.rollback()
        return None, {'message': 'Failed to update vet', 'error': str(e)}, 500

def delete_vet(vet_id):
    try:
        vet = User.query.get_or_404(vet_id)
        if vet.role != Role.VETERINARIAN:
            return {'message': 'Not a veterinarian'}, 400
        db.session.delete(vet)
        db.session.commit()
        return {'message': 'Vet deleted'}, 200
    except Exception as e:
        db.session.rollback()
        return {'message': 'Failed to delete vet', 'error': str(e)}, 500