# 🐾 Zoo Store Backend

[![Python](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/flask-2.x-green)](https://flask.palletsprojects.com/)
[![PostgreSQL](https://img.shields.io/badge/postgresql-14%2B-blue)](https://www.postgresql.org/)
[![License](https://img.shields.io/badge/license-MIT-lightgrey)](#license)

Welcome to the backend of the Zoo Store project! This is a robust RESTful API built with Flask, SQLAlchemy, Flask-RESTx, JWT authentication, and PostgreSQL. It powers a modern pet and product marketplace, supporting user management, e-commerce, chat, and more.

---

## 📚 Features
- User registration, authentication, and role management (Client, Seller, Admin, Owner)
- Product and pet management (CRUD, image upload)
- Order processing for products and pets
- Category management
- Chat messaging between users
- JWT-based authentication and authorization
- Role-based access control
- File uploads for product and pet images
- API documentation via Swagger (Flask-RESTx)

## 📁 Project Structure

```text
BackEnd_ZooStore/
├── app/
│   ├── app.py           # Flask app factory and API setup
│   ├── config.py        # Configuration (DB, JWT, CORS, uploads)
│   ├── models/          # SQLAlchemy models (User, Product, Pet, Order, Category, etc.)
│   ├── routes/          # API endpoints (auth, products, pets, orders, categories, etc.)
│   └── utils/           # Utility functions and middleware
├── migrations/          # Alembic migrations for database schema
├── run.py               # Entry point to run the Flask app
├── static/uploads/      # Uploaded images and files
└── README.md            # Project documentation
```

## 📝 Getting Started

### 1. Clone the repository
```bash
git clone https://github.com/Daulet2006/Daulet2006-Back-end-final-Daulet-Altyndana
cd BackEnd_ZooStore
```

### 2. Create and activate a virtual environment
```bash
python -m venv .venv
# On Unix/macOS:
source .venv/bin/activate
# On Windows:
.venv\Scripts\activate
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure environment variables
Create a `.env` file in the `app/` directory:
```env
DATABASE_URL=postgresql://postgres:yourpassword@localhost:5432/pet_store
SECRET_KEY=your-secret-key
JWT_SECRET_KEY=your-jwt-secret
```

### 5. Run database migrations
```bash
flask db upgrade
```

### 6. Start the backend server
```bash
python run.py
```

- The API will be available at [http://localhost:5000/](http://localhost:5000/)
- Swagger API docs: [http://localhost:5000/docs](http://localhost:5000/docs)

## 📝 API Overview

Most endpoints require JWT authentication. See Swagger docs for full details and try-it-out functionality.

### Authentication
- `POST /auth/register` — Register a new user
- `POST /auth/login` — Login and receive JWT
- `POST /auth/logout` — Logout (JWT revoke)
- `GET /auth/roles` — List available user roles

### Products
- `GET /products` — List all products
- `POST /products` — Add a new product (Seller/Admin)
- `PUT /products/<id>` — Update product info
- `DELETE /products/<id>` — Remove a product
- `POST /products/upload` — Upload product image

### Pets
- `GET /pets` — List all pets
- `POST /pets` — Add a new pet (Seller/Admin)
- `PUT /pets/<id>` — Update pet info
- `DELETE /pets/<id>` — Remove a pet
- `POST /pets/upload` — Upload pet image
- `PATCH /pets/<id>/status` — Update pet status (AVAILABLE, RESERVED, SOLD)

### Orders
- `GET /orders` — List all orders (Admin/Owner)
- `POST /orders` — Create a new order
- `PUT /orders/<id>` — Update order status
- `DELETE /orders/<id>` — Cancel an order

### Categories
- `GET /categories` — List categories
- `POST /categories` — Create a new category (Admin/Owner)

### Chat
- `GET /chat` — Retrieve chat messages
- `POST /chat` — Send a chat message

---

## 📝 Database Models (ERD)

- **User**: Handles authentication, roles (Client, Seller, Admin, Owner), and relationships to products, pets, and orders.
- **Product**: Store items for sale, linked to categories and sellers.
- **Pet**: Animals for sale/adoption, with status (AVAILABLE, RESERVED, SOLD) and owner tracking.
- **Order**: Purchases of products and pets, with many-to-many relationships.
- **Category**: Product and pet categorization.
- **ChatMessage**: User-to-user messaging with optional file attachments.

> **Tip:** See `app/models/` for full SQLAlchemy model definitions.

## 📃 Migrations
Database migrations are managed with Alembic. See [`migrations/README`](migrations/README) for details.

## 📝 Usage Example

### Register a new user
```bash
curl -X POST http://localhost:5000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username": "alice", "email": "alice@example.com", "password": "password123"}'
```

### Login and get JWT
```bash
curl -X POST http://localhost:5000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "alice@example.com", "password": "password123"}'
```

### Access protected endpoint
```bash
curl -H "Authorization: Bearer <your-jwt-token>" http://localhost:5000/products
```

## 📝 Notes
- This README describes only the backend. The frontend is located in `templates/zoo-store/` and is not covered here.
- Ensure PostgreSQL is running and accessible with the credentials in your `.env` file.
- Uploaded files are stored in `static/uploads/`.
- API documentation is available at `/docs` after starting the server.
- For development, set `debug=True` in `run.py`.

## 📚 License
Specify your license here. (e.g., [MIT](https://choosealicense.com/licenses/mit/))
