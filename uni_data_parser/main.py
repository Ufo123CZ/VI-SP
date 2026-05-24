import pandas as pd
import json
import glob
import requests
import os

def fetch_wikidata_populations(country_names):
    print("Fetching updated populations from Wikidata...")
    name_mapping = {"UK": "United Kingdom", "Czech Republic": "Czech Republic"}
    values_str = " ".join([f'"{name_mapping.get(c, c)}"@en' for c in country_names])
    
    query = f"""
    SELECT ?countryLabel (MAX(?population) AS ?pop) WHERE {{
      VALUES ?countryLabel {{ {values_str} }}
      ?country rdfs:label ?countryLabel .
      ?country wdt:P1082 ?population .
    }} GROUP BY ?countryLabel
    """
    
    url = 'https://query.wikidata.org/sparql'
    headers = {
        'User-Agent': 'InformaticsDataParser/1.0 (Contact: your_email@example.com)',
        'Accept': 'application/json'
    }
    
    try:
        response = requests.get(url, params={'format': 'json', 'query': query}, headers=headers)
        response.raise_for_status()
        data = response.json()
        pop_dict = {}
        for item in data['results']['bindings']:
            label = item['countryLabel']['value']
            reverse_map = {v: k for k, v in name_mapping.items()}
            dataset_name = reverse_map.get(label, label)
            pop_dict[dataset_name] = int(item['pop']['value'])
        print(f"Successfully fetched {len(pop_dict)} populations from Wikidata.")
        return pop_dict
    except Exception as e:
        print(f"Failed to fetch Wikidata populations: {e}")
        return {}


def parse_members_data(file_path, dynamic_populations, output_dir):
    # Using read_excel because the file is an .xlsx
    df = pd.read_excel(file_path, header=[1, 2])
    
    df.columns = [f"{col[0]}_{col[1]}" if 'Unnamed' not in col[1] else col[0] for col in df.columns]
    
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
        current_pop = dynamic_populations.get(c_name, row.get('population_old'))
        
        if uni not in members_json:
            members_json[uni] = {
                "country": c_name,
                "country_population": current_pop,
                "institution_type": row.get('institution_type'),
                "data": []
            }
        
        # --- RECALCULATION LOGIC FOR MEMBERS ---
        total = row.get('total')
        female = row.get('female')
        calc_ratio = row.get('ratio_per_1m')
        calc_female_pct = row.get('female_percentage')
        
        try:
            t_num = float(total)
            if current_pop and current_pop > 0:
                calc_ratio = (t_num / current_pop) * 1000000
                
            if not pd.isna(female):
                f_num = float(female)
                if t_num > 0:
                    calc_female_pct = f_num / t_num
        except (ValueError, TypeError):
            pass # Fails safely if total/female is "tbp", "n.a." or blank
        
        stat_entry = {
            "level": row.get('level'),
            "category": row.get('statistics'),
            "stats_2023_2024": {
                "total": total if not pd.isna(total) else None,
                "female": female if not pd.isna(female) else None,
                "female_percentage": calc_female_pct,
                "ratio_per_1m": calc_ratio,
                "programmes": row.get('programmes')
            }
        }
        members_json[uni]["data"].append(stat_entry)
        
    os.makedirs(output_dir, exist_ok=True)
    with open(os.path.join(output_dir, "members_parsed.json"), "w", encoding="utf-8") as f:
        json.dump(members_json, f, indent=4, ensure_ascii=False)
    print("Successfully parsed Members data.")


