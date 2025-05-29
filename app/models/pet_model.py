import enum
from app import db
from app.models.relationship_model import order_pet


class PetStatus(enum.Enum):
    AVAILABLE = 'AVAILABLE'
    RESERVED = 'RESERVED'
    SOLD = 'SOLD'

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