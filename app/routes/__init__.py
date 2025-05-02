# app/routes/__init__.py
from .auth_routes import bp as auth_bp
from .product_routes import bp as product_bp
from .pet_routes import bp as pet_bp
from .appointment_routes import bp as appointment_bp
from .category_routes import bp as category_bp # Import category blueprint
from .vet_routes import bp as vet_bp # Import vet blueprint
from .order_routes import bp as order_bp # Import order blueprint
from .chat_routes import bp as chat_bp # Import chat blueprint


def register_routes(app):
    app.register_blueprint(auth_bp)
    app.register_blueprint(product_bp)
    app.register_blueprint(pet_bp)
    app.register_blueprint(appointment_bp)
    app.register_blueprint(category_bp) # Register category blueprint
    app.register_blueprint(vet_bp) # Register vet blueprint
    app.register_blueprint(order_bp) # Register order blueprint
    app.register_blueprint(chat_bp) # Register chat blueprint
