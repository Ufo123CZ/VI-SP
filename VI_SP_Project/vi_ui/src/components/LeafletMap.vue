<script setup lang="ts">
import { onMounted, onUnmounted, ref } from 'vue';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';

// -- Marker Clustering
import 'leaflet.markercluster';
import 'leaflet.markercluster/dist/MarkerCluster.css';
import 'leaflet.markercluster/dist/MarkerCluster.Default.css';

// --- THE VITE ICON FIX ---
import icon from 'leaflet/dist/images/marker-icon.png';
import iconShadow from 'leaflet/dist/images/marker-shadow.png';

import type { University, IEPartnerCountry, SearchResult, ParsedDataDictionary, ModalPayload } from '@/types';

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

const emit = defineEmits<{
  (e: 'data-loaded', payload: { unis: Record<string, University[]>, partners: IEPartnerCountry[], countries: string[] }): void;
  (e: 'show-details', payload: ModalPayload): void;
}>();

const mapContainer = ref<HTMLElement | null>(null);
let map: L.Map | null = null;

const markerRegistry: Map<string, L.Marker> = new Map();
let highlightedMarker: L.Marker | null = null;

const countryClusterGroups: Record<string, L.MarkerClusterGroup> = {};
const countryGroupMap: Record<string, L.LayerGroup> = {};
let ieLayerRef: L.LayerGroup | null = null;
let allBordersLayerRef: L.LayerGroup | null = null;

// Extracted internal data to emit later
const universitiesData: Record<string, University[]> = {};
const availableCountries: string[] = [];
const iePartnersData: IEPartnerCountry[] = [];

// New dictionary states
const parsedCountriesData = ref<ParsedDataDictionary>({});
const parsedMembersData = ref<ParsedDataDictionary>({});

// Fuzzy match against Object Keys
const findMatchInDictionary = (searchName: string, dictionary: ParsedDataDictionary) => {
  if (!searchName) return null;
  const lowerSearch = searchName.toLowerCase();
  const keys = Object.keys(dictionary);

  const matchedKey = keys.find(k =>
      k.toLowerCase().includes(lowerSearch) || lowerSearch.includes(k.toLowerCase())
  );

  if (matchedKey) {
    return {
      matchedName: matchedKey,
      data: dictionary[matchedKey]
    };
  }
  return null;
};

const highlightMarker = (marker: L.Marker) => {
  if (highlightedMarker && highlightedMarker !== marker) {
    const wasGreen = [...markerRegistry.entries()]
        .some(([, m]) => m === highlightedMarker && ieLayerRef?.hasLayer(m));
    highlightedMarker.setIcon(wasGreen ? GreenIcon : DefaultIcon);
  }
  marker.setIcon(RedIcon);
  highlightedMarker = marker;
};

