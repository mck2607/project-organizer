// Global state
let taskData = { assigned_by_todos: [], assigned_to_todos: [] };
const userId = document.getElementById('take_username').value; // Get from hidden input
const userName = document.getElementById('take_name').value; // Get from hidden input
let activeFilter = "assigned_by";
let selectedTask = null;

// Utility functions
function formatDate(dateString) {
    if (!dateString) return "Not completed";
    const date = new Date(dateString);
    return date.toLocaleDateString("en-US", {
        year: "numeric",
        month: "short",
        day: "numeric"
    });
}

function getStatusClass(status) {
    const map = {
        done: "completed",
        completed: "completed",
        todo: "todo",
        in_progress: "progress",
        progress: "progress"
    };
    return map[status.toLowerCase()] || "todo";
}

function getStatusLabel(status) {
    const map = {
        done: "Completed",
        completed: "Completed",
        todo: "To Do",
        in_progress: "In Progress",
        progress: "In Progress"
    };
    return map[status.toLowerCase()] || status.charAt(0).toUpperCase() + status.slice(1);
}

function getInitials(name) {
    if (!name) return "??";
    return name.split(' ').map(n => n[0]).join('').toUpperCase().substring(0, 2);
}

const API = {
    async fetchAll() {
        const res = await fetch(`/show-esclated-todo_fetch/${encodeURIComponent(userId)}`);
        if (!res.ok) throw new Error('Failed to fetch tasks');
        return res.json();
    },
    async update(task_id, data) {
        const res = await fetch(`/api/escalated-todos/${task_id}`, {
            method: "PATCH",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify(data)
        });
        if (!res.ok) throw new Error('Failed to update task');
        return res.json();
    },
    async addResponse(task_id, response_text, user_name) {
        const res = await fetch(`/api/escalated-todos/${task_id}/responses`, {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({
                response_text: response_text,
                user_id: userId,
                user_name: user_name
            })
        });
        if (!res.ok) throw new Error('Failed to add response');
        return res.json();
    },
    async updateResponse(task_id, response_id, response_text) {
        const res = await fetch(`/api/escalated-todos/${task_id}/responses/${response_id}`, {
            method: "PATCH",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({
                response_text: response_text
            })
        });
        if (!res.ok) throw new Error('Failed to update response');
        return res.json();
    }
};

// Task card template
function createTaskCard(task) {
    const statusClass = getStatusClass(task.status);
    const statusLabel = getStatusLabel(task.status);
    const isAssignedToMe = activeFilter === "assigned_to";

    return `
        <div class="task-card" onclick="openTaskPanel(${task.todo_id})">
            <div class="task-header">
                <h3 class="task-title">${task.todo_title}</h3>
                <span class="status-badge ${statusClass}">${statusLabel}</span>
            </div>

            <div class="task-project">
                <i data-lucide="folder" class="task-project-icon"></i>
                <span>${task.project_name || "No Project"}</span>
            </div>

            <div class="task-assignee">
                <div class="task-assignee-avatar">
                    ${getInitials(isAssignedToMe ? task.created_by_name : task.assignee_name)}
                </div>
                <span>
                    ${isAssignedToMe ? `Assigned by ${task.created_by_name}` : `Assigned to ${task.assignee_name}`}
                </span>
            </div>

            <div class="task-dates">
                <span>Created: ${formatDate(task.todo_created_date)}</span>
                ${task.todo_completed_date ? `<span>Completed: ${formatDate(task.todo_completed_date)}</span>` : ''}
            </div>
        </div>
    `;
}

