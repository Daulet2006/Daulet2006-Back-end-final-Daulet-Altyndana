from flask_restx import Namespace, Resource, fields
from flask import request
from flask_jwt_extended import jwt_required
from ..models import Category, Role
from .. import db
from ..utils import role_required

category_ns = Namespace('categories', description='Operations related to product categories')

# Swagger model
category_model = category_ns.model('Category', {
    'name': fields.String(required=True, description='Category name'),
    'description': fields.String(description='Category description')
})

# Helper function
def format_category(category):
    return {
        'id': category.id,
        'name': category.name,
        'description': category.description
    }

@category_ns.route('')
class CategoryList(Resource):
    def get(self):
        """Get all categories (public)"""
        try:
            categories = Category.query.all()
            return [format_category(cat) for cat in categories], 200
        except Exception as e:
            return {'message': 'Failed to retrieve categories', 'error': str(e)}, 500

    @jwt_required()
    @role_required(Role.ADMIN, Role.OWNER)
    @category_ns.expect(category_model)
    def post(self):
        """Create a new category (Admin/Owner only)"""
        data = request.get_json()
        if not data or 'name' not in data:
            return {'message': 'Missing required field: name'}, 400

        if Category.query.filter_by(name=data['name']).first():
            return {'message': f"Category with name '{data['name']}' already exists"}, 409

        try:
            new_category = Category(
                name=data['name'],
                description=data.get('description')
            )
            db.session.add(new_category)
            db.session.commit()
            return {'message': 'Category created successfully', 'category': format_category(new_category)}, 201
        except Exception as e:
            db.session.rollback()
            return {'message': 'Failed to create category', 'error': str(e)}, 500

@category_ns.route('/<int:category_id>')
class CategoryResource(Resource):
    def get(self, category_id):
        """Get a single category (public)"""
        try:
            category = Category.query.get_or_404(category_id)
            return format_category(category), 200
        except Exception as e:
            return {'message': 'Failed to retrieve category', 'error': str(e)}, 500

    @jwt_required()
    @role_required(Role.ADMIN, Role.OWNER)
    @category_ns.expect(category_model)
    def put(self, category_id):
        """Update a category (Admin/Owner only)"""
        try:
            category = Category.query.get_or_404(category_id)
            data = request.get_json()

            if not data:
                return {'message': 'No data provided for update'}, 400

            if 'name' in data and data['name'] != category.name:
                if Category.query.filter(Category.id != category_id, Category.name == data['name']).first():
                    return {'message': f"Category with name '{data['name']}' already exists"}, 409
                category.name = data['name']

            if 'description' in data:
                category.description = data['description']

            db.session.commit()
            return {'message': 'Category updated successfully', 'category': format_category(category)}, 200
        except Exception as e:
            db.session.rollback()
            return {'message': 'Failed to update category', 'error': str(e)}, 500

    @jwt_required()
    @role_required(Role.ADMIN, Role.OWNER)
    def delete(self, category_id):
        """Delete a category (Admin/Owner only)"""
        try:
            category = Category.query.get_or_404(category_id)
            if category.products:
                return {'message': 'Cannot delete category: It is associated with existing products.'}, 400
            db.session.delete(category)
            db.session.commit()
            return {'message': 'Category deleted successfully'}, 200
        except Exception as e:
            db.session.rollback()
            return {'message': 'Failed to delete category', 'error': str(e)}, 500