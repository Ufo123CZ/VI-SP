<script setup lang="ts">
import { computed, ref, watch } from 'vue';
import { Bar, Line } from 'vue-chartjs';
import { Chart as ChartJS, Title, Tooltip, Legend, BarElement, LineElement, PointElement, CategoryScale, LinearScale } from 'chart.js';

ChartJS.register(Title, Tooltip, Legend, BarElement, LineElement, PointElement, CategoryScale, LinearScale);

const props = defineProps<{
  data: { member?: any; eter?: any }
}>();

const hasMember = computed(() => !!props.data?.member?.data?.length);

const hasEter = computed(() => {
  const eter = props.data?.eter;
  if (!eter) return false;

  return Object.entries(eter).some(([key, year]: [string, any]) => {
    if (key === 'footnotes') return false; // Ignore footnotes if they are in the dictionary
    return (
        year?.enrolled_bsc > 0 ||
        year?.enrolled_msc > 0 ||
        year?.graduates_bsc > 0 ||
        year?.graduates_msc > 0
    );
  });
});

const activeInstTab = ref<'member' | 'eter'>('member');
const showNotes = ref(false);

watch(() => props.data, () => {
  if (hasMember.value) activeInstTab.value = 'member';
  else if (hasEter.value) activeInstTab.value = 'eter';
}, { immediate: true, deep: true });

// Collect any footnotes passed down through either the member or eter dictionaries
const institutionFootnotes = computed(() => {
  let notes: any[] = [];
  if (props.data?.member?.footnotes) notes = notes.concat(props.data.member.footnotes);
  if (props.data?.eter?.footnotes) notes = notes.concat(props.data.eter.footnotes);
  return notes;
});

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

const memberChartOptions = {
  responsive: true, maintainAspectRatio: false, plugins: { legend: { position: 'top' as const } },
  scales: {
    x: { title: { display: true, text: 'Degree Level', font: { weight: 'bold' } } },
    y: { beginAtZero: true, title: { display: true, text: 'Number of Students', font: { weight: 'bold' } } }
  }
};

