<script setup lang="ts">
import { computed, ref, watch } from 'vue';
import { Bar, Line } from 'vue-chartjs';

const props = defineProps<{
  baseTitle: string;
  targetTitle: string;
  baseData: any;
  targetData: any;
}>();

const chartOptions = {
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: {
      position: 'top' as const
    }
  }
};

const pipelineChartOptions = {
  responsive: true,
  maintainAspectRatio: false,

  plugins: {
    legend: {
      position: 'top' as const
    }
  },

  scales: {
    y: {
      beginAtZero: true,

      ticks: {
        callback: function (value: any) {
          return value + '%';
        }
      }
    }
  }
};

const parseGroupedStats = (statsObj: any) => {
  if (!statsObj) return {};

  const groups: Record<
      string,
      {
        all?: any;
        degrees?: any;
      }
  > = {};

  for (const [key, value] of Object.entries(statsObj)) {
    const levelPrefix = key.split('_')[0];

    if (!groups[levelPrefix]) {
      groups[levelPrefix] = {};
    }

    if (key.includes('all-semesters')) {
      groups[levelPrefix].all = value;
    } else if (key.includes('Degrees-awarded')) {
      groups[levelPrefix].degrees = value;
    }
  }

  return groups;
};

const baseCountryStats = computed(() =>
    parseGroupedStats(props.baseData?.statistics)
);

const targetCountryStats = computed(() =>
    parseGroupedStats(props.targetData?.statistics)
);

const countryLevels = computed(() =>
    Object.keys(baseCountryStats.value)
);

const selectedCountryLevel = ref('');

watch(
    () => countryLevels.value,
    l => {
      if (l.length) {
        selectedCountryLevel.value = l[0];
      }
    },
    { immediate: true }
);

const countryEnrollmentChart = computed(() => {
  const g1 =
      baseCountryStats.value[selectedCountryLevel.value];

  const g2 =
      targetCountryStats.value[selectedCountryLevel.value];

  if (!g1 && !g2) return null;

  const ySet = new Set<string>();

  if (g1?.all) {
    Object.keys(g1.all).forEach(y => ySet.add(y));
  }

  if (g2?.all) {
    Object.keys(g2.all).forEach(y => ySet.add(y));
  }

  const years = Array.from(ySet).sort();

  return {
    labels: years,

    datasets: [
      {
        label: props.baseTitle,
        backgroundColor: '#3388ff',

        data: years.map(
            y => Number(g1?.all?.[y]?.total || 0) || 0
        )
      },

      {
        label: props.targetTitle,
        backgroundColor: '#ff9800',

        data: years.map(
            y => Number(g2?.all?.[y]?.total || 0) || 0
        )
      }
    ]
  };
});

const countryDegreesChart = computed(() => {
  const g1 =
      baseCountryStats.value[selectedCountryLevel.value];

  const g2 =
      targetCountryStats.value[selectedCountryLevel.value];

  if (!g1 && !g2) return null;

  const ySet = new Set<string>();

  if (g1?.degrees) {
    Object.keys(g1.degrees).forEach(y => ySet.add(y));
  }

  if (g2?.degrees) {
    Object.keys(g2.degrees).forEach(y => ySet.add(y));
  }

  const years = Array.from(ySet).sort();

  return {
    labels: years,

    datasets: [
      {
        type: 'line',

        label: props.baseTitle,

        borderColor: '#3388ff',
        backgroundColor: '#3388ff',

        borderWidth: 2,
        pointRadius: 4,

        data: years.map(
            y => Number(g1?.degrees?.[y]?.total || 0) || 0
        )
      },

      {
        type: 'line',

        label: props.targetTitle,

        borderColor: '#ff9800',
        backgroundColor: '#ff9800',

        borderWidth: 2,
        borderDash: [5, 5],

        pointRadius: 4,

        data: years.map(
            y => Number(g2?.degrees?.[y]?.total || 0) || 0
        )
      }
    ]
  };
});

