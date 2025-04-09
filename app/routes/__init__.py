# routes/__init__.py
from .auth_routes import bp as auth_bp
from .product_routes import bp as product_bp
from .pet_routes import bp as pet_bp
from .appointment_routes import bp as appointment_bp

def register_routes(app):
    app.register_blueprint(auth_bp)
    app.register_blueprint(product_bp)
    app.register_blueprint(pet_bp)
    app.register_blueprint(appointment_bp)
