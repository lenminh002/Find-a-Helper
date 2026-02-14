// Function to delete a task
function deleteTask(taskId) {
    if (!confirm('Are you sure you want to delete this task?')) {
        return;
    }

    fetch(`/api/delete_task/${taskId}`, {
        method: 'DELETE',
    })
        .then(response => {
            if (response.ok) {
                // Reload tasks
                location.reload();
                // Or better, re-fetch. But fetchTasks isn't global.
                // Let's make fetchTasks accessible or just reload page for now simplicity.
                // Actually, I can just remove the element if I had reference, but re-fetching is safer.
                // Since fetchTasks is inside DOMContentLoaded, I can't call it easily unless I move it out.
                // I'll move fetchTasks out or reload. Reload is fine for this demo.
            } else {
                alert('Error deleting task');
            }
        })
        .catch(error => console.error('Error:', error));
}

// Function to calculate distance between two coordinates in km
function calculateDistance(lat1, lon1, lat2, lon2) {
    const R = 6371; // Radius of the earth in km
    const dLat = deg2rad(lat2 - lat1);
    const dLon = deg2rad(lon2 - lon1);
    const a =
        Math.sin(dLat / 2) * Math.sin(dLat / 2) +
        Math.cos(deg2rad(lat1)) * Math.cos(deg2rad(lat2)) *
        Math.sin(dLon / 2) * Math.sin(dLon / 2);
    const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
    const d = R * c; // Distance in km
    return d.toFixed(2);
}

function deg2rad(deg) {
    return deg * (Math.PI / 180);
}

document.addEventListener('DOMContentLoaded', function () {
    const taskList = document.getElementById('task-list');
    const userLocationStr = localStorage.getItem('userLocation');
    let userLocation = null;

    if (userLocationStr) {
        try {
            userLocation = JSON.parse(userLocationStr);
        } catch (e) {
            console.error("Error parsing user location", e);
        }
    }

    function fetchTasks() {
        fetch('/api/my_tasks')
            .then(response => response.json())
            .then(data => {
                taskList.innerHTML = ''; // Clear existing tasks

                if (data.tasks.length === 0) {
                    taskList.innerHTML = '<p class="no-tasks">No accepted tasks yet.</p>';
                    return;
                }

                data.tasks.forEach(task => {
                    let locationDisplay = `Location: ${task.lat.toFixed(4)}, ${task.lng.toFixed(4)}`;

                    if (userLocation) {
                        const dist = calculateDistance(userLocation.lat, userLocation.lng, task.lat, task.lng);
                        locationDisplay = `Distance: <strong>${dist} km</strong>`;
                    }

                    const taskCard = document.createElement('div');
                    taskCard.className = 'task-card';

                    taskCard.innerHTML = `
                        <div class="task-header">
                            <h3>${task.title}</h3>
                            <span class="status-badge">${task.status}</span>
                        </div>
                        <div class="task-body">
                            <p>${task.description}</p>
                            <div class="task-meta">
                                <span><strong>Reward:</strong> $${task.reward}</span>
                                <span>${locationDisplay}</span>
                            </div>
                        </div>
                        <div class="task-footer">
                            <button class="btn-delete" onclick="deleteTask(${task.id})">Delete Task</button>
                        </div>
                    `;
                    taskList.appendChild(taskCard);
                });
            })
            .catch(error => console.error('Error fetching tasks:', error));
    }

    fetchTasks();
});
