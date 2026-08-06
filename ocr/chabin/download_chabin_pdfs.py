#!/usr/bin/env python3
"""Extract cahiers de doléances table data and PDF links, export as JSON."""

import json
import os
import re
import time
import urllib.request
from html import unescape
from pathlib import Path

# Répertoire des données (gitignoré) : `data/` à la racine du dépôt par défaut.
DATA_DIR = Path(os.environ.get("CAHIERS_DATA_DIR",
                               Path(__file__).resolve().parents[2] / "data"))

DEFAULT_CAHIERS_JSON = str(DATA_DIR / "cahiers-chabin.json")
DEFAULT_CHABIN_PDF_DIR = str(DATA_DIR / "cahiers_chabin-pdfs")


def parse_int(text):
    digits = re.sub(r"\D", "", text)
    return int(digits) if digits else None


def get_urls(url, output):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req) as response:
        page = response.read().decode("utf-8")

    # Find the table body rows
    tbody_match = re.search(r"<tbody>(.*?)</tbody>", page, re.DOTALL)
    if not tbody_match:
        raise ValueError("Could not find table body")

    rows = re.findall(r"<tr[^>]*>(.*?)</tr>", tbody_match.group(1), re.DOTALL)

    results = []
    for row in rows:
        cells = re.findall(r"<td[^>]*>(.*?)</td>", row, re.DOTALL)
        if len(cells) < 6:
            continue

        def cell_text(c):
            return unescape(re.sub(r"<[^>]+>", "", c).strip())

        # Commune cell may contain one or more <a href="...pdf"> links
        commune_cell = cells[2]
        pdf_links = re.findall(r'href="([^"]+\.pdf)"', commune_cell)

        insee = cell_text(cells[0])
        if not re.match(r"^\d+$", insee):
            continue  # skip header or totals rows

        entry = {
            "insee": insee,
            "intercommunalite": cell_text(cells[1]),
            "commune": cell_text(commune_cell),
            "habitants": parse_int(cell_text(cells[3])),
            "contributions": parse_int(cell_text(cells[4])),
            "mots": parse_int(cell_text(cells[5])),
            "pdf_links": pdf_links,
            "pdf_file": [os.path.basename(link) for link in pdf_links]
        }
        results.append(entry)

    results = correct_results(results)

    output_dir = os.path.dirname(output)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
    with open(output, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"Exported {len(results)} entries to {output}")


def correct_results(results):
    pdfs_la_rochelle = [
            "https://www.marieannechabin.fr/wp-content/uploads/2025/04/Cahier-de-doleances-de-La-Rochelle-1sur5-transcription.pdf",
            "https://www.marieannechabin.fr/wp-content/uploads/2025/04/Cahier-de-doleances-de-La-Rochelle-2sur5-transcription.pdf",
            "https://www.marieannechabin.fr/wp-content/uploads/2025/04/Cahier-de-doleances-de-La-Rochelle-3sur5-transcription.pdf",
            "https://www.marieannechabin.fr/wp-content/uploads/2025/04/Cahier-de-doleances-de-La-Rochelle-4sur5-transcription.pdf",
            "https://www.marieannechabin.fr/wp-content/uploads/2025/04/Cahier-de-doleances-de-La-Rochelle-5sur5-transcription.pdf"
    ]
    corrections = {
        "17056": {"contributions": 8},
        "17093": {"contributions": 27},
        "17337": {"contributions": 17},
        "17418": {"contributions": 1},
        "17485": {"contributions": 4},
        "17300": {"pdf_links": pdfs_la_rochelle,
                  "pdf_file": [os.path.basename(link) for link in pdfs_la_rochelle]
        }
    }
    for res in results:
        if res["insee"] in corrections:
            for k, v in corrections[res["insee"]].items():
                res[k] = v
    return results


def download_cahiers(json_list, data_dir):
    os.makedirs(data_dir, exist_ok=True)

    with open(json_list, encoding="utf-8") as f:
        entries = json.load(f)

    all_links = [link for entry in entries for link in entry["pdf_links"]]

    for i, pdf_url in enumerate(all_links):
        filename = os.path.join(data_dir, pdf_url.split("/")[-1])
        if os.path.exists(filename):
            print(f"Already exists, skipping: {filename}")
            continue

        print(f"Downloading ({i + 1}/{len(all_links)}): {pdf_url}")
        req = urllib.request.Request(pdf_url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req) as response, open(filename, "wb") as f:
            f.write(response.read())

        if i < len(all_links) - 1:
            time.sleep(5)


if __name__ == "__main__":
    URL = "https://www.marieannechabin.fr/edition-de-cahiers-doleances-2019/"

    get_urls(URL, DEFAULT_CAHIERS_JSON)

    download_cahiers(DEFAULT_CAHIERS_JSON, DEFAULT_CHABIN_PDF_DIR)
