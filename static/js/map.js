// 1. Initialize the map
var map = L.map('map', {
    minZoom: 13,
});

// Variable to store your location globally
var myLocation;

L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
}).addTo(map);

// 2. Ask the browser for your location
map.locate({ setView: true, });

// 3. What to do when the location is found
function onLocationFound(e) {
    myLocation = e.latlng; // Store the coordinates
    L.marker(e.latlng).addTo(map)
        .bindPopup("You are here!").openPopup();

    // Fetch nearby helpers and tasks
    fetch(`/api/nearby?lat=${e.latlng.lat}&lng=${e.latlng.lng}`)
        .then(response => response.json())
        .then(data => {
            // Display Tasks (Red)
            data.tasks.forEach(task => {
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
                        <form onsubmit="acceptTask(event, ${task.id})">
                            <button type="submit" class="btn-post">Accept Task</button>
                        </form>
                    </div>
                `;

                L.circleMarker([task.lat, task.lng], {
                    color: 'red',
                    fillColor: '#f03',
                    fillOpacity: 0.5,
                    radius: 10
                }).addTo(map)
                    .bindPopup(popupContent);
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

// Dummy function to handle task acceptance
function acceptTask(event, taskId) {
    event.preventDefault();
    alert(`Task ${taskId} accepted! (This is a demo)`);
    map.closePopup();
}