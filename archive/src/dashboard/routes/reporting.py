"""Reporting routes for the dashboard."""

from flask import Blueprint, render_template, jsonify, request, send_file
from ...core.reporting.reporting import ReportingSystem

reporting_bp = Blueprint('reporting', __name__)

def get_reporting_system():
    """Get reporting system from app context."""
    from flask import current_app
    return current_app.reporting_system

@reporting_bp.route('/api/reporting/generate', methods=['POST'])
def generate_report():
    """Generate a new report."""
    try:
        reporting = get_reporting_system()
        report_data = request.get_json()
        report = reporting.generate_report(report_data)
        return jsonify({
            'status': 'success',
            'data': report
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@reporting_bp.route('/api/reporting/list')
def list_reports():
    """List available reports."""
    try:
        reporting = get_reporting_system()
        reports = reporting.list_reports()
        return jsonify({
            'status': 'success',
            'data': reports
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@reporting_bp.route('/api/reporting/download/<report_id>')
def download_report(report_id):
    """Download a specific report."""
    try:
        reporting = get_reporting_system()
        report_file = reporting.get_report_file(report_id)
        if report_file:
            return send_file(report_file, mimetype='application/pdf')
        else:
            return jsonify({
                'status': 'error',
                'message': 'Report not found'
            }), 404
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@reporting_bp.route('/api/reporting/templates')
def get_templates():
    """Get available report templates."""
    try:
        reporting = get_reporting_system()
        templates = reporting.get_report_templates()
        return jsonify({
            'status': 'success',
            'data': templates
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500
