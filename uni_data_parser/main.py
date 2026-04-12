import pandas as pd
import json
import glob
import requests

def fetch_wikidata_populations(country_names):
    """
    Fetches the most recent population for a list of countries from Wikidata using SPARQL.
    """
    print("Fetching updated populations from Wikidata...")
    
    # Map any dataset-specific names to their official English Wikipedia/Wikidata labels
    name_mapping = {
        "UK": "United Kingdom",
        "Czech Republic": "Czech Republic" # Wikidata accepts Czechia or Czech Republic, but we map strictly just in case
    }
    
    # Format the SPARQL VALUES block (e.g., "Austria"@en "United Kingdom"@en)
    values_str = " ".join([f'"{name_mapping.get(c, c)}"@en' for c in country_names])
    
    # SPARQL query: Get max population for matching English labels
    query = f"""
    SELECT ?countryLabel (MAX(?population) AS ?pop) WHERE {{
      VALUES ?countryLabel {{ {values_str} }}
      ?country rdfs:label ?countryLabel .
      ?country wdt:P1082 ?population .
    }} GROUP BY ?countryLabel
    """
    
    url = 'https://query.wikidata.org/sparql'
    headers = {
        # Wikidata requires a User-Agent to avoid blocking automated requests
        'User-Agent': 'InformaticsDataParser/1.0 (Contact: your_email@example.com)',
        'Accept': 'application/json'
    }
    
    try:
        response = requests.get(url, params={'format': 'json', 'query': query}, headers=headers)
        response.raise_for_status()
        
        data = response.json()
        pop_dict = {}
        
        # Parse the JSON response from Wikidata
        for item in data['results']['bindings']:
            label = item['countryLabel']['value']
            
            # Reverse map the label back to your dataset's terminology (e.g., "United Kingdom" -> "UK")
            reverse_map = {v: k for k, v in name_mapping.items()}
            dataset_name = reverse_map.get(label, label)
            
            pop_dict[dataset_name] = int(item['pop']['value'])
            
        print(f"Successfully fetched {len(pop_dict)} populations from Wikidata.")
        return pop_dict
        
    except Exception as e:
        print(f"Failed to fetch Wikidata populations: {e}")
        return {}


def parse_members_data(file_path, dynamic_populations):
    df = pd.read_excel(file_path, header=[1, 2])
    
    df.columns = [
        f"{col[0]}_{col[1]}" if 'Unnamed' not in col[1] else col[0] 
        for col in df.columns
    ]
    
    df = df.rename(columns={
        'Country': 'country',
        'Institution Name': 'institution',
        'Institution Type': 'institution_type',
        'Population': 'population_old',
        'Level': 'level',
        'Statistics': 'statistics',
        '2023-2024_total': 'total',
        '2023-2024_female': 'female',
        '2023-2024_ratio per 1M': 'ratio_per_1m',
        '2023-2024_female %': 'female_percentage',
        '2023-2024_Programmes': 'programmes'
    })
    
    df = df.dropna(subset=['institution'])
    members_json = {}
    
    for _, row in df.iterrows():
        uni = row['institution']
        c_name = str(row.get('country')).strip()
        
        # Override with Wikidata population if available, else fallback to the file's old population
        current_pop = dynamic_populations.get(c_name, row.get('population_old'))
        
        if uni not in members_json:
            members_json[uni] = {
                "country": c_name,
                "country_population": current_pop,
                "institution_type": row.get('institution_type'),
                "data": []
            }
        
        stat_entry = {
            "level": row.get('level'),
            "category": row.get('statistics'),
            "stats_2023_2024": {
                "total": row.get('total'),
                "female": row.get('female'),
                "female_percentage": row.get('female_percentage'),
                "programmes": row.get('programmes')
            }
        }
        members_json[uni]["data"].append(stat_entry)
        
    with open("members_parsed.json", "w", encoding="utf-8") as f:
        json.dump(members_json, f, indent=4, ensure_ascii=False)
    print("Successfully parsed Members data.")


