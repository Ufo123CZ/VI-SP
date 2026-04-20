import os
import json
import requests
import pycountry
from lxml import etree

URL = "https://www.informatics-europe.org/join-us/current-members.html"

# ---------------------------------------------------------------------------
# XPath selectors
# ---------------------------------------------------------------------------

# All <li> blocks under #workinggroups — each block groups one or more countries
XPATH_GROUP_LI = '//*[@id="workinggroups"]/li'

# Inside a group <li>: every <h3> is a country name
XPATH_H3 = './h3'

# For a given <h3>: the immediately following <ul> sibling holds that country's partners
XPATH_PARTNER_UL = './following-sibling::ul[1]/li'

# Inside a partner <li>: the <a> tag with dept name + link
XPATH_ANCHOR = './a'

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
        headings: list[etree._Element] = group_li.xpath(XPATH_H3)

        for h3 in headings:
            country_name = "".join(h3.itertext()).strip()
            if not country_name:
                continue

            country_code = get_country_code(country_name).lower()

            partners: list[dict] = []
            for partner_li in h3.xpath(XPATH_PARTNER_UL):
                # University name: direct text inside the <li> (before/after the <a>)
                raw_texts = [t.strip() for t in partner_li.xpath('text()') if t.strip()]
                uni_name = " ".join(raw_texts)

                anchors: list[etree._Element] = partner_li.xpath(XPATH_ANCHOR)
                if anchors:
                    a = anchors[0]
                    dept_name = "".join(a.itertext()).strip()
                    link = a.get("href", "")
                    if link.startswith("/"):
                        link = "https://www.informatics-europe.org" + link
                else:
                    dept_name = ""
                    link = ""

                if uni_name or dept_name:
                    partners.append({
                        "uni_name": uni_name,
                        "dept_name": dept_name,
                        "link": link,
                    })

            results.append({
                "country": country_name,
                "country_code": country_code,
                "partners": partners,
            })

    return results


def main(output_path: str):
    data = crawl()
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"Saved {len(data)} countries → {output_path}")


if __name__ == "__main__":
    import sys
    CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
    OUTPUT_DIR = os.path.join(CURRENT_DIR, "output")
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    if "--debug" in sys.argv:
        # Print raw text of each h3 and its partner count for quick verification
        tree = fetch_tree()
        for i, group_li in enumerate(tree.xpath(XPATH_GROUP_LI), 1):
            for h3 in group_li.xpath(XPATH_H3):
                country = "".join(h3.itertext()).strip()
                partner_count = len(h3.xpath(XPATH_PARTNER_UL))
                print(f"[group {i}] {country} — {partner_count} partners")
    else:
        OUTPUT_PATH = os.path.join(OUTPUT_DIR, "ie_members.json")
        main(OUTPUT_PATH)
