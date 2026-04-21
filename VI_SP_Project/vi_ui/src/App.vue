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

const GreenIcon = L.icon({
  iconUrl: 'https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-green.png',
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

// Store country-specific layer groups for toggling
const countryGroupMap: Record<string, L.LayerGroup> = {};
let ieLayerRef: L.LayerGroup | null = null;

// Search state
const searchQuery = ref('');
const selectedCountry = ref<string>('all');
const showIEOnly = ref(false);

// Partners
const iePartnersData = ref<IEPartnerCountry[]>([]);

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
  partner?: string;
  link?: string;
  location?: {
    lat: number | null;
    lon: number | null;
  };
  departments?: Department[];
};

type IEPartner = {
  uni_name: string;
  dept_name: string;
  link: string;
  lat: number | null;
  lon: number | null;
};

type IEPartnerCountry = {
  country: string;
  country_code: string;
  partners: IEPartner[];
};

type SearchResult = {
  countryCode: string;
  uni?: University;
  dept?: Department;
  iePartner?: IEPartner;
  isIEPartner: boolean;
};

const highlightMarker = (marker: L.Marker) => {
  if (highlightedMarker && highlightedMarker !== marker) {
    // check registry to see if it was originally green
    const wasGreen = [...markerRegistry.entries()]
        .some(([, m]) => m === highlightedMarker && ieLayerRef?.hasLayer(m));
    highlightedMarker.setIcon(wasGreen ? GreenIcon : DefaultIcon);
  }
  marker.setIcon(RedIcon);
  highlightedMarker = marker;
};

const searchResults = computed((): SearchResult[] => {
  const query = searchQuery.value.trim().toLowerCase();
  if (!query) return [];

  const results: SearchResult[] = [];

  // search universities (skip if IE only filter is on)
  if (!showIEOnly.value) {
    for (const [countryCode, unis] of Object.entries(universitiesData.value)) {
      if (selectedCountry.value !== 'all' && selectedCountry.value !== countryCode) continue;

      unis.forEach((uni) => {
        if (uni.departments && uni.departments.length > 0) {
          uni.departments.forEach((dept) => {
            if (uni.name.toLowerCase().includes(query) || dept.name.toLowerCase().includes(query)) {
              results.push({ countryCode, uni, dept, isIEPartner: false });
            }
          });
        } else {
          if (uni.name.toLowerCase().includes(query)) {
            results.push({ countryCode, uni, isIEPartner: false });
          }
        }
      });
    }
  }

  // search IE partners
  iePartnersData.value.forEach((country) => {
    if (selectedCountry.value !== 'all' && selectedCountry.value !== country.country_code) return;

    country.partners.forEach((partner) => {
      if (
          partner.uni_name.toLowerCase().includes(query) ||
          partner.dept_name.toLowerCase().includes(query)
      ) {
        results.push({
          countryCode: country.country_code,
          iePartner: partner,
          isIEPartner: true,
        });
      }
    });
  });

  return results.slice(0, 20);
});

const flyToResult = (result: SearchResult) => {
  if (!map) return;

  const lat = result.isIEPartner ? result.iePartner?.lat : (result.dept?.location ?? result.uni?.location)?.lat;
  const lon = result.isIEPartner ? result.iePartner?.lon : (result.dept?.location ?? result.uni?.location)?.lon;

  if (lat && lon) {
    if (result.isIEPartner) {
      // enable IE layer if disabled
      if (ieLayerRef && !map.hasLayer(ieLayerRef)) {
        ieLayerRef.addTo(map);
      }
    } else {
      // enable country layer if disabled
      const countryLayer = countryGroupMap[result.countryCode];
      if (countryLayer && !map.hasLayer(countryLayer)) {
        countryLayer.addTo(map);
      }
    }

    map.flyTo([lat, lon], 17, { animate: true, duration: 0.8 });

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

const fetchDrawBordersAndPlaceMarkers = async (): Promise<{ countryLayers: Record<string, { borders: L.LayerGroup; markers: L.LayerGroup }>; }> => {
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
        style: { color: '#8abcff', weight: 2, fillOpacity: 0.1, fillColor: '#5ea1ff' },
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
              const marker =
                  L.marker([lat, lon])
                  .bindPopup(`
                    <b>${uni.name}</b><br/>
                    <span>${dept.name}</span>
                    ${dept.link ? `<br/><a href="${dept.link}" target="_blank" style="font-size: 12px;">Visit website</a>` : ''}
                  `)
                  .addTo(clusterGroup);
              markerRegistry.set(`${lat},${lon}`, marker);
              marker.on('click', () => highlightMarker(marker));
            }
          });
        } else {
          const lat = uni.location?.lat;
          const lon = uni.location?.lon;
          if (lat && lon) {
            const marker =
                L.marker([lat, lon])
                    .bindPopup(`
                      <b>${uni.name}</b>
                       ${uni.link ? `<br/><a href="${uni.link}" target="_blank" style="font-size: 12px;">Visit website</a>` : ''}
                     `)
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
          <img src="https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-green.png" style="width:13px; height:20px; vertical-align:middle; margin-right:6px;">
          IE Partner
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

const load_ie_partners = async (): Promise<L.LayerGroup> => {
  const iePartnersLayer = L.layerGroup();

  try {
    const response = await fetch('/partners/ie_partners.json');
    const countries: IEPartnerCountry[] = await response.json();
    iePartnersData.value = countries; // add this line

    countries.forEach(country => {
      country.partners.forEach(partner => {
        if (!partner.lat || !partner.lon) return;

        const marker = L.marker([partner.lat, partner.lon], { icon: GreenIcon })
            .bindPopup(`
        <b>${partner.uni_name}</b><br/>
        ${partner.dept_name ? `<span>${partner.dept_name}</span><br/>` : ''}
        <span style="color: green; font-weight: 600;">★ IE Partner</span><br/>
        ${partner.link ? `<a href="${partner.link}" target="_blank" style="font-size: 12px;">Visit website</a>` : ''}
      `)
            .addTo(iePartnersLayer);

        markerRegistry.set(`${partner.lat},${partner.lon}`, marker);
        marker.on('click', (e) => {
          L.DomEvent.stopPropagation(e);
          highlightMarker(marker);
        });
      });
    });


  } catch (error) {
    console.error('Error loading IE partners:', error);
  }

  return iePartnersLayer;
};

onMounted(async () => {
  if (!mapContainer.value) return;

  const europeBounds = L.latLngBounds(
      L.latLng(24.0, -35.0),
      L.latLng(72.0, 52.0)
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
  const iePartnersLayer = await load_ie_partners();
  ieLayerRef = iePartnersLayer;

  // build per-country overlays
  const overlays: Record<string, L.Layer> = {};
  overlays['IE Partners'] = iePartnersLayer;
  const countryGroupLayers: L.LayerGroup[] = [];

  for (const [countryCode, layers] of Object.entries(countryLayers)) {
    const code = countryCode.toUpperCase();
    const countryGroup = L.layerGroup([layers.borders, layers.markers]);
    overlays[code] = countryGroup;
    countryGroupMap[countryCode] = countryGroup;
    countryGroupLayers.push(countryGroup);
  }

  // add all to map by default = all checked
  countryGroupLayers.forEach(layer => layer.addTo(map!));
  // iePartnersLayer.addTo(map!);

  L.control.layers(
      { 'Street': osmLayer, 'Satellite': satelliteLayer },
      overlays,
      { position: 'bottomleft' }
  ).addTo(map);
  setLegend();

  // map.on('click', () => {
  //   if (highlightedMarker) {
  //     highlightedMarker.setIcon(DefaultIcon);
  //     highlightedMarker = null;
  //   }
  // });

  map.on('click', () => {
    if (highlightedMarker) {
      const wasGreen = ieLayerRef?.hasLayer(highlightedMarker);
      highlightedMarker.setIcon(wasGreen ? GreenIcon : DefaultIcon);
      highlightedMarker = null;
    }
  });
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

      <!-- IE filter toggle -->
      <button
        @click="showIEOnly = !showIEOnly"
        :style="`
        padding: 6px 10px;
        border-radius: 6px;
        border: 1px solid ${showIEOnly ? 'green' : '#ccc'};
        background: ${showIEOnly ? '#f0fff0' : 'white'};
        color: ${showIEOnly ? 'green' : '#333'};
        font-size: 13px;
        cursor: pointer;
        white-space: nowrap;
      `"
      >
        ★ IE Only
      </button>

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
            <div style="font-weight: 600;">
              <span v-if="result.isIEPartner" style="color: green; margin-right: 4px;">★</span>
              {{ result.isIEPartner ? result.iePartner?.uni_name : result.uni?.name }}
            </div>
            <div style="color: #666; font-size: 11px;">
              {{ result.isIEPartner ? result.iePartner?.dept_name : (result.dept?.name ?? result.uni?.institution) }}
              · {{ result.countryCode.toUpperCase() }}
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