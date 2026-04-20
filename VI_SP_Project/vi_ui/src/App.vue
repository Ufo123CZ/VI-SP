<script setup lang="ts">
import {onMounted, onUnmounted, ref, computed} from 'vue';
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

const RedIcon = L.icon({
  iconUrl: 'https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-red.png',
  shadowUrl: iconShadow,
  iconSize: [25, 41],
  iconAnchor: [12, 41],
  popupAnchor: [1, -34]
});
// -------------------------

const mapContainer = ref<HTMLElement | null>(null);
let map: L.Map | null = null;

// Marker management
const markerRegistry: Map<string, L.Marker> = new Map();
let highlightedMarker: L.Marker | null = null;

// Store country-specific cluster groups and university data
const countryClusterGroups: Record<string, L.MarkerClusterGroup> = {};
const universitiesData = ref<Record<string, University[]>>({});
const availableCountries = ref<string[]>([]);

// Search state
const searchQuery = ref('');
const selectedCountry = ref<string>('all');

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

type SearchResult = {
  countryCode: string;
  uni: University;
  dept?: Department;
};

const highlightMarker = (marker: L.Marker) => {
  if (highlightedMarker && highlightedMarker !== marker) {
    highlightedMarker.setIcon(DefaultIcon);
  }
  marker.setIcon(RedIcon);
  highlightedMarker = marker;
};

// Computed search results
const searchResults = computed((): SearchResult[] => {
  const query = searchQuery.value.trim().toLowerCase();
  if (!query) return [];

  const results: SearchResult[] = [];

  for (const [countryCode, unis] of Object.entries(universitiesData.value)) {
    if (selectedCountry.value !== 'all' && selectedCountry.value !== countryCode) continue;

    unis.forEach((uni) => {
      if (uni.departments && uni.departments.length > 0) {
        uni.departments.forEach((dept) => {
          if (
              uni.name.toLowerCase().includes(query) ||
              dept.name.toLowerCase().includes(query)
          ) {
            results.push({ countryCode, uni, dept });
          }
        });
      } else {
        if (uni.name.toLowerCase().includes(query)) {
          results.push({ countryCode, uni });
        }
      }
    });
  }

  return results.slice(0, 20); // cap at 20 results
});

const flyToResult = (result: SearchResult) => {
  if (!map) return;

  const location = result.dept?.location ?? result.uni.location;
  const lat = location?.lat;
  const lon = location?.lon;

  if (lat && lon) {
    map.flyTo([lat, lon], 17, {
      animate: true,
      duration: 0.8,
    });

    map.once('moveend', () => {
      const marker = markerRegistry.get(`${lat},${lon}`);
      if (marker) {
        highlightMarker(marker);
        marker.openPopup();
      }
    });
  }

  searchQuery.value = '';
};

