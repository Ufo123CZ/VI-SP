<script setup lang="ts">
import type { SearchResult } from '@/types';

defineProps<{
  availableCountries: string[];
  searchResults: SearchResult[];
  selectedCountry: string;
  showIEOnly: boolean;
  searchQuery: string;
}>();

const emit = defineEmits<{
  (e: 'update:selectedCountry', value: string): void;
  (e: 'update:showIEOnly', value: boolean): void;
  (e: 'update:searchQuery', value: string): void;
  (e: 'select-result', result: SearchResult): void;
}>();
</script>

<template>
  <div class="search-header">
    <select
        :value="selectedCountry"
        @input="emit('update:selectedCountry', ($event.target as HTMLSelectElement).value)"
        class="country-filter"
    >
      <option value="all">All countries</option>
      <option v-for="code in availableCountries" :key="code" :value="code">
        {{ code.toUpperCase() }}
      </option>
    </select>

    <button
        @click="emit('update:showIEOnly', !showIEOnly)"
        class="ie-toggle"
        :class="{ 'is-active': showIEOnly }"
    >
      ★ IE Only
    </button>

    <div class="search-input-wrapper">
      <input
          :value="searchQuery"
          @input="emit('update:searchQuery', ($event.target as HTMLInputElement).value)"
          type="text"
          placeholder="Search universities..."
          class="search-input"
      />

      <div v-if="searchResults.length > 0" class="results-dropdown">
        <div
            v-for="(result, i) in searchResults"
            :key="i"
            @click="emit('select-result', result)"
            class="result-item"
        >
          <div class="result-title">
            <span v-if="result.isIEPartner" class="ie-star">★</span>
            {{ result.isIEPartner ? result.iePartner?.uni_name : result.uni?.name }}
          </div>
          <div class="result-subtitle">
            {{ result.isIEPartner ? result.iePartner?.dept_name : (result.dept?.name ?? result.uni?.institution) }}
            · {{ result.countryCode.toUpperCase() }}
          </div>
        </div>
      </div>

      <div v-else-if="searchQuery.trim().length > 0" class="no-results">
        No results found
      </div>
    </div>
  </div>
</template>

<style scoped>
.search-header {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  z-index: 1000;
  background: white;
  padding: 10px 16px;
  box-shadow: 0 2px 6px rgba(0,0,0,0.2);
  display: flex;
  gap: 10px;
  align-items: center;
}

.country-filter, .search-input {
  padding: 6px 10px;
  border-radius: 6px;
  border: 1px solid #ccc;
  font-size: 13px;
  box-sizing: border-box;
}

.ie-toggle {
  padding: 6px 10px;
  border-radius: 6px;
  border: 1px solid #ccc;
  background: white;
  color: #333;
  font-size: 13px;
  cursor: pointer;
  white-space: nowrap;
  transition: all 0.2s ease;
}

.ie-toggle.is-active {
  border-color: green;
  background: #f0fff0;
  color: green;
}

.search-input-wrapper {
  position: relative;
  flex: 1;
}

.search-input {
  width: 100%;
}

.results-dropdown {
  position: absolute;
  top: 100%;
  left: 0;
  right: 0;
  background: white;
  border: 1px solid #ccc;
  border-radius: 6px;
  margin-top: 4px;
  max-height: 300px;
  overflow-y: auto;
  box-shadow: 0 4px 12px rgba(0,0,0,0.15);
  z-index: 1001;
}

.result-item {
  padding: 8px 12px;
  cursor: pointer;
  border-bottom: 1px solid #f0f0f0;
  font-size: 13px;
  background: white;
  transition: background 0.15s ease;
}

.result-item:hover {
  background: #f5f5f5;
}

.result-title {
  font-weight: 600;
}

.ie-star {
  color: green;
  margin-right: 4px;
}

.result-subtitle {
  color: #666;
  font-size: 11px;
}

.no-results {
  position: absolute;
  top: 100%;
  left: 0;
  right: 0;
  background: white;
  border: 1px solid #ccc;
  border-radius: 6px;
  margin-top: 4px;
  padding: 10px 12px;
  font-size: 13px;
  color: #999;
  box-shadow: 0 4px 12px rgba(0,0,0,0.15);
  z-index: 1001;
}
</style>