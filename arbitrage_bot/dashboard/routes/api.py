"""API routes for the dashboard."""

from flask import Blueprint, render_template, jsonify, request
from ...core.api.api import APISystem

api_bp = Blueprint('api', __name__)

def get_api_system():
    """Get API system from app context."""
    from flask import current_app
    return current_app.api_system

@api_bp.route('/api/keys')
def get_api_keys():
    """Get API key information."""
    try:
        api = get_api_system()
        keys = api.get_api_keys()
        return jsonify({
            'status': 'success',
            'data': keys
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@api_bp.route('/api/keys/create', methods=['POST'])
def create_api_key():
    """Create a new API key."""
    try:
        api = get_api_system()
        key_data = request.get_json()
        new_key = api.create_api_key(key_data)
        return jsonify({
            'status': 'success',
            'data': new_key
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@api_bp.route('/api/keys/revoke/<key_id>', methods=['POST'])
def revoke_api_key(key_id):
    """Revoke an API key."""
    try:
        api = get_api_system()
        api.revoke_api_key(key_id)
        return jsonify({
            'status': 'success',
            'data': {'key_id': key_id}
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@api_bp.route('/api/usage')
def get_api_usage():
    """Get API usage statistics."""
    try:
        api = get_api_system()
        usage_stats = api.get_api_usage()
        return jsonify({
            'status': 'success',
            'data': usage_stats
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500
