import json
import os
import time
import requests

ROR_URL = "https://api.ror.org/organizations"

# --- OVERPASS ---
# OVERPASS_URL = "https://overpass-api.de/api/interpreter"
#
# def overpass_search(name, tag="amenity", value="university"):
#     query = f"""
#     [out:json][timeout:10];
#     nwr["{tag}"="{value}"]["name"="{name}"];
#     out center;
#     """
#     try:
#         response = requests.post(
#             OVERPASS_URL,
#             data={"data": query},
#             timeout=30
#         )
#         elements = response.json().get("elements", [])
#         if elements:
#             el = elements[0]
#             lat = el.get("lat") or el.get("center", {}).get("lat")
#             lon = el.get("lon") or el.get("center", {}).get("lon")
#             return {"lat": lat, "lon": lon}
#     except requests.RequestException:
#         pass
#     return {"lat": None, "lon": None}
#
# def locate_uni(uni_name):
#     print(f"  Locating uni: {uni_name}")
#     return overpass_search(uni_name, tag="amenity", value="university")
#
# def locate_department(dept_name):
#     print(f"  Locating dept: {dept_name}")
#     location = overpass_search(dept_name, tag="amenity", value="university")
#     if location["lat"] is None:
#         location = overpass_search(dept_name, tag="building", value="university")
#     return location
# --- END OVERPASS ---

# --- NOMINATIM ---
NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
HEADERS = {"User-Agent": "uni-locator/1.0"}

def nominatim_search(query):
    time.sleep(2)
    try:
        response = requests.get(
            NOMINATIM_URL,
            params={"q": query, "format": "json", "limit": 1},
            headers=HEADERS,
            timeout=10
        )
        results = response.json()
        if results:
            return {"lat": float(results[0]["lat"]), "lon": float(results[0]["lon"])}
    except requests.RequestException:
        pass
    return {"lat": None, "lon": None}

def locate_uni(uni_name):
    print(f"  Locating uni: {uni_name}")
    return nominatim_search(uni_name)

def locate_department(dept_name, uni_name):
    print(f"  Locating dept: {dept_name}")
    location = nominatim_search(f"{dept_name} {uni_name}")
    if location["lat"] is None:
        location = nominatim_search(dept_name)
    return location
# --- END NOMINATIM ---

# --- ROR ---
# def ror_search(name):
#     try:
#         response = requests.get(
#             ROR_URL,
#             params={"query": name},
#             timeout=10
#         )
#         items = response.json().get("items", [])
#         if items:
#             addresses = items[0].get("addresses", [])
#             if addresses and addresses[0].get("lat"):
#                 return {"lat": addresses[0]["lat"], "lon": addresses[0]["lng"]}
#     except requests.RequestException:
#         pass
#     return {"lat": None, "lon": None}

# def locate_uni(uni_name):
#     print(f"  Locating uni: {uni_name}")
#     return ror_search(uni_name)

# def locate_department(dept_name, uni_name):
#     print(f"  Locating dept: {dept_name}")
#     location = ror_search(f"{dept_name} {uni_name}")
#     if location["lat"] is None:
#         location = ror_search(uni_name)
#     return location

def fill_location_data(input_file_path, output_dir):
    with open(input_file_path, 'r', encoding='utf-8') as f:
        uni_doc = json.load(f)

    for item in uni_doc:
        if "departments" in item:
            for dept in item["departments"]:
                dept["location"] = locate_department(dept["name"], item["name"])
        else:
            item["location"] = locate_uni(item["name"])

    with open(input_file_path, 'w', encoding='utf-8') as f:
        json.dump(uni_doc, f, ensure_ascii=False, indent=2)

    print(f"\nDone: {input_file_path}")

    with open(output_dir, 'a', encoding='utf-8') as f:
        f.write(f"\n{os.path.basename(input_file_path)}:\n")
        for item in uni_doc:
            if "departments" in item:
                for dept in item["departments"]:
                    if dept.get("location", {}).get("lat") is None:
                        f.write(f"  [dept]  {item['name']} > {dept['name']}\n")
            else:
                if item.get("location", {}).get("lat") is None:
                    f.write(f"  [uni]   {item['name']}\n")
