import { ref } from 'vue';
import L from 'leaflet';
import type { ParsedDataDictionary } from '@/types';

// ── Constants ─────────────────────────────────────────────────────────────────

export const CHOROPLETH_FIELD_LABELS: Record<string, string> = {
  'total':        'Total count',
  'female':       'Female count',
  'ratio per 1M': 'Ratio per 1 M pop.',
  'female %':     'Female share (%)',
};

export const DATASET_LABELS: Record<string, string> = {
  'BSc_Degrees-awarded_RU-UAS.xlsx':        'BSc – Degrees awarded',
  'BSc_First-year-students_RU-UAS.xlsx':    'BSc – First-year students',
  'BSc_Students-all-semesters_RU-UAS.xlsx': 'BSc – All students',
  'MSc_Degrees-awarded_RU-UAS.xlsx':        'MSc – Degrees awarded',
  'MSc_First-year-students_RU-UAS.xlsx':    'MSc – First-year students',
  'MSc_Students-all-semesters_RU-UAS.xlsx': 'MSc – All students',
  'PhD_Degrees-awarded_RU-UAS.xlsx':        'PhD – Degrees awarded',
  'PhD_First-year-students_RU-UAS.xlsx':    'PhD – First-year students',
  'PhD_Students-all-semesters_RU-UAS.xlsx': 'PhD – All students',
};

// GeoJSON feature names that differ from countries_parsed.json keys
const GEO_NAME_ALIASES: Record<string, string> = {
  'Czech Republic':         'Czechia',
  'Bosnia and Herz.':       'Bosnia and Herzegovina',
  'Bosnia And Herzegovina': 'Bosnia and Herzegovina',
  'Republic of Serbia':     'Serbia',
  'Macedonia':              'North Macedonia',
  'Slovak Republic':        'Slovakia',
  'Great Britain':          'UK',
  'United Kingdom':         'UK',
  'Republic of Moldova':    'Moldova',
};

// ── Helpers ───────────────────────────────────────────────────────────────────

const cleanStr = (s: string) => (s ?? '').toLowerCase().replace(/[^a-z0-9]/g, '');

const lerpColor = (a: string, b: string, t: number): string => {
  const ah = a.replace('#', ''), bh = b.replace('#', '');
  const r  = Math.round(parseInt(ah.slice(0, 2), 16) + (parseInt(bh.slice(0, 2), 16) - parseInt(ah.slice(0, 2), 16)) * t);
  const g  = Math.round(parseInt(ah.slice(2, 4), 16) + (parseInt(bh.slice(2, 4), 16) - parseInt(ah.slice(2, 4), 16)) * t);
  const b2 = Math.round(parseInt(ah.slice(4, 6), 16) + (parseInt(bh.slice(4, 6), 16) - parseInt(ah.slice(4, 6), 16)) * t);
  return `#${r.toString(16).padStart(2, '0')}${g.toString(16).padStart(2, '0')}${b2.toString(16).padStart(2, '0')}`;
};

const valueToColor = (t: number): string =>
  t <= 0.5 ? lerpColor('#d73027', '#fee08b', t / 0.5) : lerpColor('#fee08b', '#1a9850', (t - 0.5) / 0.5);

const resolveCountryName = (geoName: string, dataKeys: string[]): string | null => {
  const alias = GEO_NAME_ALIASES[geoName];
  if (alias && dataKeys.includes(alias)) return alias;
  if (dataKeys.includes(geoName)) return geoName;
  const g = cleanStr(geoName);
  return dataKeys.find(k => {
    const ck = cleanStr(k);
    if (ck.length < 4 || g.length < 4) return ck === g;
    return ck === g || ck.includes(g) || g.includes(ck);
  }) ?? null;
};

// ── Composable ────────────────────────────────────────────────────────────────

