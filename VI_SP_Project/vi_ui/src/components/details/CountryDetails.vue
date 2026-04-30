<script setup lang="ts">
import { computed, ref, watch } from 'vue';
import { Bar, Line, Doughnut } from 'vue-chartjs';

const props = defineProps<{ title: string; data: any; allCountriesData: any; }>();

const activeTab = ref<'national' | 'landscape' | 'pipeline'>('national');
const showNotes = ref(false);

const groupedStats = computed(() => {
  if (!props.data?.statistics) return {};
  const groups: Record<string, { first?: any; all?: any; degrees?: any }> = {};
  for (const [key, value] of Object.entries(props.data.statistics)) {
    const levelPrefix = key.split('_')[0];
    if (!groups[levelPrefix]) groups[levelPrefix] = {};
    if (key.includes('First-year')) groups[levelPrefix].first = value;
    else if (key.includes('all-semesters')) groups[levelPrefix].all = value;
    else if (key.includes('Degrees-awarded')) groups[levelPrefix].degrees = value;
  }
  return groups;
});

const availableLevels = computed(() => Object.keys(groupedStats.value));
const selectedLevel = ref('');

watch(() => availableLevels.value, (levels) => {
  if (levels.length > 0 && !levels.includes(selectedLevel.value)) selectedLevel.value = levels[0];
}, { immediate: true });

const enrollmentChartData = computed(() => {
  const group = groupedStats.value[selectedLevel.value];
  if (!group) return null;
  const yearSet = new Set<string>();
  ['first', 'all'].forEach(type => {
    if (group[type as keyof typeof group]) Object.keys(group[type as keyof typeof group]).forEach(y => yearSet.add(y));
  });
  if (yearSet.size === 0) return null;
  const years = Array.from(yearSet).sort();

  const datasets: any[] = [];
  const hasFirst = !!group.first;
  const hasAll = !!group.all;

  if (hasAll) {
    const firstData: number[] = []; const remainingData: number[] = []; const allData: number[] = [];
    years.forEach(y => {
      const totalAll = group.all[y]?.total !== 'n.a.' ? Number(group.all[y]?.total || 0) : 0;
      const totalFirst = hasFirst && group.first[y]?.total !== 'n.a.' ? Number(group.first[y]?.total || 0) : 0;
      if (hasFirst) { firstData.push(totalFirst); remainingData.push(Math.max(0, totalAll - totalFirst)); }
      else { allData.push(totalAll); }
    });
    if (hasFirst) {
      datasets.push({ type: 'bar', label: '1st Year Students', backgroundColor: '#3388ff', stack: 'enrollment', data: firstData });
      datasets.push({ type: 'bar', label: 'Returning Students', backgroundColor: '#bbdefb', stack: 'enrollment', data: remainingData });
    } else {
      datasets.push({ type: 'bar', label: 'Total Enrolled', backgroundColor: '#3388ff', stack: 'enrollment', data: allData });
    }
  }
  return datasets.length > 0 ? { labels: years, datasets } : null;
});

const enrollmentChartOptions = { responsive: true, maintainAspectRatio: false, interaction: { mode: 'index' as const, intersect: false }, plugins: { legend: { position: 'top' as const } }, scales: { x: { stacked: true }, y: { stacked: true, beginAtZero: true } } };

const degreesChartData = computed(() => {
  const group = groupedStats.value[selectedLevel.value];
  if (!group || !group.degrees) return null;
  const years = Object.keys(group.degrees).sort();
  if (years.length === 0) return null;
  const degreesData = years.map(y => group.degrees[y]?.total !== 'n.a.' ? Number(group.degrees[y]?.total || 0) : 0);
  return { labels: years, datasets: [{ type: 'line', label: 'Degrees Awarded', borderColor: '#ff9800', backgroundColor: '#ff9800', borderWidth: 2, pointRadius: 4, data: degreesData }] };
});

const degreesChartOptions = { responsive: true, maintainAspectRatio: false, interaction: { mode: 'index' as const, intersect: false }, plugins: { legend: { position: 'top' as const } }, scales: { y: { beginAtZero: true } } };

const pipelineChartData = computed(() => {
  if (!props.data?.statistics) return null;
  const stats = props.data.statistics;
  const getStats = (prefix: string) => {
    const key = Object.keys(stats).find(k => k.startsWith(prefix + '_') && k.includes('all-semesters'));
    return key ? stats[key] : null;
  };
  const bscStats = getStats('BSc'); const mscStats = getStats('MSc'); const phdStats = getStats('PhD');
  if (!bscStats && !mscStats && !phdStats) return null;

  const yearSet = new Set<string>();
  [bscStats, mscStats, phdStats].forEach(s => { if (s) Object.keys(s).forEach(y => yearSet.add(y)); });
  const years = Array.from(yearSet).sort();
  const mapFemalePct = (s: any) => years.map(y => (!s || !s[y] || s[y]['female %'] === 'n.a.') ? null : Number(s[y]['female %']) * 100);

  return {
    labels: years,
    datasets: [
      { label: 'BSc Female %', borderColor: '#1565c0', backgroundColor: '#1565c0', data: mapFemalePct(bscStats), tension: 0.3, pointRadius: 4, borderWidth: 2 },
      { label: 'MSc Female %', borderColor: '#ff9800', backgroundColor: '#ff9800', data: mapFemalePct(mscStats), tension: 0.3, pointRadius: 4, borderWidth: 2 },
      { label: 'PhD Female %', borderColor: '#2e7d32', backgroundColor: '#2e7d32', data: mapFemalePct(phdStats), tension: 0.3, pointRadius: 4, borderWidth: 2 }
    ]
  };
});

