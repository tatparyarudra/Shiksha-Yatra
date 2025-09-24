from flask import Flask, request, jsonify, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_mail import Mail, Message
from itsdangerous import URLSafeTimedSerializer
from werkzeug.security import generate_password_hash, check_password_hash
from flask_jwt_extended import create_access_token, JWTManager, jwt_required, get_jwt_identity
from datetime import date, datetime

app = Flask(__name__)

# --- Flask Configuration ---
app.config['SECRET_KEY'] = 'your-super-secret-key'
app.config['JWT_SECRET_KEY'] = 'your-super-secret-jwt-key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://user:password@localhost/your_database_name'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# --- Flask-Mail Configuration ---
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'your_email@gmail.com'
app.config['MAIL_PASSWORD'] = 'your_app_password'

db = SQLAlchemy(app)
mail = Mail(app)
jwt = JWTManager(app)
s = URLSafeTimedSerializer(app.config['SECRET_KEY'])

# --- Database Models ---
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    role = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=True)
    password_hash = db.Column(db.String(255), nullable=True)
    name = db.Column(db.String(255), nullable=False)
    
    def __repr__(self):
        return f'<User {self.email}>'

class TeacherRequest(db.Model):
    __tablename__ = 'teacher_requests'
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    teacher_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    status = db.Column(db.String(50), default='pending')

