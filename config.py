# config.py
import os
class Config:
    # Конфигурация для подключения к базе данных
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL', 'postgresql://postgres:qazaq001@localhost:5432/pet_store')
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Конфигурация для JWT
    JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', 'super-secret')

    # CORS настройка
    CORS_ORIGINS = '*'
    CORS_SUPPORTS_CREDENTIALS = True
    CORS_ALLOW_HEADERS = ["Content-Type", "Authorization"]
    CORS_METHODS = ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
