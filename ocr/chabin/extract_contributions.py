#!/usr/bin/env python3
# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "pdfplumber",
# ]
# ///
"""Extract individual contributions from the cahiers de doléances PDFs (Chabin edition).

Each PDF starts with a few introduction pages, then lists the contributions.
A contribution is introduced by a grey title line (e.g. "1. Manuscrit ...") and
terminated by a line of underscores.
"""

import argparse
import json
import os
import re
from pathlib import Path

import pdfplumber

# Répertoire des données (gitignoré) : `data/` à la racine du dépôt par défaut.
DATA_DIR = Path(os.environ.get("CAHIERS_DATA_DIR",
                               Path(__file__).resolve().parents[2] / "data"))

DEFAULT_CAHIERS_JSON = str(DATA_DIR / "cahiers-chabin.json")
DEFAULT_CHABIN_PDF_DIR = str(DATA_DIR / "cahiers_chabin-pdfs")
DEFAULT_RAW_CAHIER_PDFS_DIR = str(DATA_DIR / "cahiers")
DEFAULT_OUTPUT = str(DATA_DIR / "cahiers_chabin-extraction.json")


REF_GREY = (0.463, 0.443, 0.443)
V_MARGIN = 60  # used to remove header and footer
SEPARATORS = ["_" * 4, "_" * 5]
FIRST_CONTRIB_RE = re.compile(r"1\. (?:Manuscrit|Dactylo|Tract|Mail)")


def is_grey(color):
    return all(c == c_ref for c, c_ref in zip(color, REF_GREY))


def is_line_grey(line):
    return any(is_grey(c["stroking_color"]) for c in line["chars"])


def count_intro_pages(pdf):
    """Number of leading pages before the first contribution."""
    for num_intro_pages, page in enumerate(pdf.pages):
        text = page.extract_text()
        if FIRST_CONTRIB_RE.search(text):
            break
    return max(1, num_intro_pages)


def extract_contributions(pdf_file):
    with pdfplumber.open(pdf_file) as pdf:
        num_intro_pages = count_intro_pages(pdf)

        lines = []
        for page in pdf.pages[num_intro_pages:]:
            cropped_page = page.crop((0, V_MARGIN, page.width, page.height - V_MARGIN))
            lines.extend(cropped_page.extract_text_lines())

    contributions = []
    text, title = [], []
    for line in lines:
        if line["text"] not in SEPARATORS:
            # Normal line: grey lines are titles, black ones are the contribution
            if is_line_grey(line):
                title.append(line["text"])
            else:
                text.append(line["text"])
        else:
            # End of group/contribution
            if title:
                contributions.append({"title": " ".join(title), "text": "\n".join(text)})
            text, title = [], []

    if title:
        contributions.append({"title": " ".join(title), "text": "\n".join(text)})

    return [c for c in contributions if c["text"]]


def process_cahiers(cahiers_json, chabin_pdf_dir, raw_pdf_dir, output):
    city_keys = ["insee", "commune", "habitants"]
    with open(cahiers_json, encoding="utf-8") as f:
        cahiers_list = json.load(f)

    dep17_raw_pdf_dir = os.path.join(raw_pdf_dir, "BnF_GDN_17_PDF/CC/")
    raw_pdf_list = [os.path.join("BnF_GDN_17_PDF/CC", f)
                    for f in os.listdir(dep17_raw_pdf_dir)]

    results = []
    for i, cahier in enumerate(cahiers_list):
        print(f"Processing cahier {i+1}/{len(cahiers_list)}", end="\r")
        if not cahier["pdf_links"]:
            print(f'Pas de pdfs: {cahier["commune"]}')
            results.append(None)
            continue

        contributions = []
        pdf_files = []
        for pdf_url in cahier["pdf_links"]:
            # Stocké en relatif (nom de fichier dans chabin_pdf_dir), comme pdf_files.
            pdf_file = os.path.basename(pdf_url)
            pdf_files.append(pdf_file)
            contributions.extend(
                extract_contributions(os.path.join(chabin_pdf_dir, pdf_file)))

        num_contrib = cahier["contributions"]
        results.append({
            "chabin_pdf_files": pdf_files,
            "num_contrib": num_contrib,
            "contributions": contributions,
            "found_num_contrib": len(contributions),
            "city": {city_key: cahier[city_key] for city_key in city_keys},
            "pdf_files": find_pdf_files(cahier["insee"], raw_pdf_list)
        })

        if len(contributions) != num_contrib:
            print(f"{i} {pdf_files[-1]}: attendu {num_contrib}, trouvé {len(contributions)}")

    try:
        with open(output, "w") as f:
            json.dump(results, f, indent=2)
    except Exception:
        print(results)

    total = sum(r["found_num_contrib"] for r in results if r)
    print(f"Exported {total} contributions for {len(results)} cahiers to {output}")


def find_pdf_files(insee_num, raw_pdf_list):
    matching_pdfs = [f for f in raw_pdf_list
                    if os.path.basename(f).split("_")[3] == insee_num]
    if not len(matching_pdfs):
        print(f"No matching pdf for {insee_num}")
    if len(matching_pdfs) > 1:
        print(f"Multiple match: {matching_pdfs}")
    return matching_pdfs


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cahiers_json", default=DEFAULT_CAHIERS_JSON,
                        help="JSON listing the cahiers (produced by extract_cahiers_chabin.py)")
    parser.add_argument("--pdf_dir", default=DEFAULT_CHABIN_PDF_DIR,
                        help="Directory holding the chabin PDFs")
    parser.add_argument("--raw_pdf_dir", default=DEFAULT_RAW_CAHIER_PDFS_DIR,
                        help="Directory holding the raw cahier PDFs")
    parser.add_argument("--output", default=DEFAULT_OUTPUT, help="Output JSON file")
    args = parser.parse_args()

    process_cahiers(args.cahiers_json, args.pdf_dir, args.raw_pdf_dir, args.output)


if __name__ == "__main__":
    main()
