<!-- CompareModal.vue -->
<script setup lang="ts">
import { computed, ref, onMounted, watch } from 'vue';

import CountryComparison from './comparisons/CountryComparison.vue';
import InstitutionComparison from './comparisons/InstitutionComparison.vue';

const props = defineProps<{
  isOpen: boolean;
  baseTitle: string;
  baseType: 'country' | 'institution';
  baseData: any;
  allCountriesData?: any;
}>();

const emit = defineEmits<{
  (e: 'close'): void;
}>();

const targetTitle = ref('');
const searchQuery = ref('');
const isDropdownOpen = ref(false);

const allMembersData = ref<any>({});
const allEterData = ref<any>({});

const fetchJsonSafely = async (url: string) => {
  try {
    const res = await fetch(url);

    if (!res.ok) return {};

    const text = await res.text();

    if (text.trim().startsWith('<')) return {};

    return JSON.parse(text);
  } catch (error) {
    console.error(`CompareModal failed to parse ${url}`, error);
    return {};
  }
};

onMounted(async () => {
  if (props.baseType === 'institution') {
    allMembersData.value =
        (await fetchJsonSafely('/members_data/members_parsed.json')) || {};

    allEterData.value =
        (await fetchJsonSafely('/eter_data/eter_parsed.json')) || {};
  }
});

const availableTargets = computed(() => {
  if (props.baseType === 'country' && props.allCountriesData) {
    return Object.keys(props.allCountriesData)
        .filter(c => c !== props.baseTitle)
        .sort();
  }

  const set = new Set([
    ...Object.keys(allMembersData.value),
    ...Object.keys(allEterData.value)
  ]);

  set.delete(props.baseTitle);

  return Array.from(set).sort();
});

const filteredTargets = computed(() => {
  const query = searchQuery.value.toLowerCase().trim();

  if (!query) return availableTargets.value.slice(0, 50);

  return availableTargets.value
      .filter(t => t.toLowerCase().includes(query))
      .slice(0, 50);
});

const selectTarget = (t: string) => {
  targetTitle.value = t;
  searchQuery.value = t;
  isDropdownOpen.value = false;
};

const targetData = computed(() => {
  if (!targetTitle.value) return null;

  if (props.baseType === 'country') {
    return props.allCountriesData?.[targetTitle.value];
  }

  return {
    member: allMembersData.value[targetTitle.value] || null,
    eter: allEterData.value[targetTitle.value]?.informatics_data || null
  };
});

watch(
    () => props.isOpen,
    open => {
      if (open) {
        targetTitle.value = '';
        searchQuery.value = '';
        isDropdownOpen.value = false;
      }
    }
);
</script>

<template>
  <div
      v-if="isOpen"
      class="modal-overlay"
      style="z-index: 10000;"
      @click.self="emit('close')"
  >
    <div class="modal-content">
      <button class="close-btn" @click="emit('close')">
        ✕
      </button>

      <div class="modal-header">
        <h2>
          Compare
          {{ baseType === 'country' ? 'Countries' : 'Institutions' }}
        </h2>

        <div class="compare-row">
          <div class="compare-entity base">
            {{ baseTitle }}
          </div>

          <div class="compare-vs">VS</div>

          <div class="compare-entity target">
            <div class="autocomplete-wrapper">
              <input
                  type="text"
                  v-model="searchQuery"
                  @focus="isDropdownOpen = true"
                  @blur="setTimeout(() => (isDropdownOpen = false), 200)"
                  :placeholder="`Search ${baseType} to compare...`"
                  class="compare-input"
              />

              <ul
                  v-show="isDropdownOpen"
                  class="autocomplete-list"
              >
                <li
                    v-if="filteredTargets.length === 0"
                    class="no-results"
                >
                  No matches found
                </li>

                <li
                    v-for="t in filteredTargets"
                    :key="t"
                    @click="selectTarget(t)"
                >
                  {{ t }}
                </li>
              </ul>
            </div>
          </div>
        </div>
      </div>

      <div class="compare-body">
        <div
            v-if="!targetTitle"
            class="no-data-state"
        >
          <p>
            Please search and select a
            {{ baseType }}
            from the box above to begin the comparison.
          </p>
        </div>

        <CountryComparison
            v-else-if="baseType === 'country'"
            :base-title="baseTitle"
            :target-title="targetTitle"
            :base-data="baseData"
            :target-data="targetData"
        />

        <InstitutionComparison
            v-else
            :base-title="baseTitle"
            :target-title="targetTitle"
            :base-data="baseData"
            :target-data="targetData"
        />
      </div>
    </div>
  </div>
</template>

<style scoped>
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.7);

  display: flex;
  align-items: center;
  justify-content: center;

  backdrop-filter: blur(4px);
}

.modal-content {
  background: #f4f6f8;

  width: 90%;
  max-width: 900px;
  max-height: 85vh;

  overflow-y: auto;

  position: relative;

  padding: 24px;

  border-radius: 12px;
  border: 2px solid #3388ff;

  box-shadow: 0 10px 40px rgba(0, 0, 0, 0.3);
}

.close-btn {
  position: absolute;
  top: 16px;
  right: 16px;

  border: none;
  background: none;

  font-size: 20px;
  cursor: pointer;

  color: #666;

  transition: color 0.2s;
}

.close-btn:hover {
  color: #000;
}

.modal-header h2 {
  margin: 0 0 16px 0;

  color: #2c3e50;

  font-size: 18px;
  text-transform: uppercase;
  letter-spacing: 1px;
}

.compare-row {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 16px;

  background: #fff;

  padding: 16px;
  margin-bottom: 24px;

  border-radius: 8px;

  box-shadow: 0 2px 5px rgba(0, 0, 0, 0.05);
}

.compare-entity {
  flex: 1;

  text-align: center;

  font-size: 16px;
  font-weight: bold;

  color: #333;
}

.compare-vs {
  width: 32px;
  height: 32px;

  display: flex;
  align-items: center;
  justify-content: center;

  flex-shrink: 0;

  border-radius: 50%;

  background: #3388ff;
  color: white;

  font-size: 12px;
  font-weight: bold;
}

.autocomplete-wrapper {
  position: relative;

  width: 100%;
  max-width: 350px;

  margin: 0 auto;

  text-align: left;
}

.compare-input {
  width: 100%;

  padding: 10px 16px;

  border-radius: 6px;
  border: 2px solid #ccc;

  outline: none;

  font-size: 14px;
  font-weight: bold;

  color: #333;

  transition: border-color 0.2s;

  box-sizing: border-box;
}

.compare-input:focus {
  border-color: #3388ff;
}

.autocomplete-list {
  position: absolute;

  top: 100%;
  left: 0;
  right: 0;

  margin-top: 4px;
  padding: 0;

  list-style: none;

  background: white;

  border: 1px solid #ccc;
  border-radius: 6px;

  max-height: 250px;
  overflow-y: auto;

  z-index: 10001;

  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}

.autocomplete-list li {
  padding: 10px 16px;

  cursor: pointer;

  font-size: 13px;

  border-bottom: 1px solid #eee;

  transition: background 0.1s;
}

.autocomplete-list li:last-child {
  border-bottom: none;
}

.autocomplete-list li:hover {
  background: #f0f7ff;
  color: #3388ff;
}

.no-results {
  color: #999;
  font-style: italic;

  cursor: default !important;
}

.no-results:hover {
  background: white !important;
  color: #999 !important;
}

.compare-body {
  width: 100%;
}

.no-data-state {
  text-align: center;

  padding: 60px 20px;

  color: #666;

  font-size: 15px;
}
</style>