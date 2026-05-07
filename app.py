from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from datetime import datetime, date, timedelta
from functools import wraps
import os
import random

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', os.urandom(24))

# Database config: use PostgreSQL on Render, SQLite locally
database_url = os.environ.get('DATABASE_URL', 'sqlite:///smart_task_manager_v2.db')
# Render's DATABASE_URL starts with "postgres://" but SQLAlchemy needs "postgresql://"
if database_url.startswith('postgres://'):
    database_url = database_url.replace('postgres://', 'postgresql://', 1)
app.config['SQLALCHEMY_DATABASE_URI'] = database_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
bcrypt = Bcrypt(app)

# ============== MODELS ==============

# Association table for project members
project_members = db.Table('project_members',
    db.Column('user_id', db.Integer, db.ForeignKey('user.id'), primary_key=True),
    db.Column('project_id', db.Integer, db.ForeignKey('project.id'), primary_key=True)
)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20), default='member')  # admin or member
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    owned_projects = db.relationship('Project', backref='owner', lazy=True, foreign_keys='Project.owner_id')
    member_projects = db.relationship('Project', secondary=project_members, backref='members')
    assigned_tasks = db.relationship('Task', backref='assignee', lazy=True, foreign_keys='Task.assigned_to')
    created_tasks = db.relationship('Task', backref='creator', lazy=True, foreign_keys='Task.created_by')

