<script setup lang="ts">
import { ref, computed } from 'vue';
import type { University, IEPartnerCountry, SearchResult, ModalPayload} from './types';
import SearchHeader from './components/SearchHeader.vue';
import LeafletMap from './components/LeafletMap.vue';
import InfoModal from './components/InfoModal.vue';

// Filter state
const searchQuery = ref('');
const selectedCountry = ref<string>('all');
const showIEOnly = ref(false);

// Map data state
const universitiesData = ref<Record<string, University[]>>({});
const iePartnersData = ref<IEPartnerCountry[]>([]);
const ieAnduniversitiesData = ref<Record<string, University[]>>({});

const availableCountries = ref<string[]>([]);
const allCountriesData = ref<any>(null);

// Modal State
const isModalOpen = ref(false);
const modalContent = ref<ModalPayload | null>(null);

// Ref to the map component to trigger methods
const mapRef = ref<InstanceType<typeof LeafletMap> | null>(null);

// Update data once map fetches it
const handleDataLoaded = (payload: {
  unis: Record<string, University[]>,
  partners: IEPartnerCountry[],
  partnersAndUnis: Record<string, University[]>,
  countries: string[],
  allCountriesData: any; }) => {
  universitiesData.value = payload.unis;
  iePartnersData.value = payload.partners;
  availableCountries.value = payload.countries;
  allCountriesData.value = payload.allCountriesData;;
};

const handleSelectResult = (result: SearchResult) => {
  mapRef.value?.flyToResult(result);
  searchQuery.value = ''; // clear search after flying
};

const handleShowDetails = (payload: ModalPayload) => {
  modalContent.value = payload;
  isModalOpen.value = true;
};

const searchResults = computed((): SearchResult[] => {
  const query = searchQuery.value.trim().toLowerCase();
  if (!query) return [];

  const results: SearchResult[] = [];

  if (!showIEOnly.value) {
    for (const [countryCode, unis] of Object.entries(universitiesData.value)) {
      if (selectedCountry.value !== 'all' && selectedCountry.value !== countryCode) continue;

      unis.forEach((uni) => {
        if (uni.departments && uni.departments.length > 0) {
          uni.departments.forEach((dept) => {
            if (uni.name.toLowerCase().includes(query) || dept.name.toLowerCase().includes(query)) {
              results.push({ countryCode, uni, dept, isIEPartner: false });
            }
          });
        } else {
          if (uni.name.toLowerCase().includes(query)) {
            results.push({ countryCode, uni, isIEPartner: false });
          }
        }
      });
    }
  }

  iePartnersData.value.forEach((country) => {
    if (selectedCountry.value !== 'all' && selectedCountry.value !== country.country_code) return;

    country.partners.forEach((partner) => {
      if (
          partner.uni_name.toLowerCase().includes(query) ||
          partner.dept_name.toLowerCase().includes(query)
      ) {
        results.push({ countryCode: country.country_code, iePartner: partner, isIEPartner: true });
      }
    });
  });

  return results.slice(0, 20);
});
</script>

<template>
  <main>
    <SearchHeader
        v-model:searchQuery="searchQuery"
        v-model:selectedCountry="selectedCountry"
        v-model:showIEOnly="showIEOnly"
        :availableCountries="availableCountries"
        :searchResults="searchResults"
        @select-result="handleSelectResult"
    />

    <LeafletMap
        ref="mapRef"
        @data-loaded="handleDataLoaded"
        @show-details="handleShowDetails"
    />

    <InfoModal
        v-if="modalContent"
        :is-open="isModalOpen"
        :title="modalContent.title"
        :subtitle="modalContent.subtitle"
        :data="modalContent.data"
        :all-countries-data="allCountriesData"
        @close="isModalOpen = false"
    />
  </main>
</template>

<style scoped>
:global(body) {
  margin: 0;
  padding: 0;
}
</style>