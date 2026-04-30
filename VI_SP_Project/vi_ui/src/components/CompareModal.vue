<script setup lang="ts">
import { computed, ref, onMounted, watch } from 'vue';
import { Bar, Line } from 'vue-chartjs';

const props = defineProps<{
  isOpen: boolean;
  baseTitle: string;
  baseType: 'country' | 'institution';
  baseData: any;
  allCountriesData?: any;
}>();

const emit = defineEmits<{ (e: 'close'): void }>();

// Search & Target State
const targetTitle = ref('');
const searchQuery = ref('');
const isDropdownOpen = ref(false);

const allMembersData = ref<any>({});
const allEterData = ref<any>({});

// --- NEW: Bulletproof Fetch for CompareModal ---
const fetchJsonSafely = async (url: string) => {
  try {
    const res = await fetch(url);
    if (!res.ok) return {};
    const text = await res.text();
    if (text.trim().startsWith('<')) return {}; // Stop the HTML crash
    return JSON.parse(text);
  } catch (error) {
    console.error(`CompareModal failed to parse ${url}`, error);
    return {};
  }
};

// Fetch institution dictionaries dynamically safely
onMounted(async () => {
  if (props.baseType === 'institution') {
    allMembersData.value = (await fetchJsonSafely('/members_data/members_parsed.json')) || {};
    allEterData.value = (await fetchJsonSafely('/eter_data/eter_parsed.json')) || {};
  }
});

// Dropdown Options
const availableTargets = computed(() => {
  if (props.baseType === 'country' && props.allCountriesData) {
    return Object.keys(props.allCountriesData).filter(c => c !== props.baseTitle).sort();
  } else {
    // Combine both sets of keys
    const set = new Set([...Object.keys(allMembersData.value), ...Object.keys(allEterData.value)]);
    set.delete(props.baseTitle);
    return Array.from(set).sort();
  }
});

// Filter the targets based on what the user types in the search bar
const filteredTargets = computed(() => {
  const query = searchQuery.value.toLowerCase().trim();
  if (!query) return availableTargets.value.slice(0, 50); // Show first 50 by default to prevent lag

  return availableTargets.value
      .filter(t => t.toLowerCase().includes(query))
      .slice(0, 50);
});

// Select a target from the search results
const selectTarget = (t: string) => {
  targetTitle.value = t;
  searchQuery.value = t; // Fill the input with the selected name
  isDropdownOpen.value = false;
};

// Get the Target Data once a selection is made
const targetData = computed(() => {
  if (!targetTitle.value) return null;
  if (props.baseType === 'country') return props.allCountriesData[targetTitle.value];
  return {
    member: allMembersData.value[targetTitle.value] || null,
    eter: allEterData.value[targetTitle.value]?.informatics_data || null
  };
});

// Reset search state when modal opens/closes
watch(() => props.isOpen, (open) => {
  if (open) {
    targetTitle.value = '';
    searchQuery.value = '';
    isDropdownOpen.value = false;
  }
});

// =====================================
// CHART: COUNTRY COMPARISONS
// =====================================
const parseGroupedStats = (statsObj: any) => {
  if (!statsObj) return {};
  const groups: Record<string, { all?: any; degrees?: any }> = {};
  for (const [key, value] of Object.entries(statsObj)) {
    const levelPrefix = key.split('_')[0];
    if (!groups[levelPrefix]) groups[levelPrefix] = {};
    if (key.includes('all-semesters')) groups[levelPrefix].all = value;
    else if (key.includes('Degrees-awarded')) groups[levelPrefix].degrees = value;
  }
  return groups;
};

const baseCountryStats = computed(() => parseGroupedStats(props.baseData?.statistics));
const targetCountryStats = computed(() => parseGroupedStats(targetData.value?.statistics));
const countryLevels = computed(() => Object.keys(baseCountryStats.value));
const selectedCountryLevel = ref('');

watch(() => countryLevels.value, (l) => { if (l.length) selectedCountryLevel.value = l[0]; }, { immediate: true });

