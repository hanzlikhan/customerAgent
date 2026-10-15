"""Catalog onboarding for DukaanAI (Phase 6).

Makes real businesses onboardable: import a product catalog from a
spreadsheet (.xlsx / .csv) or from a photo of a printed rate list (OCR).

Two-stage design so the UI can preview before committing:
  parse_spreadsheet(path) -> (rows, errors)     # no DB writes
  parse_photo(path)       -> (rows, errors, raw_ocr_text)
  commit_rows(rows, business_id, source_doc) -> imported count
  import_spreadsheet(path, business_id) -> {imported, errors}
  import_photo(path, business_id)       -> {imported, errors, raw_ocr_text}

Row validation (never silently skips):
  - name_en must be non-empty
  - price must be numeric and > 0
  - unit must be non-empty
Invalid rows are collected into `errors` with row number + reason.

Honest limitation: OCR works on clean PRINTED rate lists. Handwriting
is unreliable and this module does not pretend otherwise — raw_ocr_text
is always returned so the caller can see exactly what was read.
"""

import csv
import os
import re
import shutil
import sys
from pathlib import Path

from . import db
from . import index

# ---------------------------------------------------------------------------
# Shared: validation + commit
# ---------------------------------------------------------------------------

REQUIRED_COLUMNS = ("name_en", "price", "unit")
OPTIONAL_COLUMNS = ("name_ur_roman", "category", "variants")


def _parse_variants(raw: str) -> dict:
    """Parse 'color: red, blue' style cells into the variants dict.

    The index reads variants["en"] / variants["ur"] for color lists, so a
    single 'key: value' cell is stored as {"en": value}. Kept deliberately
    simple — documented in the README column spec.
    """
    raw = (raw or "").strip()
    if not raw:
        return {}
    if ":" in raw:
        _, value = raw.split(":", 1)
        return {"en": value.strip()}
    return {"en": raw}


def validate_row(row: dict, lineno: int) -> tuple[dict | None, str | None]:
    """Return (clean_row, None) or (None, error_reason)."""
    name_en = str(row.get("name_en") or "").strip()
    if not name_en:
        return None, f"row {lineno}: name_en is empty"
    raw_price = row.get("price")
    try:
        price = float(str(raw_price).replace(",", "").strip())
    except (TypeError, ValueError):
        return None, f"row {lineno}: price '{raw_price}' is not numeric"
    if price <= 0:
        return None, f"row {lineno}: price must be > 0 (got {raw_price})"
    unit = str(row.get("unit") or "").strip()
    if not unit:
        return None, f"row {lineno}: unit is empty"
    name_ur = str(row.get("name_ur_roman") or "").strip() or name_en
    return {
        "name_en": name_en,
        "name_ur_roman": name_ur,
        "price": price,
        "unit": unit,
        "category": str(row.get("category") or "").strip(),
        "variants": _parse_variants(str(row.get("variants") or "")),
    }, None


def commit_rows(rows: list[dict], business_id: int,
                source_doc: str) -> int:
    """Insert validated rows and rebuild the vector index. Returns count."""
    for r in rows:
        db.add_catalog_item(
            business_id,
            r["name_en"],
            r["name_ur_roman"],
            r["price"],
            r["unit"],
            variants=r["variants"],
            category=r["category"] or None,
            source_doc=source_doc,
        )
    index.build_index(business_id)
    return len(rows)


# ---------------------------------------------------------------------------
# Spreadsheet import (.xlsx / .csv)
# ---------------------------------------------------------------------------

def _normalize_header(h: str) -> str:
    return re.sub(r"[^a-z]", "", str(h or "").strip().lower())


def _read_xlsx(path: Path) -> list[dict]:
    from openpyxl import load_workbook
    wb = load_workbook(path, read_only=True, data_only=True)
    ws = wb.active
    rows = list(ws.iter_rows(values_only=True))
    if not rows:
        return []
    header = [_normalize_header(h) for h in rows[0]]
    out = []
    for values in rows[1:]:
        if all(v is None or str(v).strip() == "" for v in values):
            continue  # skip blank rows silently — they carry no data
        out.append({h: v for h, v in zip(header, values) if h})
    return out


def _read_csv(path: Path) -> list[dict]:
    content = None
    for enc in ("utf-8-sig", "utf-8", "cp1252", "latin-1"):
        try:
            content = path.read_text(encoding=enc)
            break
        except UnicodeDecodeError:
            continue
    if content is None:
        content = path.read_text(encoding="utf-8", errors="replace")
    reader = csv.DictReader(content.splitlines())
    out = []
    for values in reader:
        row = {_normalize_header(k): v
               for k, v in values.items() if _normalize_header(k)}
        if all(v is None or str(v).strip() == "" for v in row.values()):
            continue
        out.append(row)
    return out


# Map normalized header -> canonical column name.
_HEADER_ALIASES = {
    "nameen": "name_en",
    "name": "name_en",
    "product": "name_en",
    "item": "name_en",
    "nameurroman": "name_ur_roman",
    "nameur": "name_ur_roman",
    "urdu": "name_ur_roman",
    "price": "price",
    "rate": "price",
    "keemat": "price",
    "unit": "unit",
    "per": "unit",
    "category": "category",
    "cat": "category",
    "variants": "variants",
    "colors": "variants",
    "rang": "variants",
}


