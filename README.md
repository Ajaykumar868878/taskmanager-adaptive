# Smart Task - Adaptive Task Manager

> **An adaptive productivity platform that identifies risks, improves collaboration, and helps teams focus on high-impact work.**

---

## Problem Statement

Modern teams struggle with:
- **Missed deadlines** due to poor visibility of task urgency
- **Fragmented communication** across multiple tools
- **No early warning system** for tasks approaching deadlines
- **Lack of accountability** with unclear ownership and status tracking
- **No dependency awareness** — teams start tasks that are blocked by incomplete work

## Solution

**Smart Task** solves these problems with an intelligent, all-in-one task management platform:

- **Automatic Risk Detection** — Tasks are classified as Critical, Warning, or Safe based on real-time due date analysis
- **Built-in Chat & AI Assistant** — Team communication, group chats, DMs, and broadcast announcements in one place, plus an AI helper for productivity tips
- **Task Dependencies** — Block tasks until their parent tasks are complete, preventing wasted effort
- **Admin-Only Control** — Only admins can create projects, assign tasks, and manage team structure
- **Focus Mode** — Instantly filter to see only what matters: your tasks, high-priority items, and risks
- **Dashboard Insights** — AI-generated summaries, productivity metrics, and upcoming deadline timelines

---

## Architecture

```
+------------------+     +------------------+     +------------------+
|   Flask Server   |---->|   SQLite DB      |     |   Jinja2/HTML    |
|   (Python 3.12)  |     |   (Local file)   |     |   (Bootstrap 5)  |
+------------------+     +------------------+     +------------------+
         |                        |                        |
         |   Flask-SQLAlchemy     |   ORM Models           |   CSS Custom Theme
         |   Flask-Bcrypt         |   User, Project, Task  |   Inter Font
         |   Sessions             |   ChatGroup, Message   |   Responsive Cards
         v                        v                        v
    Auth & Role           Data Persistence            UI Rendering
    Admin/Member          Cascade Deletes             Light Blue/Cyan
    Decorators            Risk Calculation            Professional Look
```

### Database Schema

| Entity      | Key Fields                                                  |
|-------------|------------------------------------------------------------|
| **User**    | username, email, password (bcrypt), role (admin/member)    |
| **Project** | name, description, owner_id, members (many-to-many)      |
| **Task**    | title, priority, due_date, status, assignee, parent_task  |
| **TaskHistory** | task_id, old_status, new_status, changed_by, timestamp |
| **Activity**| action, entity_type, description, user_id, timestamp       |
| **ChatGroup** | name, creator, members (many-to-many)                    |
| **Message** | content, sender, receiver, group, is_broadcast, timestamp |

---

## Features

### Core Task Management
- Create, edit, delete tasks with title, description, priority, due date, and assignee
- Status flow: **Todo &rarr; In Progress &rarr; Done**
- Task history tracking with timestamps and who made each change
- Task dependencies: set a parent task, and child tasks are marked as **blocked** until the parent is complete

### Risk Detection
- **Critical** (red): Task is overdue and not done
- **Warning** (orange): Task is due within 2 days
- **Safe** (green): Task has more than 2 days remaining or is completed

### Dashboard
- **Hero statement** with user greeting
- **AI Insight banner** with personalized daily summary
- **Stats cards**: Team Productivity %, Completion Rate, Overdue Rate, Avg Completion Time
- **Risk Overview** with progress bars
- **Priority Breakdown** (High/Medium/Low)
- **Special Sections**: Overdue Tasks, Blocked Tasks, Stale Tasks
- **Upcoming Deadlines Timeline** (next 7 days, scrollable cards)
- **Risky Tasks table**
- **Activity Feed**
- **Focus Mode toggle**

### Team Collaboration
- **Chat system**: AI Assistant, Direct Messages, Group Chats, Broadcast Announcements
- **Group creation** (admin only) with member selection
- **Message timestamps** on all chats
- **Broadcast** visible to everyone, but only admins can post

### Role-Based Access Control
| Action | Admin | Member |
|--------|-------|--------|
| Create Project | Yes | No |
| Delete Project | Yes | No |
| Create Task | Yes | No |
| Delete Task | Yes | No |
| Edit Task (full) | Yes | No |
| Change Status (own tasks) | Yes | Yes |
| View Chat / AI | Yes | Yes |
| Send Broadcast | Yes | No |
| Create Group | Yes | No |

---

## Screenshots

*(Add screenshots of: Dashboard, Task List, Chat, Project Management)*

| Screen | Description |
|--------|-------------|
| Dashboard | Hero statement, AI insights, stats, risk overview, upcoming deadlines |
| Tasks | Filterable table with risk badges, priority colors, edit/delete |
| Task Detail | Info cards, dependency chain, blocked warning, history timeline |
| Projects | Card grid with member management, delete control |
| Chat | Sidebar with AI, DMs, groups, broadcasts; message bubbles with timestamps |

---

## Future Scope

- [ ] **Gemini AI Integration** — Replace rule-based AI with Google Gemini for smarter, context-aware responses
- [ ] **Email Notifications** — Alerts for overdue tasks, new assignments, and broadcast messages
- [ ] **File Attachments** — Upload files to tasks and chat messages
- [ ] **Recurring Tasks** — Auto-create tasks on a schedule (daily, weekly, monthly)
- [ ] **Kanban Board View** — Drag-and-drop task status management
- [ ] **Real-time Chat** — WebSocket-based live messaging without page refresh
- [ ] **Dark Mode** — Toggle between light and dark themes
- [ ] **Export Reports** — PDF/CSV export of task analytics and project summaries
- [ ] **Multi-language Support** — Internationalization for global teams

---

## Tech Stack

| Layer | Technology |
|-------|------------|
| Backend | Flask, Flask-SQLAlchemy, Flask-Bcrypt |
| Database | SQLite (zero-config, auto-creates on startup) |
| Frontend | Bootstrap 5, Bootstrap Icons, Custom CSS |
| Font | Inter (Google Fonts) |
| Theme | Light blue / cyan professional aesthetic |

---

## Setup Instructions

### 1. Prerequisites
- Python 3.9+

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Run the Application
```bash
python app.py
```

### 4. Initialize Database
Visit `http://127.0.0.1:5000/init-db` to create tables and a default admin user.

### 5. Login
- **Admin**: `admin` / `admin123`
- Or sign up with a new account (members only)

---

## Project Structure

```
smart-task-manager/
  app.py
  requirements.txt
  README.md
  instance/
    smart_task_manager.db
  templates/
    base.html
    login.html
    signup.html
    dashboard.html
    projects.html
    tasks.html
    task_detail.html
    chat.html
```

---

## Default Credentials

| Role | Username | Password |
|------|----------|----------|
| Admin | `admin` | `admin123` |
| Member | Sign up | Your choice |

---

*Designed as an adaptive productivity platform for intelligent collaborative workflows.*
