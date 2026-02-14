from flask import Flask, render_template, jsonify, request, g
import random
import sqlite3

app = Flask(__name__)

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
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        db.commit()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/tasks')
def tasks():
    return render_template('tasks.html')

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

    # Generate dummy tasks
    task_templates = [
        {"title": "Move Couch", "reward": 50, "desc": "Need help moving a couch to the second floor."},
        {"title": "Grocery Run", "reward": 25, "desc": "Pick up groceries from Whole Foods."},
        {"title": "Dog Walking", "reward": 20, "desc": "Walk my golden retriever for 30 mins."},
        {"title": "Assemble Furniture", "reward": 40, "desc": "Assemble an IKEA desk."},
        {"title": "Yard Work", "reward": 35, "desc": "Rake leaves in the backyard."},
        {"title": "Tech Support", "reward": 30, "desc": "Help setting up a new printer."},
        {"title": "Cat Sitting", "reward": 45, "desc": "Feed my cat while I'm away for the weekend."},
        {"title": "Car Wash", "reward": 20, "desc": "Wash my sedan in the driveway."},
        {"title": "Tutoring", "reward": 40, "desc": "Algebra tutoring for 8th grader."},
        {"title": "Lift Heavy Boxes", "reward": 15, "desc": "Help move 5 boxes to the garage."},
    ]

    for i in range(20):
        # Skip if tasks with this ID (1-20) are already accepted
        if (i + 1) in accepted_ids:
            continue

        template = random.choice(task_templates)
        # Random offset within ~2km
        offset_lat = random.uniform(-0.02, 0.02)
        offset_lng = random.uniform(-0.02, 0.02)
        
        tasks.append({
            "id": i + 1,
            "title": template["title"],
            "reward": template["reward"],
            "description": template["desc"],
            "lat": lat + offset_lat,
            "lng": lng + offset_lng,
            "type": "task"
        })

    # Add user posted tasks (in-memory) to the map
    # Filter user tasks too
    for task in USER_TASKS:
        if task['id'] not in accepted_ids:
            tasks.append(task)

    return jsonify({'tasks': tasks})


# In-memory storage for user-created tasks (Available tasks)
# Structure: {id, title, desc, reward, lat, lng}
USER_TASKS = []

@app.route('/api/tasks', methods=['POST'])
def add_task():
    data = request.json
    if not data:
        return jsonify({'error': 'No data provided'}), 400

    new_task = {
        'id': len(USER_TASKS) + 100, # Offset ID to avoid conflict with dummy tasks
        'title': data.get('title'),
        'description': data.get('description'),
        'reward': data.get('reward'),
        'lat': data.get('lat'),
        'lng': data.get('lng'),
        'type': 'user_task'
    }
    USER_TASKS.append(new_task)
    return jsonify({'message': 'Task added successfully', 'task': new_task}), 201

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


# Deprecated: usage for "All Tasks"
@app.route('/api/all_tasks', methods=['GET'])
def get_all_tasks():
    return jsonify({'tasks': USER_TASKS})

@app.route('/api/delete_task/<int:task_id>', methods=['DELETE'])
def delete_task(task_id):
    db = get_db()
    db.execute('DELETE FROM tasks WHERE id = ?', (task_id,))
    db.commit()
    return jsonify({'message': 'Task deleted successfully'}), 200

if __name__ == '__main__':
    init_db()
    app.run(debug=True)
