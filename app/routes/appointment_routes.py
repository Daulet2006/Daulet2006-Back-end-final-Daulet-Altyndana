from flask_restx import Namespace, Resource, fields
from flask import request
from flask_jwt_extended import jwt_required, get_jwt_identity
from ..models import VetAppointment, User, Role, Pet
from .. import db
from ..utils import role_required
from datetime import datetime
from dateutil.parser import isoparse

appointment_ns = Namespace('appointments', description='Operations related to vet appointments')

# Swagger model
appointment_model = appointment_ns.model('Appointment', {
    'vet_id': fields.Integer(required=True, description='ID of the veterinarian'),
    'appointment_date': fields.String(required=True, description='Date in ISO format'),
    'reason': fields.String(required=True, description='Reason for appointment'),
    'pet_ids': fields.List(fields.Integer, description='IDs of the pets'),
})

# Helper functions
def format_appointment(appointment):
    return {
        'id': appointment.id,
        'client_id': appointment.client_id,
        'vet_id': appointment.vet_id,
        'appointment_date': appointment.appointment_date.isoformat(),
        'reason': appointment.reason,
        'status': appointment.status,
        'pet_ids': [pet.id for pet in appointment.pets]
    }

def has_permission(current_user_role, current_user_id, appointment):
    return (
        current_user_role in [Role.ADMIN, Role.OWNER] or
        (current_user_role == Role.CLIENT and appointment.client_id == current_user_id) or
        (current_user_role == Role.VETERINARIAN and appointment.vet_id == current_user_id)
    )

def parse_and_validate_date(date_str):
    try:
        appointment_date = isoparse(date_str)
        if appointment_date <= datetime.utcnow():
            raise ValueError("Date must be in the future")
        return appointment_date
    except (ValueError, TypeError):
        raise ValueError("Invalid date format. Use ISO format (YYYY-MM-DDTHH:MM:SS)")

@appointment_ns.route('')
class AppointmentList(Resource):
    @jwt_required()
    def get(self):
        """Get all appointments (filtered by role)"""
        current_user = get_jwt_identity()
        user_id = current_user['id']
        user_role = Role(current_user['role'])

        query = VetAppointment.query
        if user_role == Role.CLIENT:
            query = query.filter_by(client_id=user_id)
        elif user_role == Role.VETERINARIAN:
            query = query.filter_by(vet_id=user_id)
        elif user_role not in [Role.ADMIN, Role.OWNER]:
            return {'message': 'Permission denied'}, 403

        appointments = query.order_by(VetAppointment.appointment_date.asc()).all()
        return [format_appointment(a) for a in appointments], 200

    @jwt_required()
    @role_required(Role.CLIENT)
    @appointment_ns.expect(appointment_model)
    def post(self):
        """Create a new appointment"""
        current_user = get_jwt_identity()
        client_id = current_user['id']
        data = request.get_json()

        try:
            vet = User.query.filter_by(id=data['vet_id'], role=Role.VETERINARIAN).first()
            if not vet:
                return {'message': 'Veterinarian not found'}, 404

            appointment_date = parse_and_validate_date(data['appointment_date'])

            new_appointment = VetAppointment(
                client_id=client_id,
                vet_id=vet.id,
                appointment_date=appointment_date,
                reason=data['reason'],
                status='Scheduled'
            )

            pet_ids = data.get('pet_ids', [])
            if not isinstance(pet_ids, list):
                return {'message': 'pet_ids must be a list'}, 400

            pets = []
            for pid in pet_ids:
                pet = Pet.query.get(pid)
                if not pet:
                    return {'message': f'Pet {pid} not found'}, 404
                pets.append(pet)

            new_appointment.pets = pets
            db.session.add(new_appointment)
            db.session.commit()

            return {'message': 'Appointment created', 'appointment_id': new_appointment.id}, 201
        except ValueError as ve:
            return {'message': str(ve)}, 400
        except Exception as e:
            db.session.rollback()
            return {'message': 'Error creating appointment', 'error': str(e)}, 500

@appointment_ns.route('/<int:appointment_id>')
class AppointmentResource(Resource):
    @jwt_required()
    def get(self, appointment_id):
        """Get appointment by ID"""
        current_user = get_jwt_identity()
        user_id = current_user['id']
        user_role = Role(current_user['role'])

        appointment = VetAppointment.query.get_or_404(appointment_id)
        if not has_permission(user_role, user_id, appointment):
            return {'message': 'Permission denied'}, 403

        return format_appointment(appointment), 200

    @jwt_required()
    @role_required(Role.VETERINARIAN, Role.ADMIN, Role.OWNER)
    @appointment_ns.expect(appointment_model)
    def put(self, appointment_id):
        """Update an appointment"""
        current_user = get_jwt_identity()
        user_id = current_user['id']
        user_role = Role(current_user['role'])
        data = request.get_json()

        try:
            appointment = VetAppointment.query.get_or_404(appointment_id)
            if not has_permission(user_role, user_id, appointment):
                return {'message': 'Permission denied'}, 403

            if 'status' in data:
                if data['status'] not in VetAppointment.VALID_STATUSES:
                    return {'message': f"Invalid status. Allowed: {', '.join(VetAppointment.VALID_STATUSES)}"}, 400
                appointment.status = data['status']

            if 'reason' in data:
                appointment.reason = data['reason']

            if 'appointment_date' in data:
                appointment.appointment_date = parse_and_validate_date(data['appointment_date'])

            if 'pet_ids' in data:
                if not isinstance(data['pet_ids'], list):
                    return {'message': 'pet_ids must be a list'}, 400
                pets = []
                for pid in data['pet_ids']:
                    pet = Pet.query.get(pid)
                    if not pet:
                        return {'message': f'Pet {pid} not found'}, 404
                    pets.append(pet)
                appointment.pets = pets

            db.session.commit()
            return {'message': 'Appointment updated'}, 200
        except ValueError as ve:
            return {'message': str(ve)}, 400
        except Exception as e:
            db.session.rollback()
            return {'message': 'Error updating appointment', 'error': str(e)}, 500

    @jwt_required()
    @role_required(Role.CLIENT, Role.ADMIN, Role.OWNER)
    def delete(self, appointment_id):
        """Delete an appointment"""
        current_user = get_jwt_identity()
        user_id = current_user['id']
        user_role = Role(current_user['role'])

        try:
            appointment = VetAppointment.query.get_or_404(appointment_id)
            if user_role == Role.CLIENT and appointment.client_id != user_id:
                return {'message': 'Clients can only delete their own appointments'}, 403

            db.session.delete(appointment)
            db.session.commit()
            return {'message': 'Appointment deleted'}, 200
        except Exception as e:
            db.session.rollback()
            return {'message': 'Error deleting appointment', 'error': str(e)}, 500