const countryEnrollmentChart = computed(() => {
  const g1 = baseCountryStats.value[selectedCountryLevel.value];
  const g2 = targetCountryStats.value[selectedCountryLevel.value];
  if (!g1 && !g2) return null;

  const ySet = new Set<string>();
  if (g1?.all) Object.keys(g1.all).forEach(y => ySet.add(y));
  if (g2?.all) Object.keys(g2.all).forEach(y => ySet.add(y));
  const years = Array.from(ySet).sort();
  if (!years.length) return null;

  return {
    labels: years,
    datasets: [
      { label: props.baseTitle, backgroundColor: '#3388ff', data: years.map(y => Number(g1?.all?.[y]?.total || 0) || 0) },
      { label: targetTitle.value, backgroundColor: '#ff9800', data: years.map(y => Number(g2?.all?.[y]?.total || 0) || 0) }
    ]
  };
});

const countryDegreesChart = computed(() => {
  const g1 = baseCountryStats.value[selectedCountryLevel.value];
  const g2 = targetCountryStats.value[selectedCountryLevel.value];
  if (!g1 && !g2) return null;

  const ySet = new Set<string>();
  if (g1?.degrees) Object.keys(g1.degrees).forEach(y => ySet.add(y));
  if (g2?.degrees) Object.keys(g2.degrees).forEach(y => ySet.add(y));
  const years = Array.from(ySet).sort();
  if (!years.length) return null;

  return {
    labels: years,
    datasets: [
      { type: 'line', label: props.baseTitle, borderColor: '#3388ff', backgroundColor: '#3388ff', borderWidth: 2, pointRadius: 4, data: years.map(y => Number(g1?.degrees?.[y]?.total || 0) || 0) },
      { type: 'line', label: targetTitle.value, borderColor: '#ff9800', backgroundColor: '#ff9800', borderWidth: 2, borderDash: [5, 5], pointRadius: 4, data: years.map(y => Number(g2?.degrees?.[y]?.total || 0) || 0) }
    ]
  };
});

const countryPipelineChart = computed(() => {
  const buildFemaleArr = (statsObj: any, prefix: string, targetYears: string[]) => {
    const key = Object.keys(statsObj || {}).find(k => k.startsWith(prefix + '_') && k.includes('all-semesters'));
    const s = key ? statsObj[key] : null;
    return targetYears.map(y => (!s || !s[y] || s[y]['female %'] === 'n.a.') ? null : Number(s[y]['female %']) * 100);
  };

  const yearSet = new Set<string>();
  [props.baseData?.statistics, targetData.value?.statistics].forEach(stats => {
    if (stats) Object.values(stats).forEach(ds => Object.keys(ds as any).forEach(y => yearSet.add(y)));
  });
  const years = Array.from(yearSet).sort();
  if (!years.length) return null;

  const datasets = [
    { label: `${props.baseTitle} (BSc % Female)`, borderColor: '#1565c0', backgroundColor: '#1565c0', data: buildFemaleArr(props.baseData?.statistics, 'BSc', years), tension: 0.3 },
    { label: `${props.baseTitle} (MSc % Female)`, borderColor: '#e65100', backgroundColor: '#e65100', data: buildFemaleArr(props.baseData?.statistics, 'MSc', years), tension: 0.3 }
  ];

  if (targetTitle.value && targetData.value?.statistics) {
    datasets.push(
        { label: `${targetTitle.value} (BSc % Female)`, borderColor: '#1565c0', backgroundColor: '#1565c0', borderDash: [5,5], data: buildFemaleArr(targetData.value.statistics, 'BSc', years), tension: 0.3 },
        { label: `${targetTitle.value} (MSc % Female)`, borderColor: '#e65100', backgroundColor: '#e65100', borderDash: [5,5], data: buildFemaleArr(targetData.value.statistics, 'MSc', years), tension: 0.3 }
    );
  }
  return { labels: years, datasets };
});

const pipelineChartOptions = {
  responsive: true, maintainAspectRatio: false, plugins: { legend: { position: 'top' as const } },
  scales: { y: { beginAtZero: true, ticks: { callback: function(value: any) { return value + '%'; } } } }
};

