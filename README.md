# VI-SP — Informatics Europe Visualization & Statistics Platform

An interactive web platform for analyzing and visualizing informatics education data across European universities, with a focus on [Informatics Europe](https://www.informatics-europe.org/) member institutions.

## Overview

VI-SP combines geographic mapping, choropleth visualization, and statistical charts to explore the state of informatics education in Europe. It tracks student enrollment, graduation rates, female participation, and research university partnerships at both country and institution level.

## Features

- **Interactive Map** — Leaflet-based map with clustered markers for universities, IE partner institutions, and combined views
- **Choropleth Visualization** — Country-level color-coded maps showing BSc/MSc/PhD statistics across multiple metrics and years
- **Search & Filter** — Real-time search across universities and departments, with country and IE-partnership filters
- **Detail Modals** — Country-level statistics with charts, per-institution breakdowns, and side-by-side comparison view
- **Data Pipeline** — Python scripts that parse Excel/YAML sources and geocode institutions for use in the frontend

## Tech Stack

### Frontend
| Technology | Purpose |
|---|---|
| Vue 3 + TypeScript | UI framework |
| Vite | Build tool |
| Leaflet 1.9.4 + MarkerCluster | Interactive mapping |
| Chart.js 4.5.1 + vue-chartjs | Statistical charts |

### Data Pipeline (Python)
| Tool | Purpose |
|---|---|
| pandas | Excel file parsing |
| requests + lxml | Web scraping (IE member pages) |
| pycountry | Country code lookups |
| Nominatim API | University geocoding |
| Wikidata SPARQL API | Population data |

## Project Structure

```
VI-SP/
├── VI_SP_Project/vi_ui/     # Vue 3 frontend application
│   └── src/
│       ├── components/      # Map, panels, modals, search header
│       └── types/           # TypeScript type definitions
├── uni_data_parser/         # Excel → JSON parser for member statistics
├── ie_uni_crawler/          # Scraper for IE partnership data + geocoding
├── eter_data_parser/        # ETER dataset parser (enrollment/graduation)
├── uni_locator/             # Department-level geocoder (YAML → JSON)
├── data/                    # Raw YAML source data per country
├── geoJSON/                 # Country boundary GeoJSON files
└── VI_SP_Project/vi_ui/public/
    ├── borders/             # Country boundary data
    ├── unis/                # University + department data per country
    ├── eter_data/           # ETER enrollment/graduation data
    ├── members_data/        # Parsed member statistics
    ├── countries_data/      # Country-level aggregated metrics
    └── ie_members/          # IE partnership network data
```

## Getting Started

### Frontend — Development

**Requirements:** Node.js ^20.19.0 or >=22.12.0

```bash
cd VI_SP_Project/vi_ui
npm install
npm run dev
```

Open `http://localhost:5173` in your browser.

### Frontend — Production (Docker)

**Requirements:** Docker + Docker Compose

```bash
docker compose up --build
```

Open `http://localhost:8080` in your browser.

The image uses a two-stage build (Node 22 → nginx:alpine) and serves the compiled app via nginx on port 80, mapped to `8080` on the host. To change the host port, edit `docker-compose.yml`.

### Data Pipeline

**Requirements:** Python 3.14+

Install dependencies for each parser separately:

```bash
# IE member crawler
cd ie_uni_crawler
pip install requirements.txt

# University member statistics parser
cd uni_data_parser
pip install requirements.txt

# ETER data parser
cd eter_data_parser
pip install requirements.txt

# University/department geocoder
cd uni_locator
pip install requirements.txt
```

Run each script to regenerate the JSON data consumed by the frontend:

```bash
python ie_uni_crawler/ie_crawler.py        # → public/ie_members/
python uni_data_parser/main.py             # → public/members_data/, public/countries_data/
python eter_data_parser/main.py            # → public/eter_data/
python uni_locator/main.py                 # → public/unis/
```

Each script out JSON file in script-specific output directories to use them in frontend. Move the files to the appropriate `public/` subdirectories as needed. The scripts can be run independently or in sequence, depending on which data you want to update.

## Data Sources

| Source | Description |
|---|---|
| Informatics Europe website | Current IE member institutions |
| Members-DATA Excel | BSc/MSc/PhD student statistics per institution |
| ETER dataset | European Tertiary Education Register enrollment/graduation data |
| YAML files (`data/`) | Manually curated department data (CZ, DE, NO, PT, LV) |
| Wikidata SPARQL | Country population figures |
| OpenStreetMap Nominatim | University and department coordinates |

## Tracked Metrics

- Total enrolled students (BSc / MSc / PhD)
- First-year cohort sizes
- Degrees awarded per year
- Female participation count and percentage
- Students per 1 million population
- Institution type: Research University (RU) vs. University of Applied Sciences (UAS)
