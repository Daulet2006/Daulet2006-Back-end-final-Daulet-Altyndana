from flask import Blueprint, request, jsonify, send_from_directory, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from ..models import ChatMessage, User
from .. import db
from datetime import datetime
import os
from werkzeug.utils import secure_filename
import uuid
import openai
from dotenv import load_dotenv

# Загрузка переменных окружения
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

bp = Blueprint('chat', __name__, url_prefix='/chat')

# Настройка директории для загрузки файлов
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'static', 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif', 'doc', 'docx'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_ai_reply(message):
    """
    Получить ответ от OpenAI Chat API.
    """
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Ты помощник в зоомагазине. Отвечай дружелюбно, понятно и помогай с товарами и услугами для животных."},
                {"role": "user", "content": message}
            ],
            temperature=0.7,
            max_tokens=500
        )
        return response['choices'][0]['message']['content']
    except Exception as e:
        print("OpenAI error:", e)
        return "Извините, я не смог получить ответ от ИИ. Попробуйте позже."

@bp.route('', methods=['POST'])
@jwt_required()
def send_message():
    user_identity = get_jwt_identity()
    user_id = user_identity['id']

    file = None
    file_path = None
    file_name = None
    file_type = None

    if 'file' in request.files:
        file = request.files['file']
        if file and file.filename and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            unique_filename = f"{uuid.uuid4()}_{filename}"
            file_path = os.path.join(UPLOAD_FOLDER, unique_filename)
            file.save(file_path)
            file_path = os.path.join('uploads', unique_filename)
            file_name = filename
            file_type = file.content_type

    if request.form and 'message' in request.form:
        user_message = request.form['message']
    elif request.is_json:
        data = request.get_json()
        if not data or 'message' not in data:
            return jsonify({'message': 'Необходимо указать текст сообщения'}), 400
        user_message = data['message']
    else:
        return jsonify({'message': 'Неверный формат запроса'}), 400

    ai_reply = get_ai_reply(user_message)

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
    user_identity = get_jwt_identity()
    user_id = user_identity['id']

    messages = ChatMessage.query.filter_by(user_id=user_id).order_by(ChatMessage.timestamp).all()

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
    user_identity = get_jwt_identity()
    user_id = user_identity['id']

    message = ChatMessage.query.filter_by(file_path=os.path.join('uploads', filename), user_id=user_id).first()

    if not message:
        return jsonify({'message': 'Файл не найден или у вас нет прав доступа'}), 404

    return send_from_directory(
        os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'static', 'uploads'),
        filename
    )
