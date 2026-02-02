"""
Admin settings routes
"""
from flask import render_template, request, Blueprint, flash, redirect, url_for
from routes.admin.auth import admin_required, get_current_admin, superadmin_required
from models import db
from models.settings import Settings
from utils.settings_helper import get_setting

settings_bp = Blueprint('admin_settings', __name__, url_prefix='/admin')


def set_setting(key, value, description=''):
    """Set or update setting value"""
    setting = Settings.query.filter_by(key=key).first()
    if setting:
        setting.value = value
        if description:
            setting.description = description
    else:
        setting = Settings(key=key, value=value, description=description)
        db.session.add(setting)
    return setting

@settings_bp.route('/settings', methods=['GET', 'POST'])
@admin_required
def settings():
    """Settings management page"""
    admin = get_current_admin()
    
    # Product-specific admins cannot access settings
    if admin and admin.role != 'superadmin':
        flash('Access denied. Only superadmin can access settings.', 'error')
        return redirect(url_for('admin_dashboard.dashboard')), 403
    
    if request.method == 'POST':
        # Brand Settings
        set_setting('website_name', request.form.get('website_name', '').strip(), 'Website Name')
        set_setting('website_url', request.form.get('website_url', '').strip(), 'Website URL')
        set_setting('analyst_name', request.form.get('analyst_name', '').strip(), 'Analyst Name')
        
        # Payment Settings
        set_setting('upi_name', request.form.get('upi_name', '').strip(), 'UPI Name')
        set_setting('upi_handle', request.form.get('upi_handle', '').strip(), 'UPI Handle')
        
        # Support Settings
        set_setting('support_email', request.form.get('support_email', '').strip(), 'Support Email')
        set_setting('support_phone', request.form.get('support_phone', '').strip(), 'Support Phone')
        
        # Integrations
        set_setting('telegram_api_url', request.form.get('telegram_api_url', '').strip(), 'Telegram API URL')
        set_setting('whatsapp_api_url', request.form.get('whatsapp_api_url', '').strip(), 'WhatsApp API URL')
        
        # Policies
        set_setting('privacy_policy_url', request.form.get('privacy_policy_url', '').strip(), 'Privacy Policy URL')
        set_setting('terms_url', request.form.get('terms_url', '').strip(), 'Terms URL')
        
        # Maintenance Mode
        maintenance_mode = request.form.get('maintenance_mode') == 'on'
        set_setting('maintenance_mode', '1' if maintenance_mode else '0', 'Maintenance Mode')

        # User-side controls
        allow_registration = request.form.get('allow_registration') == 'on'
        set_setting('allow_registration', '1' if allow_registration else '0', 'Allow new user registration')
        contact_form_enabled = request.form.get('contact_form_enabled') == 'on'
        set_setting('contact_form_enabled', '1' if contact_form_enabled else '0', 'Contact form enabled')
        show_pricing_on_home = request.form.get('show_pricing_on_home') == 'on'
        set_setting('show_pricing_on_home', '1' if show_pricing_on_home else '0', 'Show pricing section on homepage')
        announcement_banner = request.form.get('announcement_banner', '').strip()
        set_setting('announcement_banner', announcement_banner, 'Announcement banner (user-facing, leave blank to hide)')

        try:
            db.session.commit()
            flash('Settings saved successfully!', 'success')
            return redirect(url_for('admin_settings.settings'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error saving settings: {e}', 'error')
    
    # Get all settings
    settings_dict = {
        'website_name': get_setting('website_name', 'Trade Signals'),
        'website_url': get_setting('website_url', 'https://tradesignal.tech'),
        'analyst_name': get_setting('analyst_name', 'Trade Signals Team'),
        'upi_name': get_setting('upi_name', ''),
        'upi_handle': get_setting('upi_handle', ''),
        'support_email': get_setting('support_email', 'support@tradesignal.tech'),
        'support_phone': get_setting('support_phone', '+91 99999 99999'),
        'telegram_api_url': get_setting('telegram_api_url', ''),
        'whatsapp_api_url': get_setting('whatsapp_api_url', ''),
        'privacy_policy_url': get_setting('privacy_policy_url', ''),
        'terms_url': get_setting('terms_url', ''),
        'maintenance_mode': get_setting('maintenance_mode', '0') == '1',
        'allow_registration': get_setting('allow_registration', '1') == '1',
        'contact_form_enabled': get_setting('contact_form_enabled', '1') == '1',
        'show_pricing_on_home': get_setting('show_pricing_on_home', '1') == '1',
        'announcement_banner': get_setting('announcement_banner', ''),
    }
    
    return render_template('admin/settings.html', settings=settings_dict)
