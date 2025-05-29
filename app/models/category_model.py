from app import db

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
