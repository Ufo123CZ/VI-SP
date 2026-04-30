<script setup lang="ts">
import { computed, ref } from 'vue';
import { Chart as ChartJS, Title, Tooltip, Legend, BarElement, LineElement, PointElement, ArcElement, CategoryScale, LinearScale } from 'chart.js';

import CountryDetails from './details/CountryDetails.vue';
import InstitutionDetails from './details/InstitutionDetails.vue';
import CompareModal from './CompareModal.vue';

ChartJS.register(Title, Tooltip, Legend, BarElement, LineElement, PointElement, ArcElement, CategoryScale, LinearScale);

const props = defineProps<{
  isOpen: boolean;
  title: string;
  subtitle?: string;
  data: any;
  allCountriesData: any;
}>();

const emit = defineEmits<{ (e: 'close'): void; }>();

const isCountry = computed(() => props.subtitle === 'Country Overview');
const isInstitution = computed(() => props.subtitle === 'Institution Details');

const hasData = computed(() => {
  if (isCountry.value) return !!props.data && !!props.data.statistics;
  if (isInstitution.value) return !!props.data && (!!props.data.member || !!props.data.eter);
  return false;
});

// Compare Modal State
const isCompareModalOpen = ref(false);
</script>

<template>
  <div v-if="isOpen" class="modal-overlay" @click.self="emit('close')">
    <div class="modal-content">
      <button class="close-btn" @click="emit('close')">✕</button>

      <div class="modal-header">
        <div class="header-titles">
          <h2>{{ title }}</h2>
          <h4 class="subtitle">{{ subtitle }}</h4>
          <p v-if="isCountry && data?.population" class="population-note">
            Population: {{ data.population.toLocaleString() }}
          </p>
        </div>

        <button v-if="hasData" class="open-compare-btn" @click="isCompareModalOpen = true">
          <span class="icon">↹</span> Compare
        </button>
      </div>

      <div v-if="!hasData" class="no-data-state" style="margin-top: 40px;">
        <div class="empty-icon">📊</div>
        <h3>No Data Available</h3>
        <p>We currently do not have statistical records to display for {{ title }}.</p>
      </div>

      <CountryDetails v-else-if="isCountry" :title="title" :data="data" :allCountriesData="allCountriesData" />
      <InstitutionDetails v-else-if="isInstitution" :data="data" />

      <CompareModal
          :is-open="isCompareModalOpen"
          :base-title="title"
          :base-type="isCountry ? 'country' : 'institution'"
          :base-data="data"
          :all-countries-data="allCountriesData"
          @close="isCompareModalOpen = false"
      />
    </div>
  </div>
</template>

<style scoped>
.modal-overlay { position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(0, 0, 0, 0.5); z-index: 9999; display: flex; align-items: center; justify-content: center; backdrop-filter: blur(2px); }
.modal-content { background: #f4f6f8; padding: 24px; border-radius: 12px; width: 90%; max-width: 800px; max-height: 85vh; overflow-y: auto; position: relative; box-shadow: 0 10px 25px rgba(0,0,0,0.2); }
.modal-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 12px; padding-right: 20px; }
.header-titles h2 { margin: 0 0 4px 0; color: #2c3e50; }
.subtitle { color: #3388ff; margin: 0 0 8px 0; font-weight: 600; text-transform: uppercase; font-size: 13px; letter-spacing: 0.5px; }
.population-note { color: #666; margin: 0; font-weight: 400; font-size: 14px;}
.close-btn { position: absolute; top: 16px; right: 16px; background: none; border: none; font-size: 18px; cursor: pointer; color: #666; transition: color 0.2s; }
.close-btn:hover { color: #000; }
.no-data-state { text-align: center; padding: 40px 20px; color: #666; }
.empty-icon { font-size: 48px; margin-bottom: 12px; opacity: 0.5; }
.no-data-state h3 { margin: 0 0 8px 0; color: #333; }

/* Clean Button Styling */
.open-compare-btn {
  background: white; border: 2px solid #3388ff; color: #3388ff;
  padding: 6px 14px; border-radius: 6px; font-weight: 600; font-size: 13px;
  cursor: pointer; display: flex; align-items: center; gap: 6px; transition: all 0.2s;
}
.open-compare-btn:hover { background: #3388ff; color: white; }
.open-compare-btn .icon { font-size: 16px; font-weight: bold; }
</style>