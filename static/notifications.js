const userId = document.body.dataset.userId;
let socket;
let reconnectAttempts = 0;
const MAX_RECONNECT_ATTEMPTS = 5;
const RECONNECT_DELAY = 3000;

function connectWebSocket() {
    if (!userId) {
        console.warn('⚠️ No userId found, skipping WebSocket connection');
        return;
    }

    // Use wss:// for secure connections (https) or ws:// for http
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${location.host}/ws/notifications/${userId}`;

    console.log(`🔌 Connecting to WebSocket: ${wsUrl}`);

    socket = new WebSocket(wsUrl);

    socket.onopen = () => {
        console.log('✅ Notification WebSocket connected');
        reconnectAttempts = 0;
        updateConnectionStatus(true);
    };

    socket.onerror = err => {
        console.error('❌ WebSocket error:', err);
        updateConnectionStatus(false);
    };

    socket.onclose = (event) => {
        console.log('🔌 WebSocket closed:', event.code, event.reason);
        updateConnectionStatus(false);

        // Attempt to reconnect
        if (reconnectAttempts < MAX_RECONNECT_ATTEMPTS) {
            reconnectAttempts++;
            console.log(`🔄 Reconnecting... (Attempt ${reconnectAttempts}/${MAX_RECONNECT_ATTEMPTS})`);
            setTimeout(connectWebSocket, RECONNECT_DELAY);
        } else {
            console.error('❌ Max reconnection attempts reached');
        }
    };

    socket.onmessage = event => {
        try {
            const payload = JSON.parse(event.data);
            console.log('📨 Received notification:', payload);

            if (payload.event === 'notification') {
                handleIncomingNotification(payload.data);
            }
        } catch (error) {
            console.error('Error parsing notification:', error);
        }
    };
}

function updateConnectionStatus(isConnected) {
    // Optional: Update UI to show connection status
    const statusElement = document.getElementById('wsStatus');
    if (statusElement) {
        statusElement.textContent = isConnected ? '🟢 Connected' : '🔴 Disconnected';
        statusElement.style.color = isConnected ? '#4caf50' : '#f44336';
    }
}

function handleIncomingNotification(notification) {
    playNotificationSound();
    showToast(notification);
    incrementBadge();
}

function playNotificationSound() {
    const sound = document.getElementById('notificationSound');
    if (!sound) return;
    sound.currentTime = 0;
    sound.play().catch(() => {});
}

function incrementBadge() {
    const badge = document.getElementById('notificationCount');
    if (!badge) return;
    const currentCount = parseInt(badge.textContent || '0');
    badge.textContent = currentCount + 1;
    badge.style.display = 'inline-block'; // Show badge if hidden
}

function showToast(notification) {
    const toast = document.createElement('div');
    toast.className = 'toast';
    toast.innerHTML = `
        <strong>${notification.title || 'Notification'}</strong>
        <div>${notification.message || ''}</div>
    `;

    toast.onclick = () => window.location.href = '/notifications';

    document.body.appendChild(toast);

    setTimeout(() => toast.classList.add('show'), 50);
    setTimeout(() => {
        toast.classList.remove('show');
        setTimeout(() => toast.remove(), 300);
    }, 4000);
}

// Initialize WebSocket connection when page loads
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', connectWebSocket);
} else {
    connectWebSocket();
}

// Close WebSocket when page unloads
window.addEventListener('beforeunload', () => {
    if (socket && socket.readyState === WebSocket.OPEN) {
        socket.close();
    }
});