// Render board
function renderBoard() {
    const currentTasks = activeFilter === "assigned_by" ? taskData.assigned_by_todos : taskData.assigned_to_todos;

    const todoTasks = currentTasks.filter(t => t.status.toLowerCase() === 'todo');
    const progressTasks = currentTasks.filter(t => t.status.toLowerCase() === 'in_progress' || t.is_started);
    const completedTasks = currentTasks.filter(t => t.status.toLowerCase() === 'done' || t.status.toLowerCase() === 'completed');

    document.getElementById('todoCount').textContent = todoTasks.length;
    document.getElementById('progressCount').textContent = progressTasks.length;
    document.getElementById('completedCount').textContent = completedTasks.length;

    document.getElementById('todoColumn').innerHTML = todoTasks.map(createTaskCard).join('');
    document.getElementById('progressColumn').innerHTML = progressTasks.map(createTaskCard).join('');
    document.getElementById('completedColumn').innerHTML = completedTasks.map(createTaskCard).join('');

    // Show/hide empty state
    if (currentTasks.length === 0) {
        document.getElementById('boardContainer').style.display = 'none';
        document.getElementById('emptyState').style.display = 'block';
        document.getElementById('emptyDescription').textContent =
            activeFilter === "assigned_by" ? "You haven't assigned any tasks yet." : "No tasks have been assigned to you.";
    } else {
        document.getElementById('boardContainer').style.display = 'flex';
        document.getElementById('emptyState').style.display = 'none';
    }

    // Refresh icons
    lucide.createIcons();
}