const flyToResult = (result: SearchResult) => {
  if (!map) return;

  const lat = result.isIEPartner ? result.iePartner?.lat : (result.dept?.location ?? result.uni?.location)?.lat;
  const lon = result.isIEPartner ? result.iePartner?.lon : (result.dept?.location ?? result.uni?.location)?.lon;

  if (lat && lon) {
    if (result.isIEPartner) {
      if (ieLayerRef && !map.hasLayer(ieLayerRef)) {
        ieLayerRef.addTo(map);
      }
    } else {
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
};
defineExpose({ flyToResult });

const fetchDrawBordersAndPlaceMarkers = async (): Promise<{ countryLayers: Record<string, { borders: L.LayerGroup; markers: L.LayerGroup }>; }> => {
  const bordersLayer = L.layerGroup();
  const markersLayer = L.layerGroup();
  const countryLayers: Record<string, { borders: L.LayerGroup; markers: L.LayerGroup }> = {};

  if (!map) return { countryLayers };

  const manifestResponse = await fetch('/borders/manifest.json');
  const fileNames: string[] = await manifestResponse.json();

  for (const fileName of fileNames) {
    const countryCode = fileName.replace('.geo.json', '');

    const countryBordersLayer = L.layerGroup();
    const countryMarkersLayer = L.layerGroup();
    countryLayers[countryCode] = { borders: countryBordersLayer, markers: countryMarkersLayer };

    try {
      const borderResponse = await fetch(`/borders/${fileName}`);
      const geojsonData = await borderResponse.json();

      const clusterGroup = L.markerClusterGroup({ maxClusterRadius: 50 });
      countryClusterGroups[countryCode] = clusterGroup;
      countryMarkersLayer.addLayer(clusterGroup);
      markersLayer.addLayer(countryMarkersLayer);

      const borderGeoJson = L.geoJSON(geojsonData, {
        style: { color: 'rgb(33,116,245)', weight: 1, fillOpacity: 0.1, fillColor: '#2174f5' },
        onEachFeature: (feature: any, layer: L.Layer) => {
          const countryName = feature.properties.NAME || feature.properties.name || "Unknown Country";

          const match = findMatchInDictionary(countryName, parsedCountriesData.value);

          console.log(`[2. MAP INIT] Matching ${countryName}... Match found?`, !!match);

          if (match) {
            // Interactive UI indicating clickability
            (layer as any).options.className = 'clickable-country';
            layer.bindPopup(`<b>${countryName}</b><br><span style="font-size: 11px; color: #666;">Click map area for details</span>`);

            layer.on('click', () => {

              console.log(`[3. MAP CLICK] You clicked ${countryName}. Emitting this exact data to App.vue:`, match.data);

              emit('show-details', {
                title: match.matchedName,
                subtitle: 'Country Overview',
                data: match.data
              });
            });
          } else {
            layer.bindPopup(`<b>${countryName}</b>`);
          }

          layer.on('mouseover', (e: L.LeafletMouseEvent) => {
            (e.target as L.Path).setStyle({ fillOpacity: 0.4 });
          });
          layer.on('mouseout', (e: L.LeafletMouseEvent) => {
            (e.target as L.Path).setStyle({ fillOpacity: 0.1 });
          });
        }
      });
      countryBordersLayer.addLayer(borderGeoJson);
      bordersLayer.addLayer(countryBordersLayer);

    } catch (error) {
      console.error(`Error loading border file ${fileName}:`, error);
      continue;
    }

    try {
      const unisResponse = await fetch(`/unis/${countryCode}.json`);

      if (!unisResponse.ok) {
        continue;
      }

      const unis: University[] = await unisResponse.json();
      const clusterGroup = countryClusterGroups[countryCode];

      universitiesData[countryCode] = unis;
      availableCountries.push(countryCode);

      unis.forEach((uni) => {
        if (uni.departments && uni.departments.length > 0) {
          uni.departments.forEach((dept) => {
            const lat = dept.location?.lat;
            const lon = dept.location?.lon;
            if (lat && lon) {
              const marker = L.marker([lat, lon])
                  .bindPopup(`
                    <b>${uni.name}</b><br/>
                    <span>${dept.name}</span>
                    ${dept.link ? `<br/><a class="popup-link" href="${dept.link}" target="_blank">Visit website</a>` : ''}
                  `)
                  .addTo(clusterGroup);

              markerRegistry.set(`${lat},${lon}`, marker);
              marker.on('click', () => {
                highlightMarker(marker);
                const match = findMatchInDictionary(uni.name, parsedMembersData.value);
                if (match) {
                  emit('show-details', { title: match.matchedName, subtitle: 'University Details', data: match.data });
                }
              });
            }
          });
        } else {
          const lat = uni.location?.lat;
          const lon = uni.location?.lon;
          if (lat && lon) {
            const marker = L.marker([lat, lon])
                .bindPopup(`
                  <b>${uni.name}</b>
                   ${uni.link ? `<br/><a class="popup-link" href="${uni.link}" target="_blank">Visit website</a>` : ''}
                 `)
                .addTo(clusterGroup);

            markerRegistry.set(`${lat},${lon}`, marker);
            marker.on('click', () => {
              highlightMarker(marker);
              const match = findMatchInDictionary(uni.name, parsedMembersData.value);
              if (match) {
                emit('show-details', { title: match.matchedName, subtitle: 'University Details', data: match.data });
              }
            });
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
      <div class="leaflet-custom-legend">
        <b>Legend</b>
        <div class="legend-item">
          <span class="legend-swatch border-swatch"></span>
          Country border
        </div>
        <div class="legend-item">
          <img src="${icon}" class="legend-icon">
          University
        </div>
        <div class="legend-item">
          <img src="https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-green.png" class="legend-icon">
          IE Partner
        </div>
        <div class="legend-item">
          <span class="legend-swatch cluster-swatch">3</span>
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

    for (const country of countries) {
      iePartnersData.push(country);
    }

    countries.forEach(country => {
      country.partners.forEach(partner => {
        if (!partner.lat || !partner.lon) return;

        const marker = L.marker([partner.lat, partner.lon], {
          icon: GreenIcon,
          zIndexOffset: 1000
        })
            .bindPopup(`
        <b>${partner.uni_name}</b><br/>
        ${partner.dept_name ? `<span>${partner.dept_name}</span><br/>` : ''}
        <span class="ie-star-popup">★ IE Partner</span><br/>
        ${partner.link ? `<a class="popup-link" href="${partner.link}" target="_blank">Visit website</a>` : ''}
      `)
            .addTo(iePartnersLayer);

        markerRegistry.set(`${partner.lat},${partner.lon}`, marker);
        marker.on('click', (e) => {
          L.DomEvent.stopPropagation(e);
          highlightMarker(marker);
          const match = findMatchInDictionary(partner.uni_name, parsedMembersData.value);
          if (match) {
            emit('show-details', { title: match.matchedName, subtitle: 'University Details', data: match.data });
          }
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

  // 1. Fetch JSON Dictionaries FIRST
  try {
    const [countriesRes, membersRes] = await Promise.all([
      fetch('countries_data/countries_parsed.json'),
      fetch('members_data/members_parsed.json')
    ]);
    parsedCountriesData.value = await countriesRes.json();
    parsedMembersData.value = await membersRes.json();

    console.log('[1. MAP LOAD] Fetched countries data. Available keys:', Object.keys(parsedCountriesData.value));
  } catch (error) {
    console.error('Error loading parsed data:', error);
  }

  // 2. Map Initialization
  const europeBounds = L.latLngBounds(
      L.latLng(24.0, -35.0),
      L.latLng(72.0, 52.0)
  );

  map = L.map(mapContainer.value, {
    maxBounds: europeBounds,
    maxBoundsViscosity: 1.0,
    minZoom: 4,
    zoomControl: false,
  });

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

  // Emitting the data back to App.vue once loading is done
  emit('data-loaded', {
    unis: universitiesData,
    partners: iePartnersData,
    countries: availableCountries
  });

  const overlays: Record<string, L.Layer> = {};
  overlays['IE Partners'] = iePartnersLayer;
  const countryGroupLayers: L.LayerGroup[] = [];

  const allBordersLayer = L.layerGroup();
  allBordersLayerRef = allBordersLayer;

  for (const [countryCode, layers] of Object.entries(countryLayers)) {
    const code = countryCode.toUpperCase();
    const countryGroup = L.layerGroup([layers.markers]);
    overlays[code] = countryGroup;
    countryGroupMap[countryCode] = countryGroup;
    countryGroupLayers.push(countryGroup);
    allBordersLayer.addLayer(layers.borders);
  }

  overlays['— All Borders'] = allBordersLayer;

  countryGroupLayers.forEach(layer => layer.addTo(map!));
  allBordersLayer.addTo(map!);

  L.control.layers(
      { 'Street': osmLayer, 'Satellite': satelliteLayer },
      overlays,
      { position: 'bottomleft' }
  ).addTo(map);
  setLegend();

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
  <div ref="mapContainer" class="map-container"></div>
</template>

<style scoped>
.map-container {
  height: 100vh;
  width: 100vw;
  padding-top: 50px;
  box-sizing: border-box;
  display: block;
}

/* This targets the SVGs specifically so the user knows they can click them */
:deep(.clickable-country) {
  cursor: pointer;
}

:deep(.leaflet-custom-legend) {
  background: white;
  padding: 10px 14px;
  border-radius: 8px;
  box-shadow: 0 1px 5px rgba(0,0,0,0.3);
  font-size: 13px;
  line-height: 24px;
}

:deep(.leaflet-custom-legend b) {
  display: block;
  margin-bottom: 6px;
}

:deep(.legend-item) {
  display: flex;
  align-items: center;
}

:deep(.legend-swatch) {
  display: inline-block;
  vertical-align: middle;
  margin-right: 6px;
}

:deep(.border-swatch) {
  width: 16px;
  height: 16px;
  background: #3388ff;
  opacity: 0.4;
  border: 2px solid #3388ff;
}

:deep(.cluster-swatch) {
  width: 20px;
  height: 20px;
  background: #3388ff;
  color: white;
  border-radius: 50%;
  text-align: center;
  font-size: 11px;
  line-height: 20px;
}

:deep(.legend-icon) {
  width: 13px;
  height: 20px;
  vertical-align: middle;
  margin-right: 6px;
}

:deep(.popup-link) {
  font-size: 12px;
}

:deep(.ie-star-popup) {
  color: green;
  font-weight: 600;
}
</style>