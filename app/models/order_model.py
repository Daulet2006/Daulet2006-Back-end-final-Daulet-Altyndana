from datetime import datetime
from app import db
from app.models.relationship_model import order_product, order_pet

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
