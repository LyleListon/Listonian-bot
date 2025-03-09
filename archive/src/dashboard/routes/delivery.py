"""Delivery routes for the dashboard."""

from flask import Blueprint, render_template, jsonify, request
from ...core.reporting.delivery import DeliverySystem

delivery_bp = Blueprint('delivery', __name__)

def get_delivery_system():
    """Get delivery system from app context."""
    from flask import current_app
    return current_app.delivery_system

@delivery_bp.route('/api/delivery/settings')
def get_delivery_settings():
    """Get delivery settings."""
    try:
        delivery = get_delivery_system()
        settings = delivery.get_settings()
        return jsonify({
            'status': 'success',
            'data': settings
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@delivery_bp.route('/api/delivery/update', methods=['POST'])
def update_delivery_settings():
    """Update delivery settings."""
    try:
        delivery = get_delivery_system()
        settings_data = request.get_json()
        delivery.update_settings(settings_data)
        return jsonify({
            'status': 'success',
            'data': {'updated': True}
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@delivery_bp.route('/api/delivery/test', methods=['POST'])
def test_delivery():
    """Test delivery configuration."""
    try:
        delivery = get_delivery_system()
        test_data = request.get_json()
        test_results = delivery.test_delivery(test_data)
        return jsonify({
            'status': 'success',
            'data': test_results
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@delivery_bp.route('/api/delivery/history')
def get_delivery_history():
    """Get delivery history."""
    try:
        delivery = get_delivery_system()
        history = delivery.get_delivery_history()
        return jsonify({
            'status': 'success',
            'data': history
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500
