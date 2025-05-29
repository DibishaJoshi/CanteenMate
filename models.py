from flask_sqlalchemy import SQLAlchemy

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
        return f"<Attribute {self.name}>"

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
        return f"<AttributeValue {self.value_name}>"
