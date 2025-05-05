# app/__init__.py
from flask import Flask, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager
from flask_cors import CORS
from config import Config
from flask_bcrypt import Bcrypt
from flask_migrate import Migrate

migrate = Migrate()

db = SQLAlchemy()
jwt = JWTManager()
bcrypt = Bcrypt()

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)
    bcrypt.init_app(app)  # Initialize bcrypt
    # Enable CORS for all origins
    CORS(app, resources={r"/*": {"origins": app.config.get('CORS_ORIGINS', '*')}},
         supports_credentials=app.config.get('CORS_SUPPORTS_CREDENTIALS', True),
         allow_headers=app.config.get('CORS_ALLOW_HEADERS', ["Content-Type", "Authorization"]),
         methods=app.config.get('CORS_METHODS', ["GET", "POST", "PUT", "DELETE", "OPTIONS"]))
    
    # Настройка middleware для аутентификации и проверки ролей
    from .auth_middleware import setup_auth_middleware
    setup_auth_middleware(app)
    
    # Import and register routes inside the factory to avoid circular imports
    from app.routes import register_routes
    register_routes(app)
    
    # Обработчик ошибок для случаев недостаточных прав доступа
    @app.errorhandler(403)
    def forbidden(error):
        return jsonify({
            'message': 'Недостаточно прав для выполнения этой операции',
            'error': str(error)
        }), 403

    with app.app_context():
        db.create_all()
    return app


app = create_app()