const pipelineChartOptions = { responsive: true, maintainAspectRatio: false, interaction: { mode: 'index' as const, intersect: false }, plugins: { legend: { position: 'top' as const } }, scales: { y: { beginAtZero: true, title: { display: true, text: 'Percentage of Female Students', color: '#666' }, ticks: { callback: function(value: any) { return value + '%'; } } } } };

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
watch(() => availableLandscapeYears.value, (years) => { if (years.length > 0 && !years.includes(selectedLandscapeYear.value)) selectedLandscapeYear.value = years[0]; }, { immediate: true });

const landscapeInsights = computed(() => {
  if (!props.allCountriesData || !selectedLandscapeYear.value) return null;
  const countriesStats = [];
  const targetYear = selectedLandscapeYear.value;

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
      const popM = pop / 1000000;
      countriesStats.push({
        country: countryName, bsc: bscTotal, msc: mscTotal, phd: phdTotal,
        bscDensity: bscTotal / popM, mscDensity: mscTotal / popM, phdDensity: phdTotal / popM,
        total: totalStudents, density: totalStudents / popM
      });
    }
  }
  return { byDensity: [...countriesStats].sort((a, b) => b.density - a.density), byTotal: [...countriesStats].sort((a, b) => b.total - a.total) };
});

const isTarget = (c: string) => c === props.title;

const landscapeDonutChartData = computed(() => {
  const data = landscapeInsights.value?.byTotal || [];
  if (data.length === 0) return null;
  const palette = ['#90caf9', '#b39ddb', '#80cbc4', '#c5e1a5', '#ffe082', '#ffab91', '#bcaaa4', '#cfd8dc', '#b0bec5', '#f48fb1'];
  return {
    labels: data.map(d => d.country),
    datasets: [{
      data: data.map(d => d.total),
      backgroundColor: data.map((d, index) => isTarget(d.country) ? '#ff5722' : palette[index % palette.length]),
      borderColor: data.map(d => isTarget(d.country) ? '#e64a19' : '#ffffff'),
      borderWidth: data.map(d => isTarget(d.country) ? 2 : 1),
      offset: data.map(d => isTarget(d.country) ? 15 : 0), hoverOffset: 5
    }]
  };
});

const landscapeDonutOptions = { responsive: true, maintainAspectRatio: false, cutout: '65%', plugins: { legend: { display: false } } };

const landscapeDensityChartData = computed(() => {
  const data = landscapeInsights.value?.byDensity || [];
  return {
    labels: data.map(d => d.country),
    datasets: [
      { label: 'BSc', stack: 'D', backgroundColor: data.map(d => isTarget(d.country) ? '#1565c0' : '#90caf9'), data: data.map(d => d.bscDensity) },
      { label: 'MSc', stack: 'D', backgroundColor: data.map(d => isTarget(d.country) ? '#e65100' : '#ffcc80'), data: data.map(d => d.mscDensity) },
      { label: 'PhD', stack: 'D', backgroundColor: data.map(d => isTarget(d.country) ? '#2e7d32' : '#a5d6a7'), data: data.map(d => d.phdDensity) }
    ]
  };
});

const landscapeTotalChartData = computed(() => {
  const data = landscapeInsights.value?.byTotal || [];
  return {
    labels: data.map(d => d.country),
    datasets: [
      { label: 'BSc', stack: 'T', backgroundColor: data.map(d => isTarget(d.country) ? '#1565c0' : '#90caf9'), data: data.map(d => d.bsc) },
      { label: 'MSc', stack: 'T', backgroundColor: data.map(d => isTarget(d.country) ? '#e65100' : '#ffcc80'), data: data.map(d => d.msc) },
      { label: 'PhD', stack: 'T', backgroundColor: data.map(d => isTarget(d.country) ? '#2e7d32' : '#a5d6a7'), data: data.map(d => d.phd) }
    ]
  };
});

const landscapeOptions = { responsive: true, maintainAspectRatio: false, interaction: { mode: 'index' as const, intersect: false }, plugins: { legend: { display: true, position: 'top' as const } }, scales: { x: { stacked: true }, y: { stacked: true, beginAtZero: true } } };
</script>

<template>
  <div>
    <div class="tabs">
      <button :class="{ active: activeTab === 'national' }" @click="activeTab = 'national'">National Statistics</button>
      <button :class="{ active: activeTab === 'pipeline' }" @click="activeTab = 'pipeline'">Gender Parity</button>
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
      <p class="landscape-intro">Visualizing the proportion of female students across BSc, MSc, and PhD levels.</p>
      <div v-if="pipelineChartData" class="landscape-card">
        <h3>Gender Parity Trend</h3>
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

      <div class="landscape-card">
        <h3>European Student Distribution ({{ selectedLandscapeYear }})</h3>
        <div class="chart-container donut-chart-container">
          <Doughnut v-if="landscapeDonutChartData" :data="landscapeDonutChartData" :options="landscapeDonutOptions" />
        </div>
      </div>
      <hr style="margin: 30px 0;" />
      <div class="landscape-card">
        <h3>National Density ({{ selectedLandscapeYear }})</h3>
        <div class="chart-container landscape-chart"><Bar v-if="landscapeInsights?.byDensity.length" :data="landscapeDensityChartData" :options="landscapeOptions" /></div>
      </div>
      <div class="landscape-card">
        <h3>Absolute Scale ({{ selectedLandscapeYear }})</h3>
        <div class="chart-container landscape-chart"><Bar v-if="landscapeInsights?.byTotal.length" :data="landscapeTotalChartData" :options="landscapeOptions" /></div>
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