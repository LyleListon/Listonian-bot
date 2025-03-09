"""Template routes for the dashboard."""

from flask import Blueprint, render_template, jsonify, request
from ...core.reporting.templates import TemplateSystem

templates_bp = Blueprint('templates', __name__)

def get_template_system():
    """Get template system from app context."""
    from flask import current_app
    return current_app.template_system

@templates_bp.route('/api/templates/list')
def list_templates():
    """List available report templates."""
    try:
        template_system = get_template_system()
        templates = template_system.list_templates()
        return jsonify({
            'status': 'success',
            'data': templates
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@templates_bp.route('/api/templates/create', methods=['POST'])
def create_template():
    """Create a new report template."""
    try:
        template_system = get_template_system()
        template_data = request.get_json()
        template = template_system.create_template(template_data)
        return jsonify({
            'status': 'success',
            'data': template
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@templates_bp.route('/api/templates/update/<template_id>', methods=['POST'])
def update_template(template_id):
    """Update an existing template."""
    try:
        template_system = get_template_system()
        update_data = request.get_json()
        template = template_system.update_template(template_id, update_data)
        return jsonify({
            'status': 'success',
            'data': template
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@templates_bp.route('/api/templates/delete/<template_id>', methods=['DELETE'])
def delete_template(template_id):
    """Delete a template."""
    try:
        template_system = get_template_system()
        template_system.delete_template(template_id)
        return jsonify({
            'status': 'success',
            'data': {'template_id': template_id}
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500