def parse_country_data(dynamic_populations, data_dir, output_dir):
    excel_files = glob.glob(os.path.join(data_dir, "student-statistics", "*_RU-UAS.xlsx"))
    if not excel_files:
        print("Warning: No files ending in '_RU-UAS.xlsx' were found in this directory!")
        return

    countries_dict = {}
    
    for file in excel_files:
        dataset_name = os.path.basename(file)
        print(f"Processing {file}...")
        
        # 1. Parse Footnotes
        try:
            df_fn_raw = pd.read_excel(file, sheet_name='footnotes', header=None)
            start_idx = next((i for i, row in df_fn_raw.iterrows() if str(row[0]).lower().startswith('country')), 0)
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
            pass

        # 2. Parse Statistical Data
        try:
            df_d_raw = pd.read_excel(file, sheet_name='data', header=None)
            start_idx = next((i for i, row in df_d_raw.iterrows() if str(row[0]).upper().startswith('COUNTRY')), 0)
            df_d = pd.read_excel(file, sheet_name='data', skiprows=start_idx, header=[0, 1])
            
            new_cols = []
            last_valid_c1 = ""
            for c1, c2 in df_d.columns:
                c1, c2 = str(c1), str(c2)
                if not c1.startswith('Unnamed'): last_valid_c1 = c1
                if 'Unnamed' in c2: new_cols.append(last_valid_c1)
                elif last_valid_c1.upper() in ['COUNTRY', 'INSTITUTION TYPE', 'YEAR'] or 'Unnamed' in last_valid_c1: new_cols.append(c2)
                else: new_cols.append(f"{last_valid_c1}_{c2}")
                    
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
                
                if countries_dict[c_name]["population"] is None:
                    file_pop = row[pop_col] if pop_col and not pd.isna(row[pop_col]) else None
                    countries_dict[c_name]["population"] = dynamic_populations.get(c_name, file_pop)

                row_dict = {}
                current_pop = countries_dict[c_name]["population"]
                
                # Build the Year-nested object
                for col in df_d.columns:
                    if col not in [country_col, 'Institution Type', pop_col]:
                        val = row[col]
                        if not pd.isna(val):
                            if "_" in col:
                                year, metric = col.split("_", 1)
                                if year not in row_dict:
                                    row_dict[year] = {}
                                row_dict[year][metric] = val
                            else:
                                row_dict[col] = val
                
                # --- RECALCULATION LOGIC FOR COUNTRY DATA ---
                for year, metrics in row_dict.items():
                    if isinstance(metrics, dict):
                        total = metrics.get('total')
                        female = metrics.get('female')
                        
                        try:
                            t_num = float(total)
                            
                            # Recalculate Ratio per 1 Million
                            if current_pop and current_pop > 0 and 'ratio per 1M' in metrics:
                                metrics['ratio per 1M'] = (t_num / current_pop) * 1000000
                            
                            # Recalculate Female Percentage
                            if female is not None and 'female %' in metrics:
                                f_num = float(female)
                                if t_num > 0:
                                    metrics['female %'] = f_num / t_num
                                    
                        except (ValueError, TypeError):
                            pass # Fails safely if total/female is 'tbp' or 'n.a.'

                countries_dict[c_name]["statistics"][dataset_name] = row_dict
                
        except Exception as e:
            print(f"  -> Skipping data in {file}: {e}")

    os.makedirs(output_dir, exist_ok=True)
    with open(os.path.join(output_dir, "countries_parsed.json"), "w", encoding="utf-8") as f:
        json.dump(countries_dict, f, indent=4, ensure_ascii=False)
    print("Successfully parsed Country data.")


if __name__ == "__main__":
    script_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(script_dir, "..", "data")

    target_countries = [
        "Austria", "Belgium", "Bulgaria", "Czech Republic", "Denmark", "Estonia",
        "Finland", "France", "Germany", "Greece", "Iceland", "Ireland", "Italy",
        "Latvia", "Lithuania", "Netherlands", "Norway", "Poland", "Portugal",
        "Romania", "Spain", "Sweden", "Switzerland", "Turkey", "UK"
    ]

    output_dir = os.path.join(script_dir, "output")

    dynamic_populations = fetch_wikidata_populations(target_countries)
    parse_members_data(os.path.join(data_dir, "Members-DATA-NO-PT.xlsx"), dynamic_populations, output_dir)
    parse_country_data(dynamic_populations, data_dir, output_dir)