import os

class Config:
    # Database configuration
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL', 'postgresql://postgres:qazaq001@localhost:5432/pet_store')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SECRET_KEY = os.environ.get('SECRET_KEY', 'your-secret-key')
    # JWT configuration
    JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', 'super-secret')
    # CORS configuration
    CORS_ORIGINS = '*'
    CORS_SUPPORTS_CREDENTIALS = True
    CORS_ALLOW_HEADERS = ["Content-Type", "Authorization"]
    CORS_METHODS = ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
    UPLOAD_FOLDER = os.path.join('../static', 'uploads')
