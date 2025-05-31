from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()
item_attribute_values = db.Table('item_attribute_values',
    db.Column('item_id', db.Integer, db.ForeignKey('items.id'), primary_key=True),
    db.Column('attribute_value_id', db.Integer, db.ForeignKey('attribute_values.id'), primary_key=True)
)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    fullname = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # 'student', 'staff', or 'admin'
    created_at = db.Column(db.DateTime, server_default=db.func.now())
    def __repr__(self):
        return f"<User {self.email}>"


class Category(db.Model):
    __tablename__ = 'categories'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    status = db.Column(db.Boolean, default=True)  # Active or Inactive

    items = db.relationship('Item', backref='category', lazy=True, cascade='all, delete-orphan')

    def __repr__(self):
        return f"<Category {self.name}>"

    def items_count(self):
        return len(self.items)

class Item(db.Model):
    __tablename__ = 'items'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    price = db.Column(db.Integer, nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'), nullable=False)

    description = db.Column(db.Text, nullable=True)
    image_filename = db.Column(db.String(255), nullable=True)
    available = db.Column(db.Boolean, default=True)

    attribute_values = db.relationship(
        'AttributeValue',
        secondary='item_attribute_values',
        back_populates='items'
    )
    
    def __repr__(self):
        return f"<Item {self.name}>"


# Attribute model
class Attribute(db.Model):
    __tablename__ = 'attributes'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    status = db.Column(db.Boolean, default=True)

    values = db.relationship('AttributeValue', backref='attribute', cascade='all, delete-orphan')

    def __repr__(self):
        return self.name

# AttributeValue model
class AttributeValue(db.Model):
    __tablename__ = 'attribute_values'

    id = db.Column(db.Integer, primary_key=True)
    value = db.Column(db.String(100), nullable=False)
    price_adjustment = db.Column(db.Float, default=0.0)
    attribute_id = db.Column(db.Integer, db.ForeignKey('attributes.id'), nullable=False)

    items = db.relationship(
        'Item',
        secondary='item_attribute_values',
        back_populates='attribute_values'
    )

    def __repr__(self):
        return f"<AttributeValue {self.value}>"

class Menu(db.Model):
    __tablename__ = 'menus'
    id = db.Column(db.Integer, primary_key=True)
    day = db.Column(db.String(20), nullable=False)  # monday, tuesday, etc.
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'), nullable=False)
    item_id = db.Column(db.Integer, db.ForeignKey('items.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    category = db.relationship('Category', backref='menu_items')
    item = db.relationship('Item', backref='menu_assignments')

    __table_args__ = (
        db.UniqueConstraint('day', 'category_id', 'item_id', name='unique_menu_item'),
    )

