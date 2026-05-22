<script setup lang="ts">
import { computed, ref, watch } from 'vue';
import { Bar, Line, Doughnut } from 'vue-chartjs';

const props = defineProps<{
  title: string;
  data: any;
  allCountriesData: any;
  compareTitle?: string;
  compareData?: any;
}>();

const activeTab = ref<'national' | 'landscape' | 'pipeline'>('national');
const showNotes = ref(false);

const parseGroupedStats = (statsObj: any) => {
  if (!statsObj) return {};
  const groups: Record<string, { first?: any; all?: any; degrees?: any }> = {};
  for (const [key, value] of Object.entries(statsObj)) {
    const levelPrefix = key.split('_')[0];
    if (!groups[levelPrefix]) groups[levelPrefix] = {};
    if (key.includes('First-year')) groups[levelPrefix].first = value;
    else if (key.includes('all-semesters')) groups[levelPrefix].all = value;
    else if (key.includes('Degrees-awarded')) groups[levelPrefix].degrees = value;
  }
  return groups;
};

const groupedStats = computed(() => parseGroupedStats(props.data?.statistics));
const compareGroupedStats = computed(() => parseGroupedStats(props.compareData?.statistics));

const availableLevels = computed(() => Object.keys(groupedStats.value));
const selectedLevel = ref('');

watch(() => availableLevels.value, (levels) => {
  if (levels.length > 0 && !levels.includes(selectedLevel.value)) selectedLevel.value = levels[0];
}, { immediate: true });

// Merge years dynamically for the comparison chart
const getMergedYears = (groupA: any, groupB: any, property: 'all' | 'degrees') => {
  const yearSet = new Set<string>();
  if (groupA?.[property]) Object.keys(groupA[property]).forEach(y => yearSet.add(y));
  if (groupB?.[property]) Object.keys(groupB[property]).forEach(y => yearSet.add(y));
  return Array.from(yearSet).sort();
};

// ==========================================
// 1. NATIONAL STATISTICS CHARTS
// ==========================================
const enrollmentChartData = computed(() => {
  const group = groupedStats.value[selectedLevel.value];
  const compGroup = compareGroupedStats.value[selectedLevel.value];
  if (!group && !compGroup) return null;

  const years = getMergedYears(group, compGroup, 'all');
  if (years.length === 0) return null;

  const datasets: any[] = [];

  // --- RESTORED: BASE COUNTRY STACKING LOGIC ---
  const baseHasFirst = !!group?.first;
  if (group?.all) {
    const firstData: number[] = [];
    const remainingData: number[] = [];
    const allData: number[] = [];

    years.forEach(y => {
      const totalAll = group.all[y]?.total !== 'n.a.' ? Number(group.all[y]?.total || 0) : 0;
      const totalFirst = baseHasFirst && group.first[y]?.total !== 'n.a.' ? Number(group.first[y]?.total || 0) : 0;
      if (baseHasFirst) {
        firstData.push(totalFirst);
        remainingData.push(Math.max(0, totalAll - totalFirst));
      } else {
        allData.push(totalAll);
      }
    });

    if (baseHasFirst) {
      datasets.push({ type: 'bar', label: `${props.title} (1st Year)`, backgroundColor: '#3388ff', stack: 'base', data: firstData });
      datasets.push({ type: 'bar', label: `${props.title} (Returning)`, backgroundColor: '#bbdefb', stack: 'base', data: remainingData });
    } else {
      datasets.push({ type: 'bar', label: `${props.title} (Total Enrolled)`, backgroundColor: '#3388ff', stack: 'base', data: allData });
    }
  }

  // --- RESTORED: COMPARE COUNTRY STACKING LOGIC ---
  if (props.compareTitle && compGroup?.all) {
    const compHasFirst = !!compGroup?.first;
    const compFirstData: number[] = [];
    const compRemainingData: number[] = [];
    const compAllData: number[] = [];

    years.forEach(y => {
      const totalAll = compGroup.all[y]?.total !== 'n.a.' ? Number(compGroup.all[y]?.total || 0) : 0;
      const totalFirst = compHasFirst && compGroup.first[y]?.total !== 'n.a.' ? Number(compGroup.first[y]?.total || 0) : 0;
      if (compHasFirst) {
        compFirstData.push(totalFirst);
        compRemainingData.push(Math.max(0, totalAll - totalFirst));
      } else {
        compAllData.push(totalAll);
      }
    });

    if (compHasFirst) {
      datasets.push({ type: 'bar', label: `${props.compareTitle} (1st Year)`, backgroundColor: '#ff9800', stack: 'compare', data: compFirstData });
      datasets.push({ type: 'bar', label: `${props.compareTitle} (Returning)`, backgroundColor: '#ffcc80', stack: 'compare', data: compRemainingData });
    } else {
      datasets.push({ type: 'bar', label: `${props.compareTitle} (Total Enrolled)`, backgroundColor: '#ff9800', stack: 'compare', data: compAllData });
    }
  }

  return { labels: years, datasets };
});

