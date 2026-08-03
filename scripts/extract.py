# %%
from pathlib import Path

import fitz

path = Path(
    "/Users/nicolasthomazo/Documents/Code/ocr/data/cahier-doleances/CC_01300_190304_01358_MD_15432.pdf"
)
print("Opening PDF:", path.name)
doc = fitz.open(path)
for i, page in enumerate(doc, start=1):
    print(f"========== Page {i} ==========")
    print(page.get_text())
doc.close()
# %%
path = Path(
    "/Users/nicolasthomazo/Documents/Code/ocr/data/cahier-doleances/CC_01300_190304_01358_MD_15432.pdf"
)
print("Opening PDF:", path.name)
doc = fitz.open(path)
for i, page in enumerate(doc, start=1):
    print(f"========== Page {i} ==========")
    print(page.get_text())
doc.close()
