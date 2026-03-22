let userId = localStorage.getItem('user_id');

document.addEventListener('DOMContentLoaded', () => {
    if (!userId) {
        new bootstrap.Modal('#loginModal').show();
    } else {
        loadData();
    }
});

function login() {
    const input = document.getElementById('login-user-id').value.trim();
    if (input) {
        userId = input;
        localStorage.setItem('user_id', userId);
        loadData();
        bootstrap.Modal.getInstance(document.getElementById('loginModal')).hide();
    }
}

function handleKeyPress(event) {
    if (event.key === 'Enter') {
        sendMessage();
    }
}

async function loadData() {
    if (!userId) return;
    await Promise.all([
        fetchProfile(),
        fetchTasks(),
        fetchEvents(),
        fetchSchedules()
    ]);
}

async function fetchProfile() {
    try {
        const res = await fetch(`/api/profile/${userId}`);
        const data = await res.json();

        if (data.exists) {
            updateProfile(data.profile);
            updateGoal(data.profile.id); // Hack: need goal endpoint, but we can reuse this flow
        } else {
            // First time logic handled by chat
        }
    } catch (e) {
        console.error("Profile load failed", e);
    }
}

function updateProfile(profile) {
    document.getElementById('username').textContent = `Hero (${profile.username})`;
    document.getElementById('level').textContent = profile.level;
    document.getElementById('streak').textContent = profile.streak_days;
    document.getElementById('current-xp').textContent = profile.current_xp;
    document.getElementById('next-level-xp').textContent = profile.xp_to_next_level;
    document.getElementById('tasks-completed').textContent = profile.tasks_completed;
    document.getElementById('goals-completed').textContent = profile.goals_completed;

    const xpPercent = (profile.current_xp / profile.xp_to_next_level) * 100;
    document.getElementById('xp-bar').style.width = `${xpPercent}%`;
}

async function fetchTasks() {
    const res = await fetch(`/api/tasks/${userId}?status=pending`);
    const data = await res.json();
    const taskList = document.getElementById('task-list');
    taskList.innerHTML = '';

    data.tasks.forEach(task => {
        const item = document.createElement('div');
        item.className = `list-group-item list-group-item-action d-flex justify-content-between align-items-center ${task.is_challenge ? 'bg-light-warning' : ''}`;

        item.innerHTML = `
            <div>
                <h6 class="mb-1">${task.title} <span class="badge bg-${getDifficultyColor(task.difficulty)}">${task.difficulty}</span></h6>
                <small class="text-muted">${task.description || ''}</small>
            </div>
            <div>
                <span class="badge bg-secondary">+${task.xp_reward} XP</span>
                <button class="btn btn-sm btn-success ms-2" onclick="completeTask('${task.id}')">✓</button>
            </div>
        `;
        taskList.appendChild(item);
    });
}

function getDifficultyColor(diff) {
    switch(diff) {
        case 'easy': return 'success';
        case 'medium': return 'info';
        case 'hard': return 'warning';
        case 'epic': return 'danger';
        default: return 'secondary';
    }
}

async function fetchEvents() {
    const res = await fetch(`/api/events/${userId}?limit=10`);
    const data = await res.json();
    const list = document.getElementById('events-list');
    list.innerHTML = '';

    data.events.forEach(event => {
        const item = document.createElement('li');
        item.className = 'list-group-item small';
        const descriptionHtml = typeof marked !== 'undefined' ? marked.parse(event.description) : event.description;
        item.innerHTML = `${new Date(event.created_at).toLocaleTimeString()} - ${descriptionHtml}`;
        list.appendChild(item);
    });
}

// Update Goal - separate function not fully implemented in API yet properly
async function updateGoal(userId) {
    const res = await fetch(`/api/goals/${userId}`);
    const data = await res.json();
    const container = document.getElementById('current-goal-container');

    if (data.goals.length > 0) {
        const goal = data.goals[0]; // Just take first
        container.innerHTML = `
            <h6>${goal.title}</h6>
            <p>${goal.description}</p>
            <div class="progress">
                <div class="progress-bar bg-success" style="width: 50%"></div>
            </div>
            <small>Deadline: ${goal.deadline ? new Date(goal.deadline).toLocaleDateString() : 'None'}</small>
        `;
    } else {
        container.innerHTML = '<p class="text-muted">No active goal.</p>';
    }
}

