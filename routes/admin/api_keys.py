"""
Superadmin API and Access Key management routes
"""
from flask import render_template, Blueprint, request, redirect, url_for, flash, jsonify
from routes.admin.auth import superadmin_required
from models import db
from models.settings import Settings
import secrets
import string
from datetime import datetime

api_keys_bp = Blueprint('admin_api_keys', __name__, url_prefix='/admin')

@api_keys_bp.route('/api-keys')
@superadmin_required
def api_keys():
    """API and Access Key management page (superadmin only)"""
    # Get all API keys and access keys from settings
    api_keys_list = []
    access_keys_list = []
    
    # Fetch keys from settings (stored as JSON or comma-separated)
    all_settings = Settings.query.filter(
        Settings.key.like('api_key_%') | Settings.key.like('access_key_%')
    ).all()
    
    for setting in all_settings:
        if setting.key.startswith('api_key_'):
            api_keys_list.append({
                'id': setting.key,
                'name': setting.key.replace('api_key_', ''),
                'value': setting.value[:20] + '...' if len(setting.value) > 20 else setting.value,
                'created_at': setting.updated_at or datetime.utcnow()
            })
        elif setting.key.startswith('access_key_'):
            access_keys_list.append({
                'id': setting.key,
                'name': setting.key.replace('access_key_', ''),
                'value': setting.value[:20] + '...' if len(setting.value) > 20 else setting.value,
                'created_at': setting.updated_at or datetime.utcnow()
            })
    
    return render_template('admin/api_keys.html',
                         api_keys=api_keys_list,
                         access_keys=access_keys_list)

@api_keys_bp.route('/api-keys/create', methods=['POST'])
@superadmin_required
def create_api_key():
    """Create new API key"""
    key_type = request.form.get('key_type', '').strip()  # 'api_key' or 'access_key'
    key_name = request.form.get('key_name', '').strip()
    
    if not key_name:
        flash('Key name is required.', 'error')
        return redirect(url_for('admin_api_keys.api_keys'))
    
    if key_type not in ['api_key', 'access_key']:
        flash('Invalid key type.', 'error')
        return redirect(url_for('admin_api_keys.api_keys'))
    
    # Generate secure key
    key_value = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(64))
    
    # Store in settings
    setting_key = f'{key_type}_{key_name}'
    
    # Check if key already exists
    existing = Settings.query.filter_by(key=setting_key).first()
    if existing:
        flash(f'Key with name "{key_name}" already exists.', 'error')
        return redirect(url_for('admin_api_keys.api_keys'))
    
    new_setting = Settings(
        key=setting_key,
        value=key_value,
        updated_at=datetime.utcnow()
    )
    
    try:
        db.session.add(new_setting)
        db.session.commit()
        flash(f'{key_type.replace("_", " ").title()} "{key_name}" created successfully!', 'success')
        flash(f'Full key: {key_value} (save this securely - it will not be shown again)', 'info')
    except Exception as e:
        db.session.rollback()
        flash(f'Error creating key: {e}', 'error')
    
    return redirect(url_for('admin_api_keys.api_keys'))

@api_keys_bp.route('/api-keys/<key_id>/delete', methods=['POST'])
@superadmin_required
def delete_api_key(key_id):
    """Delete API or Access key"""
    setting = Settings.query.filter_by(key=key_id).first()
    
    if not setting:
        flash('Key not found.', 'error')
        return redirect(url_for('admin_api_keys.api_keys'))
    
    key_name = setting.key.replace('api_key_', '').replace('access_key_', '')
    
    try:
        db.session.delete(setting)
        db.session.commit()
        flash(f'Key "{key_name}" deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting key: {e}', 'error')
    
    return redirect(url_for('admin_api_keys.api_keys'))

@api_keys_bp.route('/api-keys/<key_id>/regenerate', methods=['POST'])
@superadmin_required
def regenerate_api_key(key_id):
    """Regenerate API or Access key"""
    setting = Settings.query.filter_by(key=key_id).first()
    
    if not setting:
        flash('Key not found.', 'error')
        return redirect(url_for('admin_api_keys.api_keys'))
    
    # Generate new secure key
    new_key_value = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(64))
    
    setting.value = new_key_value
    setting.updated_at = datetime.utcnow()
    
    try:
        db.session.commit()
        key_name = setting.key.replace('api_key_', '').replace('access_key_', '')
        flash(f'Key "{key_name}" regenerated successfully!', 'success')
        flash(f'New key: {new_key_value} (save this securely - it will not be shown again)', 'info')
    except Exception as e:
        db.session.rollback()
        flash(f'Error regenerating key: {e}', 'error')
    
    return redirect(url_for('admin_api_keys.api_keys'))