def parse_spreadsheet(path: str | Path) -> tuple[list[dict], list[dict]]:
    """Parse without writing. Returns (valid_rows, errors)."""
    path = Path(path)
    suffix = path.suffix.lower()
    if suffix == ".xlsx":
        raw_rows = _read_xlsx(path)
    elif suffix == ".csv":
        raw_rows = _read_csv(path)
    else:
        raise ValueError(f"unsupported spreadsheet type: {suffix} "
                         "(use .xlsx or .csv)")

    valid, errors = [], []
    for i, raw in enumerate(raw_rows, start=2):  # row 1 = header
        canon = {_HEADER_ALIASES.get(k, k): v for k, v in raw.items()}
        clean, err = validate_row(canon, i)
        if err:
            errors.append({"row": i, "reason": err})
        else:
            valid.append(clean)
    return valid, errors


def import_spreadsheet(path: str | Path, business_id: int) -> dict:
    """Parse, validate, insert, rebuild index. Returns {imported, errors}."""
    rows, errors = parse_spreadsheet(path)
    imported = commit_rows(rows, business_id, source_doc=Path(path).name)
    return {"imported": imported, "errors": errors}


# ---------------------------------------------------------------------------
# Photo import (OCR of printed rate lists)
# ---------------------------------------------------------------------------

# Price = the first standalone number with 2+ digits (skips "3pc"-style
# fragments). Rate lists read "<name> <price> <unit>", e.g.
# "Premium Lawn 3450 per suit" or "Cotton - per meter - 850".
_PRICE_RE = re.compile(r"(?<![\d,])([\d,]{2,}(?:\.\d{1,2})?)(?![\d.])")
_SEP_RE = re.compile(r"\s*[-–—:|,'\"]\s*")
_UNIT_WORDS_RE = re.compile(
    r"\b(per\s*)?(met(er|re)|suit|piec?e|pcs?)\b|/\s*m\b", re.I)


def _detect_unit(text: str) -> str:
    t = " " + text.lower().replace("/", " / ") + " "
    if re.search(r"met(er|re)|\s/m\s|\sm\s", t):
        return "per meter"
    if "suit" in t:
        return "per suit"
    if re.search(r"piec|\bpc\b", t):
        return "per piece"
    return "per item"


def parse_rate_lines(text: str) -> tuple[list[dict], list[dict]]:
    """Parse OCR text lines into catalog rows. Pure function — no OCR here,
    so it is unit-testable without tesseract installed."""
    valid, errors = [], []
    for lineno, raw_line in enumerate(text.splitlines(), start=1):
        line = raw_line.strip().strip("'\"‘’“”")
        if not line:
            continue
        m = _PRICE_RE.search(line)
        if not m:
            errors.append({"row": lineno,
                           "reason": f"no price found in line: '{line}'"})
            continue
        try:
            price = float(m.group(1).replace(",", ""))
        except ValueError:
            errors.append({"row": lineno,
                           "reason": f"unparseable price in: '{line}'"})
            continue
        name_part = line[:m.start()]
        unit = _detect_unit(line[m.end():] + " " + name_part)
        # clean the name: separators -> space, drop unit words, tidy spaces
        name = _SEP_RE.sub(" ", name_part)
        name = _UNIT_WORDS_RE.sub("", name)
        name = re.sub(r"([a-zA-Z])(\d)", r"\1 \2", name)  # "Khaddar3pe"->"Khaddar 3pe"
        name = re.sub(r"\s+", " ", name).strip(" -–—:|,'\"‘’“”")
        row, err = validate_row(
            {"name_en": name, "price": price, "unit": unit}, lineno)
        if err:
            errors.append({"row": lineno, "reason": err})
        else:
            valid.append(row)
    return valid, errors


def _require_tesseract() -> None:
    if shutil.which("tesseract") is not None:
        return
    if sys.platform.startswith("win"):
        win_candidates = [
            Path(r"C:\Program Files\Tesseract-OCR\tesseract.exe"),
            Path(r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe"),
            Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "Tesseract-OCR" / "tesseract.exe",
        ]
        for cand in win_candidates:
            if cand.exists():
                import pytesseract
                pytesseract.pytesseract.tesseract_cmd = str(cand)
                return
    raise RuntimeError(
        "tesseract binary not found. Install it first:\n"
        "  Ubuntu/Debian: sudo apt-get install tesseract-ocr\n"
        "  Windows: https://github.com/UB-Mannheim/tesseract/wiki\n"
        "  macOS: brew install tesseract"
    )


def parse_photo(path: str | Path) -> tuple[list[dict], list[dict], str]:
    """OCR a rate-list photo, parse lines. Returns (rows, errors, raw_text)."""
    _require_tesseract()
    from PIL import Image
    import pytesseract

    img = Image.open(path).convert("L")  # grayscale helps OCR
    # upscale small images: tesseract likes ~300 DPI-ish input
    w, h = img.size
    if max(w, h) < 1200:
        scale = 1200 / max(w, h)
        img = img.resize((int(w * scale), int(h * scale)))
    raw_text = pytesseract.image_to_string(img)
    rows, errors = parse_rate_lines(raw_text)
    return rows, errors, raw_text


def import_photo(path: str | Path, business_id: int) -> dict:
    """OCR, parse, insert, rebuild index.
    Returns {imported, errors, raw_ocr_text}."""
    rows, errors, raw_text = parse_photo(path)
    imported = commit_rows(rows, business_id, source_doc=Path(path).name)
    return {"imported": imported, "errors": errors, "raw_ocr_text": raw_text}
