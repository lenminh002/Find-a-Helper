// Messaging Page Logic

const conversationList = document.getElementById('conversation-list');
const chatPlaceholder = document.getElementById('chat-placeholder');
const chatActive = document.getElementById('chat-active');
const chatThread = document.getElementById('chat-thread');
const chatTitle = document.getElementById('chat-task-title');
const chatReward = document.getElementById('chat-task-reward');
const msgInput = document.getElementById('msg-input');
const sendBtn = document.getElementById('msg-send-btn');

let activeTaskId = null;

// ── Load conversations ──
async function loadConversations() {
    try {
        const res = await fetch('/api/conversations');
        const data = await res.json();

        if (!data.conversations || data.conversations.length === 0) {
            conversationList.innerHTML = `
                    <div class="convo-empty">
                        <p>No conversations yet</p>
                        <span>Accept a task from the map to start messaging</span>
                    </div>`;
            return;
        }

        conversationList.innerHTML = '';
        data.conversations.forEach(convo => {
            const el = document.createElement('div');
            el.className = 'convo-item' + (convo.task_id === activeTaskId ? ' active' : '');
            el.dataset.taskId = convo.task_id;

            const timeStr = formatTime(convo.last_time);

            el.innerHTML = `
                    <div class="convo-title">${escapeHtml(convo.title)}</div>
                    <div class="convo-preview">${escapeHtml(convo.last_message)}</div>
                    <div class="convo-meta">
                        <span class="convo-reward">$${convo.reward || 0}</span>
                        <span class="convo-time">${timeStr}</span>
                    </div>
                `;

            el.addEventListener('click', () => openChat(convo));
            conversationList.appendChild(el);
        });
    } catch (err) {
        console.error('Failed to load conversations:', err);
    }
}

// ── Open a chat thread ──
async function openChat(convo) {
    activeTaskId = convo.task_id;

    // Update sidebar active state
    document.querySelectorAll('.convo-item').forEach(el => {
        el.classList.toggle('active', parseInt(el.dataset.taskId) === activeTaskId);
    });

    // Show chat area
    chatPlaceholder.style.display = 'none';
    chatActive.style.display = 'flex';
    chatTitle.textContent = convo.title;
    chatReward.textContent = '$' + (convo.reward || 0);

    // Load messages
    await loadMessages(activeTaskId);
    msgInput.focus();
}

// ── Load messages for a task ──
async function loadMessages(taskId) {
    try {
        const res = await fetch(`/api/messages/${taskId}`);
        const data = await res.json();

        chatThread.innerHTML = '';

        if (!data.messages || data.messages.length === 0) {
            chatThread.innerHTML = '<p style="color:#bbb;text-align:center;margin:2rem 0;">No messages yet. Say hello!</p>';
            return;
        }

        data.messages.forEach(msg => {
            appendMessage(msg.sender, msg.content, msg.timestamp);
        });

        chatThread.scrollTop = chatThread.scrollHeight;
    } catch (err) {
        console.error('Failed to load messages:', err);
    }
}

// ── Append a single message to the thread ──
function appendMessage(sender, content, timestamp) {
    const el = document.createElement('div');
    el.className = 'dm-msg ' + sender;
    el.innerHTML = `
            <div>${escapeHtml(content)}</div>
            <div class="dm-time">${formatTime(timestamp)}</div>
        `;
    chatThread.appendChild(el);
}

// ── Send a message ──
async function handleSend() {
    const text = msgInput.value.trim();
    if (!text || !activeTaskId) return;

    msgInput.value = '';
    sendBtn.disabled = true;

    // Optimistically show the user message
    appendMessage('user', text, new Date().toISOString());
    chatThread.scrollTop = chatThread.scrollHeight;

    try {
        const res = await fetch(`/api/messages/${activeTaskId}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ content: text })
        });
        const data = await res.json();

        if (data.reply) {
            // Show the auto-reply
            setTimeout(() => {
                appendMessage('requester', data.reply, new Date().toISOString());
                chatThread.scrollTop = chatThread.scrollHeight;
                // Refresh sidebar to update preview
                loadConversations();
            }, 600);
        }
    } catch (err) {
        console.error('Failed to send message:', err);
    }

    sendBtn.disabled = false;
    msgInput.focus();
}

// ── Event listeners ──
sendBtn.addEventListener('click', handleSend);
msgInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') handleSend();
});

// ── Helpers ──
function escapeHtml(str) {
    if (!str) return '';
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
}

function formatTime(ts) {
    if (!ts) return '';
    const d = new Date(ts);
    const now = new Date();
    const diff = now - d;

    if (diff < 60000) return 'Just now';
    if (diff < 3600000) return Math.floor(diff / 60000) + 'm ago';
    if (diff < 86400000) return Math.floor(diff / 3600000) + 'h ago';
    return d.toLocaleDateString();
}

// ── Init ──
loadConversations();

