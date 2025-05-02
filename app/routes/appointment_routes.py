# app/routes/appointment_routes.py
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from ..models import VetAppointment, User, Role, Pet # Import Pet model
from .. import db
from ..utils import role_required
from datetime import datetime
from dateutil.parser import isoparse
from .. import db
from ..utils import role_required
from datetime import datetime
from dateutil.parser import isoparse

bp = Blueprint('appointments', __name__, url_prefix='/appointments')


# Helper Functions
def format_appointment(appointment):
    """
    Форматирует объект записи о приеме для ответа в формате JSON.
    """
    return {
        'id': appointment.id,
        'client_id': appointment.client_id,
        'vet_id': appointment.vet_id,
        'appointment_date': appointment.appointment_date.isoformat(),
        'reason': appointment.reason,
        'status': appointment.status,
        'pet_ids': [pet.id for pet in appointment.pets] # Include associated pet IDs
    }


def has_permission(current_user_role, current_user_id, appointment):
    """
    Проверяет, имеет ли текущий пользователь доступ к записи о приеме.
    """
    is_admin_or_owner = current_user_role in [Role.ADMIN, Role.OWNER]
    is_client_of_appt = current_user_role == Role.CLIENT and appointment.client_id == current_user_id
    is_vet_of_appt = current_user_role == Role.VETERINARIAN and appointment.vet_id == current_user_id
    return is_admin_or_owner or is_client_of_appt or is_vet_of_appt


def parse_and_validate_date(date_str):
    """
    Проверяет, является ли строка корректной датой в будущем, и возвращает ее.
    """
    try:
        appointment_date = isoparse(date_str)
        if appointment_date <= datetime.utcnow():
            raise ValueError("Date must be in the future")
        return appointment_date
    except (ValueError, TypeError):
        raise ValueError("Invalid date format. Use ISO format (YYYY-MM-DDTHH:MM:SS)")


# Route Handlers

# Get All Appointments
@bp.route('', methods=['GET'])
@jwt_required()
def get_appointments():
    """
    Получает список всех записей о приёмах, доступных текущему пользователю.
    """
    current_user_identity = get_jwt_identity()
    current_user_id = current_user_identity['id']
    current_user_role = Role(current_user_identity['role'])

    try:
        query = VetAppointment.query
        if current_user_role == Role.CLIENT:
            query = query.filter_by(client_id=current_user_id)
        elif current_user_role == Role.VETERINARIAN:
            query = query.filter_by(vet_id=current_user_id)
        elif current_user_role not in [Role.ADMIN, Role.OWNER]:
            return jsonify({'message': 'Permission denied'}), 403

        appointments = query.order_by(VetAppointment.appointment_date.asc()).all()
        return jsonify([format_appointment(appt) for appt in appointments]), 200
    except Exception as e:
        return jsonify({'message': 'Failed to retrieve appointments', 'error': str(e)}), 500


# Get Single Appointment
@bp.route('/<int:appointment_id>', methods=['GET'])
@jwt_required()
def get_appointment(appointment_id):
    """
    Получает данные одной записи о приёме для текущего пользователя.
    """
    current_user_identity = get_jwt_identity()
    current_user_id = current_user_identity['id']
    current_user_role = Role(current_user_identity['role'])

    try:
        appointment = VetAppointment.query.get_or_404(appointment_id)

        if not has_permission(current_user_role, current_user_id, appointment):
            return jsonify({'message': 'Permission denied'}), 403

        return jsonify(format_appointment(appointment)), 200
    except Exception as e:
        return jsonify({'message': 'Failed to retrieve appointment', 'error': str(e)}), 500


