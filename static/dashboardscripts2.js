function getUserLocation() {
    if ("geolocation" in navigator) {
        navigator.geolocation.getCurrentPosition(function (position) {
            var lat = position.coords.latitude;
            var long = position.coords.longitude;
            console.log("Latitude: " + lat + ", Longitude: " + long);

            // Do something with these coordinates, like sending them to your server
        }, function (error) {
            console.log("Error occurred: " + error.message);
        });
    } else {
        console.log("Geolocation not supported by this browser.");
    }
}
function getUserLocation() {
    if (navigator.geolocation) {
        navigator.geolocation.getCurrentPosition(showPosition);
    } else {
        console.log("Geolocation is not supported by this browser.");
    }
}

function showPosition(position) {
    sendCoordinatesToServer(position.coords.latitude, position.coords.longitude);
}

function sendCoordinatesToServer(lat, lon) {
    fetch('/get_nearest_gym', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({latitude: lat, longitude: lon})
    })
    .then(response => response.json())
    .then(data => {
        const gymName = data.gymName;
        document.getElementById('gymValue').innerText = gymName;
        console.log('gym:')
        console.log(gymName)
    });
}