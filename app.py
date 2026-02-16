from flask import Flask, render_template, jsonify, request, g, session, redirect, url_for
import random
import sqlite3
import datetime
import os
import json
import urllib.request

from dotenv import load_dotenv
load_dotenv()

import ai_helpers
import dummy_tasks

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'super_secret_key_for_hackathon')

DATABASE = 'database.db'

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row
    return db

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None: # Corrected from 'if db is sorted:'
        db.close()

def init_db():
    with app.app_context():
        db = get_db()
        db.execute('''
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT,
                reward REAL,
                lat REAL,
                lng REAL,
                status TEXT DEFAULT 'accepted',
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                original_id INTEGER
            )
        ''')
        db.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL,
                bio TEXT,
                role TEXT DEFAULT 'Helper',
                expertise TEXT DEFAULT '',
                joined_date TEXT
            )
        ''')
        db.execute('''
            CREATE TABLE IF NOT EXISTS available_tasks (
                map_id INTEGER PRIMARY KEY,
                title TEXT NOT NULL,
                description TEXT,
                reward REAL,
                lat REAL,
                lng REAL
            )
        ''')
        db.execute('''
            CREATE TABLE IF NOT EXISTS chat_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        db.execute('''
            CREATE TABLE IF NOT EXISTS direct_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id INTEGER NOT NULL,
                sender TEXT NOT NULL DEFAULT 'user',
                content TEXT NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Seed a dummy user if not exists
        cur = db.execute('SELECT * FROM users LIMIT 1')
        if not cur.fetchone():
            join_date = datetime.datetime.now().strftime("%B %Y")
            db.execute('INSERT INTO users (username, bio, role, expertise, joined_date) VALUES (?, ?, ?, ?, ?)',
                       ('AstroHelper', 'Exploring the universe of helpful tasks.', 'Helper', 'Helping, Moving', join_date))
        
        db.commit()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/tasks')
def tasks():
    return render_template('tasks.html')

@app.route('/messages')
def messages():
    return render_template('message.html')

@app.route('/api/conversations', methods=['GET'])
def get_conversations():
    db = get_db()
    # Get all accepted tasks as conversations
    cur = db.execute("SELECT * FROM tasks WHERE status = 'accepted' ORDER BY timestamp DESC")
    rows = cur.fetchall()
    
    conversations = []
    for row in rows:
        # Get the latest message for preview
        msg_cur = db.execute(
            'SELECT content, sender, timestamp FROM direct_messages WHERE task_id = ? ORDER BY id DESC LIMIT 1',
            (row['id'],)
        )
        last_msg = msg_cur.fetchone()
        
        # Count unread (for demo, just count requester messages)
        unread_cur = db.execute(
            "SELECT COUNT(*) as cnt FROM direct_messages WHERE task_id = ? AND sender = 'requester'",
            (row['id'],)
        )
        
        conversations.append({
            'task_id': row['id'],
            'title': row['title'],
            'description': row['description'],
            'reward': row['reward'],
            'last_message': last_msg['content'] if last_msg else 'No messages yet',
            'last_sender': last_msg['sender'] if last_msg else None,
            'last_time': last_msg['timestamp'] if last_msg else row['timestamp'],
        })
    
    return jsonify({'conversations': conversations})

@app.route('/api/messages/<int:task_id>', methods=['GET'])
def get_messages(task_id):
    db = get_db()
    cur = db.execute(
        'SELECT * FROM direct_messages WHERE task_id = ? ORDER BY id ASC',
        (task_id,)
    )
    rows = cur.fetchall()
    
    messages_list = []
    for row in rows:
        messages_list.append({
            'id': row['id'],
            'sender': row['sender'],
            'content': row['content'],
            'timestamp': row['timestamp']
        })
    
    return jsonify({'messages': messages_list})

@app.route('/api/messages/<int:task_id>', methods=['POST'])
def send_message(task_id):
    data = request.json
    if not data or not data.get('content'):
        return jsonify({'error': 'No message content'}), 400
    
    content = data['content'].strip()
    if not content:
        return jsonify({'error': 'Empty message'}), 400
    
    db = get_db()
    
    # Save user message
    db.execute(
        'INSERT INTO direct_messages (task_id, sender, content) VALUES (?, ?, ?)',
        (task_id, 'user', content)
    )
    db.commit()
    
    # Auto-reply from "requester" for demo
    import time
    replies = [
        "Thanks for accepting! When can you start?",
        "Great, I'll be available anytime this weekend.",
        "Sounds good! Let me know if you need any details.",
        "Perfect. My address is 123 Main St. See you soon!",
        "Thanks for the update! Looking forward to it.",
    ]
    reply = random.choice(replies)
    db.execute(
        'INSERT INTO direct_messages (task_id, sender, content) VALUES (?, ?, ?)',
        (task_id, 'requester', reply)
    )
    db.commit()
    
    return jsonify({'success': True, 'reply': reply})

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

@app.route('/profile')
def userProfile():
    if 'user_id' not in session:
        # Auto-login as first user (demo)
        db = get_db()
        user = db.execute('SELECT * FROM users LIMIT 1').fetchone()
        if user:
            session['user_id'] = user['id']
        else:
            return "No users found.", 404
    
    db = get_db()
    user = db.execute('SELECT * FROM users WHERE id = ?', (session['user_id'],)).fetchone()
    
    if not user:
         session.clear()
         return redirect(url_for('index'))

    # Fetch tasks
    accepted_tasks = db.execute("SELECT * FROM tasks WHERE status = 'accepted' ORDER BY id DESC").fetchall()
    completed_tasks = db.execute("SELECT * FROM tasks WHERE status = 'completed' ORDER BY id DESC").fetchall()

    return render_template('userProfile.html', user=user, accepted_tasks=accepted_tasks, completed_tasks=completed_tasks)

@app.route('/settings')
def userSettings():
    if 'user_id' not in session:
        return redirect(url_for('index'))
    
    db = get_db()
    user = db.execute('SELECT * FROM users WHERE id = ?', (session['user_id'],)).fetchone()
    
    if not user:
         session.clear()
         return redirect(url_for('index'))

    return render_template('settings.html', user=user)

@app.route('/api/update_profile', methods=['POST'])
def update_profile():
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    data = request.json
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    field = data.get('field')
    value = data.get('value', '').strip()
    
    allowed_fields = ['username', 'bio', 'role', 'expertise']
    if field not in allowed_fields:
        return jsonify({'error': 'Invalid field'}), 400
    
    # Validate role
    if field == 'role' and value not in ['Helper', 'Requester']:
        return jsonify({'error': 'Invalid role'}), 400
    
    db = get_db()
    db.execute(f'UPDATE users SET {field} = ? WHERE id = ?', (value, session['user_id']))
    db.commit()
    
@app.route('/api/post_task', methods=['POST'])
def post_task():
    data = request.json
    if not data:
        return jsonify({'error': 'No data'}), 400
    
    title = data.get('title')
    description = data.get('description')
    reward = data.get('reward')
    lat = data.get('lat')
    lng = data.get('lng')

    db = get_db()
    cursor = db.execute(
        'INSERT INTO tasks (title, description, reward, lat, lng, status) VALUES (?, ?, ?, ?, ?, ?)',
        (title, description, reward, lat, lng, 'posted')
    )
    db.commit()
    new_id = cursor.lastrowid
    
    new_task = {
        'id': new_id + 10000, # Offset ID to avoid collision with dummy tasks (0-60)
        'title': title,
        'description': description,
        'reward': reward,
        'lat': lat,
        'lng': lng,
        'is_custom': True
    }
    return jsonify({'success': True, 'task': new_task})

@app.route('/api/delete_task', methods=['POST'])
def delete_task_frontend():
    data = request.json
    if not data or 'id' not in data:
        return jsonify({'error': 'No task ID provided'}), 400
    
    task_id = int(data['id'])
    
    # Handle offset IDs for DB tasks
    if task_id > 10000:
        db_id = task_id - 10000
        db = get_db()
        db.execute('DELETE FROM tasks WHERE id = ?', (db_id,))
        db.commit()
        return jsonify({'success': True})
    else:
        # Dummy task deletion logic (if supported) or error
        # Currently we assume only custom tasks (ID > 10000) are deletable via this button
        return jsonify({'error': 'Cannot delete system tasks'}), 400

@app.route('/api/nearby')
def get_nearby_data():
    try:
        lat = float(request.args.get('lat'))
        lng = float(request.args.get('lng'))
    except (TypeError, ValueError):
        return jsonify({'error': 'Invalid coordinates'}), 400

    tasks = []

    # Get accepted task IDs to filter them out
    db = get_db()
    cur = db.execute('SELECT original_id FROM tasks WHERE original_id IS NOT NULL')
    accepted_ids = {row['original_id'] for row in cur.fetchall()}

    # 1. Fetch user-posted tasks from DB (status='posted')
    cur = db.execute("SELECT * FROM tasks WHERE status = 'posted'")
    posted_rows = cur.fetchall()
    for row in posted_rows:
        tasks.append({
            'id': row['id'] + 10000, # Apply offset
            'title': row['title'],
            'description': row['description'],
            'reward': row['reward'],
            'lat': row['lat'],
            'lng': row['lng'],
            'is_custom': True
        })

    # 2. Add Dummy Tasks
    # 20 unique task templates — each with a distinct title + description
    task_templates = dummy_tasks.task_templates

    # Seed based on rounded location so tasks are stable for the same area
    location_seed = int(round(lat, 2) * 10000 + round(lng, 2) * 10000)
    rng = random.Random(location_seed)

    # Shuffle templates deterministically and assign to task IDs 1-60
    shuffled = list(range(len(task_templates)))
    rng.shuffle(shuffled)

    # Show up to 60 available tasks on the map
    limit = min(60, len(task_templates))
    for i in range(limit):
        if (i + 1) in accepted_ids:
            continue

        template = task_templates[shuffled[i]]
        # Deterministic offset within ~2km
        offset_lat = rng.uniform(-0.02, 0.02)
        offset_lng = rng.uniform(-0.02, 0.02)

        tasks.append({
            "id": i + 1,
            "title": template["title"],
            "reward": template["reward"],
            "description": template["desc"],
            "lat": lat + offset_lat,
            "lng": lng + offset_lng,
            "type": "task"
        })

    return jsonify({'tasks': tasks})


@app.route('/api/store_available_tasks', methods=['POST'])
def store_available_tasks():
    """Store the currently visible map tasks so the AI can query them."""
    data = request.json
    if not data or 'tasks' not in data:
        return jsonify({'error': 'No tasks provided'}), 400
    
    db = get_db()
    db.execute('DELETE FROM available_tasks')  # Clear old tasks
    for task in data['tasks']:
        db.execute(
            'INSERT OR REPLACE INTO available_tasks (map_id, title, description, reward, lat, lng) VALUES (?, ?, ?, ?, ?, ?)',
            (task['id'], task['title'], task.get('description', ''), task.get('reward', 0), task.get('lat', 0), task.get('lng', 0))
        )
    db.commit()
    return jsonify({'message': f'Stored {len(data["tasks"])} tasks'}), 200


@app.route('/api/accept_task', methods=['POST'])
def accept_task():
    data = request.json
    if not data:
         return jsonify({'error': 'No data provided'}), 400
    
    original_id = data.get('id') # The ID from the map
    title = data.get('title')
    desc = data.get('description')
    reward = data.get('reward')
    lat = data.get('lat')
    lng = data.get('lng')

    db = get_db()
    
    # Check if already accepted (idempotency)
    cur = db.execute('SELECT id FROM tasks WHERE original_id = ?', (original_id,))
    if cur.fetchone():
        return jsonify({'message': 'Task already accepted'}), 200

    db.execute('INSERT INTO tasks (title, description, reward, lat, lng, original_id) VALUES (?, ?, ?, ?, ?, ?)',
               (title, desc, reward, lat, lng, original_id))
    db.commit()

    return jsonify({'message': 'Task accepted and saved to database!'}), 201

@app.route('/api/my_tasks', methods=['GET'])
def get_my_tasks():
    db = get_db()
    cur = db.execute('SELECT * FROM tasks ORDER BY id DESC')
    rows = cur.fetchall()
    
    # Convert rows to list of dicts
    tasks = []
    for row in rows:
        tasks.append({
            'id': row['id'],
            'title': row['title'],
            'description': row['description'],
            'reward': row['reward'],
            'lat': row['lat'],
            'lng': row['lng'],
            'status': row['status']
        })
    
    return jsonify({'tasks': tasks})



@app.route('/api/delete_db_task/<int:task_id>', methods=['DELETE'])
def delete_db_task(task_id):
    db = get_db()
    db.execute('DELETE FROM tasks WHERE id = ?', (task_id,))
    db.commit()
    return jsonify({'message': 'Task deleted successfully'}), 200

@app.route('/api/chat', methods=['POST'])
def api_chat():
    # Auto-assign demo user if not logged in (hackathon convenience)
    user_id = session.get('user_id', 1)

    data = request.json
    if not data or 'message' not in data:
        return jsonify({'error': 'No message provided'}), 400

    user_message = data['message'].strip()
    if not user_message:
        return jsonify({'error': 'Empty message'}), 400

    # Extract user location (sent by chat.js from localStorage)
    user_lat = data.get('user_lat')
    user_lng = data.get('user_lng')

    db = get_db()

    # Get conversation history from DB (last 10 messages)
    cur = db.execute('SELECT role, content FROM chat_messages WHERE user_id = ? ORDER BY id DESC LIMIT 10', (user_id,))
    rows = cur.fetchall()
    # Reverse to chronological order for the AI context
    history = [{'role': row['role'], 'content': row['content']} for row in reversed(rows)]

    # Call the AI with function calling
    result = ai_helpers.chat(user_message, user_id, history, user_lat=user_lat, user_lng=user_lng)

    # Save to DB
    db.execute('INSERT INTO chat_messages (user_id, role, content) VALUES (?, ?, ?)', (user_id, 'user', user_message))
    db.execute('INSERT INTO chat_messages (user_id, role, content) VALUES (?, ?, ?)', (user_id, 'assistant', result['reply']))
    db.commit()

    return jsonify(result), 200


@app.route('/api/chat/history', methods=['GET'])
def get_chat_history():
    user_id = session.get('user_id', 1)
    db = get_db()
    cur = db.execute('SELECT role, content, timestamp FROM chat_messages WHERE user_id = ? ORDER BY id ASC', (user_id,))
    rows = cur.fetchall()
    
    history = []
    for row in rows:
        history.append({
            'role': row['role'],
            'content': row['content'],
            'timestamp': row['timestamp']
        })
    return jsonify({'history': history})


@app.route('/api/clear_chat', methods=['POST'])
def clear_chat():
    user_id = session.get('user_id', 1)
    db = get_db()
    db.execute('DELETE FROM chat_messages WHERE user_id = ?', (user_id,))
    db.commit()
    return jsonify({'message': 'Chat history cleared'}), 200

@app.route('/api/geolocate')
def geolocate():
    """Get user's approximate location from their IP address."""
    try:
        # Use ip-api.com (free, no key needed, 45 req/min)
        url = 'http://ip-api.com/json/?fields=status,lat,lon,city,regionName'
        req = urllib.request.Request(url, headers={'User-Agent': 'FindAHelper/1.0'})
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode())
        
        if data.get('status') == 'success':
            return jsonify({
                'lat': data['lat'],
                'lng': data['lon'],
                'city': data.get('city', ''),
                'region': data.get('regionName', '')
            })
        
        return jsonify({'error': 'Could not determine location'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    init_db()
    app.run(debug=True, port=5001)
