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

const fetchDrawBordersAndPlaceMarkers = async (): Promise<{
  bordersLayer: L.LayerGroup;
  markersLayer: L.LayerGroup;
}> => {
  const bordersLayer = L.layerGroup();
  const markersLayer = L.layerGroup();

  if (!map) return { bordersLayer, markersLayer };

  const manifestResponse = await fetch('/borders/manifest.json');
  const fileNames: string[] = await manifestResponse.json();

  for (const fileName of fileNames) {
    const countryCode = fileName.replace('.geo.json', '');

    try {
      const borderResponse = await fetch(`/borders/${fileName}`);
      const geojsonData = await borderResponse.json();

      // Create cluster group for this country
      const clusterGroup = L.markerClusterGroup({ maxClusterRadius: 50 });
      countryClusterGroups[countryCode] = clusterGroup;
      markersLayer.addLayer(clusterGroup); // add to group, not map directly

      // Draw border
      const borderGeoJson = L.geoJSON(geojsonData, {
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
      });
      bordersLayer.addLayer(borderGeoJson); // add to group, not map directly

    } catch (error) {
      console.error(`Error loading border file ${fileName}:`, error);
      continue;
    }

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
  return { bordersLayer, markersLayer };
};

const setLegend = () => {
  if (!map) return;

  const legend = new L.Control({ position: 'bottomright' });

  legend.onAdd = (): HTMLElement => {
    const div = L.DomUtil.create('div');
    div.innerHTML = `
      <div style="
        background: white;
        padding: 10px 14px;
        border-radius: 8px;
        box-shadow: 0 1px 5px rgba(0,0,0,0.3);
        font-size: 13px;
        line-height: 24px;
      ">
        <b style="display:block; margin-bottom:6px;">Legend</b>

        <div>
          <span style="
            display:inline-block; width:16px; height:16px;
            background:#3388ff; opacity:0.4;
            border: 2px solid #3388ff;
            vertical-align:middle; margin-right:6px;
          "></span>
          Country border
        </div>

        <div>
          <img src="${icon}" style="width:13px; height:20px; vertical-align:middle; margin-right:6px;">
          University
        </div>

        <div>
          <span style="
            display:inline-block; width:20px; height:20px;
            background:#3388ff; color:white;
            border-radius:50%; text-align:center;
            font-size:11px; line-height:20px;
            vertical-align:middle; margin-right:6px;
          ">3</span>
          University cluster
        </div>

      </div>
    `;
    return div;
  };

  legend.addTo(map);
};

onMounted(async () => {
  if (!mapContainer.value) return;

  const europeBounds = L.latLngBounds(
      L.latLng(24.0, -35.0),
      L.latLng(72.0, 45.0)
  );

  map = L.map(mapContainer.value, {
    maxBounds: europeBounds,
    maxBoundsViscosity: 1.0,
    minZoom: 4
  });

  map.fitBounds(europeBounds);

  const osmLayer = L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '&copy; OpenStreetMap contributors'
  }).addTo(map);

  const satelliteLayer = L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', {
    attribution: '&copy; Esri'
  });

  const { bordersLayer, markersLayer } = await fetchDrawBordersAndPlaceMarkers();

  // add both layers to map by default
  bordersLayer.addTo(map);
  markersLayer.addTo(map);

  // layer control to toggle them
  L.control.layers(
      {
        'Street': osmLayer,
        'Satellite': satelliteLayer,
      },
      {
        'Borders': bordersLayer,
        'Universities': markersLayer,
      }
  ).addTo(map);

  setLegend();
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