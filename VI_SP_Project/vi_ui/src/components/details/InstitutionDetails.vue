<script setup lang="ts">
import { computed, ref, watch } from 'vue';
import { Bar, Line } from 'vue-chartjs';

const props = defineProps<{
  data: { member?: any; eter?: any }
}>();

const hasMember = computed(() => !!props.data?.member?.data?.length);
const hasEter = computed(() => !!props.data?.eter && Object.keys(props.data.eter).length > 0);

const activeInstTab = ref<'member' | 'eter'>('member');

watch(() => props.data, () => {
  if (hasMember.value) activeInstTab.value = 'member';
  else if (hasEter.value) activeInstTab.value = 'eter';
}, { immediate: true, deep: true });

const memberEnrollmentChartData = computed(() => {
  if (!hasMember.value) return null;
  const levels = ['Bachelor', 'Master', 'PhD'];
  const totals = levels.map(l => props.data.member.data.find((i: any) => i?.level === l && i?.category === 'Students all semesters')?.stats_2023_2024?.total || 0);
  const females = levels.map(l => props.data.member.data.find((i: any) => i?.level === l && i?.category === 'Students all semesters')?.stats_2023_2024?.female || 0);

  if (totals.every(t => t === 0)) return null;

  return {
    labels: levels,
    datasets: [
      { label: 'Total Enrolled', backgroundColor: '#90caf9', data: totals },
      { label: 'Female Enrolled', backgroundColor: '#d81b60', data: females }
    ]
  };
});

const memberChartOptions = { responsive: true, maintainAspectRatio: false, plugins: { legend: { position: 'top' as const } }, scales: { y: { beginAtZero: true } } };

const partnerYears = computed(() => {
  if (!hasEter.value) return [];
  return Object.keys(props.data.eter).sort();
});

const partnerEnrollmentChartData = computed(() => {
  if (partnerYears.value.length === 0) return null;
  const labels = partnerYears.value;
  return {
    labels,
    datasets: [
      { label: 'BSc Enrolled', backgroundColor: '#1565c0', data: labels.map(y => props.data.eter[y]?.enrolled_bsc || 0) },
      { label: 'MSc Enrolled', backgroundColor: '#ff9800', data: labels.map(y => props.data.eter[y]?.enrolled_msc || 0) }
    ]
  };
});

const partnerGraduatesChartData = computed(() => {
  if (partnerYears.value.length === 0) return null;
  const labels = partnerYears.value;
  return {
    labels,
    datasets: [
      { label: 'BSc Graduates', borderColor: '#1565c0', backgroundColor: '#1565c0', tension: 0.3, pointRadius: 4, borderWidth: 2, data: labels.map(y => props.data.eter[y]?.graduates_bsc || 0) },
      { label: 'MSc Graduates', borderColor: '#ff9800', backgroundColor: '#ff9800', tension: 0.3, pointRadius: 4, borderWidth: 2, data: labels.map(y => props.data.eter[y]?.graduates_msc || 0) }
    ]
  };
});

const partnerLineOptions = { responsive: true, maintainAspectRatio: false, plugins: { legend: { position: 'top' as const } }, scales: { y: { beginAtZero: true } } };
</script>

<template>
  <div>
    <div v-if="hasMember && hasEter" class="tabs">
      <button :class="{ active: activeInstTab === 'member' }" @click="activeInstTab = 'member'">Informatics Europe Data</button>
      <button :class="{ active: activeInstTab === 'eter' }" @click="activeInstTab = 'eter'">ETER Historical Data</button>
    </div>

    <div v-if="activeInstTab === 'member' && hasMember" class="tab-pane">
      <p class="landscape-intro">Informatics enrollment profile based on the 2023-2024 academic year.</p>
      <div v-if="memberEnrollmentChartData" class="landscape-card">
        <h3>Student Enrollment (2023-2024)</h3>
        <div class="chart-container landscape-chart"><Bar :data="memberEnrollmentChartData" :options="memberChartOptions" /></div>
      </div>
      <div v-else class="no-data-state"><p>No enrollment breakdown available for this institution.</p></div>
    </div>

    <div v-if="activeInstTab === 'eter' && hasEter" class="tab-pane">
      <p class="landscape-intro">Historical informatics statistics via the European Tertiary Education Register (ETER).</p>
      <div v-if="partnerEnrollmentChartData" class="landscape-card">
        <h3>Enrollment Over Time</h3>
        <div class="chart-container landscape-chart"><Bar :data="partnerEnrollmentChartData" :options="memberChartOptions" /></div>
      </div>
      <div v-if="partnerGraduatesChartData" class="landscape-card">
        <h3>Graduates Over Time</h3>
        <div class="chart-container landscape-chart"><Line :data="partnerGraduatesChartData" :options="partnerLineOptions" /></div>
      </div>
      <div v-if="!partnerEnrollmentChartData && !partnerGraduatesChartData" class="no-data-state"><p>No historical data available.</p></div>
    </div>
  </div>
</template>

<style scoped>
.landscape-intro { font-size: 14px; color: #555; margin-top: 0; margin-bottom: 20px; }
.landscape-card { margin-bottom: 30px; }
.landscape-card h3 { margin: 0 0 16px 0; font-size: 16px; color: #333; }
.chart-container { width: 100%; margin-bottom: 20px; }
.landscape-chart { height: 250px; }
.no-data-state { padding: 40px; text-align: center; color: #666; font-size: 14px; background: #f8f9fa; border-radius: 8px;}
.tabs { display: flex; gap: 12px; border-bottom: 2px solid #ddd; margin-bottom: 20px; }
.tabs button { background: none; border: none; padding: 8px 16px; font-size: 15px; font-weight: 600; color: #777; cursor: pointer; position: relative; top: 2px; }
.tabs button.active { color: #3388ff; border-bottom: 2px solid #3388ff; }
.tabs button:hover:not(.active) { color: #333; }
.tab-pane { background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.03); }
</style>