# This file is part of NeuraSelf-UwU.
# Copyright (c) 2025-Present Routo
#
# NeuraSelf-UwU is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# You should have received a copy of the GNU General Public License
# along with NeuraSelf-UwU. If not, see <https://www.gnu.org/licenses/>.


from flask import Flask, render_template, jsonify, request, session, redirect, url_for
from functools import wraps
import threading
import time
import json
import logging
import os
import secrets
import core.state as state
import utils.utils as utils
import asyncio
from datetime import datetime, timedelta

app = Flask(__name__)
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

AUTH_FILE = os.path.join(state.CONFIG_DIR, 'auth.json')
LOGIN_ATTEMPTS = {}
BLOCK_DURATION = 300  
MAX_ATTEMPTS = 5

def load_auth_config():
    if os.path.exists(AUTH_FILE):
        try:
            with open(AUTH_FILE, 'r') as f:
                cfg = json.load(f)
                
            if cfg.get('secret_key') == "generate_a_random_long_secret_key_here_please":
                new_secret = secrets.token_hex(32)
                cfg['secret_key'] = new_secret
                with open(AUTH_FILE, 'w') as f:
                    json.dump(cfg, f, indent=4)
                
            return cfg
        except:
            pass
    return None

auth_cfg = load_auth_config()
if auth_cfg:
    app.secret_key = auth_cfg.get('secret_key', 'neuraself_fallback_secret')
else:
    app.secret_key = 'temporary_secret_key'

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'logged_in' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def check_rate_limit(ip):
    now = time.time()
    if ip in LOGIN_ATTEMPTS:
        attempts, block_time = LOGIN_ATTEMPTS[ip]
        if block_time > now:
            return False, int(block_time - now)
        if now - block_time > BLOCK_DURATION: 
             LOGIN_ATTEMPTS[ip] = [0, 0]
    return True, 0

def fail_login(ip):
    now = time.time()
    if ip not in LOGIN_ATTEMPTS:
        LOGIN_ATTEMPTS[ip] = [1, 0]
    else:
        attempts, block_time = LOGIN_ATTEMPTS[ip]
        attempts += 1
        if attempts >= MAX_ATTEMPTS:
            block_time = now + BLOCK_DURATION
        LOGIN_ATTEMPTS[ip] = [attempts, block_time]