const enrollmentChartOptions = { responsive: true, maintainAspectRatio: false, plugins: { legend: { position: 'top' as const } }, scales: { x: { stacked: true }, y: { stacked: true, beginAtZero: true } } };

const degreesChartData = computed(() => {
  const group = groupedStats.value[selectedLevel.value];
  const compGroup = compareGroupedStats.value[selectedLevel.value];
  if (!group && !compGroup) return null;

  const years = getMergedYears(group, compGroup, 'degrees');
  if (years.length === 0) return null;

  const datasets: any[] = [];
  if (group?.degrees) {
    datasets.push({ type: 'line', label: `${props.title}`, borderColor: '#3388ff', backgroundColor: '#3388ff', borderWidth: 2, pointRadius: 4, data: years.map(y => group.degrees[y]?.total !== 'n.a.' ? Number(group.degrees[y]?.total || 0) : 0) });
  }
  if (props.compareTitle && compGroup?.degrees) {
    datasets.push({ type: 'line', label: `${props.compareTitle}`, borderColor: '#ff9800', backgroundColor: '#ff9800', borderWidth: 2, borderDash: [5, 5], pointRadius: 4, data: years.map(y => compGroup.degrees[y]?.total !== 'n.a.' ? Number(compGroup.degrees[y]?.total || 0) : 0) });
  }
  return { labels: years, datasets };
});

const degreesChartOptions = { responsive: true, maintainAspectRatio: false, interaction: { mode: 'index' as const, intersect: false }, plugins: { legend: { position: 'top' as const } }, scales: { y: { beginAtZero: true } } };

// ==========================================
// 2. PIPELINE / GENDER CHARTS
// ==========================================
const pipelineChartData = computed(() => {
  const buildFemaleArr = (statsObj: any, prefix: string, targetYears: string[]) => {
    const key = Object.keys(statsObj || {}).find(k => k.startsWith(prefix + '_') && k.includes('all-semesters'));
    const s = key ? statsObj[key] : null;
    return targetYears.map(y => (!s || !s[y] || s[y]['female %'] === 'n.a.') ? null : Number(s[y]['female %']) * 100);
  };

  const yearSet = new Set<string>();
  [props.data?.statistics, props.compareData?.statistics].forEach(stats => {
    if (stats) Object.values(stats).forEach(ds => Object.keys(ds as any).forEach(y => yearSet.add(y)));
  });
  const years = Array.from(yearSet).sort();

  const datasets = [
    { label: `${props.title} (BSc)`, borderColor: '#1565c0', backgroundColor: '#1565c0', data: buildFemaleArr(props.data?.statistics, 'BSc', years), tension: 0.3 },
    { label: `${props.title} (MSc)`, borderColor: '#ff9800', backgroundColor: '#ff9800', data: buildFemaleArr(props.data?.statistics, 'MSc', years), tension: 0.3 }
  ];

  if (props.compareTitle && props.compareData?.statistics) {
    datasets.push(
        { label: `${props.compareTitle} (BSc)`, borderColor: '#1565c0', backgroundColor: '#1565c0', borderDash: [5,5], data: buildFemaleArr(props.compareData.statistics, 'BSc', years), tension: 0.3 },
        { label: `${props.compareTitle} (MSc)`, borderColor: '#ff9800', backgroundColor: '#ff9800', borderDash: [5,5], data: buildFemaleArr(props.compareData.statistics, 'MSc', years), tension: 0.3 }
    );
  }
  return { labels: years, datasets };
});

const pipelineChartOptions = {
  responsive: true, maintainAspectRatio: false, plugins: { legend: { position: 'top' as const } },
  scales: { y: { beginAtZero: true, ticks: { callback: function(value: any) { return value + '%'; } } } }
};

