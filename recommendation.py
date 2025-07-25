import pandas as pd
from sklearn.neighbors import NearestNeighbors
from collections import defaultdict
from datetime import datetime

from models import db, Order, Item, User, OrderItem, Menu


def get_today_menu_item_ids():
    """Return set of item IDs available in today's menu."""
    today = datetime.now().strftime('%A').lower()
    menu_items = db.session.query(Menu.item_id).filter(Menu.day == today).all()
    return set(item_id for (item_id,) in menu_items)


def build_user_item_matrix():
    """Build user-item matrix from order history"""
    orders = db.session.query(Order).all()
    data = []
    for order in orders:
        user_id = order.user_id
        for oi in order.items:
            data.append({
                'user_id': user_id,
                'item_id': oi.item_id,
                'quantity': oi.quantity
            })
    df = pd.DataFrame(data)
    if df.empty:
        return None, None
    user_item_matrix = pd.pivot_table(
        df,
        index='user_id',
        columns='item_id',
        values='quantity',
        aggfunc='sum',
        fill_value=0
    )
    return user_item_matrix, df


def train_knn(user_item_matrix, n_neighbors=3):
    """Train KNN model on user-item matrix"""
    if user_item_matrix is None or user_item_matrix.empty:
        return None, 0

    n_samples = user_item_matrix.shape[0]
    k = min(n_neighbors, n_samples - 1)

    if k <= 0:
        return None, 0

    model = NearestNeighbors(metric='cosine', algorithm='brute')
    model.fit(user_item_matrix.values)
    return model, k


def recommend_items_for_user_with_explanations(user_id, user_item_matrix, model, n_neighbors=3, top_n=5):
    """Get recommended items for a specific user WITH explanations (menu-filtered)"""
    if user_item_matrix is None or user_id not in user_item_matrix.index or model is None:
        return []

    menu_item_ids = get_today_menu_item_ids()
    if not menu_item_ids:
        return []

    user_vector = user_item_matrix.loc[user_id].values.reshape(1, -1)
    n_samples = user_item_matrix.shape[0]
    k = min(n_neighbors, n_samples - 1)

    if k <= 0:
        return []

    distances, indices = model.kneighbors(user_vector, n_neighbors=k + 1)
    similar_user_indices = indices.flatten()[1:]  # Skip first index (the user themselves)
    similar_user_ids = user_item_matrix.index[similar_user_indices].tolist()

    if not similar_user_ids:
        return []

    similar_users = User.query.filter(User.id.in_(similar_user_ids)).all()
    similar_users_map = {}
    for user in similar_users:
        if hasattr(user, 'name'):
            user_name = user.name
        elif hasattr(user, 'username'):
            user_name = user.username
        elif hasattr(user, 'email'):
            user_name = user.email.split('@')[0]
        elif hasattr(user, 'first_name') and hasattr(user, 'last_name'):
            user_name = f"{user.first_name} {user.last_name}"
        elif hasattr(user, 'first_name'):
            user_name = user.first_name
        else:
            user_name = f"User {user.id}"
        similar_users_map[user.id] = user_name

    neighbors_matrix = user_item_matrix.loc[similar_user_ids]
    summed_vector = neighbors_matrix.sum(axis=0)
    user_items = user_item_matrix.loc[user_id]
    unseen_items = summed_vector[user_items == 0]

    if unseen_items.empty:
        return []

    recommended_items = unseen_items.sort_values(ascending=False).head(top_n * 2)

    recommendations = []
    for item_id, popularity_score in recommended_items.items():
        if item_id not in menu_item_ids:
            continue

        item = Item.query.get(item_id)
        if not item:
            continue

        users_who_ordered = []
        for similar_user_id in similar_user_ids:
            if user_item_matrix.loc[similar_user_id, item_id] > 0:
                quantity = int(user_item_matrix.loc[similar_user_id, item_id])
                user_name = similar_users_map.get(similar_user_id, f"User {similar_user_id}")
                users_who_ordered.append({
                    'name': user_name,
                    'quantity': quantity
                })

        explanation = generate_explanation(users_who_ordered, item.name)

        recommendations.append({
            'item': item,
            'explanation': explanation,
            'explanation_type': 'collaborative',
            'popularity_score': int(popularity_score),
            'similar_users': users_who_ordered
        })

        if len(recommendations) >= top_n:
            break

    return recommendations