def protect_large_ints(obj):
    if isinstance(obj, dict):
        return {k: protect_large_ints(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [protect_large_ints(v) for v in obj]
    elif isinstance(obj, int) and (obj > 9007199254740991 or obj < -9007199254740991):
        return str(obj)
    return obj

@app.route('/')
@login_required
def home():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        ip = request.remote_addr
        allowed, wait_time = check_rate_limit(ip)
        
        if not allowed:
             return jsonify({'success': False, 'error': f'Too many failed attempts. Try again in {wait_time}s'})

        data = request.json
        cfg = load_auth_config()
        
        if not cfg:
             return jsonify({'success': False, 'error': 'Auth config missing'})
             
        if data.get('username') == cfg.get('username') and data.get('password') == cfg.get('password'):
            session['logged_in'] = True
            session.permanent = True
            if ip in LOGIN_ATTEMPTS: del LOGIN_ATTEMPTS[ip]
            return jsonify({'success': True})
        else:
            fail_login(ip)
            return jsonify({'success': False, 'error': 'Invalid Credentials'})
            
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    return redirect(url_for('login'))

@app.route('/api/accounts/list')
@login_required
def account_list():
    accounts = []
    for bot in state.bot_instances:
        if not bot.user or not bot.is_ready: continue
        accounts.append({
            'id': str(bot.user.id),
            'username': bot.username,
            'avatar': str(bot.user.display_avatar.url) if bot.user.display_avatar else None,
            'paused': bot.paused
        })
    return jsonify(accounts)

def get_bot(account_id):
    if not account_id:
        return state.bot_instances[0] if state.bot_instances else None
    for bot in state.bot_instances:
        if bot.user and str(bot.user.id) == str(account_id):
            return bot
    return state.bot_instances[0] if state.bot_instances else None

@app.route('/api/stats')
@login_required
def stats():
    account_id = request.args.get('id')
    bot = get_bot(account_id)
    
    if not bot or not bot.user:
        return jsonify({})
        
    uid = str(bot.user.id)
    st = state.account_stats.get(uid)
    
    
    if not st:
        return jsonify({})
    
    uptime_start = st['uptime_start']
    elapsed = time.time() - uptime_start
    total_cmds = st.get('total_cmd_count', 0)
    mins = elapsed / 60
    cpm = round(total_cmds / mins, 1) if mins > 0.1 else 0
    
    cph = 0
    if len(st['cowoncy_history']) > 1:
        first = st['cowoncy_history'][0]
        last = st['cowoncy_history'][-1]
        time_diff_hrs = (last[0] - first[0]) / 3600
        cash_diff = last[1] - first[1]
        if time_diff_hrs > 0.01:
            cph = round(cash_diff / time_diff_hrs)

    response_data = {
        'uptime': utils.format_seconds(elapsed),
        'cash': st['current_cash'],
        'logs': [l for l in state.command_logs if not account_id or str(l.get('bot_id')) == str(account_id)][:200],
        'status': "PAUSED" if bot.paused else "ONLINE",
        'security': {
             'captchas': st.get('captchas_solved', 0),
             'bans': st.get('bans_detected', 0),
             'warnings': st.get('warnings_detected', 0),
             'last_message': st.get('last_captcha_msg', '')
        },
        'analytics': {
            'cph': cph,
            'gems_used': st.get('gems_used', 0)
        },
        'bot': {
            'user_id': uid,
            'username': bot.username,
            'channel_id': bot.channel_id,
            'paused': bot.paused,
            'throttled': time.time() < bot.throttle_until,
            'cooldown_remaining': max(0, int(bot.throttle_until - time.time())),
            'cooldown_command': bot.last_sent_command
        },
        'chart_data': {
            'hunt': st.get('hunt_count', 0),
            'battle': st.get('battle_count', 0),
            'session_hunt': st.get('session_hunt_count', 0),
            'session_battle': st.get('session_battle_count', 0),
            'session_owo': st.get('session_owo_count', 0),
            'other': st.get('other_count', 0),
            'owo': st.get('owo_count', 0),
            'total': total_cmds,
            'perf_bpm': cpm
        },
        'system': {
            'last_cash_update': st.get('last_cash_update', 0),
            'pending_commands': len(st.get('pending_commands', []))
        },
        'quest_data': st.get('quest_data', []),
        'next_quest_timer': st.get('next_quest_timer'),
        'cmd_states': {k: {**v, 'content': '[Dynamic function]' if callable(v.get('content')) else v.get('content')} for k, v in bot.cmd_states.items()}
    }
    
    return jsonify(response_data)

@app.route('/api/debug')
@login_required
def debug():
    return jsonify({
        'account_stats': state.account_stats,
        'bot_instances': len(state.bot_instances),
        'command_logs_count': len(state.command_logs),
        'full_history_count': len(state.full_session_history)
    })

@app.route('/api/history')
@login_required
def get_history():
    return jsonify(list(reversed(state.full_session_history)))

@app.route('/api/history/analytics')
@login_required
def get_analytics():
    try:
        from utils import history_tracker
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        dat = history_tracker.get_analytics_data(start_date=start_date, end_date=end_date)
        dat['recent_logs'] = list(state.full_session_history)[-500:]
        return jsonify(dat)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route('/api/settings', methods=['GET', 'POST'])
@login_required
def settings():
    config_path = os.path.join(state.CONFIG_DIR, 'settings.json')
    if request.method == 'POST':
        new_config = request.json
        try:
            with open(config_path, 'w') as f:
                json.dump(new_config, f, indent=4)
            
            for bot in state.bot_instances:
                bot.config = new_config
                core_cfg = new_config.get('core', {})
                bot.prefix = core_cfg.get('prefix', 'owo ')
                bot._load_config()
            state.log_command("SYS", "Settings updated and synced real-time", "success")
            return jsonify({"status": "success"})
        except Exception as e:
            state.log_command("ERROR", f"Failed to save settings: {e}")
            return jsonify({"status": "error", "message": str(e)}), 500
    else:
        try:
            if os.path.exists(config_path):
                with open(config_path, 'r') as f:
                    data = json.load(f)
                    return jsonify(protect_large_ints(data))
            return jsonify({})
        except:
            return jsonify({})

@app.route('/api/accounts', methods=['GET', 'POST'])
@login_required
def accounts_api():
    if request.method == 'POST':
        new_accounts = request.json
        try:
            accounts_path = os.path.join(BASE_DIR, 'config', 'accounts.json')
            with open(accounts_path, 'w') as f:
                json.dump(new_accounts, f, indent=4)

            for bot in state.bot_instances:
                bot.accounts = new_accounts
                
            state.log_command("SYS", "Accounts updated successfully. Restart recommended.", "success")
            return jsonify({"status": "success"})
        except Exception as e:
            return jsonify({"status": "error", "message": str(e)}), 500
    else:
        try:
            accounts_path = os.path.join(BASE_DIR, 'config', 'accounts.json')
            with open(accounts_path, 'r') as f:
                return jsonify(json.load(f))
        except:
            return jsonify([])

@app.route('/api/security/test', methods=['POST'])
@login_required
def test_security():
    account_id = request.args.get('id')
    bot = get_bot(account_id)
    if not bot:
        return jsonify({'status': 'error', 'message': 'Bot not found'}), 404
        
    sec = bot.get_cog('Security')
    if sec:
        asyncio.run_coroutine_threadsafe(sec.play_beep(), bot.loop)
        sec._show_desktop_notification("Test: Neura Security Alert working!")
        sec._send_webhook("SYSTEM TEST", "This is a test of your security notification system. All systems are operational.")
        return jsonify({'status': 'success', 'message': 'Test signals sent'})
    
    return jsonify({'status': 'error', 'message': 'Security module not loaded'}), 500

@app.route('/api/control', methods=['POST'])
@login_required
def control():
    data = request.json
    action = data.get('action')
    account_id = data.get('id')
    bot = get_bot(account_id)
    
    if not bot: return jsonify({'success': False, 'error': 'Bot not found'})
    
    if action == 'stop':
        bot.paused = True
        bot.log("SYS", "Bot STOPPED via Dashboard")
            
    elif action == 'start':
        bot.paused = False
        bot.throttle_until = 0
        bot.log("SYS", "Bot RESUMED via Dashboard")
            
    elif action == 'cash':
        asyncio.run_coroutine_threadsafe(
            bot.send_message(f"{bot.prefix}cash", skip_typing=True, priority=True),
            bot.loop
        )
        state.log_command("CMD", "Manual Cash Check Sent", "info", bot_name=bot.username)
        
    return jsonify({'success': True})

@app.route('/api/security', methods=['POST'])
@login_required
def security():
    data = request.json
    action = data.get('action')
    account_id = data.get('id')
    bot = get_bot(account_id)
    
    if not bot: return jsonify({'success': False, 'error': 'Bot not found'})

    if action == 'resume':
        bot.paused = False
        bot.throttle_until = 0
        state.log_command("SEC", f"User Resumed {bot.username} from Security Alert", "success")
            
    return jsonify({'success': True})

@app.route('/api/captcha/current')
@login_required
def captcha_current():
    account_id = request.args.get('id')
    bot = get_bot(account_id)
    if not bot: return jsonify({'success': False})
    
    st = bot.stats
    captcha_data = st.get('current_captcha')
    
    if captcha_data and captcha_data.get('image_url'):
        timestamp = captcha_data.get('timestamp', 0)
        if time.time() - timestamp < 600:
            return jsonify({
                'success': True,
                'url': captcha_data['image_url'],
                'cash': captcha_data.get('cash', 16000),
                'command': captcha_data.get('command_template', 'owo autohunt {cash} {password}'),
                'age_seconds': int(time.time() - timestamp)
            })
        else:
            if 'current_captcha' in st:
                del st['current_captcha']
    
    return jsonify({'success': False, 'message': 'No active captcha'})

@app.route('/api/captcha/submit', methods=['POST'])
@login_required
def captcha_submit():
    data = request.json
    code = data.get('code', '').strip()
    account_id = data.get('id')
    bot = get_bot(account_id)
    
    if not bot: return jsonify({'success': False, 'error': 'Bot not found'})
    
    if not code:
        return jsonify({'success': False, 'error': 'No password provided'})
    
    st = bot.stats
    captcha_data = st.get('current_captcha')
    if not captcha_data:
        return jsonify({'success': False, 'error': 'No active captcha'})
    
    cash = captcha_data.get('cash', 16000)
    command_template = captcha_data.get('command_template', f"owo autohunt {cash} {{password}}")
    full_command = command_template.replace('{password}', code)
    
    asyncio.run_coroutine_threadsafe(
        bot.send_message(full_command, skip_typing=True, priority=True), 
        bot.loop
    )
    
    if 'current_captcha' in st:
        del st['current_captcha']
    
    st['captchas_solved_today'] = st.get('captchas_solved_today', 0) + 1
    st['captcha_success_count'] = st.get('captcha_success_count', 0) + 1
    state.log_command("CMD", f"Captcha solution sent: {full_command}", bot_name=bot.username)
    
    return jsonify({'success': True, 'message': f'Captcha solution sent: {full_command}'})

@app.route('/api/captcha/stats')
@login_required
def captcha_stats():
    account_id = request.args.get('id')
    bot = get_bot(account_id)
    st = bot.stats if bot else {}
    
    solved = st.get('captchas_solved_today', 0)
    success = st.get('captcha_success_count', 0)
    success_rate = 100 if solved == 0 else round((success / max(solved, 1)) * 100)
    
    return jsonify({
        'solved': solved,
        'success_rate': success_rate
    })

@app.route('/api/bot/command', methods=['POST'])
@login_required
def bot_command():
    data = request.json
    command = data.get('command', '').strip()
    account_id = data.get('id')
    bot = get_bot(account_id)
    
    if not bot: return jsonify({'success': False, 'error': 'Bot not found'})
    
    if not command:
        return jsonify({'success': False, 'error': 'No command provided'})
    
    asyncio.run_coroutine_threadsafe(
        bot.send_message(command, skip_typing=True, priority=True), 
        bot.loop
    )
    state.log_command("CMD", f"Manual command sent: {command}", bot_name=bot.username)
    return jsonify({'success': True, 'message': f'Command sent: {command}'})