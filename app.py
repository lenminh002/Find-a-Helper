from flask import Flask, render_template, jsonify, request
import random

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/nearby')
def get_nearby_data():
    try:
        lat = float(request.args.get('lat'))
        lng = float(request.args.get('lng'))
    except (TypeError, ValueError):
        return jsonify({'error': 'Invalid coordinates'}), 400

    tasks = []

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

    return jsonify({'tasks': tasks})

if __name__ == '__main__':
    app.run(debug=True)
