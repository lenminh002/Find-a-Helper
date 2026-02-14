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

// 2. Ask the browser for your location
map.locate({ setView: true, });

// 3. What to do when the location is found
function onLocationFound(e) {
    myLocation = e.latlng; // Store the coordinates
    localStorage.setItem('userLocation', JSON.stringify(myLocation)); // Save for Tasks page

    L.marker(e.latlng).addTo(map)
        .bindPopup("You are here!").openPopup();

    // Fetch nearby helpers and tasks
    fetch(`/api/nearby?lat=${e.latlng.lat}&lng=${e.latlng.lng}`)
        .then(response => response.json())
        .then(data => {
            // Display Tasks (Red)
            data.tasks.forEach(task => {
                availableTasks[task.id] = task; // Store for access in acceptTask

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

                markers[task.id] = marker; // Store marker reference
            });


        })
        .catch(error => console.error('Error fetching nearby data:', error));
}

map.on('locationfound', onLocationFound);

function onLocationError(e) {
    alert("Location access denied or unavailable: " + e.message);
    map.setView([51.505, -0.09], 13);
}

map.on('locationerror', onLocationError);

// 4. Click function with distance calculation
// 4. Click function (Optional or Removed)
// map.on('click', onMapClick);

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