import enum
from app import db

class Role(enum.Enum):
    CLIENT = 'CLIENT'
    SELLER = 'SELLER'
    ADMIN = 'ADMIN'
    OWNER = 'OWNER'

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