// Open task panel
function openTaskPanel(taskId) {
    const currentTasks = activeFilter === "assigned_by" ? taskData.assigned_by_todos : taskData.assigned_to_todos;
    selectedTask = currentTasks.find(t => t.todo_id === taskId);

    if (!selectedTask) return;

    const isAssignedToMe = activeFilter === "assigned_to";
    const canInteract = isAssignedToMe && selectedTask.status !== "completed" && selectedTask.status !== "done";

    document.getElementById('panelTitle').textContent = `Task #${selectedTask.todo_title}`;

    const panelContent = document.getElementById('panelContent');
    panelContent.innerHTML = `
        <div class="panel-section">
            <div class="section-title">
                <i data-lucide="info" class="section-title-icon"></i>
                Task Information
            </div>
            <div class="property-grid">
                <div class="property-item">
                    <span class="property-label">Creator:</span>
                    <span class="property-value">
                        <div class="task-assignee-avatar" style="width: 16px; height: 16px; font-size: 8px;">
                            ${getInitials(selectedTask.created_by_name ? selectedTask.created_by_name : "Unknown")}
                        </div>
                        ${selectedTask.created_by_name ? selectedTask.created_by_name : "Unknown"}
                    </span>
                </div>
                <div class="property-item">
                    <span class="property-label">Status:</span>
                    <span class="property-value">
                        <span class="status-badge ${getStatusClass(selectedTask.status)}">${getStatusLabel(selectedTask.status)}</span>
                    </span>
                </div>
                <div class="property-item">
                    <span class="property-label">Project:</span>
                    <span class="property-value">
                        <i data-lucide="folder" style="width: 14px; height: 14px;"></i>
                        ${selectedTask.project_name || "No Project"}
                    </span>
                </div>
                <div class="property-item">
                    <span class="property-label">${isAssignedToMe ? 'Assigned by:' : 'Assigned to:'}</span>
                    <span class="property-value">
                        <div class="task-assignee-avatar" style="width: 16px; height: 16px; font-size: 8px;">
                            ${getInitials(isAssignedToMe ? selectedTask.created_by_name : selectedTask.assignee_name)}
                        </div>
                        ${isAssignedToMe ? selectedTask.created_by_name : selectedTask.assignee_name}
                    </span>
                </div>
                <div class="property-item">
                    <span class="property-label">Created:</span>
                    <span class="property-value">
                        <i data-lucide="calendar" style="width: 14px; height: 14px;"></i>
                        ${formatDate(selectedTask.todo_created_date)}
                    </span>
                </div>
                <div class="property-item">
                    <span class="property-label">Completed:</span>
                    <span class="property-value">
                        <i data-lucide="calendar-check" style="width: 14px; height: 14px;"></i>
                        ${selectedTask.todo_completed_date ? formatDate(selectedTask.todo_completed_date) : "Not completed"}
                    </span>
                </div>
                <div class="property-item">
                    <span class="property-label">Description:</span>
                    <span class="property-value">
                        ${selectedTask.todo_descr ? selectedTask.todo_descr : "Not Description..."}
                    </span>
                </div>
            </div>
        </div>

        ${canInteract ? `
            <div class="panel-section">
                <div class="section-title">
                    <i data-lucide="settings" class="section-title-icon"></i>
                    Actions
                </div>
                <div class="checkbox-container">
                    <div class="checkbox ${selectedTask.is_started ? 'checked' : ''}"
                         onclick="toggleTaskStart(${selectedTask.todo_id}, ${!selectedTask.is_started})">
                    </div>
                    <span>Mark as Started</span>
                </div>
                <div style="display: flex; gap: 12px; margin-top: 16px;">
                    ${selectedTask.status !== 'completed' && selectedTask.status !== 'done' ? `
                        <button class="btn btn-success" onclick="completeTask(${selectedTask.todo_id})">
                            <i data-lucide="check-circle" style="width: 14px; height: 14px;"></i>
                            Mark Complete
                        </button>
                    ` : ''}
                    <button class="btn btn-warning" onclick="forwardTask(${selectedTask.todo_id})">
                        <i data-lucide="forward" style="width: 14px; height: 14px;"></i>
                        Forward
                    </button>
                </div>
            </div>
        ` : ''}

        <div class="panel-section">
            <div class="section-title">
                <i data-lucide="message-circle" class="section-title-icon"></i>
                Responses (${selectedTask.responses ? selectedTask.responses.length : 0})
            </div>

            ${selectedTask.responses && selectedTask.responses.length > 0 ? `
                <div style="margin-bottom: 20px;">
                    ${selectedTask.responses.map((response, index) => `
                        <div class="response-item">
                            <div class="response-header">
                                <span>Response ${index + 1} • ${formatDate(response.created_at)} • By: ${response.user_name || 'Unknown'}</span>
                            </div>
                            <div class="response-text">${response.response_text}</div>
                            ${response.updated_at && response.updated_at !== response.created_at ? `
                                <div style="font-size: 12px; color: var(--text-tertiary); margin-top: 8px;">
                                    Last updated: ${formatDate(response.updated_at)}
                                </div>
                            ` : ''}
                        </div>
                    `).join('')}
                </div>
            ` : '<p style="color: var(--text-secondary); font-style: italic; margin-bottom: 20px;">No responses yet.</p>'}

            ${canInteract ? `
                <form onsubmit="addResponse(event, ${selectedTask.todo_id})">
                    <div class="form-group">
                        <label class="form-label">Add Response:</label>
                        <textarea
                            class="form-textarea"
                            placeholder="Provide updates, questions, or status on this task..."
                            required
                        ></textarea>
                    </div>
                    <button type="submit" class="btn btn-primary">
                        <i data-lucide="plus" style="width: 14px; height: 14px;"></i>
                        Add Response
                    </button>
                </form>
            ` : ''}
        </div>

        <!-- Forward Task Form (hidden by default) -->
        <div class="panel-section" id="forwardForm" style="display: none;">
            <div class="section-title">
                <i data-lucide="forward" class="section-title-icon"></i>
                Forward Task
            </div>
            <form onsubmit="submitForwardTask(event, ${selectedTask.todo_id})">
                <div class="form-group">
                    <label class="form-label">Forward to:</label>
                    <select id="forwardSelect" class="form-select" required>
                        <option value="">Select a user</option>
                    </select>
                </div>
                <div class="form-group">
                    <label class="form-label">Reason for forwarding:</label>
                    <textarea
                        id="forwardReason"
                        class="form-textarea"
                        placeholder="Explain why you're forwarding this task..."
                        required
                    ></textarea>
                </div>
                <div style="display: flex; gap: 12px;">
                    <button type="submit" class="btn btn-primary">
                        <i data-lucide="send" style="width: 14px; height: 14px;"></i>
                        Forward Task
                    </button>
                    <button type="button" class="btn btn-secondary" onclick="hideForwardForm()">
                        Cancel
                    </button>
                </div>
            </form>
        </div>
    `;

    // Show panel
    document.getElementById('sidePanelOverlay').classList.add('active');
    document.getElementById('sidePanel').classList.add('active');

    // Refresh icons
    lucide.createIcons();
}