export function useChoropleth(parsedCountriesData: ReturnType<typeof ref<ParsedDataDictionary>>) {
  // Layer registry — filled by LeafletMap when borders are drawn
  const countryGeoLayers: Record<string, L.Path[]> = {};
  const colorCache: Record<string, string> = {};

  // Reactive UI state (consumed by ChoroplethPanel)
  const active   = ref(false);
  const dataset  = ref('');
  const year     = ref('');
  const field    = ref('ratio per 1M');
  const appliedField = ref('ratio per 1M');
  const min      = ref(0);
  const max      = ref(1);
  const datasets = ref<string[]>([]);
  const years    = ref<string[]>([]);

  /** Call this after parsedCountriesData is loaded to populate dataset/year dropdowns */
  const init = () => {
    const dsSet = new Set<string>();
    for (const country of Object.values(parsedCountriesData.value as Record<string, any>))
      for (const ds of Object.keys(country?.statistics ?? {})) dsSet.add(ds);
    datasets.value = [...dsSet].sort();
    if (datasets.value.length) {
      dataset.value = datasets.value[0];
      onDatasetChange();
    }
  };

  /** Rebuild year list and pick the year with the most real numeric data */
  const onDatasetChange = () => {
    const ds = dataset.value;
    const f  = field.value;
    const countries = Object.values(parsedCountriesData.value as Record<string, any>);

    const yearSet = new Set<string>();
    for (const c of countries)
      for (const yr of Object.keys(c?.statistics?.[ds] ?? {})) yearSet.add(yr);
    years.value = [...yearSet].sort();

    let bestYear = '', bestCount = -1;
    for (const yr of years.value) {
      const count = countries.filter(c => {
        const v = c?.statistics?.[ds]?.[yr]?.[f];
        return typeof v === 'number' && isFinite(v);
      }).length;
      if (count >= bestCount) { bestCount = count; bestYear = yr; }
    }
    year.value = bestYear || years.value[years.value.length - 1] || '';
  };

  /** Register a Leaflet Path under its GeoJSON country name (called from onEachFeature) */
  const registerPath = (countryName: string, path: L.Path) => {
    if (!countryGeoLayers[countryName]) countryGeoLayers[countryName] = [];
    countryGeoLayers[countryName].push(path);
  };

  /** Restore cached colour for one country (used by mouseout) */
  const restoreColor = (countryName: string, path: L.Path) => {
    if (!active.value) { path.setStyle({ fillOpacity: 0.1 }); return; }
    path.setStyle({ fillColor: colorCache[countryName] ?? '#b0b0b0', fillOpacity: 0.7 });
  };

  const formatValue = (v: number): string => {
    if (appliedField.value === 'female %')     return `${(v * 100).toFixed(1)}%`;
    if (appliedField.value === 'ratio per 1M') return v.toFixed(1);
    return Math.round(v).toLocaleString();
  };

  const apply = () => {
    if (!dataset.value || !year.value) return;
    const dataKeys = Object.keys(parsedCountriesData.value);
    const values: Record<string, number | null> = {};

    for (const geoName of Object.keys(countryGeoLayers)) {
      const matched = resolveCountryName(geoName, dataKeys);
      const raw = matched
        ? (parsedCountriesData.value as any)[matched]?.statistics?.[dataset.value]?.[year.value]?.[field.value]
        : undefined;
      values[geoName] = (typeof raw === 'number' && isFinite(raw)) ? raw : null;
    }

    const nums = Object.values(values).filter((v): v is number => v !== null);
    min.value = nums.length ? Math.min(...nums) : 0;
    max.value = nums.length ? Math.max(...nums) : 1;

    for (const [geoName, paths] of Object.entries(countryGeoLayers)) {
      const val   = values[geoName];
      const color = val === null ? '#b0b0b0' : valueToColor((val - min.value) / (max.value - min.value || 1));
      colorCache[geoName] = color;
      paths.forEach(p => p.setStyle({ fillColor: color, fillOpacity: 0.7, color: '#444', weight: 1 }));
    }

    appliedField.value = field.value;
    active.value = true;
  };

  const clear = () => {
    for (const paths of Object.values(countryGeoLayers))
      paths.forEach(p => p.setStyle({ fillColor: '#2174f5', fillOpacity: 0.1, color: 'rgb(33,116,245)', weight: 1 }));
    active.value = false;
  };

  return {
    // state
    active, dataset, year, field, min, max, datasets, years,
    // methods
    init, onDatasetChange, registerPath, restoreColor, formatValue, apply, clear,
  };
}