const countryPipelineChart = computed(() => {
  const buildFemaleArr = (
      statsObj: any,
      prefix: string,
      targetYears: string[]
  ) => {
    const key = Object.keys(statsObj || {}).find(
        k =>
            k.startsWith(prefix + '_') &&
            k.includes('all-semesters')
    );

    const s = key ? statsObj[key] : null;

    return targetYears.map(y =>
        !s ||
        !s[y] ||
        s[y]['female %'] === 'n.a.'
            ? null
            : Number(s[y]['female %']) * 100
    );
  };

  const yearSet = new Set<string>();

  [props.baseData?.statistics, props.targetData?.statistics]
      .forEach(stats => {
        if (stats) {
          Object.values(stats).forEach(ds => {
            Object.keys(ds as any).forEach(y =>
                yearSet.add(y)
            );
          });
        }
      });

  const years = Array.from(yearSet).sort();

  return {
    labels: years,

    datasets: [
      {
        label: `${props.baseTitle} (BSc % Female)`,

        borderColor: '#1565c0',
        backgroundColor: '#1565c0',

        data: buildFemaleArr(
            props.baseData?.statistics,
            'BSc',
            years
        ),

        tension: 0.3
      },

      {
        label: `${props.baseTitle} (MSc % Female)`,

        borderColor: '#e65100',
        backgroundColor: '#e65100',

        data: buildFemaleArr(
            props.baseData?.statistics,
            'MSc',
            years
        ),

        tension: 0.3
      },

      {
        label: `${props.targetTitle} (BSc % Female)`,

        borderColor: '#1565c0',
        backgroundColor: '#1565c0',

        borderDash: [5, 5],

        data: buildFemaleArr(
            props.targetData?.statistics,
            'BSc',
            years
        ),

        tension: 0.3
      },

      {
        label: `${props.targetTitle} (MSc % Female)`,

        borderColor: '#e65100',
        backgroundColor: '#e65100',

        borderDash: [5, 5],

        data: buildFemaleArr(
            props.targetData?.statistics,
            'MSc',
            years
        ),

        tension: 0.3
      }
    ]
  };
});
</script>

<template>
  <div>
    <div class="dataset-selector">
      <label>
        Degree Level (For Enrollment & Degrees):
      </label>

      <div class="pill-container">
        <button
            v-for="l in countryLevels"
            :key="l"
            @click="selectedCountryLevel = l"
            class="pill-btn"
            :class="{
            active: selectedCountryLevel === l
          }"
        >
          {{ l }}
        </button>
      </div>
    </div>

    <div
        class="landscape-card"
        v-if="countryEnrollmentChart"
    >
      <h3>Total Enrollment Comparison</h3>

      <div class="chart-container landscape-chart">
        <Bar
            :data="countryEnrollmentChart"
            :options="chartOptions"
        />
      </div>
    </div>

    <div
        class="landscape-card"
        v-if="countryDegreesChart"
    >
      <h3>Degrees Awarded Comparison</h3>

      <div class="chart-container landscape-chart">
        <Line
            :data="countryDegreesChart"
            :options="chartOptions"
        />
      </div>
    </div>

    <div
        class="landscape-card"
        v-if="countryPipelineChart"
    >
      <h3>
        Gender Parity Comparison (% Female)
      </h3>

      <div class="chart-container landscape-chart">
        <Line
            :data="countryPipelineChart"
            :options="pipelineChartOptions"
        />
      </div>
    </div>
  </div>
</template>

<style scoped>
.dataset-selector {
  margin-bottom: 20px;

  display: flex;
  justify-content: center;
  align-items: center;
  flex-direction: column;
}

.dataset-selector label {
  display: block;

  margin-bottom: 8px;

  font-weight: bold;
}

.pill-container {
  display: flex;
  gap: 8px;
}

.pill-btn {
  padding: 6px 16px;

  border-radius: 20px;
  border: 1px solid #ccc;

  background: white;

  cursor: pointer;

  font-size: 13px;
  font-weight: 600;

  color: #666;
}

.pill-btn.active {
  background: #3388ff;
  border-color: #3388ff;
  color: white;
}

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
</style>