// Close task panel
function closeTaskPanel() {
    document.getElementById('sidePanelOverlay').classList.remove('active');
    document.getElementById('sidePanel').classList.remove('active');
    selectedTask = null;
}

// Task interaction functions
async function toggleTaskStart(taskId, isStarted) {
    try {
        await API.update(taskId, { is_started: isStarted, status: isStarted ? 'in_progress' : 'todo' });

        // Update local data
        const currentTasks = activeFilter === "assigned_by" ? taskData.assigned_by_todos : taskData.assigned_to_todos;
        const task = currentTasks.find(t => t.todo_id === taskId);
        if (task) {
            task.is_started = isStarted;
            if (isStarted) {
                task.status = 'in_progress';
            }
        }

        showNotification('Task status updated!', 'success');
        renderBoard();
        if (selectedTask && selectedTask.todo_id === taskId) {
            openTaskPanel(taskId);
        }
    } catch (error) {
        console.error('Error updating task start status:', error);
        showNotification('Error updating task status', 'error');
    }
}

async function completeTask(taskId) {
    if (!confirm('Are you sure you want to mark this task as completed?')) {
        return;
    }

    try {
        const completedDate = new Date().toISOString().slice(0, 19).replace('T', ' ');
        await API.update(taskId, { status: 'completed', todo_completed_date: completedDate });

        // Update local data
        const currentTasks = activeFilter === "assigned_by" ? taskData.assigned_by_todos : taskData.assigned_to_todos;
        const task = currentTasks.find(t => t.todo_id === taskId);
        if (task) {
            task.status = 'completed';
            task.todo_completed_date = completedDate;
        }

        showNotification('Task completed successfully!', 'success');
        renderBoard();
        if (selectedTask && selectedTask.todo_id === taskId) {
            openTaskPanel(taskId);
        }
    } catch (error) {
        console.error('Error completing task:', error);
        showNotification('Error completing task', 'error');
    }
}

// Response management functions
async function addResponse(event, taskId) {
    event.preventDefault();
    const form = event.target;
    const responseText = form.querySelector('textarea').value;

    if (!responseText.trim()) {
        showNotification('Please provide a response before submitting.', 'warning');
        return;
    }

    try {
        console.log(`Calling API → Add response to task ${taskId}`);

        // 🔥 CALL THE API HERE
        const apiResponse = await API.addResponse(taskId, responseText, userName);

        // 🔥 Update local data based on API response
        const currentTasks = activeFilter === "assigned_by"
            ? taskData.assigned_by_todos
            : taskData.assigned_to_todos;

        const task = currentTasks.find(t => t.todo_id === taskId);
        if (task) {
            if (!task.responses) task.responses = [];
            task.responses.push(apiResponse);  // use backend-created response
        }

        showNotification('Response added successfully!', 'success');
        form.reset();

        if (selectedTask && selectedTask.todo_id === taskId) {
            openTaskPanel(taskId);
        }

    } catch (error) {
        console.error('API Error adding response:', error);
        showNotification('Error adding response', 'error');
    }
}
let selectedForwardTaskId = null;
function closeForwardModal() {
    document.getElementById("forwardModal").style.display = "none";
    selectedForwardTaskId = null;
}
function forwardTask(taskId) {
    selectedForwardTaskId = taskId;

    // SHOW forward form
    document.getElementById('forwardForm').style.display = 'block';

    // Populate developers dynamically
    const select = document.getElementById("forwardSelect");
    select.innerHTML = `<option value="">Select a developer</option>`;

    developers.forEach(dev => {
        select.innerHTML += `
            <option value="${dev.username}">${dev.name} (${dev.position})</option>
        `;
    });

    document.getElementById('forwardForm').scrollIntoView({ behavior: 'smooth' });
}