const partnerYears = computed(() => {
  if (!hasEter.value) return [];
  // Filter out footnotes so they don't break the chart's X-axis
  return Object.keys(props.data.eter).filter(k => k !== 'footnotes').sort();
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

const partnerTimeOptions = {
  responsive: true, maintainAspectRatio: false, plugins: { legend: { position: 'top' as const } },
  scales: {
    x: { title: { display: true, text: 'Academic Year', font: { weight: 'bold' } } },
    y: { beginAtZero: true, title: { display: true, text: 'Number of Students', font: { weight: 'bold' } } }
  }
};
</script>

<template>
  <div>
    <div class="tabs">
      <button :class="{ active: activeInstTab === 'member' }" @click="activeInstTab = 'member'">Informatics Europe Data</button>
      <button :class="{ active: activeInstTab === 'eter' }" @click="activeInstTab = 'eter'">ETER Data</button>
    </div>

    <div v-if="activeInstTab === 'member'" class="tab-pane">
      <div v-if="hasMember">
        <div v-if="memberEnrollmentChartData" class="landscape-card">
          <h3>Student Enrollment (2023-2024)</h3>
          <p class="landscape-intro" style="margin-top: -10px;">Visualizing the current number of enrolled students by degree level and gender.</p>
          <div class="chart-container landscape-chart">
            <Bar :data="memberEnrollmentChartData" :options="memberChartOptions" />
          </div>
        </div>

        <div class="footnotes-section" v-if="institutionFootnotes.length > 0">
          <hr />
          <div class="footnotes-header" @click="showNotes = !showNotes">
            <h3>Methodology & Notes</h3>
            <button class="toggle-btn">{{ showNotes ? 'Hide Notes' : 'Show Notes' }}</button>
          </div>
          <div v-show="showNotes" class="footnotes-content">
            <div v-for="(note, index) in institutionFootnotes" :key="index" class="footnote-card">
              <div class="footnote-title">{{ note.dataset?.replace('.xlsx', '') || 'Dataset Note' }}</div>
              <div class="footnote-text">{{ note.note }}</div>
            </div>
          </div>
        </div>
      </div>
      <div v-else class="no-data-state"><p>⚠️ No <b>Informatics Europe</b> data is available for this institution.</p></div>
    </div>

    <div v-if="activeInstTab === 'eter'" class="tab-pane">
      <div v-if="hasEter">
        <div v-if="partnerEnrollmentChartData" class="landscape-card">
          <h3>Enrollment Over Time</h3>
          <p class="landscape-intro" style="margin-top: -10px;">Visualizing the historical trend of enrolled students across academic years.</p>
          <div class="chart-container landscape-chart">
            <Bar :data="partnerEnrollmentChartData" :options="partnerTimeOptions" />
          </div>
        </div>
        <div v-if="partnerGraduatesChartData" class="landscape-card">
          <h3>Graduates Over Time</h3>
          <p class="landscape-intro" style="margin-top: -10px;">Visualizing the historical trend of successfully awarded degrees across academic years.</p>
          <div class="chart-container landscape-chart">
            <Line :data="partnerGraduatesChartData" :options="partnerTimeOptions" />
          </div>
        </div>

        <div class="footnotes-section" v-if="institutionFootnotes.length > 0">
          <hr />
          <div class="footnotes-header" @click="showNotes = !showNotes">
            <h3>Methodology & Notes</h3>
            <button class="toggle-btn">{{ showNotes ? 'Hide Notes' : 'Show Notes' }}</button>
          </div>
          <div v-show="showNotes" class="footnotes-content">
            <div v-for="(note, index) in institutionFootnotes" :key="index" class="footnote-card">
              <div class="footnote-title">{{ note.dataset?.replace('.xlsx', '') || 'Dataset Note' }}</div>
              <div class="footnote-text">{{ note.note }}</div>
            </div>
          </div>
        </div>
      </div>
      <div v-else class="no-data-state"><p>⚠️ No <b>ETER historical</b> data is available for this institution.</p></div>
    </div>
  </div>
</template>

<style scoped>
.landscape-intro { font-size: 14px; color: #555; margin-top: 0; margin-bottom: 20px; }
.landscape-card { margin-bottom: 30px; }
.landscape-card h3 { margin: 0 0 16px 0; font-size: 16px; color: #333; }
.chart-container { width: 100%; margin-bottom: 20px; }
.landscape-chart { height: 250px; }
.tabs { display: flex; gap: 12px; border-bottom: 2px solid #ddd; margin-bottom: 20px; }
.tabs button { background: none; border: none; padding: 8px 16px; font-size: 15px; font-weight: 600; color: #777; cursor: pointer; position: relative; top: 2px; }
.tabs button.active { color: #3388ff; border-bottom: 2px solid #3388ff; }
.tabs button:hover:not(.active) { color: #333; }
.tab-pane { background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.03); }
.no-data-state { padding: 40px; text-align: center; color: #d32f2f; font-size: 14px; background: #ffebee; border-radius: 8px; border: 1px dashed #ef9a9a;}

/* Footnote Styles */
hr { border: 0; height: 1px; background: #ddd; margin: 20px 0; }
.footnotes-header { display: flex; justify-content: space-between; align-items: center; cursor: pointer; padding: 8px 0; }
.footnotes-header h3 { margin: 0; font-size: 16px; color: #333; }
.toggle-btn { background: white; border: 1px solid #ccc; padding: 4px 10px; border-radius: 4px; font-size: 12px; cursor: pointer; }
.footnotes-content { margin-top: 12px; }
.footnote-card { background: #f8f9fa; border-left: 4px solid #3388ff; padding: 12px; margin-bottom: 10px; border-radius: 0 6px 6px 0; }
.footnote-title { font-weight: 600; font-size: 12px; color: #3388ff; margin-bottom: 4px; }
.footnote-text { font-size: 12px; color: #555; line-height: 1.4; white-space: pre-wrap; }
</style>