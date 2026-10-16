"""Extract first-page text from reference PDFs for verification (no web)."""

from __future__ import annotations

import json
from pathlib import Path

from pypdf import PdfReader

REF_DIR = Path(r"C:\Users\Pasan\OneDrive\Desktop\traffic\references")


def main() -> None:
    out: list[dict] = []
    for pdf in sorted(REF_DIR.glob("*.pdf")):
        entry: dict = {"file": pdf.name, "pages": 0, "first_page_text": "", "error": None}
        try:
            reader = PdfReader(str(pdf))
            entry["pages"] = len(reader.pages)
            if reader.pages:
                entry["first_page_text"] = (reader.pages[0].extract_text() or "")[:3500]
        except Exception as exc:  # noqa: BLE001
            entry["error"] = str(exc)
        out.append(entry)
    dest = Path(__file__).resolve().parents[1] / "docs/research_paper/reference_pdf_extracts.json"
    dest.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"Wrote {dest} ({len(out)} files)")


if __name__ == "__main__":
    main()
