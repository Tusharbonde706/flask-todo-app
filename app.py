from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from functools import wraps

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-change-this-in-production'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///tasks.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Models
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    tasks = db.relationship('Task', backref='user', lazy=True, cascade='all, delete-orphan')

class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    priority = db.Column(db.String(20), default='medium')
    status = db.Column(db.String(20), default='pending')
    due_date = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

# Login required decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# Routes
@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        if not username or not password:
            flash('Username and password are required!', 'danger')
            return redirect(url_for('register'))
        
        if password != confirm_password:
            flash('Passwords do not match!', 'danger')
            return redirect(url_for('register'))
        
        if User.query.filter_by(username=username).first():
            flash('Username already exists!', 'danger')
            return redirect(url_for('register'))
        
        hashed_password = generate_password_hash(password)
        new_user = User(username=username, password=hashed_password)
        db.session.add(new_user)
        db.session.commit()
        
        flash('Registration successful! Please log in.', 'success')
        return redirect(url_for('login'))
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = User.query.filter_by(username=username).first()
        
        if user and check_password_hash(user.password, password):
            session['user_id'] = user.id
            session['username'] = user.username
            flash('Login successful!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password!', 'danger')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    filter_status = request.args.get('status', 'all')
    filter_priority = request.args.get('priority', 'all')
    
    query = Task.query.filter_by(user_id=session['user_id'])
    
    if filter_status != 'all':
        query = query.filter_by(status=filter_status)
    if filter_priority != 'all':
        query = query.filter_by(priority=filter_priority)
    
    tasks = query.order_by(Task.created_at.desc()).all()
    
    # Statistics
    total_tasks = Task.query.filter_by(user_id=session['user_id']).count()
    completed_tasks = Task.query.filter_by(user_id=session['user_id'], status='completed').count()
    pending_tasks = Task.query.filter_by(user_id=session['user_id'], status='pending').count()
    
    return render_template('dashboard.html', tasks=tasks, total_tasks=total_tasks,
                         completed_tasks=completed_tasks, pending_tasks=pending_tasks,
                         filter_status=filter_status, filter_priority=filter_priority)

@app.route('/task/add', methods=['GET', 'POST'])
@login_required
def add_task():
    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')
        priority = request.form.get('priority')
        due_date_str = request.form.get('due_date')
        
        if not title:
            flash('Task title is required!', 'danger')
            return redirect(url_for('add_task'))
        
        due_date = None
        if due_date_str:
            due_date = datetime.strptime(due_date_str, '%Y-%m-%d')
        
        new_task = Task(
            title=title,
            description=description,
            priority=priority,
            due_date=due_date,
            user_id=session['user_id']
        )
        
        db.session.add(new_task)
        db.session.commit()
        
        flash('Task added successfully!', 'success')
        return redirect(url_for('dashboard'))
    
    return render_template('add_task.html')

@app.route('/task/edit/<int:task_id>', methods=['GET', 'POST'])
@login_required
def edit_task(task_id):
    task = Task.query.get_or_404(task_id)
    
    if task.user_id != session['user_id']:
        flash('Unauthorized access!', 'danger')
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        task.title = request.form.get('title')
        task.description = request.form.get('description')
        task.priority = request.form.get('priority')
        task.status = request.form.get('status')
        due_date_str = request.form.get('due_date')
        
        if due_date_str:
            task.due_date = datetime.strptime(due_date_str, '%Y-%m-%d')
        
        db.session.commit()
        flash('Task updated successfully!', 'success')
        return redirect(url_for('dashboard'))
    
    return render_template('edit_task.html', task=task)

@app.route('/task/delete/<int:task_id>')
@login_required
def delete_task(task_id):
    task = Task.query.get_or_404(task_id)
    
    if task.user_id != session['user_id']:
        flash('Unauthorized access!', 'danger')
        return redirect(url_for('dashboard'))
    
    db.session.delete(task)
    db.session.commit()
    flash('Task deleted successfully!', 'success')
    return redirect(url_for('dashboard'))

@app.route('/task/toggle/<int:task_id>')
@login_required
def toggle_task(task_id):
    task = Task.query.get_or_404(task_id)
    
    if task.user_id != session['user_id']:
        flash('Unauthorized access!', 'danger')
        return redirect(url_for('dashboard'))
    
    task.status = 'completed' if task.status == 'pending' else 'pending'
    db.session.commit()
    return redirect(url_for('dashboard'))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
