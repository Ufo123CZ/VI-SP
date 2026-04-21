import json
import os
import time
import requests
import pycountry
from lxml import etree

URL = "https://www.informatics-europe.org/join-us/current-members.html"

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
NOMINATIM_HEADERS = {"User-Agent": "ie-uni-crawler/1.0"}

# ---------------------------------------------------------------------------
# XPath selectors
# ---------------------------------------------------------------------------

XPATH_GROUP_LI   = '//*[@id="workinggroups"]/li'
XPATH_H3         = './h3'
XPATH_PARTNER_UL = './following-sibling::ul[1]/li'
XPATH_ANCHOR     = './a'

# ---------------------------------------------------------------------------


def get_country_code(name: str) -> str:
    name = name.strip()
    try:
        return pycountry.countries.lookup(name).alpha_2
    except LookupError:
        pass
    try:
        return pycountry.countries.search_fuzzy(name)[0].alpha_2
    except (LookupError, IndexError):
        return ""


_geo_cache: dict[str, tuple[float, float] | None] = {}


def geocode(uni_name: str, country: str) -> tuple[float, float] | None:
    """Return (lat, lon) for a university via Nominatim, or None if not found."""
    query = f"{uni_name}, {country}"
    if query in _geo_cache:
        return _geo_cache[query]

    try:
        resp = requests.get(
            NOMINATIM_URL,
            params={"q": query, "format": "json", "limit": 1},
            headers=NOMINATIM_HEADERS,
            timeout=10,
        )
        resp.raise_for_status()
        results = resp.json()
        coords = (float(results[0]["lat"]), float(results[0]["lon"])) if results else None
    except Exception:
        coords = None

    _geo_cache[query] = coords
    time.sleep(1)  # Nominatim requires max 1 req/s
    return coords


def fetch_tree() -> etree._Element:
    response = requests.get(URL, timeout=15)
    response.raise_for_status()
    parser = etree.HTMLParser(encoding=response.encoding or "utf-8")
    return etree.fromstring(response.content, parser)


def crawl() -> list[dict]:
    tree = fetch_tree()

    group_items: list[etree._Element] = tree.xpath(XPATH_GROUP_LI)
    if not group_items:
        raise RuntimeError(
            f"XPath '{XPATH_GROUP_LI}' matched 0 elements — "
            "the site markup may have changed."
        )

    results: list[dict] = []

    for group_li in group_items:
        for h3 in group_li.xpath(XPATH_H3):
            country_name = "".join(h3.itertext()).strip()
            if not country_name:
                continue

            country_code = get_country_code(country_name).lower()

            partners: list[dict] = []
            for partner_li in h3.xpath(XPATH_PARTNER_UL):
                raw_texts = [t.strip() for t in partner_li.xpath("text()") if t.strip()]
                uni_name  = " ".join(raw_texts)

                anchors: list[etree._Element] = partner_li.xpath(XPATH_ANCHOR)
                if anchors:
                    a         = anchors[0]
                    dept_name = "".join(a.itertext()).strip()
                    link      = a.get("href", "")
                    if link.startswith("/"):
                        link = "https://www.informatics-europe.org" + link
                else:
                    dept_name = ""
                    link      = ""

                if not (uni_name or dept_name):
                    continue

                print(f"  Geocoding: {uni_name or dept_name} ({country_name})")
                coords = geocode(uni_name or dept_name, country_name)

                partners.append({
                    "uni_name":  uni_name,
                    "dept_name": dept_name,
                    "link":      link,
                    "lat":       coords[0] if coords else None,
                    "lon":       coords[1] if coords else None,
                })

            results.append({
                "country":      country_name,
                "country_code": country_code,
                "partners":     partners,
            })

    return results

def crawl_and_find(output_path: str):
    data = crawl()
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"Saved {len(data)} countries → {output_path}")