// ==========================================
// 3. LANDSCAPE (DONUT AND DENSITY) CHARTS
// ==========================================
const availableLandscapeYears = computed(() => {
  if (!props.allCountriesData) return [];
  const years = new Set<string>();
  for (const details of Object.values(props.allCountriesData)) {
    const stats = (details as any).statistics;
    if (!stats) continue;
    for (const dataset of Object.values(stats)) Object.keys(dataset as any).forEach(y => years.add(y));
  }
  return Array.from(years).sort().reverse();
});

const selectedLandscapeYear = ref('');
watch(() => availableLandscapeYears.value, (years) => {
  if (years.length > 0 && !years.includes(selectedLandscapeYear.value)) selectedLandscapeYear.value = years[0];
}, { immediate: true });

const landscapeInsights = computed(() => {
  if (!props.allCountriesData || !selectedLandscapeYear.value) return null;
  const countriesStats = [];
  const targetYear = selectedLandscapeYear.value;

  let baseCountryHasData = false;

  for (const [countryName, details] of Object.entries(props.allCountriesData)) {
    const stats = (details as any).statistics; const pop = (details as any).population;
    if (!stats || !pop) continue;

    const getTotalForYear = (prefix: string) => {
      const key = Object.keys(stats).find(k => k.startsWith(prefix + '_') && k.includes('all-semesters'));
      if (!key || !stats[key] || !stats[key][targetYear]) return 0;
      const val = stats[key][targetYear].total; return val === 'n.a.' ? 0 : Number(val);
    };

    const bscTotal = getTotalForYear('BSc'); const mscTotal = getTotalForYear('MSc'); const phdTotal = getTotalForYear('PhD');
    const totalStudents = bscTotal + mscTotal + phdTotal;

    if (totalStudents > 0) {

      if (countryName === props.title) baseCountryHasData = true;

      const popM = pop / 1000000;
      countriesStats.push({
        country: countryName, bsc: bscTotal, msc: mscTotal, phd: phdTotal,
        bscDensity: bscTotal / popM, mscDensity: mscTotal / popM, phdDensity: phdTotal / popM,
        total: totalStudents, density: totalStudents / popM
      });
    }
  }

  if (!baseCountryHasData) return null;

  return { byDensity: [...countriesStats].sort((a, b) => b.density - a.density), byTotal: [...countriesStats].sort((a, b) => b.total - a.total) };
});

const isTarget = (c: string) => c === props.title;
const isCompareTarget = (c: string) => c === props.compareTitle;

const landscapeDonutChartData = computed(() => {
  const data = landscapeInsights.value?.byTotal || [];
  if (data.length === 0) return null;
  const palette = ['#90caf9', '#b39ddb', '#80cbc4', '#c5e1a5', '#ffe082', '#ffab91', '#bcaaa4', '#cfd8dc', '#b0bec5', '#f48fb1'];
  return {
    labels: data.map(d => d.country),
    datasets: [{
      data: data.map(d => d.total),
      backgroundColor: data.map((d, index) => isTarget(d.country) ? '#ff5722' : (isCompareTarget(d.country) ? '#d50000' : palette[index % palette.length])),
      borderColor: data.map(d => isTarget(d.country) || isCompareTarget(d.country) ? '#ffffff' : '#ffffff'),
      borderWidth: data.map(d => isTarget(d.country) || isCompareTarget(d.country) ? 2 : 1),
      offset: data.map(d => isTarget(d.country) || isCompareTarget(d.country) ? 15 : 0), hoverOffset: 5
    }]
  };
});

const landscapeDonutOptions = { responsive: true, maintainAspectRatio: false, cutout: '65%', plugins: { legend: { display: false } } };

const landscapeDensityChartData = computed(() => {
  const data = landscapeInsights.value?.byDensity || [];
  return {
    labels: data.map(d => d.country),
    datasets: [
      { label: 'BSc', stack: 'D', backgroundColor: data.map(d => isTarget(d.country) ? '#1565c0' : (isCompareTarget(d.country) ? '#880e4f' : '#90caf9')), data: data.map(d => d.bscDensity) },
      { label: 'MSc', stack: 'D', backgroundColor: data.map(d => isTarget(d.country) ? '#e65100' : (isCompareTarget(d.country) ? '#bf360c' : '#ffcc80')), data: data.map(d => d.mscDensity) },
      { label: 'PhD', stack: 'D', backgroundColor: data.map(d => isTarget(d.country) ? '#2e7d32' : (isCompareTarget(d.country) ? '#1b5e20' : '#a5d6a7')), data: data.map(d => d.phdDensity) }
    ]
  };
});