function hideForwardForm() {
    document.getElementById('forwardForm').style.display = 'none';
}

async function submitForwardTask(event, taskId) {
    event.preventDefault();

    const forwardTo = document.getElementById("forwardSelect").value;
    const reason = document.getElementById("forwardReason").value;

    if (!forwardTo || !reason.trim()) {
        showNotification('Please fill in all fields.', 'warning');
        return;
    }

    try {
        const selectedDev = developers.find(d => d.username === forwardTo);

        // API CALL TO BACKEND
        const response = await fetch(`/api/escalated-todos/${taskId}/forward`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                forward_to_username: forwardTo,
                forward_to_name: selectedDev.name,
                reason: reason
            })
        });

        const data = await response.json();

        if (!response.ok) {
            showNotification(data.detail || "Error forwarding", "error");
            return;
        }

        showNotification("Task forwarded successfully!", "success");

        // Close form
        hideForwardForm();

        // Refresh tasks in UI
        loadTasks();

    } catch (error) {
        console.error("Error forwarding task:", error);
        showNotification("Error forwarding task", "error");
    }
}

// Filter functions
function handleFilterChange(newFilter) {
    if (newFilter === activeFilter) return;

    activeFilter = newFilter;

    document.querySelectorAll('.filter-tab').forEach(btn => btn.classList.remove('active'));
    document.getElementById(newFilter === "assigned_by" ? "assignedByBtn" : "assignedToBtn").classList.add('active');

    updateFilterCounts();
    renderBoard();
}

function updateFilterCounts() {
    document.getElementById("assignedByCount").textContent = taskData.assigned_by_todos.length;
    document.getElementById("assignedToCount").textContent = taskData.assigned_to_todos.length;
}

// Show notification
function showNotification(message, type = 'info') {
    const notification = document.createElement('div');
    notification.className = `notification ${type}`;
    notification.textContent = message;

    document.body.appendChild(notification);

    setTimeout(() => {
        notification.remove();
    }, 5000);
}

// Theme toggle
function toggleTheme() {
    const root = document.documentElement;
    const themeToggle = document.getElementById('themeToggle');

    if (root.getAttribute('data-theme') === 'dark') {
        root.removeAttribute('data-theme');
        themeToggle.textContent = '🌙';
    } else {
        root.setAttribute('data-theme', 'dark');
        themeToggle.textContent = '☀️';
    }
}

// Fetch tasks from API
async function fetchTasks() {
    const loading = document.getElementById("loading");
    const boardContainer = document.getElementById("boardContainer");
    const emptyState = document.getElementById("emptyState");

    loading.style.display = "flex";
    boardContainer.style.display = "none";
    emptyState.style.display = "none";

    try {
        const data = await API.fetchAll();

        // Store the data in global state
        taskData.assigned_by_todos = data.assigned_by_todos || [];
        taskData.assigned_to_todos = data.assigned_to_todos || [];

        console.log('Fetched data:', taskData);

        // Update counts and render
        updateFilterCounts();
        renderBoard();

        loading.style.display = "none";
    } catch (error) {
        console.error('Error loading tasks:', error);
        loading.style.display = "none";
        emptyState.style.display = "block";
        document.getElementById('emptyDescription').textContent = 'Error loading tasks. Please try again.';
        showNotification('Error loading tasks', 'error');
    }
}

// Initialize app
function init() {
    document.getElementById("assignedByBtn").addEventListener("click", () => handleFilterChange("assigned_by"));
    document.getElementById("assignedToBtn").addEventListener("click", () => handleFilterChange("assigned_to"));
    document.getElementById("themeToggle").addEventListener("click", toggleTheme);
    document.getElementById("panelClose").addEventListener("click", closeTaskPanel);

    document.getElementById('sidePanelOverlay').addEventListener('click', function(e) {
        if (e.target === this) {
            closeTaskPanel();
        }
    });

    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape') {
            closeTaskPanel();
        }
    });

    fetchTasks();
}

document.addEventListener("DOMContentLoaded", init);
lucide.createIcons();