// =====================================
// CHART: INSTITUTION COMPARISONS
// =====================================
const instEnrollmentChart = computed(() => {
  const levels = ['Bachelor', 'Master', 'PhD'];
  const getTotals = (d: any) => levels.map(l => d?.data?.find((i: any) => i?.level === l && i?.category === 'Students all semesters')?.stats_2023_2024?.total || 0);

  return {
    labels: levels,
    datasets: [
      { label: props.baseTitle, backgroundColor: '#3388ff', data: getTotals(props.baseData?.member) },
      { label: targetTitle.value, backgroundColor: '#ff9800', data: getTotals(targetData.value?.member) }
    ]
  };
});

const eterYears = computed(() => {
  const ySet = new Set<string>();
  if (props.baseData?.eter) Object.keys(props.baseData.eter).forEach(y => ySet.add(y));
  if (targetData.value?.eter) Object.keys(targetData.value.eter).forEach(y => ySet.add(y));
  return Array.from(ySet).sort();
});

const eterEnrollmentChart = computed(() => {
  if (!eterYears.value.length) return null;
  return {
    labels: eterYears.value,
    datasets: [
      { label: `${props.baseTitle} (BSc)`, backgroundColor: '#3388ff', data: eterYears.value.map(y => props.baseData?.eter?.[y]?.enrolled_bsc || 0) },
      { label: `${targetTitle.value} (BSc)`, backgroundColor: '#1565c0', data: eterYears.value.map(y => targetData.value?.eter?.[y]?.enrolled_bsc || 0) },
      { label: `${props.baseTitle} (MSc)`, backgroundColor: '#ff9800', data: eterYears.value.map(y => props.baseData?.eter?.[y]?.enrolled_msc || 0) },
      { label: `${targetTitle.value} (MSc)`, backgroundColor: '#e65100', data: eterYears.value.map(y => targetData.value?.eter?.[y]?.enrolled_msc || 0) }
    ]
  };
});

const chartOptions = { responsive: true, maintainAspectRatio: false, plugins: { legend: { position: 'top' as const } } };
</script>

<template>
  <div v-if="isOpen" class="modal-overlay" style="z-index: 10000;" @click.self="emit('close')">
    <div class="modal-content">
      <button class="close-btn" @click="emit('close')">✕</button>

      <div class="modal-header">
        <h2>Compare {{ baseType === 'country' ? 'Countries' : 'Institutions' }}</h2>
        <div class="compare-row">
          <div class="compare-entity base">{{ baseTitle }}</div>
          <div class="compare-vs">VS</div>
          <div class="compare-entity target">

            <div class="autocomplete-wrapper">
              <input
                  type="text"
                  v-model="searchQuery"
                  @focus="isDropdownOpen = true"
                  @blur="setTimeout(() => isDropdownOpen = false, 200)"
                  :placeholder="`Search ${baseType} to compare...`"
                  class="compare-input"
              />
              <ul v-show="isDropdownOpen" class="autocomplete-list">
                <li v-if="filteredTargets.length === 0" class="no-results">No matches found</li>
                <li v-for="t in filteredTargets" :key="t" @click="selectTarget(t)">
                  {{ t }}
                </li>
              </ul>
            </div>

          </div>
        </div>
      </div>

      <div class="compare-body">
        <div v-if="!targetTitle" class="no-data-state">
          <p>Please search and select a {{ baseType }} from the box above to begin the comparison.</p>
        </div>

        <div v-else>
          <div v-if="baseType === 'country'">
            <div class="dataset-selector" style="margin-bottom: 20px; display: flex; justify-content: center; align-items: center; flex-direction: column;">
              <label style="display:block; margin-bottom:8px; font-weight:bold;">Degree Level (For Enrollment & Degrees):</label>
              <div style="display:flex; gap:8px;">
                <button v-for="l in countryLevels" :key="l" @click="selectedCountryLevel = l" class="pill-btn" :class="{active: selectedCountryLevel === l}">{{ l }}</button>
              </div>
            </div>

            <div class="landscape-card" v-if="countryEnrollmentChart">
              <h3>Total Enrollment Comparison</h3>
              <div class="chart-container landscape-chart"><Bar :data="countryEnrollmentChart" :options="chartOptions" /></div>
            </div>

            <div class="landscape-card" v-if="countryDegreesChart">
              <h3>Degrees Awarded Comparison</h3>
              <div class="chart-container landscape-chart"><Line :data="countryDegreesChart" :options="chartOptions" /></div>
            </div>

            <div class="landscape-card" v-if="countryPipelineChart">
              <h3>Gender Parity Comparison (% Female)</h3>
              <div class="chart-container landscape-chart"><Line :data="countryPipelineChart" :options="pipelineChartOptions" /></div>
            </div>
          </div>

          <div v-if="baseType === 'institution'">
            <div class="landscape-card">
              <h3>Current Enrollment (Informatics Europe)</h3>
              <div class="chart-container landscape-chart">
                <Bar :data="instEnrollmentChart" :options="chartOptions" />
              </div>
            </div>

            <div class="landscape-card" v-if="eterEnrollmentChart">
              <h3>Historical Enrollment (ETER)</h3>
              <div class="chart-container landscape-chart">
                <Bar :data="eterEnrollmentChart" :options="chartOptions" />
              </div>
            </div>
          </div>
        </div>
      </div>

    </div>
  </div>
