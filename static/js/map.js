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
}

map.on('locationfound', onLocationFound);

function onLocationError(e) {
    alert("Location access denied or unavailable: " + e.message);
    map.setView([51.505, -0.09], 13);
}

map.on('locationerror', onLocationError);

// 4. Click function with distance calculation
var popup = L.popup();

function onMapClick(e) {
    var content = "You clicked the map.";

    if (myLocation) {
        // Calculate distance in meters
        var meters = myLocation.distanceTo(e.latlng);

        // Convert to kilometers and round to 2 decimal places
        var km = (meters / 1000).toFixed(2);
        content = "This spot is <b>" + km + " km</b> away from you.";
    }

    popup
        .setLatLng(e.latlng)
        .setContent(content)
        .openOn(map);
}

map.on('click', onMapClick);