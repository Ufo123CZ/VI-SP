import pandas as pd
import json
import re
import difflib
import os

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_SOURCE_DIR = os.path.join(_SCRIPT_DIR, 'source')
_OUTPUT_DIR = os.path.join(_SCRIPT_DIR, 'output')

# Configuration: Update this with your exact ETER Excel filename
ETER_EXCEL_FILE = os.path.join(_SOURCE_DIR, 'eter-export-selected-1777372360417.xlsx')
OUTPUT_FILE = os.path.join(_OUTPUT_DIR, 'eter_parsed.json')

# List all your extra country JSON files here
EXTRA_JSON_FILES = [os.path.join(_SOURCE_DIR, name) for name in ['pt.json', 'cz.json', 'de.json', 'lv.json', 'no.json']]

# Generic words that should NEVER be allowed to match as a standalone substring
GENERIC_WORDS = [
    'university', 'universität', 'universiteit', 'universiteti', 
    'college', 'academy', 'institute', 'faculty', 'department'
]

def clean_name(name):
    """Cleans university names to improve matching accuracy."""
    if not isinstance(name, str):
        return ""
    # Remove text in parentheses like "(Federated Member)"
    name = re.sub(r'\(.*?\)', '', name)
    # Remove trailing punctuation
    name = name.strip(' ,;:-')
    return name.strip().lower()

def load_target_institutions():
    """Loads and maps target universities from all JSON files."""
    targets = {}

    # 1. Load from members_parsed.json
    try:
        with open(os.path.join(_SOURCE_DIR, 'members_parsed.json'), 'r', encoding='utf-8') as f:
            members = json.load(f)
            for original_name in members.keys():
                cleaned = clean_name(original_name)
                if cleaned:
                    targets[cleaned] = original_name
    except FileNotFoundError:
        print("Warning: members_parsed.json not found.")

    # 2. Load from ie_partners.json
    try:
        with open(os.path.join(_SOURCE_DIR, 'ie_partners.json'), 'r', encoding='utf-8') as f:
            partners_data = json.load(f)
            for country in partners_data:
                for partner in country.get('partners', []):
                    uni_name = partner.get('uni_name', '')
                    if not uni_name:
                        uni_name = partner.get('dept_name', '')
                    
                    cleaned = clean_name(uni_name)
                    if cleaned:
                        targets[cleaned] = partner.get('uni_name', partner.get('dept_name', ''))
    except FileNotFoundError:
        print("Warning: ie_partners.json not found.")

    # 3. Load from the newly added country JSON files
    for filepath in EXTRA_JSON_FILES:
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                country_data = json.load(f)
                for institution in country_data:
                    uni_name = institution.get('name', '')
                    cleaned = clean_name(uni_name)
                    if cleaned:
                        targets[cleaned] = uni_name
        except FileNotFoundError:
            pass # Skip silently if not all country files exist yet
        except json.JSONDecodeError:
            print(f"Warning: {filepath} is not valid JSON. Skipping.")

    return targets

def find_match(eter_local, eter_english, targets_map):
    """Attempts to strictly match an ETER record to our target dictionary."""
    eter_l = clean_name(eter_local)
    eter_e = clean_name(eter_english)
    target_keys = list(targets_map.keys())

    if not eter_l and not eter_e:
        return None

    # Strategy 1: Exact Match (Fastest and safest)
    if eter_l in targets_map: return targets_map[eter_l]
    if eter_e in targets_map: return targets_map[eter_e]

    # Strategy 2: Safe Substring Match
    for t_key in target_keys:
        if t_key in GENERIC_WORDS:
            continue # Don't let a generic word accidentally trigger a match
            
        # If the target name is entirely inside the ETER name (e.g. "TU Wien" inside "TU Wien Faculty of IT")
        if len(t_key) > 5:
            if eter_e and t_key in eter_e: return targets_map[t_key]
            if eter_l and t_key in eter_l: return targets_map[t_key]
            
        # If the ETER name is entirely inside the target name (must be a substantial string)
        if eter_e and len(eter_e) > 10 and eter_e in t_key: return targets_map[t_key]
        if eter_l and len(eter_l) > 10 and eter_l in t_key: return targets_map[t_key]

    # Strategy 3: VERY Strict Fuzzy Match (Cutoff increased to 0.95 to stop Milan/Tirana overlaps)
    if eter_e:
        matches_e = difflib.get_close_matches(eter_e, target_keys, n=1, cutoff=0.95)
        if matches_e: return targets_map[matches_e[0]]
    
    if eter_l:
        matches_l = difflib.get_close_matches(eter_l, target_keys, n=1, cutoff=0.95)
        if matches_l: return targets_map[matches_l[0]]

    return None

def parse_numeric(val):
    """ETER uses 'm', 'c', 'x', 'a' for missing/confidential data. Returns 0 if not a number."""
    try:
        return int(float(val))
    except (ValueError, TypeError):
        return 0

def main():
    print("Loading target universities from all JSON files...")
    targets_map = load_target_institutions()
    print(f"Tracking {len(targets_map)} unique target institutions.")

    print(f"Reading ETER Excel file: {ETER_EXCEL_FILE}...")
    try:
        df = pd.read_excel(ETER_EXCEL_FILE, dtype=str)
    except Exception as e:
        print(f"Error loading Excel file: {e}")
        return

    results = {}
    matched_count = 0

    print("Matching ETER records strictly...")
    for _, row in df.iterrows():
        local_name = row.get('BAS.INSTNAME', '')
        english_name = row.get('BAS.INSTNAMEENGL', '')
        
        # Try to find a safe match
        matched_target = find_match(local_name, english_name, targets_map)
        
        if matched_target:
            year = row.get('BAS.REFYEAR', 'Unknown')
            
            # Initialize the university if it doesn't exist
            if matched_target not in results:
                matched_count += 1
                results[matched_target] = {
                    "eter_id": row.get('BAS.ETERID', ''),
                    "name_local": local_name,
                    "name_english": english_name,
                    "country": row.get('BAS.COUNTRY', ''),
                    "city": row.get('GEO.CITY', ''),
                    "coordinates": {
                        "lat": row.get('GEO.COORDLAT'),
                        "lon": row.get('GEO.COORDLON')
                    },
                    "informatics_data": {}
                }

            # Add the yearly data
            results[matched_target]["informatics_data"][year] = {
                "enrolled_bsc": parse_numeric(row.get('STUD.ISCED6FOE06')),
                "enrolled_msc": parse_numeric(row.get('STUD.ISCED7FOE06')),
                "graduates_bsc": parse_numeric(row.get('GRAD.ISCED6FOE06')),
                "graduates_msc": parse_numeric(row.get('GRAD.ISCED7FOE06'))
            }

    os.makedirs(_OUTPUT_DIR, exist_ok=True)
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=4, ensure_ascii=False)

    print(f"\nDone! Successfully and safely matched {matched_count} institutions.")
    print(f"Data saved to {OUTPUT_FILE}")

if __name__ == "__main__":
    main()