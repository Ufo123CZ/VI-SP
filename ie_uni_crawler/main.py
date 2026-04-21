import os

from ie_crawler import crawl_and_find

if __name__ == "__main__":
    CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
    OUTPUT_DIR = os.path.join(CURRENT_DIR, "output")
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    output_path = os.path.join(OUTPUT_DIR, "ie_partners.json")
    crawl_and_find(output_path)