def parse_country_data(dynamic_populations):
    # 1. Update glob to look for standard Excel files
    excel_files = glob.glob("*_RU-UAS.xlsx")
    
    if not excel_files:
        print("Warning: No files ending in '_RU-UAS.xlsx' were found in this directory!")
        return

    countries_dict = {}
    
    for file in excel_files:
        dataset_name = file
        print(f"Processing {file}...")
        
        # --- Parse Footnotes Sheet ---
        try:
            # Read without headers to find where 'Country' starts
            df_fn_raw = pd.read_excel(file, sheet_name='footnotes', header=None)
            start_idx = 0
            for i, row in df_fn_raw.iterrows():
                if str(row[0]).lower().startswith('country'):
                    start_idx = i
                    break
            
            # Read properly with the correct header row
            df_fn = pd.read_excel(file, sheet_name='footnotes', skiprows=start_idx)
            
            for _, row in df_fn.iterrows():
                if pd.isna(row.get('Country')):
                    continue
                c_name = str(row.get('Country')).replace('(RU + UAS)', '').replace('(RU)', '').strip()
                if c_name not in countries_dict:
                    countries_dict[c_name] = {"population": None, "footnotes": [], "statistics": {}}
                countries_dict[c_name]["footnotes"].append({
                    "dataset": dataset_name,
                    "note": row.get('Footnote')
                })
        except Exception as e:
            print(f"  -> Skipping footnotes in {file}: {e}")

        # --- Parse Data Sheet ---
        try:
            # Read without headers to find where 'COUNTRY' starts
            df_d_raw = pd.read_excel(file, sheet_name='data', header=None)
            start_idx = 0
            for i, row in df_d_raw.iterrows():
                if str(row[0]).upper().startswith('COUNTRY'):
                    start_idx = i
                    break
            
            # Read properly with MultiIndex headers
            df_d = pd.read_excel(file, sheet_name='data', skiprows=start_idx, header=[0, 1])
            
            new_cols = []
            last_valid_c1 = ""
            for c1, c2 in df_d.columns:
                c1, c2 = str(c1), str(c2)
                if not c1.startswith('Unnamed'):
                    last_valid_c1 = c1
                
                if 'Unnamed' in c2:
                    new_cols.append(last_valid_c1)
                elif last_valid_c1.upper() in ['COUNTRY', 'INSTITUTION TYPE', 'YEAR'] or 'Unnamed' in last_valid_c1:
                    new_cols.append(c2)
                else:
                    new_cols.append(f"{last_valid_c1}_{c2}")
                    
            df_d.columns = new_cols
            country_col = next((c for c in df_d.columns if 'COUNTRY' in str(c).upper()), None)
            pop_col = next((c for c in df_d.columns if 'population' in str(c).lower()), None)
            
            for _, row in df_d.iterrows():
                raw_c = str(row[country_col])
                if raw_c == 'nan' or raw_c in ['RU', 'UAS', 'Ratio', 'n.a.', 'tbp'] or raw_c.startswith(('Disclaimer', 'Although', 'The', 'Please')):
                    continue
                
                c_name = raw_c.replace('(RU + UAS)', '').replace('(RU)', '').strip()
                
                if c_name not in countries_dict:
                    countries_dict[c_name] = {"population": None, "footnotes": [], "statistics": {}}
                
                # Assign Wikidata Population (fallback to file parameter if API missed it)
                if countries_dict[c_name]["population"] is None:
                    file_pop = row[pop_col] if pop_col and not pd.isna(row[pop_col]) else None
                    countries_dict[c_name]["population"] = dynamic_populations.get(c_name, file_pop)

                row_dict = {}
                for col in df_d.columns:
                    if col not in [country_col, 'Institution Type', pop_col]:
                        val = row[col]
                        if not pd.isna(val):
                            # Split "2010/11_total" into Year ("2010/11") and Metric ("total")
                            if "_" in col:
                                year, metric = col.split("_", 1)
                                if year not in row_dict:
                                    row_dict[year] = {}
                                row_dict[year][metric] = val
                            else:
                                row_dict[col] = val
                                
                # Assign directly as an object, removing the unnecessary array [ ]
                countries_dict[c_name]["statistics"][dataset_name] = row_dict
                
        except Exception as e:
            print(f"  -> Skipping data in {file}: {e}")

    with open("countries_parsed.json", "w", encoding="utf-8") as f:
        json.dump(countries_dict, f, indent=4, ensure_ascii=False)
    print("Successfully parsed Country data.")


if __name__ == "__main__":
    # 1. Provide the list of countries (dynamically or hardcoded based on your dataset)
    # The script looks up these exact names in Wikidata
    target_countries = [
        "Austria", "Belgium", "Bulgaria", "Czech Republic", "Denmark", "Estonia", 
        "Finland", "France", "Germany", "Greece", "Iceland", "Ireland", "Italy", 
        "Latvia", "Lithuania", "Netherlands", "Norway", "Poland", "Portugal", 
        "Romania", "Spain", "Sweden", "Switzerland", "Turkey", "UK"
    ]
    
    # 2. Fetch populations from Wikidata
    dynamic_populations = fetch_wikidata_populations(target_countries)
    
    # 3. Parse Data
    parse_members_data("Members-DATA-NO-PT.xlsx", dynamic_populations)
    parse_country_data(dynamic_populations)