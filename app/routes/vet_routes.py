from flask_restx import Namespace, Resource, fields
from flask import request
from flask_jwt_extended import jwt_required
from ..models import User, Role
from .. import db
from ..utils import role_required

vet_ns = Namespace('vets', description='Operations related to veterinarians')

# Swagger model
vet_model = vet_ns.model('Vet', {
    'username': fields.String(required=True, description='Vet username'),
    'email': fields.String(required=True, description='Vet email')
})

# Helper function
def format_vet(vet):
    return {
        'id': vet.id,
        'username': vet.username,
        'email': vet.email
    }

@vet_ns.route('')
class VetList(Resource):
    def get(self):
        """Get all veterinarians"""
        try:
            vets = User.query.filter_by(role=Role.VETERINARIAN).all()
            return [format_vet(v) for v in vets], 200
        except Exception as e:
            return {'message': 'Failed to retrieve vets', 'error': str(e)}, 500

@vet_ns.route('/<int:vet_id>')
class VetResource(Resource):
    def get(self, vet_id):
        """Get a veterinarian by ID"""
        try:
            vet = User.query.get_or_404(vet_id)
            if vet.role != Role.VETERINARIAN:
                return {'message': 'Not a veterinarian'}, 400
            return format_vet(vet), 200
        except Exception as e:
            return {'message': 'Failed to retrieve vet', 'error': str(e)}, 500

    @jwt_required()
    @role_required(Role.ADMIN)
    @vet_ns.expect(vet_model)
    def put(self, vet_id):
        """Update a veterinarian"""
        data = request.get_json()
        try:
            vet = User.query.get_or_404(vet_id)
            if vet.role != Role.VETERINARIAN:
                return {'message': 'Not a veterinarian'}, 400

            if 'email' in data:
                vet.email = data['email']
            if 'username' in data:
                vet.username = data['username']

            db.session.commit()
            return {'message': 'Vet information updated'}, 200
        except Exception as e:
            return {'message': 'Failed to update vet', 'error': str(e)}, 500

    @jwt_required()
    @role_required(Role.ADMIN)
    def delete(self, vet_id):
        """Delete a veterinarian"""
        try:
            vet = User.query.get_or_404(vet_id)
            if vet.role != Role.VETERINARIAN:
                return {'message': 'Not a veterinarian'}, 400
            db.session.delete(vet)
            db.session.commit()
            return {'message': 'Vet deleted'}, 200
        except Exception as e:
            return {'message': 'Failed to delete vet', 'error': str(e)}, 500