def get_fallback_recommendations_with_explanations(top_n=5):
    """Get fallback recommendations with explanations (menu-filtered)"""
    menu_item_ids = get_today_menu_item_ids()
    if not menu_item_ids:
        return []

    try:
        from sqlalchemy import func
        popular_items_query = db.session.query(
            Item,
            func.count(OrderItem.id).label('order_count')
        ).join(OrderItem, Item.id == OrderItem.item_id)\
         .group_by(Item.id)\
         .order_by(func.count(OrderItem.id).desc())\
         .limit(top_n * 2).all()

        recommendations = []
        for item, order_count in popular_items_query:
            if item.id not in menu_item_ids:
                continue
            explanation = f"Popular choice - ordered {order_count} times by other customers"
            recommendations.append({
                'item': item,
                'explanation': explanation,
                'explanation_type': 'popular',
                'order_count': order_count
            })

            if len(recommendations) >= top_n:
                return recommendations

    except Exception:
        pass

    # Fallback to newest menu items
    fallback_items = Item.query.filter(Item.id.in_(menu_item_ids))\
                               .order_by(Item.id.desc())\
                               .limit(top_n).all()
    recommendations = []
    for item in fallback_items:
        recommendations.append({
            'item': item,
            'explanation': "New item - try something fresh!",
            'explanation_type': 'new'
        })

    return recommendations


def generate_explanation(users_who_ordered, item_name):
    """Generate human-readable explanation for why an item is recommended"""
    if not users_who_ordered:
        return f"Recommended based on your preferences"

    named_users = [user for user in users_who_ordered if not user['name'].startswith('User ')]

    if len(named_users) == 0:
        if len(users_who_ordered) == 1:
            return f"Recommended because a customer with similar taste ordered this"
        else:
            return f"Recommended because {len(users_who_ordered)} customers with similar taste ordered this"

    elif len(named_users) == 1:
        user = named_users[0]
        if user['quantity'] > 1:
            return f"Recommended because a customer (similar to you) ordered this {user['quantity']} times"
        else:
            return f"Recommended because a customer (similar to you) also ordered this"

    elif len(named_users) == 2:
        return f"Recommended because some users (similar to you) also ordered this"

    else:
        total_users = len(users_who_ordered)
        if total_users == len(named_users):
            return f"Recommended because {total_users} customers with similar taste also ordered this"
        else:
            return f"Recommended because {named_users[0]['name']}, {named_users[1]['name']} and {total_users - 2} other customers with similar taste ordered this"


def get_user_order_history_explanation(user_id, limit=3):
    """Get explanation based on user's own order history"""
    user_orders = db.session.query(Order).filter(Order.user_id == user_id).all()

    if not user_orders:
        return "Based on popular items (no order history yet)"

    item_counts = defaultdict(int)
    for order in user_orders:
        for order_item in order.items:
            item_counts[order_item.item_id] += order_item.quantity

    top_items = sorted(item_counts.items(), key=lambda x: x[1], reverse=True)[:limit]

    if not top_items:
        return "Based on your preferences"

    top_item_names = []
    for item_id, count in top_items:
        item = Item.query.get(item_id)
        if item:
            top_item_names.append(item.name)

    if len(top_item_names) == 1:
        return f"Based on your love for {top_item_names[0]}"
    elif len(top_item_names) == 2:
        return f"Based on your preferences for {top_item_names[0]} and {top_item_names[1]}"
    else:
        return f"Based on your preferences for {', '.join(top_item_names[:-1])}, and {top_item_names[-1]}"
