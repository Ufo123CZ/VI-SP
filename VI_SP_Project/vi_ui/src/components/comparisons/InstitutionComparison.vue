<script setup lang="ts">
import { computed } from 'vue';
import { Bar } from 'vue-chartjs';

const props = defineProps<{
  baseTitle: string;
  targetTitle: string;
  baseData: any;
  targetData: any;
}>();

// 1. Specific Options for Informatics Europe (Member) Data
const instMemberOptions = {
  responsive: true,
  maintainAspectRatio: false,
  plugins: { legend: { position: 'top' as const } },
  scales: {
    x: { title: { display: true, text: 'Degree Level', font: { weight: 'bold' } } },
    y: { beginAtZero: true, title: { display: true, text: 'Number of Students', font: { weight: 'bold' } } }
  }
};

// 2. Specific Options for ETER Historical Data
const instEterOptions = {
  responsive: true,
  maintainAspectRatio: false,
  plugins: { legend: { position: 'top' as const } },
  scales: {
    x: { title: { display: true, text: 'Academic Year', font: { weight: 'bold' } } },
    y: { beginAtZero: true, title: { display: true, text: 'Number of Students', font: { weight: 'bold' } } }
  }
};

const hasBaseMemberData = computed(() => !!props.baseData?.member);
const hasTargetMemberData = computed(() => !!props.targetData?.member);

const hasAnyMemberData = computed(() => {
  return hasBaseMemberData.value || hasTargetMemberData.value;
});

const instEnrollmentChart = computed(() => {
  if (!hasAnyMemberData.value) return null;

  const levels = ['Bachelor', 'Master', 'PhD'];

  const getTotals = (d: any) =>
      levels.map(
          l =>
              d?.data?.find(
                  (i: any) =>
                      i?.level === l &&
                      i?.category === 'Students all semesters'
              )?.stats_2023_2024?.total || 0
      );

  return {
    labels: levels,
    datasets: [
      {
        label: props.baseTitle,
        backgroundColor: '#3388ff',
        data: getTotals(props.baseData?.member)
      },
      {
        label: props.targetTitle,
        backgroundColor: '#ff9800',
        data: getTotals(props.targetData?.member)
      }
    ]
  };
});

const hasBaseEterData = computed(() => !!props.baseData?.eter);
const hasTargetEterData = computed(() => !!props.targetData?.eter);

const hasAnyEterData = computed(() => {
  return hasBaseEterData.value || hasTargetEterData.value;
});

const eterYears = computed(() => {
  const ySet = new Set<string>();

  if (props.baseData?.eter) {
    Object.keys(props.baseData.eter).forEach(y => ySet.add(y));
  }

  if (props.targetData?.eter) {
    Object.keys(props.targetData.eter).forEach(y => ySet.add(y));
  }

  return Array.from(ySet).sort();
});

const eterEnrollmentChart = computed(() => {
  if (!hasAnyEterData.value) return null;

  return {
    labels: eterYears.value,
    datasets: [
      {
        label: `${props.baseTitle} (BSc)`,
        backgroundColor: '#3388ff',
        data: eterYears.value.map(
            y => props.baseData?.eter?.[y]?.enrolled_bsc || 0
        )
      },
      {
        label: `${props.targetTitle} (BSc)`,
        backgroundColor: '#1565c0',
        data: eterYears.value.map(
            y => props.targetData?.eter?.[y]?.enrolled_bsc || 0
        )
      },
      {
        label: `${props.baseTitle} (MSc)`,
        backgroundColor: '#ff9800',
        data: eterYears.value.map(
            y => props.baseData?.eter?.[y]?.enrolled_msc || 0
        )
      },
      {
        label: `${props.targetTitle} (MSc)`,
        backgroundColor: '#e65100',
        data: eterYears.value.map(
            y => props.targetData?.eter?.[y]?.enrolled_msc || 0
        )
      }
    ]
  };
});
</script>

<template>
  <div>
    <div class="landscape-card">
      <h3>
        Current Enrollment (Informatics Europe)
      </h3>

      <div v-if="!hasAnyMemberData" class="empty-state">
        No Informatics Europe data available for these institutions.
      </div>

      <div v-else class="chart-container landscape-chart">
        <Bar :data="instEnrollmentChart!" :options="instMemberOptions"/>
      </div>
    </div>

    <div class="landscape-card">
      <h3>
        Enrollment (ETER)
      </h3>

      <div v-if="!hasAnyEterData" class="empty-state">
        No ETER data available for these institutions.
      </div>

      <div v-else class="chart-container landscape-chart">
        <Bar :data="eterEnrollmentChart!" :options="instEterOptions"/>
      </div>
    </div>
  </div>
</template>

<style scoped>
.landscape-card {
  margin-bottom: 30px;
  background: white;
  padding: 20px;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.03);
}

.landscape-card h3 {
  margin: 0 0 16px 0;
  font-size: 16px;
  color: #333;
  text-align: center;
}

.chart-container {
  width: 100%;
  height: 300px;
}

.empty-state {
  text-align: center;
  padding: 40px;
  color: #d32f2f;
  background: #ffebee;
  border-radius: 8px;
}
</style>