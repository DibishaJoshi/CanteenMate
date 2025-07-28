from flask_sqlalchemy import SQLAlchemy
from datetime import datetime,date

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
    role = db.Column(db.String(20), nullable=False)  
    phone = db.Column(db.String(10))
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

addon_item_association = db.Table('addon_item_association',
    db.Column('addon_id', db.Integer, db.ForeignKey('addons.id'), primary_key=True),
    db.Column('item_id', db.Integer, db.ForeignKey('items.id'), primary_key=True)
)

class Item(db.Model):
    __tablename__ = 'items'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    price = db.Column(db.Float, nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'), nullable=False)

    description = db.Column(db.Text, nullable=True)
    image_filename = db.Column(db.String(255), nullable=True)
    available = db.Column(db.Boolean, default=True)

    attribute_values = db.relationship(
        'AttributeValue',
        secondary=item_attribute_values,
        back_populates='items'
    )

    addons = db.relationship(
        'Addon',
        secondary=addon_item_association,
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



class Addon(db.Model):
    __tablename__ = 'addons'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    price = db.Column(db.Float, nullable=False)
    category = db.Column(db.String(50), nullable=False)
    description = db.Column(db.Text)
    status = db.Column(db.Boolean, default=True)

    items = db.relationship('Item', secondary='addon_item_association', back_populates='addons')

    def __repr__(self):
        return f"<Addon {self.name}>"

    def applied_items_count(self):
        return len(self.items)
    
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

class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    contact = db.Column(db.String(20), nullable=False)
    email = db.Column(db.String(100), nullable=False)
    delivery = db.Column(db.String(20), nullable=False)
    building = db.Column(db.String(100))
    floor = db.Column(db.String(100))
    payment = db.Column(db.String(20), nullable=False)
    status = db.Column(db.String(20), nullable=False, default='Pending')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    total_amount = db.Column(db.Float, nullable=False)  
    khalti_token = db.Column(db.String(255), nullable=True)

    items = db.relationship('OrderItem', backref='order', lazy=True)

    @property
    def delivery_address(self):
        parts = [self.building, self.floor]
        return ', '.join([p for p in parts if p]) or "N/A"
    @property
    def total_price(self):
        return sum(item.quantity * item.price for item in self.items)


class OrderItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('order.id'), nullable=False)
    item_id = db.Column(db.Integer, db.ForeignKey('items.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    price = db.Column(db.Float, nullable=False)
    item = db.relationship('Item', backref='order_items')
    @property
    def quantity_price(self):
        return self.quantity * self.price
    
class OrderAddon(db.Model):
    __tablename__ = 'order_addons'
    
    id = db.Column(db.Integer, primary_key=True)
    order_item_id = db.Column(db.Integer, db.ForeignKey('order_item.id'), nullable=False)
    addon_id = db.Column(db.Integer, db.ForeignKey('addons.id'), nullable=False)
    name = db.Column(db.String(255), nullable=False)
    price = db.Column(db.Numeric(10, 2), nullable=False)
    category = db.Column(db.String(100))
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    order_item = db.relationship('OrderItem', backref='order_addons')
    addon = db.relationship('Addon', backref='order_addons')
class CartItem(db.Model):
    __tablename__ = 'cart_items'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    item_id = db.Column(db.Integer, db.ForeignKey('items.id'), nullable=False)
    quantity = db.Column(db.Integer, default=1)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_date = db.Column(db.Date, default=date.today)

    user = db.relationship("User", backref="cart_items")
    item = db.relationship("Item", backref="in_carts")    

class Review(db.Model):
    __tablename__ = 'reviews'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    order_id = db.Column(db.Integer, db.ForeignKey('order.id'), nullable=False)
    item_id = db.Column(db.Integer, db.ForeignKey('items.id'), nullable=False)
    rating = db.Column(db.Integer, nullable=False)  # 1-5 stars
    comment = db.Column(db.Text)
    service_rating = db.Column(db.Integer)  # Optional: 1-5 stars for service
    delivery_rating = db.Column(db.Integer)  # Optional: 1-5 stars for delivery
    would_recommend = db.Column(db.Boolean, default=True)
    is_verified = db.Column(db.Boolean, default=True)  # Verified purchase
    helpful_count = db.Column(db.Integer, default=0)  # How many found it helpful
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = db.relationship('User', backref=db.backref('reviews', lazy=True))
    order = db.relationship('Order', backref=db.backref('reviews', lazy=True))
    item = db.relationship('Item', backref=db.backref('reviews', lazy=True))
    
    def __repr__(self):
        return f'<Review {self.id}: {self.rating} stars for Item {self.item_id}>'
    
    @property
    def average_overall_rating(self):
        """Calculate average of food, service, and delivery ratings"""
        ratings = [self.rating]
        if self.service_rating:
            ratings.append(self.service_rating)
        if self.delivery_rating:
            ratings.append(self.delivery_rating)
        return sum(ratings) / len(ratings) if ratings else 0

class ReviewHelpful(db.Model):
    __tablename__ = 'review_helpful'
    
    id = db.Column(db.Integer, primary_key=True)
    review_id = db.Column(db.Integer, db.ForeignKey('reviews.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    is_helpful = db.Column(db.Boolean, default=True)  # True for helpful, False for not helpful
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    review = db.relationship('Review', backref=db.backref('helpful_votes', lazy=True))
    user = db.relationship('User', backref=db.backref('review_votes', lazy=True))
    
    # Ensure one vote per user per review
    __table_args__ = (db.UniqueConstraint('review_id', 'user_id', name='unique_review_vote'),)
