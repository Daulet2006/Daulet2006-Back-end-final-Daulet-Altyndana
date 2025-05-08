from flask_restx import Namespace, Resource
from flask import jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from .. import db
from ..models import Order, Product, Pet, User, Role
from ..utils import role_required
from sqlalchemy import func, text
from datetime import datetime, timedelta

dashboard_ns = Namespace('dashboard', description='Operations related to dashboard statistics')

@dashboard_ns.route('/stats')
class DashboardStats(Resource):
    @jwt_required()
    @role_required(Role.ADMIN, Role.OWNER)
    def get(self):
        """Get dashboard statistics for admin/owner"""
        try:
            total_orders = Order.query.count()
            total_products = Product.query.count()
            total_pets = Pet.query.count()
            total_users = User.query.count()
            
            pending_orders = Order.query.filter_by(status='Pending').count()
            completed_orders = Order.query.filter_by(status='Completed').count()
            cancelled_orders = Order.query.filter_by(status='Cancelled').count()
            
            week_ago = datetime.utcnow() - timedelta(days=7)
            recent_orders = Order.query.filter(Order.order_date >= week_ago).count()
            
            users_by_role = {role.value: User.query.filter_by(role=role).count() for role in Role}
            
            total_revenue = db.session.query(func.sum(Order.total_amount)).filter_by(status='Completed').scalar() or 0
            
            return {
                'total_orders': total_orders,
                'total_products': total_products,
                'total_pets': total_pets,
                'total_users': total_users,
                'orders_by_status': {
                    'pending': pending_orders,
                    'completed': completed_orders,
                    'cancelled': cancelled_orders
                },
                'recent_orders': recent_orders,
                'users_by_role': users_by_role,
                'total_revenue': float(total_revenue)
            }, 200
        except Exception as e:
            return {'message': 'Failed to retrieve dashboard statistics', 'error': str(e)}, 500

@dashboard_ns.route('/recent-orders')
class RecentOrders(Resource):
    @jwt_required()
    @role_required(Role.ADMIN, Role.OWNER, Role.SELLER)
    def get(self):
        """Get recent orders for dashboard"""
        try:
            current_user_identity = get_jwt_identity()
            current_user_id = current_user_identity['id']
            current_user_role = Role(current_user_identity['role'])
            
            thirty_days_ago = datetime.utcnow() - timedelta(days=30)
            query = Order.query.filter(Order.order_date >= thirty_days_ago)
            
            if current_user_role == Role.SELLER:
                seller_products = Product.query.filter_by(seller_id=current_user_id).all()
                product_ids = [product.id for product in seller_products]
                if product_ids:
                    order_ids = db.session.query(text('order_id')).select_from(text('order_product')).filter(
                        text('product_id').in_(product_ids)).distinct().all()
                    order_ids = [id[0] for id in order_ids]
                    query = query.filter(Order.id.in_(order_ids))
                else:
                    return [], 200
            
            recent_orders = query.order_by(Order.order_date.desc()).limit(10).all()
            
            formatted_orders = []
            for order in recent_orders:
                client = User.query.get(order.client_id)
                formatted_orders.append({
                    'id': order.id,
                    'client_name': client.username if client else 'Unknown',
                    'order_date': order.order_date.isoformat(),
                    'total_amount': order.total_amount,
                    'status': order.status
                })
            
            return formatted_orders, 200
        except Exception as e:
            return {'message': 'Failed to retrieve recent orders', 'error': str(e)}, 500