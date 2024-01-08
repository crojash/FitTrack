let map;
let service;
let infowindow;

function initMap() {
    // Initialize the map at a default location
    let pyrmont = new google.maps.LatLng(-33.866, 151.196);
    infowindow = new google.maps.InfoWindow();
    map = new google.maps.Map(
        document.getElementById('gymMap'), { center: pyrmont, zoom: 15 });
  
    // Create the Places service
    service = new google.maps.places.PlacesService(map);
  
    // Use the user's geolocation data
    navigator.geolocation.getCurrentPosition((position) => {
        let pos = {
            lat: position.coords.latitude,
            lng: position.coords.longitude
        };
        map.setCenter(pos);
  
        // Search for gyms nearby
        let request = {
            location: pos,
            radius: '500',
            query: 'gym'
        };
  
        service.textSearch(request, callback);
    });
}

function callback(results, status) {
    if (status == google.maps.places.PlacesServiceStatus.OK) {
        // Taking only the closest gym
        let place = results[0];
        createMarker(place);

        // Fetching and setting the image of the gym
        document.getElementById('gymImage').src = place.photos[0].getUrl();
    }
}

function createMarker(place) {
    let marker = new google.maps.Marker({
        map: map,
        position: place.geometry.location
    });
  
    google.maps.event.addListener(marker, 'click', function() {
        infowindow.setContent(place.name);
        infowindow.open(map, this);
    });
}
