<script setup lang="ts">
import { onMounted, onUnmounted, ref } from 'vue';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';

import 'leaflet.markercluster';
import 'leaflet.markercluster/dist/MarkerCluster.css';
import 'leaflet.markercluster/dist/MarkerCluster.Default.css';

import icon from 'leaflet/dist/images/marker-icon.png';
import iconShadow from 'leaflet/dist/images/marker-shadow.png';

import type { University, IEPartnerCountry, SearchResult, ParsedDataDictionary, ModalPayload } from '@/types';
import { useChoropleth } from './utils/useChoropleth';
import ChoroplethPanel from './ChoroplethPanel.vue';

// ── Icons ─────────────────────────────────────────────────────────────────────

const DefaultIcon = L.icon({ iconUrl: icon, shadowUrl: iconShadow, iconSize: [25, 41], iconAnchor: [12, 41], popupAnchor: [1, -34] });
L.Marker.prototype.options.icon = DefaultIcon;

const RedIcon = L.icon({
  iconUrl: 'https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-red.png',
  shadowUrl: iconShadow, iconSize: [25, 41], iconAnchor: [12, 41], popupAnchor: [1, -34],
});
const GreenIcon = L.icon({
  iconUrl: 'https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-green.png',
  shadowUrl: iconShadow, iconSize: [25, 41], iconAnchor: [12, 41], popupAnchor: [1, -34],
});

// ── Emits ─────────────────────────────────────────────────────────────────────

const emit = defineEmits<{
  (e: 'data-loaded', payload: { unis: Record<string, University[]>, partners: IEPartnerCountry[], countries: string[], allCountriesData: any }): void;
  (e: 'show-details', payload: ModalPayload): void;
}>();

// ── Map state ─────────────────────────────────────────────────────────────────

const mapContainer = ref<HTMLElement | null>(null);
let map: L.Map | null = null;

const markerRegistry         = new Map<string, L.Marker>();
const combinedMarkerRegistry = new Map<string, L.Marker>();
const iePartnerMarkers       = new Set<L.Marker>();
const iePartnerCoords        = new Set<string>();
const countryClusterGroups: Record<string, L.MarkerClusterGroup> = {};
const countryGroupMap:      Record<string, L.LayerGroup> = {};

let highlightedMarker:  L.Marker | null = null;
let ieLayerRef:         L.LayerGroup | null = null;
let unisWrapperRef:     L.LayerGroup | null = null;
let allBordersLayerRef: L.LayerGroup | null = null;
let combinedActive = false;
let syncLayerContentsRef: (() => void) | null = null;

const universitiesData: Record<string, University[]> = {};
const availableCountries: string[] = [];
const iePartnersData: IEPartnerCountry[] = [];

// ── Data ──────────────────────────────────────────────────────────────────────

const parsedCountriesData = ref<ParsedDataDictionary>({});
const parsedMembersData   = ref<ParsedDataDictionary>({});
const parsedEterData      = ref<ParsedDataDictionary>({});

// ── Choropleth ────────────────────────────────────────────────────────────────

const choropleth     = useChoropleth(parsedCountriesData);
const choroplethOpen = ref(false);

// ── Helpers ───────────────────────────────────────────────────────────────────

const cleanForMatch = (str: string) => str ? str.toLowerCase().replace(/[^a-z0-9]/g, '') : '';

const findMatchInDictionary = (searchName: string, dictionary: ParsedDataDictionary) => {
  if (!searchName || !dictionary || Object.keys(dictionary).length === 0) return null;
  const lowerSearch = cleanForMatch(searchName);
  const keys = Object.keys(dictionary);
  const matchedKey = keys.find(k => {
    const cleanK = cleanForMatch(k);
    if (cleanK.length < 5 || lowerSearch.length < 5) return cleanK === lowerSearch;
    return cleanK.includes(lowerSearch) || lowerSearch.includes(cleanK);
  });
  return matchedKey ? { matchedName: matchedKey, data: dictionary[matchedKey] } : null;
};

const handleInstitutionDetailsClick = (rawName: string) => {
  const matchMember = findMatchInDictionary(rawName, parsedMembersData.value);
  const matchEter   = findMatchInDictionary(rawName, parsedEterData.value);
  const title = matchMember?.matchedName ?? matchEter?.matchedName ?? rawName;
  emit('show-details', {
    title,
    subtitle: 'Institution Details',
    data: {
      member: matchMember?.data ?? null,
      eter:   matchEter?.data.informatics_data ?? null,
    },
  });
};

