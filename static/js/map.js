// 1. Initialize the map
var map = L.map('map', {
    minZoom: 13,
});

// Variable to store your location globally
var myLocation;

L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
}).addTo(map);


let availableTasks = {};
let markers = {}; // Store references to task markers

// 2. Set up location with the map
function initLocation(lat, lng, source) {
    var latlng = L.latLng(lat, lng);
    myLocation = latlng;
    localStorage.setItem('userLocation', JSON.stringify(myLocation));

    map.setView(latlng, 14);

    L.marker(latlng).addTo(map)
        .bindPopup("You are here!").openPopup();

    loadNearbyTasks(latlng);
}

function loadNearbyTasks(latlng) {
    fetch(`/api/nearby?lat=${latlng.lat}&lng=${latlng.lng}`)
        .then(response => response.json())
        .then(data => {
            data.tasks.forEach(task => {
                availableTasks[task.id] = task;

                var taskLatLng = L.latLng(task.lat, task.lng);
                var distance = myLocation.distanceTo(taskLatLng);
                var distanceKm = (distance / 1000).toFixed(2);

                var popupContent = `
                    <div class="task-popup">
                        <h3>${task.title}</h3>
                        <p><strong>Description:</strong> ${task.description}</p>
                        <p><strong>Reward:</strong> $${task.reward}</p>
                        <p><strong>Distance:</strong> ${distanceKm} km</p>
                        <hr style="margin: 10px 0; border: 0; border-top: 1px solid #eee;">
                        <button onclick="acceptTask(event, ${task.id})" class="btn-post">Accept Task</button>
                    </div>
                `;

                var marker = L.circleMarker([task.lat, task.lng], {
                    color: 'red',
                    fillColor: '#f03',
                    fillOpacity: 0.5,
                    radius: 10
                }).addTo(map)
                    .bindPopup(popupContent);

                markers[task.id] = marker;
            });

            // Store tasks in backend so the AI can search them
            fetch('/api/store_available_tasks', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ tasks: data.tasks })
            }).catch(err => console.warn('Could not store tasks for AI:', err));
        })
        .catch(error => console.error('Error fetching nearby data:', error));
}

// 3. Try browser geolocation first
map.on('locationfound', function (e) {
    initLocation(e.latlng.lat, e.latlng.lng, 'browser');
});

map.on('locationerror', function (e) {
    console.warn('Browser geolocation failed, trying IP-based fallback...');
    // Fallback: get location from server via IP geolocation
    fetch('/api/geolocate')
        .then(response => response.json())
        .then(data => {
            if (data.lat && data.lng) {
                initLocation(data.lat, data.lng, 'ip');
            } else {
                console.error('IP geolocation failed too');
            }
        })
        .catch(err => {
            console.error('All geolocation methods failed:', err);
        });
});

map.locate({ setView: false });

// Expose highlightTask for the AI chat to call
window.highlightTask = function (taskId) {
    var marker = markers[taskId];
    if (marker) {
        map.setView(marker.getLatLng(), 16);
        marker.openPopup();
    }
};

// Handle task acceptance and save to DB
function acceptTask(event, taskId) {
    event.preventDefault();

    const task = availableTasks[taskId];
    if (!task) {
        alert("Error: Task details not found.");
        return;
    }

    const taskData = {
        id: task.id, // Send original ID
        title: task.title,
        description: task.description,
        reward: task.reward,
        lat: task.lat,
        lng: task.lng
    };

    fetch('/api/accept_task', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(taskData),
    })
        .then(response => response.json())
        .then(data => {

            map.closePopup();

            // Remove marker from map
            if (markers[taskId]) {
                map.removeLayer(markers[taskId]);
                delete markers[taskId];
                delete availableTasks[taskId]; // Also remove from availableTasks
            }
        })
        .catch((error) => {
            console.error('Error:', error);
            alert('Error accepting task');
        });
}