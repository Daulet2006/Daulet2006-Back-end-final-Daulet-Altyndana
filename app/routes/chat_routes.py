# app/routes/chat_routes.py
from flask import Blueprint, request, jsonify, send_from_directory, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from ..models import ChatMessage, User
from .. import db
from datetime import datetime
import os
from werkzeug.utils import secure_filename
import uuid

bp = Blueprint('chat', __name__, url_prefix='/chat')

# Настройка директории для загрузки файлов
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'static', 'uploads')
# Создаем директорию, если она не существует
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
# Разрешенные расширения файлов
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif', 'doc', 'docx'}

def allowed_file(filename):
    """
    Проверяет, разрешено ли загружать файл с данным расширением.
    """
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_ai_reply(message):
    """
    Функция-заглушка для генерации ответа от ИИ.
    В реальном приложении здесь может быть интеграция с OpenAI API или другим сервисом.
    """
    # Простая логика для демонстрации
    if 'привет' in message.lower():
        return "Здравствуйте! Чем я могу вам помочь?"
    elif 'кошка' in message.lower() or 'кошек' in message.lower():
        return "У нас есть широкий выбор кормов для кошек различных брендов. Также у нас есть игрушки, лежанки и другие товары для ваших питомцев."
    elif 'собака' in message.lower() or 'собак' in message.lower():
        return "Для собак у нас представлены корма премиум-класса, игрушки, поводки и многое другое. Что именно вас интересует?"
    elif 'ветеринар' in message.lower() or 'врач' in message.lower():
        return "Вы можете записаться к ветеринару через наше приложение. Перейдите в раздел 'Записи к ветеринару' и выберите удобное время."
    elif 'цена' in message.lower() or 'стоимость' in message.lower() or 'сколько стоит' in message.lower():
        return "Цены на наши товары варьируются в зависимости от категории и бренда. Пожалуйста, уточните, какой товар вас интересует."
    else:
        return "Спасибо за ваше сообщение! Чем еще я могу помочь вам с выбором товаров для ваших питомцев?"


@bp.route('', methods=['POST'])
@jwt_required()
def send_message():
    """
    Обработка отправки сообщения пользователем и получения ответа от ИИ.
    """
    user_identity = get_jwt_identity()
    user_id = user_identity['id']
    
    # Проверяем, есть ли файл в запросе
    file = None
    file_path = None
    file_name = None
    file_type = None
    
    if 'file' in request.files:
        file = request.files['file']
        if file and file.filename and allowed_file(file.filename):
            # Безопасное имя файла
            filename = secure_filename(file.filename)
            # Генерируем уникальное имя файла
            unique_filename = f"{uuid.uuid4()}_{filename}"
            # Полный путь к файлу
            file_path = os.path.join(UPLOAD_FOLDER, unique_filename)
            # Сохраняем файл
            file.save(file_path)
            # Сохраняем относительный путь для БД
            file_path = os.path.join('uploads', unique_filename)
            file_name = filename
            file_type = file.content_type
    
    # Получаем текст сообщения
    if request.form and 'message' in request.form:
        user_message = request.form['message']
    elif request.is_json:
        data = request.get_json()
        if not data or 'message' not in data:
            return jsonify({'message': 'Необходимо указать текст сообщения'}), 400
        user_message = data['message']
    else:
        return jsonify({'message': 'Неверный формат запроса'}), 400
    
    # Получаем ответ от ИИ
    ai_reply = get_ai_reply(user_message)
    
    # Сохраняем сообщение и ответ в базе данных
    new_message = ChatMessage(
        user_id=user_id,
        message=user_message,
        reply=ai_reply,
        timestamp=datetime.utcnow(),
        file_path=file_path,
        file_name=file_name,
        file_type=file_type
    )
    
    db.session.add(new_message)
    db.session.commit()
    
    response_data = {
        'id': new_message.id,
        'message': new_message.message,
        'reply': new_message.reply,
        'timestamp': new_message.timestamp.isoformat()
    }
    
    if file_path:
        response_data['file'] = {
            'name': file_name,
            'path': file_path,
            'type': file_type
        }
    
    return jsonify(response_data), 201


@bp.route('/history', methods=['GET'])
@jwt_required()
def get_chat_history():
    """
    Получение истории сообщений пользователя.
    """
    user_identity = get_jwt_identity()
    user_id = user_identity['id']
    
    # Получаем все сообщения пользователя, отсортированные по времени
    messages = ChatMessage.query.filter_by(user_id=user_id).order_by(ChatMessage.timestamp).all()
    
    # Форматируем сообщения для ответа
    formatted_messages = []
    for msg in messages:
        message_data = {
            'id': msg.id,
            'message': msg.message,
            'reply': msg.reply,
            'timestamp': msg.timestamp.isoformat()
        }
        
        if msg.file_path:
            message_data['file'] = {
                'name': msg.file_name,
                'path': msg.file_path,
                'type': msg.file_type
            }
        
        formatted_messages.append(message_data)
    
    return jsonify(formatted_messages), 200


@bp.route('/files/<path:filename>', methods=['GET'])
@jwt_required()
def download_file(filename):
    """
    Скачивание файла, прикрепленного к сообщению.
    """
    user_identity = get_jwt_identity()
    user_id = user_identity['id']
    
    # Проверяем, существует ли сообщение с таким файлом и принадлежит ли оно пользователю
    message = ChatMessage.query.filter_by(file_path=os.path.join('uploads', filename), user_id=user_id).first()
    
    if not message:
        return jsonify({'message': 'Файл не найден или у вас нет прав доступа'}), 404
    
    # Отправляем файл
    return send_from_directory(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), os.path.join('static', 'uploads', filename))