const highlightMarker = (marker: L.Marker) => {
  if (highlightedMarker && highlightedMarker !== marker) {
    highlightedMarker.setIcon(iePartnerMarkers.has(highlightedMarker) ? GreenIcon : DefaultIcon);
  }
  marker.setIcon(RedIcon);
  highlightedMarker = marker;
};

// ── Exposed API ───────────────────────────────────────────────────────────────

const flyToResult = (result: SearchResult) => {
  if (!map) return;
  const lat = result.isIEPartner ? result.iePartner?.lat : (result.dept?.location ?? result.uni?.location)?.lat;
  const lon = result.isIEPartner ? result.iePartner?.lon : (result.dept?.location ?? result.uni?.location)?.lon;
  if (!lat || !lon) return;

  if (result.isIEPartner) {
    if (ieLayerRef && !map.hasLayer(ieLayerRef)) { ieLayerRef.addTo(map); syncLayerContentsRef?.(); }
  } else {
    if (unisWrapperRef && !map.hasLayer(unisWrapperRef)) { unisWrapperRef.addTo(map); syncLayerContentsRef?.(); }
  }
  map.flyTo([lat, lon], 17, { animate: true, duration: 0.8 });
  map.once('moveend', () => {
    const registry = combinedActive ? combinedMarkerRegistry : markerRegistry;
    const marker = registry.get(`${lat},${lon}`);
    if (marker) { highlightMarker(marker); marker.openPopup(); }
  });
};

defineExpose({ flyToResult });

// ── Map building ──────────────────────────────────────────────────────────────