const landscapeTotalChartData = computed(() => {
  const data = landscapeInsights.value?.byTotal || [];
  return {
    labels: data.map(d => d.country),
    datasets: [
      { label: 'BSc', stack: 'T', backgroundColor: data.map(d => isTarget(d.country) ? '#1565c0' : (isCompareTarget(d.country) ? '#880e4f' : '#90caf9')), data: data.map(d => d.bsc) },
      { label: 'MSc', stack: 'T', backgroundColor: data.map(d => isTarget(d.country) ? '#e65100' : (isCompareTarget(d.country) ? '#bf360c' : '#ffcc80')), data: data.map(d => d.msc) },
      { label: 'PhD', stack: 'T', backgroundColor: data.map(d => isTarget(d.country) ? '#2e7d32' : (isCompareTarget(d.country) ? '#1b5e20' : '#a5d6a7')), data: data.map(d => d.phd) }
    ]
  };
});

const landscapeOptions = computed(() => ({
  responsive: true,
  maintainAspectRatio: false,
  interaction: { mode: 'index' as const, intersect: false },
  plugins: { legend: { display: true, position: 'top' as const } },
  scales: {
    x: {
      stacked: true,
      ticks: {
        color: (context: any) => {
          const idx = context.index !== undefined ? context.index : context.tick?.value;
          const label = context.chart?.data?.labels?.[idx];
          return label === props.title || label === props.compareTitle ? '#000' : '#666';
        },
        font: (context: any) => {
          const idx = context.index !== undefined ? context.index : context.tick?.value;
          const label = context.chart?.data?.labels?.[idx];
          return { weight: label === props.title || label === props.compareTitle ? 'bold' : 'normal' };
        }
      }
    },
    y: { stacked: true, beginAtZero: true }
  }
}));
</script>

