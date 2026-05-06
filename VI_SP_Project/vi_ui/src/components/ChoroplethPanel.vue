<script setup lang="ts">
import { CHOROPLETH_FIELD_LABELS, DATASET_LABELS } from './utils/useChoropleth.ts';

const props = defineProps<{
  active:    boolean;
  dataset:   string;
  year:      string;
  field:     string;
  min:       number;
  max:       number;
  datasets:  string[];
  years:     string[];
  formatValue: (v: number) => string;
}>();

const emit = defineEmits<{
  (e: 'update:dataset', v: string): void;
  (e: 'update:year',    v: string): void;
  (e: 'update:field',   v: string): void;
  (e: 'dataset-change'): void;
  (e: 'apply'): void;
  (e: 'clear'): void;
}>();

const open = defineModel<boolean>('open', { default: false });
</script>

<template>
  <!-- Trigger button -->
  <button
    class="ch-trigger"
    :class="{ 'ch-trigger--active': active }"
    @click="open = !open"
    title="Colour map by statistics"
  >
    <svg viewBox="0 0 20 20" fill="currentColor" class="ch-icon" xmlns="http://www.w3.org/2000/svg">
      <rect x="2" y="4" width="4" height="12" rx="1"/>
      <rect x="8" y="7" width="4" height="9" rx="1"/>
      <rect x="14" y="2" width="4" height="14" rx="1"/>
    </svg>
    Colour map
  </button>

  <!-- Panel -->
  <Transition name="ch-slide">
    <div v-if="open" class="ch-panel">
      <div class="ch-panel-header">
        <span class="ch-panel-title">Choropleth Settings</span>
        <button class="ch-close" @click="open = false">✕</button>
      </div>

      <label class="ch-label">Dataset</label>
      <select
        :value="dataset"
        class="ch-select"
        @change="emit('update:dataset', ($event.target as HTMLSelectElement).value); emit('dataset-change')"
      >
        <option v-for="ds in datasets" :key="ds" :value="ds">
          {{ DATASET_LABELS[ds] ?? ds }}
        </option>
      </select>

      <label class="ch-label">Year</label>
      <select :value="year" class="ch-select" @change="emit('update:year', ($event.target as HTMLSelectElement).value)">
        <option v-for="yr in years" :key="yr" :value="yr">{{ yr }}</option>
      </select>

      <label class="ch-label">Metric</label>
      <div class="ch-field-group">
        <label
          v-for="(label, key) in CHOROPLETH_FIELD_LABELS"
          :key="key"
          class="ch-radio-label"
          :class="{ 'ch-radio-label--checked': field === key }"
        >
          <input
            type="radio"
            :value="key"
            :checked="field === key"
            class="ch-radio"
            @change="emit('update:field', key); emit('dataset-change')"
          />
          {{ label }}
        </label>
      </div>

      <div class="ch-actions">
        <button class="ch-btn ch-btn--apply" @click="emit('apply')">Apply</button>
        <button v-if="active" class="ch-btn ch-btn--clear" @click="emit('clear')">Reset</button>
      </div>

      <!-- Gradient scale -->
      <div class="ch-scale">
        <span class="ch-scale-label">{{ active ? formatValue(min) : 'Low' }}</span>
        <div class="ch-gradient-bar"></div>
        <span class="ch-scale-label">{{ active ? formatValue(max) : 'High' }}</span>
      </div>

      <div class="ch-no-data-row">
        <span class="ch-no-data-swatch"></span>No data
      </div>
    </div>
  </Transition>
</template>

<style scoped>
.ch-trigger {
  position: absolute;
  top: 60px; right: 12px;
  z-index: 1001;
  display: flex; align-items: center; gap: 6px;
  padding: 7px 13px;
  background: #fff; border: 1px solid #ccc; border-radius: 6px;
  font-size: 13px; font-weight: 600; cursor: pointer;
  box-shadow: 0 1px 5px rgba(0,0,0,.2); color: #333;
  transition: background .15s, border-color .15s;
}
.ch-trigger:hover       { background: #f0f4ff; border-color: #3388ff; }
.ch-trigger--active     { background: #e6f0ff; border-color: #3388ff; color: #1a5ccf; }
.ch-icon                { width: 16px; height: 16px; }

.ch-panel {
  position: absolute;
  top: 100px; right: 12px;
  z-index: 1001; width: 272px;
  background: #fff; border-radius: 10px;
  box-shadow: 0 4px 20px rgba(0,0,0,.18);
  padding: 16px; font-size: 13px;
  display: flex; flex-direction: column; gap: 8px;
}
.ch-panel-header  { display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px; }
.ch-panel-title   { font-weight: 700; font-size: 14px; color: #222; }
.ch-close         { background: none; border: none; cursor: pointer; font-size: 15px; color: #888; line-height: 1; }
.ch-close:hover   { color: #333; }

.ch-label { font-weight: 600; color: #555; font-size: 11px; text-transform: uppercase; letter-spacing: .05em; }
.ch-select {
  width: 100%; padding: 6px 8px; border: 1px solid #ddd;
  border-radius: 5px; font-size: 13px; background: #fafafa; color: #222; cursor: pointer;
}
.ch-select:focus { outline: none; border-color: #3388ff; }

.ch-field-group       { display: flex; flex-direction: column; gap: 4px; }
.ch-radio-label       { display: flex; align-items: center; gap: 6px; padding: 5px 8px; border-radius: 5px; cursor: pointer; transition: background .1s; }
.ch-radio-label:hover { background: #f0f4ff; }
.ch-radio-label--checked { background: #e6f0ff; color: #1a5ccf; font-weight: 600; }
.ch-radio             { accent-color: #3388ff; }

.ch-actions      { display: flex; gap: 8px; margin-top: 4px; }
.ch-btn          { flex: 1; padding: 8px; border-radius: 5px; border: none; font-size: 13px; font-weight: 600; cursor: pointer; transition: background .15s; }
.ch-btn--apply   { background: #3388ff; color: #fff; }
.ch-btn--apply:hover { background: #1565c0; }
.ch-btn--clear   { background: #f0f0f0; color: #444; }
.ch-btn--clear:hover { background: #e0e0e0; }

.ch-scale        { display: flex; align-items: center; gap: 6px; margin-top: 4px; }
.ch-scale-label  { font-size: 11px; color: #777; white-space: nowrap; }
.ch-gradient-bar {
  flex: 1; height: 14px; border-radius: 4px;
  background: linear-gradient(to right, #d73027, #fee08b, #1a9850);
  border: 1px solid #ddd;
}
.ch-no-data-row    { display: flex; align-items: center; gap: 6px; font-size: 12px; color: #666; }
.ch-no-data-swatch { display: inline-block; width: 18px; height: 14px; background: #b0b0b0; border-radius: 3px; border: 1px solid #ddd; }

.ch-slide-enter-active, .ch-slide-leave-active { transition: opacity .2s, transform .2s; }
.ch-slide-enter-from,   .ch-slide-leave-to     { opacity: 0; transform: translateY(-8px); }
</style>
