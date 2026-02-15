// Chat Widget — AI Assistant with persistence, task cards, and markdown

document.addEventListener('DOMContentLoaded', () => {
    const toggle = document.getElementById('chat-toggle');
    const panel = document.getElementById('chat-panel');
    const closeBtn = document.getElementById('chat-close');
    const clearBtn = document.getElementById('chat-clear');
    const input = document.getElementById('chat-input');
    const sendBtn = document.getElementById('chat-send');
    const messages = document.getElementById('chat-messages');

    if (!toggle || !panel) return;

    const STORAGE_KEY = 'findahelper_chat';

    // --- Simple Markdown → HTML ---
    function renderMarkdown(text) {
        // Use marked to parse markdown
        const rawHtml = marked.parse(text);
        // Sanitize with DOMPurify
        return DOMPurify.sanitize(rawHtml);
    }

    // --- Persistence ---
    function loadMessages() {
        fetch('/api/chat/history')
            .then(res => res.json())
            .then(data => {
                if (data.history && data.history.length > 0) {
                    data.history.forEach(msg => {
                        appendMessage(msg.content, msg.role, false);
                    });
                } else {
                    appendMessage("Hi! I'm your Find a Helper assistant. Ask me about tasks, pricing, or anything else!", 'assistant', false);
                }
            })
            .catch(err => console.error('Failed to load chat history:', err));
    }

    // Toggle chat panel
    toggle.addEventListener('click', () => {
        panel.classList.toggle('open');
        if (panel.classList.contains('open')) {
            input.focus();
        }
    });

    closeBtn.addEventListener('click', () => {
        panel.classList.remove('open');
    });

    // Clear chat
    if (clearBtn) {
        clearBtn.addEventListener('click', () => {
            if (confirm('Are you sure you want to clear the chat history?')) {
                fetch('/api/clear_chat', { method: 'POST' })
                    .then(res => {
                        if (res.ok) {
                            messages.innerHTML = '';
                            appendMessage("Chat cleared! How can I help you?", 'assistant', false);
                        }
                    })
                    .catch(err => console.error('Failed to clear chat:', err));
            }
        });
    }

    // --- Task Cards ---
    // Ensure highlightTask exists even if map hasn't loaded
    if (!window.highlightTask) {
        window.highlightTask = function (taskId) {
            alert('Map is still loading. Please try again in a moment.');
        };
    }

    function renderTaskCards(tasks, save = true) {
        if (!tasks || tasks.length === 0) return;

        const container = document.createElement('div');
        container.className = 'chat-task-cards';

        tasks.forEach(task => {
            const taskId = task.map_id || task.id;
            const card = document.createElement('div');
            card.className = 'chat-task-card';
            card.dataset.taskId = taskId;
            card.innerHTML = `
                <div class="task-card-header">
                    <span class="task-card-title">#${taskId} ${escapeHtml(task.title)}</span>
                    <span class="task-card-reward">$${task.reward}</span>
                </div>
                <div class="task-card-desc">${escapeHtml(task.description || task.desc || '')}</div>
                <button class="task-card-show" onclick="window.highlightTask(${taskId})">
                    📍 Show on Map
                </button>
            `;
            container.appendChild(card);
        });

        messages.appendChild(container);
        messages.scrollTop = messages.scrollHeight;
    }

    function escapeHtml(str) {
        const div = document.createElement('div');
        div.textContent = str;
        return div.innerHTML;
    }

    // --- Task Proposal Card (Conversational Creation) ---
    function renderTaskProposal(proposal) {
        if (!proposal || !proposal.title) return;

        const card = document.createElement('div');
        card.className = 'task-proposal-card';
        card.innerHTML = `
            <div class="proposal-header">Task Proposal</div>
            <div class="proposal-detail"><strong>Title:</strong> ${escapeHtml(proposal.title)}</div>
            <div class="proposal-detail"><strong>Description:</strong> ${escapeHtml(proposal.description || '')}</div>
            <div class="proposal-detail"><strong>Reward:</strong> $${proposal.reward || 0}</div>
            <div class="proposal-actions">
                <button class="proposal-confirm">Confirm & Post</button>
                <button class="proposal-reject">Reject</button>
            </div>
        `;

        // Confirm button
        card.querySelector('.proposal-confirm').addEventListener('click', () => {
            const locData = JSON.parse(localStorage.getItem('userLocation') || '{}');
            let lat = locData.lat, lng = locData.lng;

            if (!lat || !lng) {
                if (typeof map !== 'undefined') {
                    const center = map.getCenter();
                    lat = center.lat;
                    lng = center.lng;
                } else {
                    alert('Cannot determine location. Please allow location access.');
                    return;
                }
            }

            fetch('/api/post_task', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    title: proposal.title,
                    description: proposal.description || '',
                    reward: proposal.reward || 0,
                    lat: lat,
                    lng: lng
                })
            })
                .then(res => res.json())
                .then(data => {
                    if (data.success) {
                        card.innerHTML = '<div class="proposal-success">Task posted! Look for the green marker on the map.</div>';
                        // Refresh map
                        if (typeof loadNearbyTasks === 'function' && typeof L !== 'undefined') {
                            loadNearbyTasks(L.latLng(lat, lng));
                        }
                    } else {
                        card.innerHTML = '<div class="proposal-error">Error: ' + (data.error || 'Unknown error') + '</div>';
                    }
                })
                .catch(err => {
                    console.error(err);
                    card.innerHTML = '<div class="proposal-error">Network error posting task.</div>';
                });
        });

        // Reject button
        card.querySelector('.proposal-reject').addEventListener('click', () => {
            card.innerHTML = '<div class="proposal-rejected">Task cancelled.</div>';
        });

        messages.appendChild(card);
        messages.scrollTop = messages.scrollHeight;
    }

    // Send message
    async function sendMessage() {
        const text = input.value.trim();
        if (!text) return;

        appendMessage(text, 'user');
        input.value = '';
        sendBtn.disabled = true;

        const typingEl = appendMessage('Thinking...', 'typing', false);

        try {
            // Get user location from localStorage (saved by map.js)
            const locData = JSON.parse(localStorage.getItem('userLocation') || '{}');
            const payload = { message: text };
            if (locData.lat && locData.lng) {
                payload.user_lat = locData.lat;
                payload.user_lng = locData.lng;
            }

            const res = await fetch('/api/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });

            typingEl.remove();

            if (res.ok) {
                const data = await res.json();
                appendMessage(data.reply, 'assistant');

                // Render task proposal card if AI proposed a task
                if (data.task_proposal) {
                    renderTaskProposal(data.task_proposal);
                }

                // Render task cards if AI found tasks
                if (data.found_tasks && data.found_tasks.length > 0) {
                    renderTaskCards(data.found_tasks);
                }

                // Highlight task on map if AI picked one
                if (data.highlight_task_id && window.highlightTask) {
                    window.highlightTask(data.highlight_task_id);
                }
            } else if (res.status === 401) {
                appendMessage('Please log in first to use the assistant.', 'assistant');
            } else {
                const err = await res.json().catch(() => ({}));
                appendMessage(err.error || 'Something went wrong. Try again.', 'assistant');
            }
        } catch (e) {
            typingEl.remove();
            appendMessage('Network error. Please check your connection.', 'assistant');
        }

        sendBtn.disabled = false;
        input.focus();
    }

    function appendMessage(text, type, save = false) {
        const msg = document.createElement('div');
        msg.className = `chat-msg ${type}`;

        if (type === 'assistant') {
            msg.innerHTML = renderMarkdown(text);
            msg.dataset.rawText = text;
        } else {
            msg.textContent = text;
        }

        messages.appendChild(msg);
        messages.scrollTop = messages.scrollHeight;
        return msg;
    }

    // Send on click
    sendBtn.addEventListener('click', sendMessage);

    // Send on Enter
    input.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });

    // Load saved messages
    loadMessages();
});
