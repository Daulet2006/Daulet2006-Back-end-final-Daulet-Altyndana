from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from ..models import Appointment
from .. import db
from datetime import datetime
from ..utils import role_required

bp = Blueprint('appointments', __name__, url_prefix='/appointments')

# Получение записей для текущего пользователя
@bp.route('/', methods=['GET'])
@jwt_required()
def get_appointments():
    current_user = get_jwt_identity()
    appointments = Appointment.query.filter_by(user_id=current_user['id']).order_by(Appointment.date.desc()).all()
    return jsonify([{
        'id': a.id,
        'vet_id': a.vet_id,
        'date': a.date.isoformat(),
        'status': a.status
    } for a in appointments])

# Создание новой записи (для customer)
@bp.route('/', methods=['POST'])
@role_required('customer')  # Только для customer
def create_appointment():
    data = request.get_json()
    current_user = get_jwt_identity()
    new_appointment = Appointment(
        user_id=current_user['id'],
        vet_id=data['vet_id'],
        date=datetime.fromisoformat(data['date'])
    )
    db.session.add(new_appointment)
    db.session.commit()
    return jsonify({'message': 'Appointment created'}), 201

# Обновление статуса записи (для vet и admin)
@bp.route('/<int:id>', methods=['PUT'])
@role_required('vet', 'admin')  # Для обновления только vet и admin
@jwt_required()
def update_appointment(id):
    appointment = Appointment.query.get_or_404(id)
    data = request.get_json()
    current_user = get_jwt_identity()

    if current_user['role'] == 'vet' and appointment.vet_id == current_user['id']:
        appointment.status = data['status']
    elif current_user['role'] == 'admin':
        appointment.status = data['status']
    else:
        return jsonify({'message': 'Access denied'}), 403

    db.session.commit()
    return jsonify({'message': 'Appointment updated'}), 200

# Удаление записи (для admin или владельца записи)
@bp.route('/<int:id>', methods=['DELETE'])
@role_required('admin', 'customer')  # Для удаления только admin или customer
@jwt_required()
def delete_appointment(id):
    appointment = Appointment.query.get_or_404(id)
    current_user = get_jwt_identity()

    if current_user['role'] == 'admin' or appointment.user_id == current_user['id']:
        db.session.delete(appointment)
        db.session.commit()
        return jsonify({'message': 'Appointment deleted'}), 200

    return jsonify({'message': 'Access denied'}), 403
