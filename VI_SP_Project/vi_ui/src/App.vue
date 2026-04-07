<script setup lang="ts">
import {onMounted, onUnmounted, ref} from 'vue';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';

// -- Marker Clustering
import 'leaflet.markercluster';
import 'leaflet.markercluster/dist/MarkerCluster.css';
import 'leaflet.markercluster/dist/MarkerCluster.Default.css';

// --- THE VITE ICON FIX ---
import icon from 'leaflet/dist/images/marker-icon.png';
import iconShadow from 'leaflet/dist/images/marker-shadow.png';

const DefaultIcon = L.icon({
  iconUrl: icon,
  shadowUrl: iconShadow,
  iconSize: [25, 41],
  iconAnchor: [12, 41],
  popupAnchor: [1, -34]
});
L.Marker.prototype.options.icon = DefaultIcon;
// -------------------------

const mapContainer = ref<HTMLElement | null>(null);
let map: L.Map | null = null;

// --- these were missing! ---
const countryClusterGroups: Record<string, L.MarkerClusterGroup> = {};

type Department = {
  name: string;
  link?: string;
  location: {
    lat: number | null;
    lon: number | null;
  };
};

type University = {
  institution: string;
  name: string;
  link?: string;
  location?: {
    lat: number | null;
    lon: number | null;
  };
  departments?: Department[];
};

const fetchDrawBordersAndPlaceMarkers = async () => {
  if (!map) return;

  const manifestResponse = await fetch('/borders/manifest.json');
  const fileNames: string[] = await manifestResponse.json();

  for (const fileName of fileNames) {
    const countryCode = fileName.split('.')[0]; // "cz.geojson" -> "cz"

    try {
      // Load border
      const borderResponse = await fetch(`/borders/${fileName}`);
      const geojsonData = await borderResponse.json();

      // Create cluster group for this country
      const clusterGroup = L.markerClusterGroup({ maxClusterRadius: 50 });
      countryClusterGroups[countryCode] = clusterGroup;
      map!.addLayer(clusterGroup);

      // Draw border
      L.geoJSON(geojsonData, {
        style: { color: '#3388ff', weight: 2, fillOpacity: 0.1, fillColor: '#3388ff' },
        onEachFeature: (feature: any, layer: L.Layer) => {
          const countryName = feature.properties.NAME || feature.properties.name || "Unknown Country";
          layer.bindPopup(`<b>${countryName}</b>`);
          layer.on('mouseover', (e: L.LeafletMouseEvent) => {
            (e.target as L.Path).setStyle({ fillOpacity: 0.4 });
          });
          layer.on('mouseout', (e: L.LeafletMouseEvent) => {
            (e.target as L.Path).setStyle({ fillOpacity: 0.1 });
          });
        }
      }).addTo(map!);

    } catch (error) {
      console.error(`Error loading border file ${fileName}:`, error);
      continue; // skip to next country if border fails
    }

    // Load and place universities for this country
    try {
      const unisResponse = await fetch(`/unis/${countryCode}.json`);
      const unis: University[] = await unisResponse.json();

      const clusterGroup = countryClusterGroups[countryCode];

      unis.forEach((uni) => {
        if (uni.departments && uni.departments.length > 0) {
          uni.departments.forEach((dept) => {
            const lat = dept.location?.lat;
            const lon = dept.location?.lon;
            if (lat && lon) {
              L.marker([lat, lon])
                  .bindPopup(`<b>${uni.name}</b><br/><span>${dept.name}</span>`)
                  .addTo(clusterGroup);
            }
          });
        } else {
          const lat = uni.location?.lat;
          const lon = uni.location?.lon;
          if (lat && lon) {
            L.marker([lat, lon])
                .bindPopup(`<b>${uni.name}</b>`)
                .addTo(clusterGroup);
          }
        }
      });

      console.log(`Loaded universities for ${countryCode}`);
    } catch (error) {
      console.error(`No universities file found for ${countryCode}`);
    }
  }

  console.log("All countries loaded!");
};

onMounted(async () => {
  if (!mapContainer.value) return;

  const europeBounds = L.latLngBounds(
      L.latLng(34.0, -15.0),
      L.latLng(72.0, 45.0)
  );

  map = L.map(mapContainer.value, {
    maxBounds: europeBounds,
    maxBoundsViscosity: 1.0,
    minZoom: 4
  });

  map.fitBounds(europeBounds);

  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '&copy; OpenStreetMap contributors'
  }).addTo(map);

  await fetchDrawBordersAndPlaceMarkers();
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