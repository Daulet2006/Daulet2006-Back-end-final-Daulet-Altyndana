# app/routes/category_routes.py
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from ..models import Category, Role
from .. import db
from ..utils import role_required

bp = Blueprint('categories', __name__, url_prefix='/categories')

# Helper function to format category data
def format_category(category):
    return {
        'id': category.id,
        'name': category.name,
        'description': category.description
    }

# Get all categories (Public)
@bp.route('', methods=['GET'])
def get_categories():
    try:
        categories = Category.query.all()
        return jsonify([format_category(cat) for cat in categories]), 200
    except Exception as e:
        return jsonify({'message': 'Failed to retrieve categories', 'error': str(e)}), 500

# Get single category (Public)
@bp.route('/<int:category_id>', methods=['GET'])
def get_category(category_id):
    try:
        category = Category.query.get_or_404(category_id)
        return jsonify(format_category(category)), 200
    except Exception as e:
        # Flask handles 404 from get_or_404
        return jsonify({'message': 'Failed to retrieve category', 'error': str(e)}), 500

# Create category (Admin/Owner only)
@bp.route('', methods=['POST'])
@jwt_required()
@role_required(Role.ADMIN, Role.OWNER)
def create_category():
    data = request.get_json()
    if not data or 'name' not in data:
        return jsonify({'message': 'Missing required field: name'}), 400

    if Category.query.filter_by(name=data['name']).first():
        return jsonify({'message': f"Category with name '{data['name']}' already exists"}), 409 # Conflict

    try:
        new_category = Category(
            name=data['name'],
            description=data.get('description')
        )
        db.session.add(new_category)
        db.session.commit()
        return jsonify({'message': 'Category created successfully', 'category': format_category(new_category)}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': 'Failed to create category', 'error': str(e)}), 500

# Update category (Admin/Owner only)
@bp.route('/<int:category_id>', methods=['PUT', 'PATCH'])
@jwt_required()
@role_required(Role.ADMIN, Role.OWNER)
def update_category(category_id):
    try:
        category = Category.query.get_or_404(category_id)
        data = request.get_json()

        if not data:
            return jsonify({'message': 'No data provided for update'}), 400

        # Check for name conflict if name is being changed
        if 'name' in data and data['name'] != category.name:
            if Category.query.filter(Category.id != category_id, Category.name == data['name']).first():
                return jsonify({'message': f"Category with name '{data['name']}' already exists"}), 409
            category.name = data['name']

        if 'description' in data:
            category.description = data['description']

        db.session.commit()
        return jsonify({'message': 'Category updated successfully', 'category': format_category(category)}), 200
    except Exception as e:
        db.session.rollback()
        # Flask handles 404 from get_or_404
        return jsonify({'message': 'Failed to update category', 'error': str(e)}), 500

# Delete category (Admin/Owner only)
@bp.route('/<int:category_id>', methods=['DELETE'])
@jwt_required()
@role_required(Role.ADMIN, Role.OWNER)
def delete_category(category_id):
    try:
        category = Category.query.get_or_404(category_id)

        # Optional: Check if category is in use by products before deleting
        if category.products:
             return jsonify({'message': 'Cannot delete category: It is associated with existing products.'}), 400

        db.session.delete(category)
        db.session.commit()
        return jsonify({'message': 'Category deleted successfully'}), 200
    except Exception as e:
        db.session.rollback()
        # Flask handles 404 from get_or_404
        return jsonify({'message': 'Failed to delete category', 'error': str(e)}), 500