# Create Appointment
@bp.route('', methods=['POST'])
@jwt_required()
@role_required(Role.CLIENT)
def create_appointment():
    """
    Создает новую запись о приёме для клиента.
    """
    current_user_identity = get_jwt_identity()
    client_id = current_user_identity['id']
    data = request.get_json()

    # pet_ids is optional for creation
    if not all(k in data for k in ('vet_id', 'appointment_date', 'reason')):
        return jsonify({'message': 'Missing required fields (vet_id, appointment_date, reason)'}), 400

    vet_id = data['vet_id']
    appointment_date_str = data['appointment_date']
    reason = data['reason']

    try:
        # Validate Vet ID
        vet = User.query.filter_by(id=vet_id, role=Role.VETERINARIAN).first()
        if not vet:
            return jsonify({'message': f'Veterinarian with ID {vet_id} not found or is not a vet'}), 404

        # Validate and parse date
        appointment_date = parse_and_validate_date(appointment_date_str)

        new_appointment = VetAppointment(
            client_id=client_id,
            vet_id=vet_id,
            appointment_date=appointment_date,
            reason=reason,
            status='Scheduled'
        )

        # Handle Pet association (M:N)
        pet_ids = data.get('pet_ids', [])
        if not isinstance(pet_ids, list):
            return jsonify({'message': 'pet_ids must be a list of integers'}), 400

        pets_to_associate = []
        for pet_id in pet_ids:
            pet = Pet.query.get(pet_id)
            if not pet:
                db.session.rollback()
                return jsonify({'message': f'Pet with ID {pet_id} not found'}), 404
            # Optional: Check if pet belongs to the client creating the appointment
            # if pet.owner_id != client_id: # Assuming Pet has an owner_id
            #     db.session.rollback()
            #     return jsonify({'message': f'Pet with ID {pet_id} does not belong to you'}), 403
            pets_to_associate.append(pet)

        new_appointment.pets = pets_to_associate # Associate pets

        db.session.add(new_appointment)
        db.session.commit()
        return jsonify({'message': 'Appointment created successfully', 'appointment_id': new_appointment.id}), 201
    except ValueError as ve:
        return jsonify({'message': str(ve)}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': 'Failed to create appointment', 'error': str(e)}), 500


# Update Appointment
@bp.route('/<int:appointment_id>', methods=['PUT', 'PATCH'])
@jwt_required()
@role_required(Role.VETERINARIAN, Role.ADMIN, Role.OWNER)
def update_appointment(appointment_id):
    """
    Обновляет существующую запись о приёме (например, статус или дату).ек
    """
    current_user_identity = get_jwt_identity()
    current_user_id = current_user_identity['id']
    current_user_role = Role(current_user_identity['role'])
    data = request.get_json()

    try:
        appointment = VetAppointment.query.get_or_404(appointment_id)

        if not has_permission(current_user_role, current_user_id, appointment):
            return jsonify({'message': 'Permission denied'}), 403

        # Обновление полей
        if 'status' in data:
            if data['status'] not in VetAppointment.VALID_STATUSES:
                return jsonify(
                    {'message': f"Invalid status value. Allowed: {', '.join(VetAppointment.VALID_STATUSES)}"}), 400
            appointment.status = data['status']

        if 'reason' in data:
            appointment.reason = data['reason']

        if 'appointment_date' in data:
            appointment_date = parse_and_validate_date(data['appointment_date'])
            appointment.appointment_date = appointment_date

        # Handle Pet association update (M:N)
        if 'pet_ids' in data:
            pet_ids = data['pet_ids']
            if not isinstance(pet_ids, list):
                return jsonify({'message': 'pet_ids must be a list of integers'}), 400

            pets_to_associate = []
            for pet_id in pet_ids:
                pet = Pet.query.get(pet_id)
                if not pet:
                    db.session.rollback()
                    return jsonify({'message': f'Pet with ID {pet_id} not found'}), 404
                # Optional: Check pet ownership if relevant
                pets_to_associate.append(pet)

            appointment.pets = pets_to_associate # Replace existing associations

        db.session.commit()
        return jsonify({'message': 'Appointment updated successfully'}), 200

    except ValueError as ve:
        return jsonify({'message': str(ve)}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': 'Failed to update appointment', 'error': str(e)}), 500


# Delete Appointment
@bp.route('/<int:appointment_id>', methods=['DELETE'])
@jwt_required()
@role_required(Role.CLIENT, Role.ADMIN, Role.OWNER)
def delete_appointment(appointment_id):
    """
    Удаляет запись о приёме (только для клиента, админа или владельца).
    """
    current_user_identity = get_jwt_identity()
    current_user_id = current_user_identity['id']
    current_user_role = Role(current_user_identity['role'])

    try:
        appointment = VetAppointment.query.get_or_404(appointment_id)

        if current_user_role == Role.CLIENT and appointment.client_id != current_user_id:
            return jsonify({'message': 'Permission denied: Clients can only delete their own appointments'}), 403

        db.session.delete(appointment)
        db.session.commit()
        return jsonify({'message': 'Appointment deleted successfully'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': 'Failed to delete appointment', 'error': str(e)}), 500
