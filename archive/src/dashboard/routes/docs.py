"""Documentation routes for the dashboard."""

from flask import Blueprint, render_template, jsonify, request, send_file
from ...core.docs.docs import DocsSystem

docs_bp = Blueprint('docs', __name__)

def get_docs_system():
    """Get docs system from app context."""
    from flask import current_app
    return current_app.docs_system

@docs_bp.route('/api/docs/endpoints')
def get_api_endpoints():
    """Get API endpoint documentation."""
    try:
        docs = get_docs_system()
        endpoints = docs.get_api_endpoints()
        return jsonify({
            'status': 'success',
            'data': endpoints
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@docs_bp.route('/api/docs/schemas')
def get_api_schemas():
    """Get API schema documentation."""
    try:
        docs = get_docs_system()
        schemas = docs.get_api_schemas()
        return jsonify({
            'status': 'success',
            'data': schemas
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@docs_bp.route('/api/docs/guides')
def get_api_guides():
    """Get API guides and tutorials."""
    try:
        docs = get_docs_system()
        guides = docs.get_api_guides()
        return jsonify({
            'status': 'success',
            'data': guides
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@docs_bp.route('/api/docs/examples')
def get_api_examples():
    """Get API usage examples."""
    try:
        docs = get_docs_system()
        examples = docs.get_api_examples()
        return jsonify({
            'status': 'success',
            'data': examples
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500
