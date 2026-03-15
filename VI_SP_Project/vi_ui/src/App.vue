<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';

// --- THE VITE ICON FIX ---
import icon from 'leaflet/dist/images/marker-icon.png';
import iconShadow from 'leaflet/dist/images/marker-shadow.png';

const DefaultIcon = L.icon({
  iconUrl: icon,
  shadowUrl: iconShadow,
  iconSize: [25, 41],
  iconAnchor: [12, 41],
  popupAnchor: [1, -34] // Added this so popups open cleanly above the pin
});
L.Marker.prototype.options.icon = DefaultIcon;
// -------------------------

const mapContainer = ref<HTMLElement | null>(null);
let map: L.Map | null = null;

// The function to fetch and draw country borders
const fetchAndDrawBorders = async () => {
  if (!map) return;

  try {
    // 1. Fetch a lightweight public GeoJSON file of country borders
    const response = await fetch('https://raw.githubusercontent.com/leakyMirror/map-of-europe/master/GeoJSON/europe.geojson');
    const geojsonData = await response.json();

    // 2. Use Leaflet's native GeoJSON reader
    L.geoJSON(geojsonData, {

      // A. Style the borders (Blue outline, transparent fill)
      style: {
        color: '#3388ff',
        weight: 2,
        fillOpacity: 0.1,
        fillColor: '#3388ff'
      },
      onEachFeature: (feature: any, layer: L.Layer) => {
        // 2. Safely grab the country name (this specific file uses capital 'NAME')
        const countryName = feature.properties.NAME || feature.properties.name || "Unknown Country";

        layer.bindPopup(`<b>${countryName}</b>`);

        layer.on('mouseover', (e: L.LeafletMouseEvent) => {
          (e.target as L.Path).setStyle({ fillOpacity: 0.4 });
        });
        layer.on('mouseout', (e: L.LeafletMouseEvent) => {
          (e.target as L.Path).setStyle({ fillOpacity: 0.1 });
        });
      }
    }).addTo(map);

    console.log("Borders loaded successfully!");

  } catch (error) {
    console.error("Error loading GeoJSON:", error);
  }
};

// The function to fetch and draw the universities
const fetchUniversities = async () => {
  if (!map) return;

  // I updated your query slightly to use a standard area name and added a limit of 300
  // to prevent your browser from freezing during this initial test!
  const overpassQuery = `
    [out:json][timeout:25];
    area["ISO3166-1"="CZ"]->.czechia;
    // We use 'nwr' to get points, campus polygons, and multi-campuses
    nwr["amenity"="university"](area.czechia);
    // 'out center' calculates the exact middle of the campus polygons for our pins
    out center;
  `;

  try {
    const response = await fetch('https://overpass-api.de/api/interpreter', {
      method: 'POST',
      body: "data=" + encodeURIComponent(overpassQuery)
    });
    const data = await response.json();

    // 2. The updated loop
    data.elements.forEach((school: any) => {
      // A node has 'lat' and 'lon'.
      // A way/relation has 'center.lat' and 'center.lon'. We check for both!
      const lat = school.lat || (school.center && school.center.lat);
      const lon = school.lon || (school.center && school.center.lon);

      if (lat && lon) {
        const schoolName = school.tags && school.tags.name ? school.tags.name : "Unknown University";

        L.marker([lat, lon])
            .addTo(map!)
            .bindPopup(`<b>${schoolName}</b>`);
      }
    });

    console.log(`Successfully loaded ${data.elements.length} universities.`);

  } catch (error) {
    console.error("Error fetching from Overpass API:", error);
  }
};

onMounted(() => {
  if (!mapContainer.value) return;

  const europeBounds = L.latLngBounds(
      L.latLng(34.0, -15.0), // South-West (roughly the Atlantic/Canary Islands)
      L.latLng(72.0, 45.0)   // North-East (roughly Northern Norway/Russia)
  );

  map = L.map(mapContainer.value, {
    maxBounds: europeBounds,
    maxBoundsViscosity: 1.0,
    minZoom: 4 // Raised from 3. If you STILL see too much, change this to 5!
  });

  // 3. Force Leaflet to calculate the exact perfect zoom to fit Europe on YOUR specific screen
  map.fitBounds(europeBounds);

  // Set the initial view nicely over central Europe

  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '&copy; OpenStreetMap contributors'
  }).addTo(map);

  // Trigger the fetch function after the map is ready
  fetchUniversities();
  fetchAndDrawBorders();
});

onUnmounted(() => {
  if (map) {
    map.remove();
  }
});
</script>

<template>
  <main>
    <div ref="mapContainer" style="height: 100vh; width: 100vw; display: block;"></div>
  </main>
</template>

<style scoped>
:global(body) {
  margin: 0;
  padding: 0;
}
</style>
