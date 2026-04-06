import yaml
import json
import os

from country_codes import country_meta

def build_country(data):
    output = []
    
    for institution_type in data.get("institutions", []):
        title = institution_type.get("title", "")
        merged = {}

        for item in institution_type.get("data", []):
            name = item.get("name", "")
            departments = item.get("departments")

            if departments:
                if name not in merged:
                    merged[name] = {
                        "institution": title,
                        "name": name,
                        "departments": []
                    }
                for dept in departments:
                    link = dept.get("link", "")
                    merged[name]["departments"].append({
                        "name": dept.get("name", ""),
                        "link": link,
                        "location": ""
                    })
            else:
                link = item.get("link", "")
                output.append({
                    "institution": title,
                    "name": name,
                    "link": link,
                    "location": ""
                })

        output.extend(merged.values())
    return output

def get_country_data(input_file_path, output_dir):
    with open(input_file_path, 'r', encoding='utf-8') as input_file:
        data = yaml.safe_load(input_file)

    output_file_body = build_country(data)
    country_name = data.get("country", "unknown")
    country_code = country_meta(country_name).get("iso", country_name)

    output_file_path = os.path.join(output_dir, country_code + ".json")

    with open(output_file_path, 'w', encoding='utf-8') as output_file:
        json.dump(output_file_body, output_file, ensure_ascii=False, indent=2)
        
    print(f"Processed {input_file_path} -> {output_file_path}")
    print(f"Identified universities in {country_name} and saved to {output_file_path}")

    return output_file_path