const fetchDrawBordersAndPlaceMarkers = async (): Promise<{
  countryLayers: Record<string, { borders: L.LayerGroup; markers: L.LayerGroup }>;
}> => {
  const bordersLayer = L.layerGroup();
  const markersLayer = L.layerGroup();
  const countryLayers: Record<string, { borders: L.LayerGroup; markers: L.LayerGroup }> = {};

  if (!map) return { countryLayers };

  const manifestResponse = await fetch('/borders/manifest.json');
  const fileNames: string[] = await manifestResponse.json();

  for (const fileName of fileNames) {
    const countryCode = fileName.replace('.geo.json', '');

    // per-country layer groups
    const countryBordersLayer = L.layerGroup();
    const countryMarkersLayer = L.layerGroup();
    countryLayers[countryCode] = { borders: countryBordersLayer, markers: countryMarkersLayer };

    try {
      const borderResponse = await fetch(`/borders/${fileName}`);
      const geojsonData = await borderResponse.json();

      const clusterGroup = L.markerClusterGroup({ maxClusterRadius: 50 });
      countryClusterGroups[countryCode] = clusterGroup;
      countryMarkersLayer.addLayer(clusterGroup); // into country layer
      markersLayer.addLayer(countryMarkersLayer); // into global layer

      const borderGeoJson = L.geoJSON(geojsonData, {
        style: { color: '#76aefd', weight: 2, fillOpacity: 0.1, fillColor: '#5ea1ff' },
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
      countryBordersLayer.addLayer(borderGeoJson); // into country layer
      bordersLayer.addLayer(countryBordersLayer);  // into global layer

    } catch (error) {
      console.error(`Error loading border file ${fileName}:`, error);
      continue;
    }

    try {
      const unisResponse = await fetch(`/unis/${countryCode}.json`);
      const unis: University[] = await unisResponse.json();
      const clusterGroup = countryClusterGroups[countryCode];

      universitiesData.value[countryCode] = unis;
      availableCountries.value.push(countryCode);

      unis.forEach((uni) => {
        if (uni.departments && uni.departments.length > 0) {
          uni.departments.forEach((dept) => {
            const lat = dept.location?.lat;
            const lon = dept.location?.lon;
            if (lat && lon) {
              const marker = L.marker([lat, lon])
                  .bindPopup(`<b>${uni.name}</b><br/><span>${dept.name}</span>`)
                  .addTo(clusterGroup);
              markerRegistry.set(`${lat},${lon}`, marker);
              marker.on('click', () => highlightMarker(marker));
            }
          });
        } else {
          const lat = uni.location?.lat;
          const lon = uni.location?.lon;
          if (lat && lon) {
            const marker = L.marker([lat, lon])
                .bindPopup(`<b>${uni.name}</b>`)
                .addTo(clusterGroup);
            markerRegistry.set(`${lat},${lon}`, marker);
            marker.on('click', () => highlightMarker(marker));
          }
        }
      });

    } catch (error) {
      console.error(`No universities file found for ${countryCode}`);
    }
  }

  return { countryLayers };
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
    minZoom: 4,
    zoomControl: false, // disable default position
  });

  // re-add it at bottom left
  L.control.zoom({ position: 'bottomleft' }).addTo(map);

  map.fitBounds(europeBounds);

  const osmLayer = L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '&copy; OpenStreetMap contributors'
  }).addTo(map);

  const satelliteLayer = L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', {
    attribution: '&copy; Esri'
  });

  const { countryLayers } = await fetchDrawBordersAndPlaceMarkers();

  // build per-country overlays
  const overlays: Record<string, L.Layer> = {};
  const countryGroupLayers: L.LayerGroup[] = [];

  for (const [countryCode, layers] of Object.entries(countryLayers)) {
    const code = countryCode.toUpperCase();
    const countryGroup = L.layerGroup([layers.borders, layers.markers]);
    overlays[code] = countryGroup;
    countryGroupLayers.push(countryGroup);
  }

  // add all to map by default = all checked
  countryGroupLayers.forEach(layer => layer.addTo(map!));

  L.control.layers(
      { 'Street': osmLayer, 'Satellite': satelliteLayer },
      overlays,
      { position: 'bottomleft' }
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
    <!-- Search header -->
    <div style="
      position: fixed;
      top: 0; left: 0; right: 0;
      z-index: 1000;
      background: white;
      padding: 10px 16px;
      box-shadow: 0 2px 6px rgba(0,0,0,0.2);
      display: flex;
      gap: 10px;
      align-items: center;
    ">
      <!-- Country filter -->
      <select
          v-model="selectedCountry"
          style="padding: 6px 10px; border-radius: 6px; border: 1px solid #ccc; font-size: 13px;"
      >
        <option value="all">All countries</option>
        <option v-for="code in availableCountries" :key="code" :value="code">
          {{ code.toUpperCase() }}
        </option>
      </select>

      <!-- Search input -->
      <div style="position: relative; flex: 1;">
        <input
            v-model="searchQuery"
            type="text"
            placeholder="Search universities..."
            style="
            width: 100%;
            padding: 6px 10px;
            border-radius: 6px;
            border: 1px solid #ccc;
            font-size: 13px;
            box-sizing: border-box;
          "
        />

        <!-- Results dropdown -->
        <div
            v-if="searchResults.length > 0"
            style="
            position: absolute;
            top: 100%; left: 0; right: 0;
            background: white;
            border: 1px solid #ccc;
            border-radius: 6px;
            margin-top: 4px;
            max-height: 300px;
            overflow-y: auto;
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
            z-index: 1001;
          "
        >
          <div
              v-for="(result, i) in searchResults"
              :key="i"
              @click="flyToResult(result)"
              style="
              padding: 8px 12px;
              cursor: pointer;
              border-bottom: 1px solid #f0f0f0;
              font-size: 13px;
            "
              onmouseover="this.style.background='#f5f5f5'"
              onmouseout="this.style.background='white'"
          >
            <div style="font-weight: 600;">{{ result.uni.name }}</div>
            <div style="color: #666; font-size: 11px;">
              {{ result.dept?.name ?? result.uni.institution }} · {{ result.countryCode.toUpperCase() }}
            </div>
          </div>
        </div>

        <!-- No results -->
        <div
            v-else-if="searchQuery.trim().length > 0"
            style="
            position: absolute;
            top: 100%; left: 0; right: 0;
            background: white;
            border: 1px solid #ccc;
            border-radius: 6px;
            margin-top: 4px;
            padding: 10px 12px;
            font-size: 13px;
            color: #999;
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
            z-index: 1001;
          "
        >
          No results found
        </div>

      </div>
    </div>

    <!-- Map pushed down by header height -->
    <div ref="mapContainer" style="height: 100vh; width: 100vw; padding-top: 50px; box-sizing: border-box; display: block;"></div>
  </main>
</template>

<style scoped>
:global(body) {
  margin: 0;
  padding: 0;
}
</style>