const fetchDrawBordersAndPlaceMarkers = async (): Promise<{ countryLayers: Record<string, { borders: L.LayerGroup; markers: L.LayerGroup }> }> => {
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
      const clusterGroup = L.markerClusterGroup({ maxClusterRadius: 100 });
      countryClusterGroups[countryCode] = clusterGroup;
      countryMarkersLayer.addLayer(clusterGroup);
      markersLayer.addLayer(countryMarkersLayer);

      const borderGeoJson = L.geoJSON(geojsonData, {
        style: { color: 'rgb(33,116,245)', weight: 1, fillOpacity: 0.1, fillColor: '#2174f5' },
        onEachFeature: (feature: any, layer: L.Layer) => {
          const countryName = feature.properties.NAME || feature.properties.name || 'Unknown Country';
          const match = findMatchInDictionary(countryName, parsedCountriesData.value);
          (layer as any).options.className = 'clickable-country';
          layer.bindPopup(`<b>${countryName}</b><br><span style="font-size:11px;color:#666">Click map area for details</span>`);

          choropleth.registerPath(countryName, layer as L.Path);

          layer.on('click', () => {
            emit('show-details', { title: match?.matchedName ?? countryName, subtitle: 'Country Overview', data: match?.data ?? null });
          });
          layer.on('mouseover', (e: L.LeafletMouseEvent) => {
            (e.target as L.Path).setStyle({ fillOpacity: choropleth.active.value ? 0.9 : 0.4 });
          });
          layer.on('mouseout', (e: L.LeafletMouseEvent) => {
            choropleth.restoreColor(countryName, e.target as L.Path);
          });
        },
      });
      countryBordersLayer.addLayer(borderGeoJson);
      bordersLayer.addLayer(countryBordersLayer);
    } catch { continue; }

    try {
      const unisResponse = await fetch(`/unis/${countryCode}.json`);
      if (!unisResponse.ok) continue;
      const unis: University[] = await unisResponse.json();
      const clusterGroup = countryClusterGroups[countryCode];
      universitiesData[countryCode] = unis;
      availableCountries.push(countryCode);

      unis.forEach((uni) => {
        const placeMarker = (lat: number, lon: number, deptName?: string, link?: string) => {
          const marker = L.marker([lat, lon])
              .bindPopup(`
              <b>${uni.name}</b>${deptName ? `<br/><span>${deptName}</span>` : ''}
              ${link ? `<br/><a class="popup-link" href="${link}" target="_blank">Visit website</a>` : ''}
              <div class="popup-action"><button class="popup-details-btn">View Statistics</button></div>
            `)
              .addTo(clusterGroup);
          markerRegistry.set(`${lat},${lon}`, marker);
          marker.on('click', () => highlightMarker(marker));
          marker.on('popupopen', (e) => {
            const btn = e.popup.getElement()?.querySelector('.popup-details-btn');
            if (btn) btn.onclick = () => handleInstitutionDetailsClick(uni.name);
          });
        };
        if (uni.departments?.length) {
          uni.departments.forEach(dept => { if (dept.location?.lat && dept.location?.lon) placeMarker(dept.location.lat, dept.location.lon, dept.name, dept.link); });
        } else if (uni.location?.lat && uni.location?.lon) {
          placeMarker(uni.location.lat, uni.location.lon, undefined, uni.link);
        }
      });
    } catch { }
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
        <div class="legend-item"><span class="legend-swatch border-swatch"></span>Country border</div>
        <div class="legend-item"><img src="${icon}" class="legend-icon">University</div>
        <div class="legend-item"><img src="https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-green.png" class="legend-icon">IE Members</div>
        <div class="legend-item"><span class="legend-swatch cluster-swatch">3</span>University cluster</div>
      </div>`;
    return div;
  };
  legend.addTo(map);
};

const load_ie_partners = async (): Promise<L.LayerGroup> => {
  const iePartnersLayer = L.layerGroup();
  try {
    const countries: IEPartnerCountry[] = await fetch('/ie_members/ie_members.json').then(r => r.json());
    for (const country of countries) iePartnersData.push(country);
    const ieCountryClusters: Record<string, L.MarkerClusterGroup> = {};
    countries.forEach(country => {
      if (!ieCountryClusters[country.country_code]) {
        ieCountryClusters[country.country_code] = L.markerClusterGroup({ maxClusterRadius: 100 });
        iePartnersLayer.addLayer(ieCountryClusters[country.country_code]);
      }
      const cluster = ieCountryClusters[country.country_code];
      country.partners.forEach(partner => {
        if (!partner.lat || !partner.lon) return;
        const marker = L.marker([partner.lat, partner.lon], { icon: GreenIcon, zIndexOffset: 1000 })
            .bindPopup(`
            <b>${partner.uni_name}</b><br/>${partner.dept_name ? `<span>${partner.dept_name}</span><br/>` : ''}
            <span class="ie-star-popup">★ IE Partner</span><br/>
            ${partner.link ? `<a class="popup-link" href="${partner.link}" target="_blank">Visit website</a>` : ''}
            <div class="popup-action"><button class="popup-details-btn">View Statistics</button></div>
          `)
            .addTo(cluster);
        iePartnerMarkers.add(marker);
        iePartnerCoords.add(`${partner.lat},${partner.lon}`);
        markerRegistry.set(`${partner.lat},${partner.lon}`, marker);
        marker.on('click', (e) => { L.DomEvent.stopPropagation(e); highlightMarker(marker); });
        marker.on('popupopen', (e) => {
          const btn = e.popup.getElement()?.querySelector('.popup-details-btn');
          if (btn) btn.onclick = () => handleInstitutionDetailsClick(partner.uni_name || partner.dept_name);
        });
      });
    });
  } catch (error) { console.error('Error loading IE partners:', error); }
  return iePartnersLayer;
};

const buildCombinedLayer = (): L.LayerGroup => {
  const combinedLayer = L.layerGroup();
  const clusters: Record<string, L.MarkerClusterGroup> = {};
  const getCluster = (code: string) => {
    if (!clusters[code]) { clusters[code] = L.markerClusterGroup({ maxClusterRadius: 100 }); combinedLayer.addLayer(clusters[code]); }
    return clusters[code];
  };

  for (const [countryCode, unis] of Object.entries(universitiesData)) {
    const cluster = getCluster(countryCode);
    unis.forEach(uni => {
      const placeMarker = (lat: number, lon: number, deptName?: string, link?: string) => {
        if (iePartnerCoords.has(`${lat},${lon}`)) return;
        const marker = L.marker([lat, lon])
            .bindPopup(`
            <b>${uni.name}</b>${deptName ? `<br/><span>${deptName}</span>` : ''}
            ${link ? `<br/><a class="popup-link" href="${link}" target="_blank">Visit website</a>` : ''}
            <div class="popup-action"><button class="popup-details-btn">View Statistics</button></div>
          `)
            .addTo(cluster);
        combinedMarkerRegistry.set(`${lat},${lon}`, marker);
        marker.on('click', () => highlightMarker(marker));
        marker.on('popupopen', (e) => {
          const btn = e.popup.getElement()?.querySelector('.popup-details-btn');
          if (btn) btn.onclick = () => handleInstitutionDetailsClick(uni.name);
        });
      };
      if (uni.departments?.length) {
        uni.departments.forEach(dept => { if (dept.location?.lat && dept.location?.lon) placeMarker(dept.location.lat, dept.location.lon, dept.name, dept.link); });
      } else if (uni.location?.lat && uni.location?.lon) {
        placeMarker(uni.location.lat, uni.location.lon, undefined, uni.link);
      }
    });
  }

  const seen: Record<string, true> = {};
  iePartnersData.forEach(country => {
    const cluster = getCluster(country.country_code);
    country.partners.forEach(partner => {
      if (!partner.lat || !partner.lon || seen[`${partner.lat},${partner.lon}`]) return;
      seen[`${partner.lat},${partner.lon}`] = true;
      const marker = L.marker([partner.lat, partner.lon], { icon: GreenIcon, zIndexOffset: 1000 })
          .bindPopup(`
          <b>${partner.uni_name}</b><br/>${partner.dept_name ? `<span>${partner.dept_name}</span><br/>` : ''}
          <span class="ie-star-popup">★ IE Partner</span><br/>
          ${partner.link ? `<a class="popup-link" href="${partner.link}" target="_blank">Visit website</a>` : ''}
          <div class="popup-action"><button class="popup-details-btn">View Statistics</button></div>
        `)
          .addTo(cluster);
      iePartnerMarkers.add(marker);
      combinedMarkerRegistry.set(`${partner.lat},${partner.lon}`, marker);
      marker.on('click', (e) => { L.DomEvent.stopPropagation(e); highlightMarker(marker); });
      marker.on('popupopen', (e) => {
        const btn = e.popup.getElement()?.querySelector('.popup-details-btn');
        if (btn) btn.onclick = () => handleInstitutionDetailsClick(partner.uni_name || partner.dept_name);
      });
    });
  });

  return combinedLayer;
};

// ── Lifecycle ─────────────────────────────────────────────────────────────────

onMounted(async () => {
  if (!mapContainer.value) return;

  const fetchJsonSafely = async (url: string) => {
    try {
      const res = await fetch(url);
      if (!res.ok) return {};
      const text = await res.text();
      if (text.trim().startsWith('<')) { console.warn(`[Map] ${url} returned HTML`); return {}; }
      return JSON.parse(text);
    } catch (e) { console.error(`[Map] Failed to parse ${url}:`, e); return {}; }
  };

  parsedCountriesData.value = await fetchJsonSafely('/countries_data/countries_parsed.json');
  parsedMembersData.value   = await fetchJsonSafely('/members_data/members_parsed.json');
  parsedEterData.value      = await fetchJsonSafely('/eter_data/eter_parsed.json');

  choropleth.init();

  const europeBounds = L.latLngBounds(L.latLng(24.0, -35.0), L.latLng(72.0, 52.0));
  map = L.map(mapContainer.value, { maxBounds: europeBounds, maxBoundsViscosity: 1.0, minZoom: 4, zoomControl: false });
  L.control.zoom({ position: 'bottomleft' }).addTo(map);
  map.fitBounds(europeBounds);

  map.on('click', () => {
    if (highlightedMarker) {
      highlightedMarker.setIcon(iePartnerMarkers.has(highlightedMarker) ? GreenIcon : DefaultIcon);
      highlightedMarker = null;
    }
  });

  const osmLayer       = L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', { attribution: '&copy; OpenStreetMap contributors' }).addTo(map);
  const satelliteLayer = L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', { attribution: '&copy; Esri' });

  const { countryLayers } = await fetchDrawBordersAndPlaceMarkers();
  const iePartnersLayer   = await load_ie_partners();
  const combinedLayer     = buildCombinedLayer();

  emit('data-loaded', { unis: universitiesData, partners: iePartnersData, countries: availableCountries, allCountriesData: parsedCountriesData.value });

  const allBordersLayer      = L.layerGroup();
  const allUniversitiesLayer = L.layerGroup();
  allBordersLayerRef = allBordersLayer;

  for (const [countryCode, layers] of Object.entries(countryLayers)) {
    allBordersLayer.addLayer(layers.borders);
    allUniversitiesLayer.addLayer(layers.markers);
    countryGroupMap[countryCode] = allUniversitiesLayer;
  }

  const unisWrapper = L.layerGroup([allUniversitiesLayer]);
  const ieWrapper   = L.layerGroup();
  ieLayerRef     = ieWrapper;
  unisWrapperRef = unisWrapper;

  const syncLayerContents = () => {
    const unisOn = map!.hasLayer(unisWrapper);
    const ieOn   = map!.hasLayer(ieWrapper);
    if (unisOn && ieOn) {
      unisWrapper.clearLayers(); ieWrapper.clearLayers();
      if (!map!.hasLayer(combinedLayer)) combinedLayer.addTo(map!);
      combinedActive = true;
    } else {
      if (combinedActive) { map!.removeLayer(combinedLayer); combinedActive = false; }
      if (unisOn && !unisWrapper.hasLayer(allUniversitiesLayer)) unisWrapper.addLayer(allUniversitiesLayer);
      else if (!unisOn) unisWrapper.clearLayers();
      if (ieOn && !ieWrapper.hasLayer(iePartnersLayer)) ieWrapper.addLayer(iePartnersLayer);
      else if (!ieOn) ieWrapper.clearLayers();
    }
  };

  syncLayerContentsRef = syncLayerContents;
  map.on('overlayadd', syncLayerContents);
  map.on('overlayremove', syncLayerContents);

  const overlays: Record<string, L.Layer> = { 'Universities': unisWrapper, 'IE Partners': ieWrapper, 'Borders': allBordersLayer };
  allBordersLayer.addTo(map);
  unisWrapper.addTo(map);

  L.control.layers({ 'Street': osmLayer, 'Satellite': satelliteLayer }, overlays, { position: 'bottomleft' }).addTo(map);
  setLegend();
});

onUnmounted(() => { if (map) map.remove(); });
</script>

<template>
  <div class="map-wrapper">
    <div ref="mapContainer" class="map-container"></div>

    <ChoroplethPanel
        v-model:open="choroplethOpen"
        :active="choropleth.active.value"
        :dataset="choropleth.dataset.value"
        :year="choropleth.year.value"
        :field="choropleth.field.value"
        :min="choropleth.min.value"
        :max="choropleth.max.value"
        :datasets="choropleth.datasets.value"
        :years="choropleth.years.value"
        :format-value="choropleth.formatValue"
        @update:dataset="choropleth.dataset.value = $event"
        @update:year="choropleth.year.value = $event"
        @update:field="choropleth.field.value = $event"
        @dataset-change="choropleth.onDatasetChange()"
        @apply="choropleth.apply()"
        @clear="choropleth.clear()"
    />
  </div>
</template>

<style scoped>
.map-wrapper   { position: relative; width: 100vw; height: 100vh; }
.map-container { height: 100%; width: 100%; padding-top: 50px; box-sizing: border-box; display: block; }

:deep(.clickable-country) { cursor: pointer; }
:deep(.leaflet-custom-legend) { background: white; padding: 10px 14px; border-radius: 8px; box-shadow: 0 1px 5px rgba(0,0,0,0.3); font-size: 13px; line-height: 24px; }
:deep(.leaflet-custom-legend b) { display: block; margin-bottom: 6px; }
:deep(.legend-item) { display: flex; align-items: center; }
:deep(.legend-swatch) { display: inline-block; vertical-align: middle; margin-right: 6px; }
:deep(.border-swatch) { width: 16px; height: 16px; background: #3388ff; opacity: 0.4; border: 2px solid #3388ff; }
:deep(.cluster-swatch) { width: 20px; height: 20px; background: #3388ff; color: white; border-radius: 50%; text-align: center; font-size: 11px; line-height: 20px; }
:deep(.legend-icon) { width: 13px; height: 20px; vertical-align: middle; margin-right: 6px; }
:deep(.popup-link) { font-size: 12px; }
:deep(.ie-star-popup) { color: green; font-weight: 600; }
:deep(.popup-action) { margin-top: 12px; text-align: center; }
:deep(.popup-details-btn) {
  background-color: #3388ff; color: white; border: none;
  padding: 8px 12px; border-radius: 4px; cursor: pointer;
  font-size: 12px; font-weight: bold; width: 100%; transition: background-color 0.2s;
}
:deep(.popup-details-btn:hover) { background-color: #1565c0; }
</style>