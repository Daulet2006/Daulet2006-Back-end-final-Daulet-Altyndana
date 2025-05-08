import os
from flask import Flask, jsonify, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager
from flask_cors import CORS
from flask_bcrypt import Bcrypt
from flask_migrate import Migrate
from flask_restx import Api
from app.config import Config

migrate = Migrate()
db = SQLAlchemy()
jwt = JWTManager()
bcrypt = Bcrypt()

api = Api(
    title='Zoo Store API',
    version='1.0',
    description='Документация к API Zoo Store',
    doc='/docs',
    ui_config={
        'displayOperationId': True,
        'docExpansion': 'none',
        'filter': True,
        'defaultModelsExpandDepth': 1,
        'defaultModelExpandDepth': 1
    },
    css='/static/css/swagger-custom.css',
    security=[{'BearerAuth': []}],  # Define JWT security
    authorizations={
        'BearerAuth': {
            'type': 'apiKey',
            'in': 'header',
            'name': 'Authorization',
            'description': 'Enter your JWT token as "Bearer <token>"'
        }
    }
)


def create_app():
    app = Flask(__name__, static_url_path='/static')
    app.config.from_object(Config)
    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)
    bcrypt.init_app(app)
    api.init_app(app)

    # Setup upload directory
    app.config['UPLOAD_FOLDER'] = os.path.join('static', 'uploads')

    # Create the upload directory if it doesn't exist
    if not os.path.exists(app.config['UPLOAD_FOLDER']):
        os.makedirs(app.config['UPLOAD_FOLDER'])

    # Route for serving uploaded files
    @app.route('/get/<path:filename>')
    def static_file(filename):
        return send_from_directory(os.path.join('..','static', 'uploads'), filename)
    # Enable CORS
    CORS(app, resources={r"/*": {"origins": app.config.get('CORS_ORIGINS', '*')}},
         supports_credentials=app.config.get('CORS_SUPPORTS_CREDENTIALS', True),
         allow_headers=app.config.get('CORS_ALLOW_HEADERS', ["Content-Type", "Authorization"]),
         methods=app.config.get('CORS_METHODS', ["GET", "POST", "PUT", "DELETE", "OPTIONS"]))

    # Middleware for authentication and role checking
    from .auth_middleware import setup_auth_middleware
    setup_auth_middleware(app)

    # Register API namespaces
    from .routes.auth_routes import auth_ns
    from .routes.product_routes import product_ns
    from .routes.pet_routes import pet_ns
    from .routes.appointment_routes import appointment_ns
    from .routes.category_routes import category_ns
    from .routes.vet_routes import vet_ns
    from .routes.order_routes import order_ns
    from .routes.chat_routes import chat_ns
    from .routes.dashboard_routes import dashboard_ns
    from .routes.users_routes import users_ns
    from .routes.role_routes import role_ns

    # Add namespaces to the API
    api.add_namespace(auth_ns)
    api.add_namespace(product_ns)
    api.add_namespace(pet_ns)
    api.add_namespace(appointment_ns)
    api.add_namespace(category_ns)
    api.add_namespace(vet_ns)
    api.add_namespace(order_ns)
    api.add_namespace(chat_ns)
    api.add_namespace(dashboard_ns)
    api.add_namespace(users_ns)
    api.add_namespace(role_ns)

    # Error handler
    @app.errorhandler(403)
    def forbidden(error):
        return jsonify({
            'message': 'Недостаточно прав для выполнения этой операции',
            'error': str(error)
        }), 403

    with app.app_context():
        db.create_all()  # Create all tables

    return app