</template>

<style scoped>
.modal-overlay { position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(0, 0, 0, 0.7); display: flex; align-items: center; justify-content: center; backdrop-filter: blur(4px); }
.modal-content { background: #f4f6f8; padding: 24px; border-radius: 12px; width: 90%; max-width: 900px; max-height: 85vh; overflow-y: auto; position: relative; box-shadow: 0 10px 40px rgba(0,0,0,0.3); border: 2px solid #3388ff; }
.close-btn { position: absolute; top: 16px; right: 16px; background: none; border: none; font-size: 20px; cursor: pointer; color: #666; transition: color 0.2s; }
.close-btn:hover { color: #000; }
.modal-header h2 { margin: 0 0 16px 0; color: #2c3e50; font-size: 18px; text-transform: uppercase; letter-spacing: 1px;}

.compare-row { display: flex; align-items: center; justify-content: center; gap: 16px; background: #fff; padding: 16px; border-radius: 8px; margin-bottom: 24px; box-shadow: 0 2px 5px rgba(0,0,0,0.05); }
.compare-entity { flex: 1; text-align: center; font-size: 16px; font-weight: bold; color: #333; }
.compare-vs { background: #3388ff; color: white; width: 32px; height: 32px; display: flex; align-items: center; justify-content: center; border-radius: 50%; font-size: 12px; font-weight: bold; flex-shrink: 0; }

.autocomplete-wrapper { position: relative; width: 100%; max-width: 350px; margin: 0 auto; text-align: left; }
.compare-input { padding: 10px 16px; border-radius: 6px; border: 2px solid #ccc; font-size: 14px; width: 100%; font-weight: bold; color: #333; outline: none; transition: border-color 0.2s; box-sizing: border-box; }
.compare-input:focus { border-color: #3388ff; }
.autocomplete-list { position: absolute; top: 100%; left: 0; right: 0; background: white; border: 1px solid #ccc; border-radius: 6px; margin-top: 4px; max-height: 250px; overflow-y: auto; list-style: none; padding: 0; box-shadow: 0 4px 12px rgba(0,0,0,0.15); z-index: 10001; }
.autocomplete-list li { padding: 10px 16px; cursor: pointer; font-size: 13px; border-bottom: 1px solid #eee; transition: background 0.1s; }
.autocomplete-list li:last-child { border-bottom: none; }
.autocomplete-list li:hover { background: #f0f7ff; color: #3388ff; }
.no-results { color: #999; font-style: italic; cursor: default !important; }
.no-results:hover { background: white !important; color: #999 !important; }

.landscape-card { margin-bottom: 30px; background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.03); }
.landscape-card h3 { margin: 0 0 16px 0; font-size: 16px; color: #333; text-align: center; }
.chart-container { width: 100%; height: 300px; }
.no-data-state { text-align: center; padding: 60px 20px; color: #666; font-size: 15px; }
.pill-btn { padding: 6px 16px; border-radius: 20px; border: 1px solid #ccc; background: white; cursor: pointer; font-size: 13px; font-weight: 600; color: #666; }
.pill-btn.active { background: #3388ff; border-color: #3388ff; color: white; }
</style>