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

@app.route('/login')
def login():
    # Simple dummy login for demo purposes
    # Logs in the first user in the DB
    db = get_db()
    user = db.execute('SELECT * FROM users LIMIT 1').fetchone()
    if user:
        session['user_id'] = user['id']
        return redirect(url_for('userProfile'))
    return "No users found to login.", 404

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

@app.route('/profile')
def userProfile():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    db = get_db()
    user = db.execute('SELECT * FROM users WHERE id = ?', (session['user_id'],)).fetchone()
    
    if not user:
         session.clear()
         return redirect(url_for('login'))

    return render_template('userProfile.html', user=user)

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
    
    return jsonify({'message': 'Profile updated', 'field': field, 'value': value}), 200

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
    cur = db.execute('SELECT original_id FROM tasks')
    accepted_ids = {row['original_id'] for row in cur.fetchall() if row['original_id'] is not None}

    # 20 unique task templates — each with a distinct title + description
    task_templates = [
        {"title": "Move Couch",           "reward": 50, "desc": "Need help moving a couch to the second floor."},
        {"title": "Grocery Run",          "reward": 25, "desc": "Pick up groceries from Whole Foods."},
        {"title": "Dog Walking",          "reward": 20, "desc": "Walk my golden retriever for 30 mins."},
        {"title": "Assemble Furniture",   "reward": 40, "desc": "Assemble an IKEA desk."},
        {"title": "Yard Work",            "reward": 35, "desc": "Rake leaves in the backyard."},
        {"title": "Tech Support",         "reward": 30, "desc": "Help setting up a new printer."},
        {"title": "Cat Sitting",          "reward": 45, "desc": "Feed my cat while I'm away for the weekend."},
        {"title": "Car Wash",             "reward": 20, "desc": "Wash my sedan in the driveway."},
        {"title": "Tutoring",             "reward": 40, "desc": "Algebra tutoring for 8th grader."},
        {"title": "Lift Heavy Boxes",     "reward": 15, "desc": "Help move 5 boxes to the garage."},
        {"title": "Move Dining Table",    "reward": 45, "desc": "Help relocate a dining table to a new apartment."},
        {"title": "Pharmacy Pickup",      "reward": 15, "desc": "Pick up a prescription from CVS."},
        {"title": "Walk Two Huskies",     "reward": 30, "desc": "Walk two huskies around the park for 45 mins."},
        {"title": "Mount TV",             "reward": 35, "desc": "Mount a 55-inch TV on a living room wall."},
        {"title": "Garden Weeding",       "reward": 25, "desc": "Weed the front garden beds and trim hedges."},
        {"title": "WiFi Setup",           "reward": 25, "desc": "Set up a new mesh WiFi system at home."},
        {"title": "Pet Sitting",          "reward": 40, "desc": "Watch my two dogs overnight while I travel."},
        {"title": "Bike Repair",          "reward": 20, "desc": "Fix a flat tire and adjust brakes on my bike."},
        {"title": "Math Tutoring",        "reward": 35, "desc": "Help with calculus homework for a college student."},
        {"title": "Garage Cleanup",       "reward": 30, "desc": "Help organize and clean out a cluttered garage."},
    ]

    # Seed based on rounded location so tasks are stable for the same area
    location_seed = int(round(lat, 2) * 10000 + round(lng, 2) * 10000)
    rng = random.Random(location_seed)

    # Shuffle templates deterministically and assign to task IDs 1-20
    shuffled = list(range(len(task_templates)))
    rng.shuffle(shuffled)

    for i in range(20):
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



@app.route('/api/delete_task/<int:task_id>', methods=['DELETE'])
def delete_task(task_id):
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
