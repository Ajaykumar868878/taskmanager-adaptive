# Smart Task Manager

An Adaptive Smart Task Manager with Risk Detection & Activity Insights built with Flask and MySQL.

## Features

- **Authentication**: Signup, Login, Logout with session-based protection
- **User Roles**: Admin (full control) and Member (limited access)
- **Projects**: Create projects, add/remove members, view project stats
- **Task Management**: Create, edit, delete tasks with priority, due date, assignee, and status flow (Todo -> In Progress -> Done)
- **Risk Detection**: Automatic classification (Critical/Warning/Safe) based on due dates
- **Activity Feed**: Real-time tracking of all actions (task created, updated, status changed, assigned)
- **Task History**: Timeline view of status changes for each task
- **Focus Mode**: Toggle to show only your tasks, high-priority tasks, and risky tasks
- **Insights**: Dashboard analytics with stats, priority breakdown, and daily summaries
- **Filters**: Filter tasks by project, status, priority, and assigned user

## Tech Stack

- **Backend**: Flask, Flask-SQLAlchemy, Flask-Bcrypt
- **Database**: MySQL (via PyMySQL)
- **Frontend**: Bootstrap 5, Bootstrap Icons, custom CSS

## Setup Instructions

### 1. Prerequisites

- Python 3.9+
- MySQL Server running locally

### 2. Create MySQL Database

Open MySQL and run:

```sql
CREATE DATABASE smart_task_manager;
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Database Connection

Edit `app.py` and update the `SQLALCHEMY_DATABASE_URI` if your MySQL credentials differ:

```python
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://username:password@localhost/smart_task_manager'
```

Default is `root` user with no password.

### 5. Initialize Database

```bash
python app.py
```

Then visit `http://127.0.0.1:5000/init-db` to create tables and a default admin user.

### 6. Login

- **Admin**: `admin` / `admin123`
- Or sign up with a new account

## Project Structure

```
smart task manager/
  app.py                 # Main Flask application
  requirements.txt       # Python dependencies
  templates/
    base.html            # Base layout with navbar
    login.html           # Login page
    signup.html          # Signup page
    dashboard.html       # Dashboard with stats, risks, activity, insights
    projects.html        # Project list and management
    tasks.html           # Task list with filters
    task_detail.html     # Task detail with history timeline
```

## Default Admin Credentials

- **Username**: `admin`
- **Password**: `admin123`
- **Role**: Admin

## Risk Logic

- **Critical**: Task is overdue and not done
- **Warning**: Task is due within 2 days and not done
- **Safe**: Task has more than 2 days remaining or is completed
# taskmanager-adaptive
