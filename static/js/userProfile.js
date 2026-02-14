// User Profile Interactivity — with DB persistence

document.addEventListener('DOMContentLoaded', () => {

    // === Sign Out Confirmation ===
    const signOutBtn = document.getElementById('btn-sign-out');
    if (signOutBtn) {
        signOutBtn.addEventListener('click', (e) => {
            e.preventDefault();
            if (confirm("Are you sure you want to sign out?")) {
                window.location.href = signOutBtn.href;
            }
        });
    }

    // === Inline Edit Logic ===
    document.querySelectorAll('.btn-edit').forEach(btn => {
        btn.addEventListener('click', () => {
            const row = btn.closest('.field-row');
            const valueEl = row.querySelector('.field-value');
            const editEl = row.querySelector('.field-edit');

            if (!editEl) return;

            valueEl.style.display = 'none';
            editEl.style.display = 'block';
            btn.style.display = 'none';

            const input = editEl.querySelector('.field-input');
            if (input) input.focus();
        });
    });

    // Save buttons — persist to DB
    document.querySelectorAll('.btn-save').forEach(btn => {
        btn.addEventListener('click', async () => {
            const row = btn.closest('.field-row');
            const field = row.dataset.field;
            const valueEl = row.querySelector('.field-value');
            const editEl = row.querySelector('.field-edit');
            const editBtn = row.querySelector('.btn-edit');
            const input = editEl.querySelector('.field-input');

            const newVal = (input.value || '').trim() || 'N/A';

            try {
                const res = await fetch('/api/update_profile', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ field: field, value: newVal === 'N/A' ? '' : newVal })
                });

                if (res.ok) {
                    valueEl.textContent = newVal;

                    // Update sidebar username if username was changed
                    if (field === 'username') {
                        const sidebarUsername = document.getElementById('sidebar-username');
                        if (sidebarUsername) sidebarUsername.textContent = newVal;

                        // Update avatar
                        const avatar = document.querySelector('.sidebar-avatar');
                        if (avatar) {
                            avatar.src = `https://ui-avatars.com/api/?name=${encodeURIComponent(newVal)}&background=222&color=fff&size=88`;
                        }
                    }
                } else {
                    const err = await res.json();
                    alert('Failed to save: ' + (err.error || 'Unknown error'));
                }
            } catch (e) {
                alert('Network error. Please try again.');
                console.error(e);
            }

            editEl.style.display = 'none';
            valueEl.style.display = 'block';
            editBtn.style.display = 'inline-block';
        });
    });

    // Cancel buttons
    document.querySelectorAll('.btn-cancel').forEach(btn => {
        btn.addEventListener('click', () => {
            const row = btn.closest('.field-row');
            const valueEl = row.querySelector('.field-value');
            const editEl = row.querySelector('.field-edit');
            const editBtn = row.querySelector('.btn-edit');

            editEl.style.display = 'none';
            valueEl.style.display = 'block';
            editBtn.style.display = 'inline-block';
        });
    });
});