async function sendMessage() {
    const input = document.getElementById('user-input');
    const message = input.value.trim();
    if (!message) return;

    appendMessage(message, 'user');
    input.value = '';

    try {
        const res = await fetch('/api/chat', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ user_id: userId, message: message })
        });

        const data = await res.json();

        if (data.success) {
            appendMessage(data.message || "Action processed.", 'agent');
            loadData(); // Refresh UI
        } else {
            appendMessage("Error processing request.", 'agent-error');
        }
    } catch (e) {
        appendMessage("Network error.", 'agent-error');
    }
}

function appendMessage(text, type) {
    const box = document.getElementById('chat-box');
    const msg = document.createElement('div');
    msg.className = `chat-message ${type}`;
    if (typeof marked !== 'undefined') {
        msg.innerHTML = marked.parse(text);
    } else {
        msg.textContent = text;
    }
    box.appendChild(msg);
    box.scrollTop = box.scrollHeight;
}

// Task Completion
async function completeTask(taskId) {
    try {
        const res = await fetch(`/api/tasks/complete/${taskId}`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ user_id: userId })
        });

        const data = await res.json();
        if (data.success) {
            // Show celebration logic here?
            fetchTasks();
            fetchProfile();
            fetchEvents();
            appendMessage(`✅ Completed: ${data.message}`, 'agent');
        }
    } catch (e) {
        console.error(e);
    }
}

// Schedules
async function fetchSchedules() {
    try {
        const res = await fetch(`/api/schedules/${userId}`);
        const data = await res.json();
        const tbody = document.getElementById('schedule-list');
        tbody.innerHTML = '';
        
        data.schedules.forEach(schedule => {
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td>${schedule.name}</td>
                <td><span class="badge bg-${schedule.job_type === 'reflector' ? 'info' : 'primary'}">${schedule.job_type}</span></td>
                <td><code>${schedule.cron_expression}</code></td>
                <td><small>${schedule.last_run_at || 'Never'}</small></td>
                <td>
                    <button class="btn btn-sm btn-danger" onclick="deleteSchedule('${schedule.id}')">Delete</button>
                </td>
            `;
            tbody.appendChild(tr);
        });
    } catch (e) {
        console.error("Schedule fetch failed", e);
    }
}

async function createSchedule() {
    const name = document.getElementById('job-name').value;
    const type = document.getElementById('job-type').value;
    const cron = document.getElementById('cron-expression').value;
    const message = document.getElementById('job-message').value;
    
    if (!name || !cron) {
        alert("Please fill in all required fields (Name and Cron Expression).");
        return;
    }
    
    if (type === 'chat' && !message) {
        alert("For Chat jobs, you must provide a message.");
        return;
    }
    
    try {
        const res = await fetch('/api/schedules', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                user_id: userId,
                name: name,
                job_type: type,
                cron_expression: cron,
                message_content: type === 'chat' ? message : null
            })
        });
        
        const data = await res.json();
        if (data.success) {
            alert("Schedule created successfully!");
            // Hide modal properly
            const modalEl = document.getElementById('addScheduleModal');
            const modal = bootstrap.Modal.getInstance(modalEl);
            modal.hide();
            
            // Clear form
            document.getElementById('add-schedule-form').reset();
            toggleMessageField(); // Ensure visibility matches default selection
            
            fetchSchedules();
        } else {
            alert('Failed to create schedule: ' + (data.error || 'Unknown error'));
        }
    } catch (e) {
        console.error(e);
        alert("An error occurred while creating the schedule.");
    }
}

async function deleteSchedule(jobId) {
    if (!confirm('Are you sure you want to delete this schedule?')) return;
    try {
        await fetch(`/api/schedules/${jobId}`, { method: 'DELETE' });
        fetchSchedules();
    } catch (e) {
        console.error(e);
    }
}

function toggleMessageField() {
    const type = document.getElementById('job-type').value;
    const field = document.getElementById('message-field');
    if (type === 'chat') {
        field.style.display = 'block';
    } else {
        field.style.display = 'none';
    }
}