<template>
  <div>
    <div class="tabs">
      <button :class="{ active: activeTab === 'national' }" @click="activeTab = 'national'">National Statistics</button>
      <button :class="{ active: activeTab === 'pipeline' }" @click="activeTab = 'pipeline'">Female Representation</button>
      <button :class="{ active: activeTab === 'landscape' }" @click="activeTab = 'landscape'">European Context</button>
    </div>

    <div v-if="activeTab === 'national'" class="tab-pane">
      <div v-if="availableLevels.length > 0" class="dataset-selector">
        <label><strong>Select Degree Level:</strong></label>
        <div class="pills-container">
          <button v-for="level in availableLevels" :key="level" @click="selectedLevel = level" class="pill-btn" :class="{ 'active': selectedLevel === level }">{{ level }}</button>
        </div>
      </div>
      <div v-if="enrollmentChartData" class="landscape-card">
        <h3>Enrollment Trends</h3>
        <div class="chart-container landscape-chart"><Bar :data="enrollmentChartData" :options="enrollmentChartOptions" /></div>
      </div>
      <div v-if="degreesChartData" class="landscape-card">
        <h3>Degrees Awarded</h3>
        <div class="chart-container landscape-chart"><Line :data="degreesChartData" :options="degreesChartOptions" /></div>
      </div>
      <div class="footnotes-section" v-if="data?.footnotes?.length > 0">
        <hr />
        <div class="footnotes-header" @click="showNotes = !showNotes">
          <h3>Methodology & Notes</h3>
          <button class="toggle-btn">{{ showNotes ? 'Hide Notes' : 'Show Notes' }}</button>
        </div>
        <div v-show="showNotes" class="footnotes-content">
          <div v-for="(note, index) in data.footnotes" :key="index" class="footnote-card">
            <div class="footnote-title">{{ note.dataset.replace('.xlsx', '') }}</div>
            <div class="footnote-text">{{ note.note }}</div>
          </div>
        </div>
      </div>
    </div>

    <div v-if="activeTab === 'pipeline'" class="tab-pane">
      <p class="landscape-intro">Visualizing the proportion of female students across BSc and MSc levels.</p>
      <div v-if="pipelineChartData" class="landscape-card">
        <h3>Trend in Female Representation</h3>
        <div class="chart-container main-chart"><Line :data="pipelineChartData" :options="pipelineChartOptions" /></div>
      </div>
    </div>

    <div v-if="activeTab === 'landscape'" class="tab-pane">
      <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 20px;">
        <p class="landscape-intro" style="margin-bottom: 0; max-width: 65%;">Comparing the national academic pipeline across Europe based on the selected academic year.</p>
        <div v-if="availableLandscapeYears.length > 0" style="text-align: right;">
          <label style="display: block; font-size: 12px; color: #666; margin-bottom: 4px;"><strong>Academic Year:</strong></label>
          <select v-model="selectedLandscapeYear" class="custom-select" style="min-width: 120px;">
            <option v-for="year in availableLandscapeYears" :key="year" :value="year">{{ year }}</option>
          </select>
        </div>
      </div>

      <div v-if="!landscapeInsights" class="no-data-state">
        <p>No European Context data is available for <b>{{ title }}</b> in the <b>{{ selectedLandscapeYear }}</b> academic year.</p>
      </div>

      <div v-else>
        <div class="landscape-card">
          <h3>European Student Distribution ({{ selectedLandscapeYear }})</h3>
          <div class="chart-container donut-chart-container">
            <Doughnut :data="landscapeDonutChartData" :options="landscapeDonutOptions" />
          </div>
        </div>

        <hr style="margin: 30px 0;" />

        <div class="landscape-card">
          <h3>National Density ({{ selectedLandscapeYear }})</h3>
          <div class="chart-container landscape-chart">
            <Bar :data="landscapeDensityChartData" :options="landscapeOptions" />
          </div>
        </div>

        <div class="landscape-card">
          <h3>Absolute Scale ({{ selectedLandscapeYear }})</h3>
          <div class="chart-container landscape-chart">
            <Bar :data="landscapeTotalChartData" :options="landscapeOptions" />
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.landscape-intro { font-size: 14px; color: #555; margin-top: 0; margin-bottom: 20px; }
hr { border: 0; height: 1px; background: #ddd; margin: 20px 0; }
.tabs { display: flex; gap: 12px; border-bottom: 2px solid #ddd; margin-top: 16px; margin-bottom: 20px; }
.tabs button { background: none; border: none; padding: 8px 16px; font-size: 15px; font-weight: 600; color: #777; cursor: pointer; position: relative; top: 2px; }
.tabs button.active { color: #3388ff; border-bottom: 2px solid #3388ff; }
.tabs button:hover:not(.active) { color: #333; }
.tab-pane { background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.03); }
.dataset-selector { margin-bottom: 20px; }
.dataset-selector label { display: block; margin-bottom: 8px; font-size: 14px; }
.custom-select { padding: 6px 12px; border-radius: 6px; border: 1px solid #ccc; font-size: 13px; background-color: #f8f9fa; cursor: pointer; }
.pills-container { display: flex; gap: 8px; flex-wrap: wrap; }
.pill-btn { padding: 6px 16px; border-radius: 20px; border: 1px solid #ccc; background: white; cursor: pointer; font-size: 13px; font-weight: 600; color: #666; transition: all 0.2s; }
.pill-btn:hover { background: #f5f5f5; }
.pill-btn.active { background: #3388ff; border-color: #3388ff; color: white; }
.chart-container { width: 100%; margin-bottom: 20px; }
.main-chart { height: 320px; }
.landscape-chart { height: 250px; }
.donut-chart-container { height: 280px; position: relative; display: flex; justify-content: center; }
.landscape-card { margin-bottom: 30px; }
.landscape-card h3 { margin: 0 0 16px 0; font-size: 16px; color: #333; }
.footnotes-header { display: flex; justify-content: space-between; align-items: center; cursor: pointer; padding: 8px 0; }
.footnotes-header h3 { margin: 0; font-size: 16px; color: #333; }
.toggle-btn { background: white; border: 1px solid #ccc; padding: 4px 10px; border-radius: 4px; font-size: 12px; cursor: pointer; }
.footnotes-content { margin-top: 12px; }
.footnote-card { background: #f8f9fa; border-left: 4px solid #3388ff; padding: 12px; margin-bottom: 10px; border-radius: 0 6px 6px 0; }
.footnote-title { font-weight: 600; font-size: 12px; color: #3388ff; margin-bottom: 4px; }
.footnote-text { font-size: 12px; color: #555; line-height: 1.4; white-space: pre-wrap; }
</style>