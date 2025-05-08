from flask_restx import Namespace, Resource, fields, reqparse
from flask import request, jsonify, send_from_directory, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from ..models import ChatMessage, User
from .. import db
from datetime import datetime
import os
import uuid
from werkzeug.utils import secure_filename
import openai
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

chat_ns = Namespace('chat', description='Operations related to chat messages')

# Allowed file extensions
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif', 'doc', 'docx'}

# Request parser for file uploads and message
chat_parser = reqparse.RequestParser()
chat_parser.add_argument('message', type=str, required=True, help='Chat message text')
chat_parser.add_argument('file', type=reqparse.FileStorage, location='files', help='Optional file attachment')

# Swagger models
chat_message_model = chat_ns.model('ChatMessage', {
    'message': fields.String(required=True, description='User message text'),
    'file': fields.Raw(description='Optional file attachment (multipart/form-data)')
})

chat_response_model = chat_ns.model('ChatResponse', {
    'id': fields.Integer(description='Message ID'),
    'message': fields.String(description='User message'),
    'reply': fields.String(description='AI reply'),
    'timestamp': fields.String(description='Message timestamp (ISO format)'),
    'file': fields.Nested(chat_ns.model('File', {
        'name': fields.String(description='File name'),
        'path': fields.String(description='File path'),
        'type': fields.String(description='File MIME type')
    }), description='Attached file details', required=False)
})

# Helper functions
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_ai_reply(message):
    """
    Get response from OpenAI Chat API.
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

@chat_ns.route('')
class ChatMessageResource(Resource):
    @jwt_required()
    @chat_ns.expect(chat_parser)
    @chat_ns.marshal_with(chat_response_model, code=201)
    def post(self):
        """Send a new chat message with optional file upload"""
        user_identity = get_jwt_identity()
        user_id = user_identity['id']
        args = chat_parser.parse_args()
        user_message = args['message']
        file = args['file']

        file_path = None
        file_name = None
        file_type = None

        # Handle file upload
        if file and file.filename and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            unique_filename = f"{uuid.uuid4()}_{filename}"
            file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], unique_filename)
            os.makedirs(current_app.config['UPLOAD_FOLDER'], exist_ok=True)
            file.save(file_path)
            file_path = os.path.join('uploads', unique_filename)
            file_name = filename
            file_type = file.content_type

        # Get AI reply
        ai_reply = get_ai_reply(user_message)

        # Save message to database
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

        # Prepare response
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

        return response_data, 201

@chat_ns.route('/history')
class ChatHistoryResource(Resource):
    @jwt_required()
    @chat_ns.marshal_list_with(chat_response_model)
    def get(self):
        """Get chat history for the authenticated user"""
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

        return formatted_messages, 200

@chat_ns.route('/files/<path:filename>')
class ChatFileResource(Resource):
    @jwt_required()
    def get(self, filename):
        """Download a file attached to a chat message"""
        user_identity = get_jwt_identity()
        user_id = user_identity['id']

        # Verify user has access to the file
        message = ChatMessage.query.filter_by(file_path=os.path.join('uploads', filename), user_id=user_id).first()

        if not message:
            return {'message': 'Файл не найден или у вас нет прав доступа'}, 404

        # Send the file
        return send_from_directory(
            current_app.config['UPLOAD_FOLDER'],
            filename
        )