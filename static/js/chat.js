// Chat Widget — AI Assistant

document.addEventListener('DOMContentLoaded', () => {
    const toggle = document.getElementById('chat-toggle');
    const panel = document.getElementById('chat-panel');
    const closeBtn = document.getElementById('chat-close');
    const input = document.getElementById('chat-input');
    const sendBtn = document.getElementById('chat-send');
    const messages = document.getElementById('chat-messages');

    if (!toggle || !panel) return;

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

    // Send message
    async function sendMessage() {
        const text = input.value.trim();
        if (!text) return;

        // Add user message
        appendMessage(text, 'user');
        input.value = '';
        sendBtn.disabled = true;

        // Show typing indicator
        const typingEl = appendMessage('Thinking...', 'typing');

        try {
            const res = await fetch('/api/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ message: text })
            });

            // Remove typing indicator
            typingEl.remove();

            if (res.ok) {
                const data = await res.json();
                appendMessage(data.reply, 'assistant');
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

    function appendMessage(text, type) {
        const msg = document.createElement('div');
        msg.className = `chat-msg ${type}`;
        msg.textContent = text;
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

    // Welcome message
    appendMessage("Hi! I'm your Find a Helper assistant. Ask me about tasks, pricing, or anything else!", 'assistant');
});