class Project(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    owner_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    tasks = db.relationship('Task', backref='project', lazy=True, cascade='all, delete-orphan')

class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    priority = db.Column(db.String(20), default='Medium')  # Low, Medium, High
    due_date = db.Column(db.Date, nullable=False)
    status = db.Column(db.String(20), default='Todo')  # Todo, In Progress, Done
    assigned_to = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=False)
    parent_task_id = db.Column(db.Integer, db.ForeignKey('task.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    histories = db.relationship('TaskHistory', backref='task', lazy=True, cascade='all, delete-orphan', order_by='TaskHistory.created_at.desc()')
    child_tasks = db.relationship('Task', backref=db.backref('parent', remote_side=[id]), lazy=True)

    def risk_level(self):
        if self.status == 'Done':
            return 'safe'
        today = date.today()
        if self.due_date < today:
            return 'critical'
        elif (self.due_date - today).days <= 2:
            return 'warning'
        return 'safe'

    def risk_badge(self):
        return self.risk_level()

    def is_blocked(self):
        if self.parent and self.parent.status != 'Done':
            return True
        return False

class TaskHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(db.Integer, db.ForeignKey('task.id'), nullable=False)
    old_status = db.Column(db.String(20), nullable=True)
    new_status = db.Column(db.String(20), nullable=False)
    changed_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', foreign_keys=[changed_by])

class Activity(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    action = db.Column(db.String(50), nullable=False)
    entity_type = db.Column(db.String(20), nullable=False)
    entity_id = db.Column(db.Integer, nullable=False)
    description = db.Column(db.Text, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', foreign_keys=[user_id])

# Chat Group Members association
group_members = db.Table('group_members',
    db.Column('user_id', db.Integer, db.ForeignKey('user.id'), primary_key=True),
    db.Column('group_id', db.Integer, db.ForeignKey('chat_group.id'), primary_key=True)
)

class ChatGroup(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    members = db.relationship('User', secondary=group_members, backref='chat_groups')
    creator = db.relationship('User', foreign_keys=[created_by])

class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    receiver_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)  # for DMs
    group_id = db.Column(db.Integer, db.ForeignKey('chat_group.id'), nullable=True)  # for groups
    is_broadcast = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    sender = db.relationship('User', foreign_keys=[sender_id], backref='sent_messages')
    receiver = db.relationship('User', foreign_keys=[receiver_id], backref='received_messages')
    group = db.relationship('ChatGroup', backref='messages')

class UserChatStatus(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, unique=True)
    last_read_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', backref='chat_status', uselist=False)

# ============== DECORATORS ==============

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please login first.', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please login first.', 'error')
            return redirect(url_for('login'))
        user = User.query.get(session['user_id'])
        if user.role != 'admin':
            flash('Admin access required.', 'error')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function

# ============== CONTEXT PROCESSORS ==============

@app.context_processor
def inject_unread_messages():
    has_unread = False
    if 'user_id' in session:
        user_id = session['user_id']
        chat_status = UserChatStatus.query.filter_by(user_id=user_id).first()
        last_read = chat_status.last_read_at if chat_status else datetime.min
        # Check for messages sent to user or broadcast after last read
        unread = Message.query.filter(
            (Message.created_at > last_read) &
            (Message.sender_id != user_id) &
            (
                (Message.receiver_id == user_id) |
                (Message.is_broadcast == True) |
                (Message.group_id != None)
            )
        ).first()
        has_unread = unread is not None
    return dict(has_unread_messages=has_unread)

# ============== HELPERS ==============

def log_activity(action, entity_type, entity_id, description):
    activity = Activity(
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        description=description,
        user_id=session['user_id']
    )
    db.session.add(activity)
    db.session.commit()

def get_task_risk_counts(tasks):
    critical = warning = safe = 0
    for task in tasks:
        level = task.risk_level()
        if level == 'critical':
            critical += 1
        elif level == 'warning':
            warning += 1
        else:
            safe += 1
    return {'critical': critical, 'warning': warning, 'safe': safe}

def get_insights(user_id=None):
    query = Task.query
    if user_id:
        query = query.filter((Task.assigned_to == user_id) | (Task.created_by == user_id))
    tasks = query.all()

    total = len(tasks)
    completed = sum(1 for t in tasks if t.status == 'Done')
    overdue = sum(1 for t in tasks if t.risk_level() == 'critical' and t.status != 'Done')
    high_priority = sum(1 for t in tasks if t.priority == 'High')
    medium_priority = sum(1 for t in tasks if t.priority == 'Medium')
    low_priority = sum(1 for t in tasks if t.priority == 'Low')

    today = date.today()
    today_completed = sum(1 for t in tasks if t.status == 'Done' and t.updated_at and t.updated_at.date() == today)

    # New metrics
    productivity_pct = round((completed / total * 100), 1) if total > 0 else 0
    completion_rate = round((completed / total * 100), 1) if total > 0 else 0
    overdue_rate = round((overdue / total * 100), 1) if total > 0 else 0

    # Avg completion time (days from created to updated for done tasks)
    done_tasks = [t for t in tasks if t.status == 'Done' and t.updated_at]
    avg_completion_days = 0
    if done_tasks:
        total_days = sum((t.updated_at.date() - t.created_at.date()).days for t in done_tasks)
        avg_completion_days = round(total_days / len(done_tasks), 1)

    # Blocked tasks
    blocked_count = sum(1 for t in tasks if t.is_blocked() and t.status != 'Done')

    # Unassigned tasks (no assignee or assignee is 0 - but our model requires assigned_to)
    # We'll consider tasks with status 'Todo' and created long ago as potentially stale
    stale_tasks = [t for t in tasks if t.status == 'Todo' and (today - t.due_date).days > 7]

    return {
        'total': total,
        'completed': completed,
        'overdue': overdue,
        'high_priority': high_priority,
        'medium_priority': medium_priority,
        'low_priority': low_priority,
        'today_completed': today_completed,
        'productivity_pct': productivity_pct,
        'completion_rate': completion_rate,
        'overdue_rate': overdue_rate,
        'avg_completion_days': avg_completion_days,
        'blocked_count': blocked_count,
        'stale_count': len(stale_tasks)
    }

def ai_assistant_response(user_message, user_id):
    """Simple rule-based AI assistant for task management."""
    msg = user_message.lower()
    user = User.query.get(user_id)
    tasks = Task.query.filter((Task.assigned_to == user_id) | (Task.created_by == user_id)).all()

    overdue_count = sum(1 for t in tasks if t.risk_level() == 'critical' and t.status != 'Done')
    high_count = sum(1 for t in tasks if t.priority == 'High' and t.status != 'Done')
    total_pending = sum(1 for t in tasks if t.status != 'Done')

    if any(w in msg for w in ['overdue', 'late', 'delayed', 'behind']):
        if overdue_count == 0:
            return "Great news! You have no overdue tasks right now. Keep up the good work!"
        return f"You have {overdue_count} overdue task(s). I recommend tackling the oldest one first. Would you like help prioritizing?"

    if any(w in msg for w in ['priority', 'important', 'focus', 'urgent', 'high']):
        if high_count == 0:
            return "You have no high-priority pending tasks. Your workload looks manageable!"
        return f"You have {high_count} high-priority task(s) pending. Focus on these before anything else!"

    if any(w in msg for w in ['tip', 'advice', 'help', 'productivity', 'how to']):
        tips = [
            "Try the Pomodoro technique: 25 minutes of focus, then a 5-minute break.",
            "Eat the frog! Tackle your hardest task first thing in the morning.",
            "Break large tasks into smaller subtasks to make progress visible.",
            "Review your tasks at the end of each day and plan for tomorrow.",
            "Use Focus Mode to see only your most critical tasks."
        ]
        return random.choice(tips)

    if any(w in msg for w in ['status', 'progress', 'done', 'complete']):
        done = sum(1 for t in tasks if t.status == 'Done')
        return f"You have completed {done} tasks. {total_pending} task(s) are still pending. You're doing great!"

    if any(w in msg for w in ['hello', 'hi', 'hey', 'greetings']):
        return f"Hello {user.username}! I'm your Smart Task AI. Ask me about your tasks, priorities, or productivity tips!"

    if any(w in msg for w in ['schedule', 'plan', 'today', 'tomorrow']):
        today_tasks = [t for t in tasks if t.due_date == date.today() and t.status != 'Done']
        if today_tasks:
            names = ', '.join([t.title for t in today_tasks[:3]])
            return f"You have {len(today_tasks)} task(s) due today: {names}. Stay focused!"
        return "No tasks due today! It's a good day to get ahead on future work."

    if any(w in msg for w in ['risk', 'danger', 'safe', 'warning']):
        critical = sum(1 for t in tasks if t.risk_level() == 'critical' and t.status != 'Done')
        warning = sum(1 for t in tasks if t.risk_level() == 'warning' and t.status != 'Done')
        return f"Risk check: {critical} critical, {warning} warning. I suggest addressing critical tasks immediately."

    return "I'm here to help! Ask me about your tasks, priorities, overdue items, or productivity tips."


# ============== AUTH ROUTES ==============

@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return render_template('landing.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        if user and bcrypt.check_password_hash(user.password, password):
            session['user_id'] = user.id
            session['username'] = user.username
            session['role'] = user.role
            flash('Login successful!', 'success')
            return redirect(url_for('dashboard'))
        flash('Invalid username or password.', 'error')
    return render_template('login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        role = 'member'  # Force member role; admins are created via init-db only

        if User.query.filter_by(username=username).first():
            flash('Username already exists.', 'error')
            return render_template('signup.html')
        if User.query.filter_by(email=email).first():
            flash('Email already exists.', 'error')
            return render_template('signup.html')

        hashed_pw = bcrypt.generate_password_hash(password).decode('utf-8')
        user = User(username=username, email=email, password=hashed_pw, role=role)
        db.session.add(user)
        db.session.commit()
        flash('Account created! Please login.', 'success')
        return redirect(url_for('login'))
    return render_template('signup.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out successfully.', 'success')
    return redirect(url_for('login'))

@app.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    user = User.query.get(session['user_id'])
    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'profile':
            email = request.form.get('email')
            user.email = email
            db.session.commit()
            flash('Profile updated successfully.', 'success')
        elif action == 'password':
            current_password = request.form.get('current_password')
            new_password = request.form.get('new_password')
            confirm_password = request.form.get('confirm_password')
            if not bcrypt.check_password_hash(user.password, current_password):
                flash('Current password is incorrect.', 'error')
            elif new_password != confirm_password:
                flash('New passwords do not match.', 'error')
            else:
                user.password = bcrypt.generate_password_hash(new_password).decode('utf-8')
                db.session.commit()
                flash('Password updated successfully.', 'success')
        return redirect(url_for('settings'))
    return render_template('settings.html', user=user)

# ============== DASHBOARD ==============

@app.route('/dashboard')
@login_required
def dashboard():
    user = User.query.get(session['user_id'])
    focus_mode = request.args.get('focus') == 'on'

    if focus_mode:
        tasks = Task.query.filter(
            ((Task.assigned_to == session['user_id']) | (Task.priority == 'High')),
            Task.status != 'Done'
        ).all()
    else:
        tasks = Task.query.join(Project).filter(
            (Project.owner_id == session['user_id']) |
            (Project.members.any(id=session['user_id']))
        ).all()

    risk_counts = get_task_risk_counts(tasks)
    insights = get_insights(session['user_id'])

    activities = Activity.query.order_by(Activity.created_at.desc()).limit(15).all()

    # Enrich activities with entity names
    for act in activities:
        if act.entity_type == 'task':
            task = Task.query.get(act.entity_id)
            act.entity_name = task.title if task else 'Unknown'
        elif act.entity_type == 'project':
            proj = Project.query.get(act.entity_id)
            act.entity_name = proj.name if proj else 'Unknown'

    risky_tasks = [t for t in tasks if t.risk_level() != 'safe' and t.status != 'Done']
    risky_tasks.sort(key=lambda x: (x.due_date or date.max))

    # Special sections
    overdue_tasks = [t for t in tasks if t.risk_level() == 'critical' and t.status != 'Done']
    blocked_tasks = [t for t in tasks if t.is_blocked() and t.status != 'Done']
    stale_tasks = [t for t in tasks if t.status == 'Todo' and (date.today() - t.due_date).days > 7]

    # Upcoming deadlines (next 7 days, not done)
    upcoming_deadlines = [t for t in tasks if t.status != 'Done' and 0 <= (t.due_date - date.today()).days <= 7]
    upcoming_deadlines.sort(key=lambda x: x.due_date)

    # AI-generated style message
    high_pending = insights['high_priority']
    overdue_count = insights['overdue']
    blocked_count = insights['blocked_count']
    ai_parts = []
    if high_pending > 0:
        ai_parts.append(f"{high_pending} high-priority task{'s' if high_pending > 1 else ''}")
    if overdue_count > 0:
        ai_parts.append(f"{overdue_count} overdue task{'s' if overdue_count > 1 else ''} needing attention")
    if blocked_count > 0:
        ai_parts.append(f"{blocked_count} blocked task{'s' if blocked_count > 1 else ''}")
    if ai_parts:
        ai_message = "You have " + ", ".join(ai_parts) + " today."
    else:
        ai_message = "Great job! No urgent items on your radar today. Stay productive!"

    return render_template('dashboard.html',
                           user=user,
                           tasks=tasks,
                           risk_counts=risk_counts,
                           insights=insights,
                           activities=activities,
                           risky_tasks=risky_tasks,
                           focus_mode=focus_mode,
                           overdue_tasks=overdue_tasks,
                           blocked_tasks=blocked_tasks,
                           stale_tasks=stale_tasks,
                           upcoming_deadlines=upcoming_deadlines,
                           ai_message=ai_message,
                           date=date)

# ============== PROJECTS ==============

@app.route('/projects')
@login_required
def projects():
    user = User.query.get(session['user_id'])
    if user.role == 'admin':
        all_projects = Project.query.all()
    else:
        all_projects = Project.query.filter(
            (Project.owner_id == user.id) |
            (Project.members.any(id=user.id))
        ).all()

    for proj in all_projects:
        proj.task_count = len(proj.tasks)

    users = User.query.all()
    return render_template('projects.html', projects=all_projects, users=users, user=user)

@app.route('/projects/create', methods=['POST'])
@admin_required
def create_project():
    name = request.form.get('name')
    description = request.form.get('description')
    member_ids = request.form.getlist('members')

    project = Project(name=name, description=description, owner_id=session['user_id'])
    db.session.add(project)
    db.session.commit()

    for mid in member_ids:
        user = User.query.get(int(mid))
        if user:
            project.members.append(user)

    db.session.commit()
    log_activity('created', 'project', project.id, f"Created project '{name}'")
    flash('Project created successfully.', 'success')
    return redirect(url_for('projects'))

@app.route('/projects/<int:project_id>/delete', methods=['POST'])
@login_required
def delete_project(project_id):
    project = Project.query.get_or_404(project_id)
    if project.owner_id != session['user_id'] and session.get('role') != 'admin':
        flash('Permission denied.', 'error')
        return redirect(url_for('projects'))
    db.session.delete(project)
    db.session.commit()
    flash('Project deleted.', 'success')
    return redirect(url_for('projects'))

@app.route('/projects/<int:project_id>/members', methods=['POST'])
@login_required
def manage_members(project_id):
    project = Project.query.get_or_404(project_id)
    if project.owner_id != session['user_id'] and session.get('role') != 'admin':
        flash('Permission denied.', 'error')
        return redirect(url_for('projects'))

    action = request.form.get('action')
    user_id = int(request.form.get('user_id'))
    user = User.query.get(user_id)

    if action == 'add' and user not in project.members:
        project.members.append(user)
        log_activity('assigned', 'project', project.id, f"Added {user.username} to project '{project.name}'")
        flash(f'{user.username} added to project.', 'success')
    elif action == 'remove' and user in project.members:
        project.members.remove(user)
        log_activity('assigned', 'project', project.id, f"Removed {user.username} from project '{project.name}'")
        flash(f'{user.username} removed from project.', 'success')

    db.session.commit()
    return redirect(url_for('projects'))

# ============== TASKS ==============

@app.route('/tasks')
@login_required
def tasks():
    user = User.query.get(session['user_id'])
    project_id = request.args.get('project_id', type=int)
    status_filter = request.args.get('status', '')
    priority_filter = request.args.get('priority', '')
    user_filter = request.args.get('user_id', '')

    query = Task.query.join(Project).filter(
        (Project.owner_id == session['user_id']) |
        (Project.members.any(id=session['user_id']))
    )

    if project_id:
        query = query.filter(Task.project_id == project_id)
    if status_filter:
        query = query.filter(Task.status == status_filter)
    if priority_filter:
        query = query.filter(Task.priority == priority_filter)
    if user_filter:
        query = query.filter(Task.assigned_to == int(user_filter))

    all_tasks = query.order_by(
        db.case(
            (Task.priority == 'High', 1),
            (Task.priority == 'Medium', 2),
            else_=3
        ),
        Task.due_date
    ).all()

    projects_list = Project.query.filter(
        (Project.owner_id == session['user_id']) |
        (Project.members.any(id=session['user_id']))
    ).all()

    users = User.query.all()
    all_tasks_for_dropdown = Task.query.all()
    return render_template('tasks.html',
                           tasks=all_tasks,
                           projects=projects_list,
                           users=users,
                           all_tasks=all_tasks_for_dropdown,
                           user=user,
                           selected_project=project_id,
                           selected_status=status_filter,
                           selected_priority=priority_filter,
                           selected_user=user_filter)

@app.route('/tasks/create', methods=['POST'])
@admin_required
def create_task():
    try:
        title = request.form.get('title', '').strip()
        if not title:
            flash('Title is required.', 'error')
            return redirect(url_for('tasks'))

        description = request.form.get('description', '').strip()
        priority = request.form.get('priority', 'Medium')

        due_date_str = request.form.get('due_date', '')
        if not due_date_str:
            flash('Due date is required.', 'error')
            return redirect(url_for('tasks'))
        try:
            due_date = datetime.strptime(due_date_str, '%Y-%m-%d').date()
        except ValueError:
            flash('Invalid due date format.', 'error')
            return redirect(url_for('tasks'))

        assigned_to_str = request.form.get('assigned_to', '')
        if not assigned_to_str:
            flash('Assigned to is required.', 'error')
            return redirect(url_for('tasks'))
        assigned_to = int(assigned_to_str)

        project_id_str = request.form.get('project_id', '')
        if not project_id_str:
            flash('Project is required.', 'error')
            return redirect(url_for('tasks'))
        project_id = int(project_id_str)

        parent_id = request.form.get('parent_task_id', '')
        parent_task_id = int(parent_id) if parent_id else None

        task = Task(
            title=title,
            description=description or None,
            priority=priority,
            due_date=due_date,
            assigned_to=assigned_to,
            created_by=session['user_id'],
            project_id=project_id,
            parent_task_id=parent_task_id,
            status='Todo'
        )
        db.session.add(task)
        db.session.commit()

        # Log history
        history = TaskHistory(task_id=task.id, new_status='Todo', changed_by=session['user_id'])
        db.session.add(history)
        db.session.commit()

        assigned_user = User.query.get(assigned_to)
        log_activity('created', 'task', task.id, f"Created task '{title}' and assigned to {assigned_user.username}")
        flash('Task created successfully.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error creating task: {str(e)}', 'error')
    return redirect(url_for('tasks'))

@app.route('/tasks/<int:task_id>/update', methods=['POST'])
@login_required
def update_task(task_id):
    task = Task.query.get_or_404(task_id)
    user = User.query.get(session['user_id'])
    is_admin = user.role == 'admin'

    # Members can only update status on tasks assigned to them
    if not is_admin:
        if task.assigned_to != user.id:
            flash('You can only update tasks assigned to you.', 'error')
            return redirect(url_for('tasks'))
        # Members can only change status
        old_status = task.status
        new_status = request.form.get('status')
        if new_status != old_status:
            task.status = new_status
            history = TaskHistory(task_id=task.id, old_status=old_status, new_status=new_status, changed_by=user.id)
            db.session.add(history)
            log_activity('status_changed', 'task', task.id, f"Changed status from '{old_status}' to '{new_status}' for '{task.title}'")
            db.session.commit()
            flash('Status updated successfully.', 'success')
        return redirect(url_for('tasks'))

    # Admin can update everything
    old_status = task.status
    task.title = request.form.get('title')
    task.description = request.form.get('description')
    task.priority = request.form.get('priority')
    task.due_date = datetime.strptime(request.form.get('due_date'), '%Y-%m-%d').date()
    task.assigned_to = int(request.form.get('assigned_to'))
    parent_id = request.form.get('parent_task_id')
    task.parent_task_id = int(parent_id) if parent_id else None
    new_status = request.form.get('status')

    if new_status != old_status:
        task.status = new_status
        history = TaskHistory(task_id=task.id, old_status=old_status, new_status=new_status, changed_by=user.id)
        db.session.add(history)
        log_activity('status_changed', 'task', task.id, f"Changed status from '{old_status}' to '{new_status}' for '{task.title}'")
    else:
        log_activity('updated', 'task', task.id, f"Updated task '{task.title}'")

    db.session.commit()
    flash('Task updated successfully.', 'success')
    return redirect(url_for('tasks'))

@app.route('/tasks/<int:task_id>/delete', methods=['POST'])
@admin_required
def delete_task(task_id):
    task = Task.query.get_or_404(task_id)
    db.session.delete(task)
    db.session.commit()
    log_activity('deleted', 'task', task_id, f"Deleted task '{task.title}'")
    flash('Task deleted.', 'success')
    return redirect(url_for('tasks'))

@app.route('/tasks/<int:task_id>')
@login_required
def task_detail(task_id):
    task = Task.query.get_or_404(task_id)
    histories = TaskHistory.query.filter_by(task_id=task_id).order_by(TaskHistory.created_at.desc()).all()
    user = User.query.get(session['user_id'])
    return render_template('task_detail.html', task=task, histories=histories, user=user)

# ============== CHAT ROUTES ==============

@app.route('/chat')
@login_required
def chat():
    user = User.query.get(session['user_id'])
    users = User.query.filter(User.id != user.id).all()
    groups = ChatGroup.query.all()

    # Mark chat as read
    chat_status = UserChatStatus.query.filter_by(user_id=user.id).first()
    if not chat_status:
        chat_status = UserChatStatus(user_id=user.id)
        db.session.add(chat_status)
    chat_status.last_read_at = datetime.utcnow()
    db.session.commit()

    # Get selected chat type and id
    chat_type = request.args.get('type', 'ai')  # ai, dm, group, broadcast
    chat_id = request.args.get('id', type=int)

    messages = []
    selected_user = None
    selected_group = None
    ai_mode = False

    if chat_type == 'dm' and chat_id:
        selected_user = User.query.get(chat_id)
        messages = Message.query.filter(
            ((Message.sender_id == user.id) & (Message.receiver_id == chat_id)) |
            ((Message.sender_id == chat_id) & (Message.receiver_id == user.id))
        ).order_by(Message.created_at.asc()).all()
    elif chat_type == 'group' and chat_id:
        selected_group = ChatGroup.query.get(chat_id)
        if selected_group and user in selected_group.members:
            messages = Message.query.filter_by(group_id=chat_id).order_by(Message.created_at.asc()).all()
        else:
            flash('You are not a member of this group.', 'error')
            return redirect(url_for('chat'))
    elif chat_type == 'broadcast':
        messages = Message.query.filter_by(is_broadcast=True).order_by(Message.created_at.asc()).all()
    elif chat_type == 'ai':
        ai_mode = True
        messages = Message.query.filter_by(sender_id=user.id, receiver_id=user.id).order_by(Message.created_at.asc()).all()

    return render_template('chat.html',
                           users=users,
                           groups=groups,
                           user=user,
                           messages=messages,
                           chat_type=chat_type,
                           chat_id=chat_id,
                           selected_user=selected_user,
                           selected_group=selected_group,
                           ai_mode=ai_mode)

@app.route('/chat/send', methods=['POST'])
@login_required
def send_message():
    user = User.query.get(session['user_id'])
    content = request.form.get('content', '').strip()
    chat_type = request.form.get('chat_type', 'dm')
    chat_id = request.form.get('chat_id', type=int)

    if not content:
        flash('Message cannot be empty.', 'error')
        return redirect(url_for('chat', type=chat_type, id=chat_id))

    if chat_type == 'ai':
        # Save user message
        msg = Message(content=content, sender_id=user.id, receiver_id=user.id)
        db.session.add(msg)
        db.session.commit()

        # Get AI response
        ai_reply = ai_assistant_response(content, user.id)
        ai_msg = Message(content=f"[AI Assistant] {ai_reply}", sender_id=user.id, receiver_id=user.id)
        db.session.add(ai_msg)
        db.session.commit()
        return redirect(url_for('chat', type='ai'))

    if chat_type == 'dm':
        msg = Message(content=content, sender_id=user.id, receiver_id=chat_id)
        db.session.add(msg)
        db.session.commit()
        return redirect(url_for('chat', type='dm', id=chat_id))

    if chat_type == 'group':
        group = ChatGroup.query.get(chat_id)
        if group and user in group.members:
            msg = Message(content=content, sender_id=user.id, group_id=chat_id)
            db.session.add(msg)
            db.session.commit()
            return redirect(url_for('chat', type='group', id=chat_id))
        flash('You are not a member of this group.', 'error')
        return redirect(url_for('chat'))

    if chat_type == 'broadcast':
        if user.role != 'admin':
            flash('Only admin can send broadcast messages.', 'error')
            return redirect(url_for('chat'))
        msg = Message(content=content, sender_id=user.id, is_broadcast=True)
        db.session.add(msg)
        db.session.commit()
        return redirect(url_for('chat', type='broadcast'))

    return redirect(url_for('chat'))

@app.route('/chat/group/create', methods=['POST'])
@admin_required
def create_group():
    name = request.form.get('name')
    member_ids = request.form.getlist('members')

    group = ChatGroup(name=name, created_by=session['user_id'])
    db.session.add(group)
    db.session.commit()

    # Add creator
    creator = User.query.get(session['user_id'])
    group.members.append(creator)

    for mid in member_ids:
        user = User.query.get(int(mid))
        if user:
            group.members.append(user)

    db.session.commit()
    flash(f"Group '{name}' created successfully.", 'success')
    return redirect(url_for('chat', type='group', id=group.id))

@app.route('/chat/group/<int:group_id>/members', methods=['POST'])
@admin_required
def manage_group_members(group_id):
    group = ChatGroup.query.get_or_404(group_id)
    action = request.form.get('action')
    user_id = int(request.form.get('user_id'))
    user = User.query.get(user_id)

    if action == 'add' and user not in group.members:
        group.members.append(user)
        flash(f'{user.username} added to group.', 'success')
    elif action == 'remove' and user in group.members:
        group.members.remove(user)
        flash(f'{user.username} removed from group.', 'success')

    db.session.commit()
    return redirect(url_for('chat', type='group', id=group_id))

# ============== INITIAL SETUP ==============

@app.route('/init-db')
def init_db():
    db.create_all()
    # Create admin user if not exists
    if not User.query.filter_by(username='admin').first():
        hashed = bcrypt.generate_password_hash('admin123').decode('utf-8')
        admin = User(username='admin', email='admin@example.com', password=hashed, role='admin')
        db.session.add(admin)
        db.session.commit()
        return 'Database initialized with admin user (admin/admin123)'
    return 'Database already initialized.'

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