class Progress(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    subject = db.Column(db.String(255), nullable=False)
    tasks_completed = db.Column(db.Integer, default=0)
    total_tasks = db.Column(db.Integer, default=0)
    date = db.Column(db.Date, nullable=False)

class Badge(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    name = db.Column(db.String(255), nullable=False)
    image_url = db.Column(db.String(255), nullable=False)

class Question(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    subject = db.Column(db.String(255), nullable=False)
    chapter = db.Column(db.String(255), nullable=False)
    text = db.Column(db.String(255), nullable=False)
    type = db.Column(db.String(50), nullable=False)
    options = db.Column(db.JSON, nullable=False)
    answer = db.Column(db.String(255), nullable=False)

@app.route('/signup', methods=['POST'])
def signup():
    data = request.get_json()
    email = data.get('email')
    name = data.get('name')
    role = data.get('role')

    if not all([email, name, role]):
        return jsonify({"msg": "Missing required fields"}), 400

    if User.query.filter_by(email=email).first():
        return jsonify({"msg": "Email already registered"}), 409
    
    new_user = User(email=email, name=name, role=role)
    db.session.add(new_user)
    db.session.commit()
    
    token = s.dumps(email, salt='password-creation')
    link = url_for('create_password', token=token, _external=True)

    msg = Message('Set Your Password for Shiksha Yatra', sender=app.config['MAIL_USERNAME'], recipients=[email])
    msg.body = f'Hello {name},\n\nClick on this link to set your password: {link}\n\nThis link will expire in 1 hour.'
    mail.send(msg)
    
    return jsonify({"msg": "Account created. Check your email to set your password."}), 201

@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')

    user = User.query.filter_by(email=email).first()

    if user is None:
        return jsonify({"msg": "No such email/mobile number found."}), 404
    
    if not user.password_hash or not check_password_hash(user.password_hash, password):
        return jsonify({"msg": "Incorrect password. Please try again."}), 401
        
    access_token = create_access_token(identity=user.id)
    return jsonify(access_token=access_token, user_info={'username': user.name, 'role': user.role}), 200

@app.route('/create-password/<token>', methods=['GET', 'POST'])
def create_password(token):
    try:
        email = s.loads(token, salt='password-creation', max_age=3600)
    except:
        return jsonify({"msg": "The password link is invalid or has expired."}), 400
    
    user = User.query.filter_by(email=email).first()
    if not user:
        return jsonify({"msg": "User not found."}), 404
    
    if request.method == 'POST':
        data = request.get_json()
        password = data.get('password')
        
        if not password:
            return jsonify({"msg": "Password is required"}), 400
            
        user.password_hash = generate_password_hash(password)
        db.session.commit()
        
        return jsonify({"msg": "Password set successfully. You can now log in."}), 200
        
    return jsonify({"msg": "Please send a POST request with the new password."}), 200

@app.route('/teacher/classes/<int:teacher_id>', methods=['GET'])
@jwt_required()
def get_teacher_classes(teacher_id):
    return jsonify({
        "classes": [
            {"id": 1, "name": "Class 6", "student_count": 25},
            {"id": 2, "name": "Class 7", "student_count": 20}
        ]
    })

@app.route('/teacher/upload-content', methods=['POST'])
@jwt_required()
def upload_content():
    return jsonify({"msg": "Content uploaded successfully"}), 201

@app.route('/teacher/post-notice', methods=['POST'])
@jwt_required()
def post_notice():
    return jsonify({"msg": "Notice posted successfully"}), 201

@app.route('/student/send_request', methods=['POST'])
@jwt_required()
def send_request():
    current_student_id = get_jwt_identity()
    data = request.get_json()
    teacher_id = data.get('teacher_id')

    new_request = TeacherRequest(student_id=current_student_id, teacher_id=teacher_id)
    db.session.add(new_request)
    db.session.commit()
    
    return jsonify({"msg": "Request sent successfully"}), 201

@app.route('/teacher/requests', methods=['GET'])
@jwt_required()
def get_student_requests():
    current_teacher_id = get_jwt_identity()
    pending_requests = TeacherRequest.query.filter_by(teacher_id=current_teacher_id, status='pending').all()
    requests_data = []
    for req in pending_requests:
        student = User.query.get(req.student_id)
        requests_data.append({
            "id": req.id,
            "student_id": student.id,
            "name": student.name,
            "class": "6th"
        })

    return jsonify({"requests": requests_data}), 200

@app.route('/teacher/manage_request', methods=['POST'])
@jwt_required()
def manage_request():
    data = request.get_json()
    request_id = data.get('request_id')
    action = data.get('action')
    
    teacher_request = TeacherRequest.query.get(request_id)
    if not teacher_request:
        return jsonify({"msg": "Request not found"}), 404
        
    if action == 'accept':
        teacher_request.status = 'accepted'
    elif action == 'reject':
        teacher_request.status = 'rejected'
    
    db.session.commit()
    
    return jsonify({"msg": f"Request {action}ed successfully"}), 200

@app.route('/student/progress/monthly', methods=['GET'])
@jwt_required()
def get_monthly_progress():
    return jsonify({
        "monthly_tasks": [
            {"date": "2023-10-01", "tasks": 5},
            {"date": "2023-10-02", "tasks": 8},
            {"date": "2023-10-03", "tasks": 3},
        ]
    })

@app.route('/student/progress/subjects', methods=['GET'])
@jwt_required()
def get_subject_progress():
    return jsonify({
        "subject_progress": [
            {"subject": "Maths", "percentage": 50},
            {"subject": "Science", "percentage": 75},
            {"subject": "History", "percentage": 25},
        ]
    })

@app.route('/student/badges', methods=['GET'])
@jwt_required()
def get_student_badges():
    return jsonify({
        "badges": [
            {"name": "First Lesson", "image_url": "assets/images/badges/badge_1.png"},
            {"name": "Quiz Master", "image_url": "assets/images/badges/badge_2.png"},
            {"name": "Daily Streak", "image_url": "assets/images/badges/badge_3.png"},
        ]
    })

@app.route('/quizzes/<string:subject>/<string:chapter>', methods=['GET'])
@jwt_required()
def get_quiz_questions(subject, chapter):
    return jsonify({
        "questions": [
            {
                'id': 1,
                'question': 'What is the capital of Odisha?',
                'type': 'mcq',
                'options': ['Bhubaneswar', 'Cuttack', 'Puri', 'Rourkela'],
                'answer': 'Bhubaneswar'
            },
        ]
    })

@app.route('/sync_progress', methods=['POST'])
@jwt_required()
def sync_progress():
    data = request.get_json()
    tasks = data.get('tasks', [])
    current_user_id = get_jwt_identity()

    for task_data in tasks:
        print(f"Syncing task {task_data['name']} for user {current_user_id}")
    
    return jsonify({"msg": "Progress synced successfully"}), 200

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
