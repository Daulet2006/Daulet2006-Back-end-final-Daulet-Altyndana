from . import db
from datetime import datetime
import enum

# Enum for User Roles
class Role(enum.Enum):
    CLIENT = 'CLIENT'
    SELLER = 'SELLER'
    ADMIN = 'ADMIN'
    OWNER = 'OWNER'



class PetStatus(enum.Enum):
    AVAILABLE = 'AVAILABLE'
    RESERVED = 'RESERVED'
    SOLD = 'SOLD'
# Association table for Orders and Products (M:N)
order_product = db.Table('order_product',
    db.Column('order_id', db.Integer, db.ForeignKey('order.id'), primary_key=True),
    db.Column('product_id', db.Integer, db.ForeignKey('product.id'), primary_key=True),
    db.Column('quantity', db.Integer, nullable=False, default=1)
)

# Association table for Orders and Pets (M:N)
order_pet = db.Table('order_pet',
    db.Column('order_id', db.Integer, db.ForeignKey('order.id'), primary_key=True),
    db.Column('pet_id', db.Integer, db.ForeignKey('pet.id'), primary_key=True)
)

class User(db.Model):
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String(80), unique=False, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    role = db.Column(db.Enum(Role), nullable=False, default=Role.CLIENT.value)
    isBanned = db.Column(db.Boolean, nullable=False, default=False)
    orders = db.relationship('Order', backref='client', lazy=True, foreign_keys='Order.client_id')
    products_for_sale = db.relationship('Product', backref='seller', lazy=True, foreign_keys='Product.seller_id')
    pets_for_sale = db.relationship('Pet', backref='seller', lazy=True, foreign_keys='Pet.seller_id')
    owned_products = db.relationship('Product', foreign_keys='Product.owner_id', backref='owner', lazy=True)
    owned_pets = db.relationship('Pet', foreign_keys='Pet.owner_id', backref='owner', lazy=True)

    def __repr__(self):
        return f'<User {self.username} ({self.role})>'

class Category(db.Model):
    __tablename__ = 'category'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    description = db.Column(db.String(300))
    products = db.relationship('Product', backref='category', lazy=True)
    pets = db.relationship('Pet', backref='category', lazy=True)

    def __repr__(self):
        return f'<Category {self.name}>'

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'products': [
                {'id': p.id, 'name': p.name, 'price': float(p.price)}
                for p in self.products
            ],
            'pets': [
                {'id': p.id, 'name': p.name, 'species': p.species}
                for p in self.pets
            ]
        }

class Product(db.Model):
    __tablename__ = 'product'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(300))
    price = db.Column(db.Float, nullable=False)
    stock = db.Column(db.Integer, nullable=False)
    image_url = db.Column(db.String(255))
    seller_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('category.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    owner_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)

    def __repr__(self):
        return f'<Product {self.name}>'

class Pet(db.Model):
    __tablename__ = 'pet'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    species = db.Column(db.String(50), nullable=False)
    breed = db.Column(db.String(50))
    age = db.Column(db.Integer, nullable=False)
    price = db.Column(db.Float, nullable=False)
    description = db.Column(db.String(300))
    image_url = db.Column(db.String(255))
    seller_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('category.id'), nullable=True)
    status = db.Column(db.Enum(PetStatus), nullable=False, default=PetStatus.AVAILABLE.value)  # Обновлено
    owner_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    orders = db.relationship('Order', secondary=order_pet, back_populates='pets')

    def __repr__(self):
        return f'<Pet {self.name} ({self.species})>'

class Order(db.Model):
    __tablename__ = 'order'
    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    order_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    total_amount = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(50), default='Pending')
    products = db.relationship('Product', secondary=order_product, lazy='subquery', backref=db.backref('orders', lazy=True))
    pets = db.relationship('Pet', secondary=order_pet, lazy='subquery', back_populates='orders')

    def __repr__(self):
        return f'<Order {self.id} by User {self.client_id}>'

class ChatMessage(db.Model):
    __tablename__ = 'chat_message'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    message = db.Column(db.Text, nullable=False)
    reply = db.Column(db.Text, nullable=True)
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    file_path = db.Column(db.String(255), nullable=True)
    file_name = db.Column(db.String(255), nullable=True)
    file_type = db.Column(db.String(100), nullable=True)
    user = db.relationship('User', backref=db.backref('chat_messages', lazy=True))

    def __repr__(self):
        return f'<ChatMessage {self.id} from User {self.user_id}>'
