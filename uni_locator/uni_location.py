import json
import os
import time
import requests

from country_codes import country_meta

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
HEADERS = {"User-Agent": "uni-locator/1.0"}

def _nominatim_fetch(query, country_code=None):
    """Returns raw list of results, hard-filtered to country if specified."""
    time.sleep(2)
    params = {"q": query, "format": "json", "limit": 5, "addressdetails": 1}
    if country_code:
        params["countrycodes"] = country_code
    try:
        response = requests.get(NOMINATIM_URL, params=params, headers=HEADERS, timeout=10)
        results = response.json()
        if country_code:
            results = [r for r in results
                       if r.get("address", {}).get("country_code", "").lower() == country_code.lower()]
        return results
    except requests.RequestException:
        return []

def _city_from_uni(uni_name):
    """Extract city from uni name, e.g. 'v Plzni' → 'Plzeň'."""
    _LOCATIVE = {
        "Praze": "Praha", "Brně": "Brno", "Plzni": "Plzeň",
        "Ostravě": "Ostrava", "Olomouci": "Olomouc", "Liberci": "Liberec",
        "Zlíně": "Zlín", "Jihlavě": "Jihlava", "Opavě": "Opava",
    }
    import re
    m = re.search(r'\bv\s+(\w+)', uni_name)
    if m:
        return _LOCATIVE.get(m.group(1), m.group(1))
    return None

def _to_location(result):
    return {"lat": float(result["lat"]), "lon": float(result["lon"])}

def locate_uni(uni_name, country_code=None):
    print(f"  Locating uni: {uni_name}")
    results = _nominatim_fetch(uni_name, country_code)
    if results:
        print(f"    {results[0]['lat']}, {results[0]['lon']}")
        return _to_location(results[0])
    print("    No results found")
    return {"lat": None, "lon": None}

def locate_department(dept_name, uni_name, country_code=None):
    print(f"  Locating dept: {dept_name} > {uni_name}")
    city = _city_from_uni(uni_name)

    # Step 1: dept + city (pins to correct city)
    if city:
        results = _nominatim_fetch(f"{dept_name} {city}", country_code)
        if results:
            print(f"    Matched via dept+city: {results[0]['display_name']}")
            print(f"    {results[0]['lat']}, {results[0]['lon']}")
            return _to_location(results[0])

    # Step 2: dept + full uni name (more specific, avoids same-name depts in other cities/countries)
    results = _nominatim_fetch(f"{dept_name} {uni_name}", country_code)
    if results:
        print(f"    Matched via dept+uni: {results[0]['display_name']}")
        print(f"    {results[0]['lat']}, {results[0]['lon']}")
        return _to_location(results[0])

    # Step 3: fallback to uni coords
    print("    Falling back to uni location")
    return locate_uni(uni_name, country_code)

def fill_location_data(input_file_path, no_location_output_path):
    with open(input_file_path, 'r', encoding='utf-8') as f:
        uni_doc = json.load(f)

    iso = os.path.splitext(os.path.basename(input_file_path))[0]  # e.g. "cz" from "output/cz.json"
    print(f"\nProcessing {input_file_path} (country code: {iso})")

    for item in uni_doc:
        if "departments" in item:
            for dept in item["departments"]:
                dept["location"] = locate_department(dept["name"], item["name"], iso)
        else:
            item["location"] = locate_uni(item["name"], iso)


    with open(input_file_path, 'w', encoding='utf-8') as f:
        json.dump(uni_doc, f, ensure_ascii=False, indent=2)

    print(f"\nDone: {input_file_path}")

    with open(no_location_output_path, 'a', encoding='utf-8') as f:
        f.write(f"\n{os.path.basename(input_file_path)}:\n")
        for item in uni_doc:
            if "departments" in item:
                for dept in item["departments"]:
                    if dept.get("location", {}).get("lat") is None:
                        f.write(f"  [dept]  {item['name']} > {dept['name']}\n")
            else:
                if item.get("location", {}).get("lat") is None:
                    f.write(f"  [uni]   {item['name']}\n")