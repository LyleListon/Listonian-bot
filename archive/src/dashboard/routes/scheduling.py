"""Scheduling routes for the dashboard."""

from flask import Blueprint, render_template, jsonify, request
from ...core.reporting.scheduling import SchedulingSystem

scheduling_bp = Blueprint('scheduling', __name__)

def get_scheduling_system():
    """Get scheduling system from app context."""
    from flask import current_app
    return current_app.scheduling_system

@scheduling_bp.route('/api/scheduling/add', methods=['POST'])
async def add_schedule():
    """Add a new report schedule."""
    try:
        scheduling = get_scheduling_system()
        schedule_data = request.get_json()
        schedule = await scheduling.add_schedule(
            report_type=schedule_data['report_type'],
            symbol=schedule_data['symbol'],
            schedule_type=schedule_data['schedule_type'],
            schedule_value=schedule_data['schedule_value'],
            parameters=schedule_data.get('parameters', {})
        )
        return jsonify({
            'status': 'success',
            'data': schedule
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@scheduling_bp.route('/api/scheduling/list')
async def list_schedules():
    """List all report schedules."""
    try:
        scheduling = get_scheduling_system()
        schedules = await scheduling.get_schedules()
        return jsonify({
            'status': 'success',
            'data': schedules
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@scheduling_bp.route('/api/scheduling/update/<schedule_id>', methods=['POST'])
async def update_schedule(schedule_id):
    """Update an existing schedule."""
    try:
        scheduling = get_scheduling_system()
        update_data = request.get_json()
        await scheduling.update_schedule(
            schedule_id,
            schedule_type=update_data.get('schedule_type'),
            schedule_value=update_data.get('schedule_value'),
            parameters=update_data.get('parameters'),
            enabled=update_data.get('enabled')
        )
        return jsonify({
            'status': 'success',
            'data': {'schedule_id': schedule_id}
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@scheduling_bp.route('/api/scheduling/delete/<schedule_id>', methods=['DELETE'])
async def delete_schedule(schedule_id):
    """Delete a schedule."""
    try:
        scheduling = get_scheduling_system()
        await scheduling.delete_schedule(schedule_id)
        return jsonify({
            'status': 'success',
            'data': {'schedule_id': schedule_id}
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500
