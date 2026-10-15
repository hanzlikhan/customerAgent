# PHASE 6 REPORT — Catalog Onboarding

**Date:** 2026-10-14 · **Status:** ✅ COMPLETE (all verifications passed)
**Repo:** `~/workspace/dukaanai/`

## What was built

| File | Purpose |
|---|---|
| `dukaanai/onboarding.py` | Two-stage import: `parse_*` (preview, no writes) + `commit_rows` (insert + index rebuild). `import_spreadsheet` / `import_photo` one-shot wrappers |
| `app.py` (Tab 3 "📦 Catalog") | File uploader → parsed preview table + row errors → Import button → confirmation + live retrieval check |
| `data/catalog_template.xlsx` | 3 example rows + bold header |
| `requirements.txt` | Added `pytesseract`, `pillow` |
| `README.md` | New "Catalog onboarding" section: column spec, aliases, validation rules, OCR limitations |

**Spreadsheet column spec** (case-insensitive, aliases accepted):
`name_en` (req; aliases: name, product, item), `name_ur_roman` (opt, falls
back to EN; aliases: urdu), `price` (req, numeric > 0; aliases: rate,
keemat), `unit` (req; alias: per), `category` (opt), `variants` (opt,
`"color: red, blue"` → `{"en": "red, blue"}`; aliases: colors, rang).

**Photo OCR:** tesseract 5.3.4 reads printed rate-list lines shaped
`<name> <price> <unit>`; raw OCR text always surfaced to the caller/UI.

## Verification results (all real runs)

### 1. Spreadsheet import — 5/6 rows, 1 correctly rejected ✅
Test file: 6 rows (5 valid incl. 1 Roman-Urdu name + blank-UR fallback,
1 invalid: price = -100).
- `imported: 5`, `errors: [{"row": 7, "reason": "row 7: price must be > 0 (got -100)"}]`
- DB confirmed 5 rows; variants parsed (`{"en": "red, blue"}`); blank
  `name_ur_roman` fell back to `name_en` ✅
- Live retrieval: `"Test Velvet price"` → correct chunk, similarity 0.7561 ✅

### 2. CSV import ✅
2 rows (1 valid, 1 `price=abc`): valid parsed, invalid rejected with
`"row 3: price 'abc' is not numeric"`.

### 3. Photo OCR import — 5/5 lines parsed ✅
Test: PIL-generated image, 5 clean printed lines.
Raw OCR text (honest, as read):
```
Premium Lawn 3450 per suit
Cotton - per meter-850
Khaddar3pe 1200 persuit
‘Wash n Wear 950 /m
Silk Fancy, 5200 per meter
```
Parsed result — all 5 correct:
| Name | Price | Unit |
|---|---|---|
| Premium Lawn | 3450 | per suit |
| Cotton | 850 | per meter |
| Khaddar 3pe | 1200 | per suit |
| Wash n Wear | 950 | per meter |
| Silk Fancy | 5200 | per meter |

Note: the first implementation only found prices at end-of-line and
parsed **1/5** — a genuine parser bug caught by this test, fixed by
finding the first standalone number and tolerating OCR artifacts
(missing spaces, stray quotes, `/m`).

### 4. Regression ✅
- `py_compile` clean on `onboarding.py`, `app.py`
- Streamlit headless boot: `/_stcore/health` → **HTTP 200** (Tab 3 included)
- Test businesses + their Chroma collections removed afterwards —
  repo left pristine (only `business_1` remains)

## Honest build notes & limitations

1. **Tesseract install saga:** `apt-get update` hung on a dead mirror, so
   tesseract 5.3.4 + libtesseract5 + eng/osd data were installed via
   direct `.deb` downloads from archive.ubuntu.com plus a manually
   fetched `libgif7`. Works. On Hanzla's Windows machine: install from
   https://github.com/UB-Mannheim/tesseract/wiki (documented in the
   error message the code raises when the binary is absent).
2. **Handwriting is out of scope** — stated in the module docstring, the
   UI caption, and the README. Printed lists only.
3. **OCR artifacts are real** (`Khaddar3pe`, `persuit`, curly quotes):
   the parser tolerates common ones, and the UI preview + raw-OCR
   expander exist precisely so the owner catches what it cannot.
4. **Price heuristic:** first standalone number with 2+ digits. A price
   like "50" works; a quantity like "3pc" is correctly skipped. Prices
   embedded mid-word without spacing may still misparse — the preview
   step is the safety net.
5. No API keys anywhere. No Groq calls in this phase (all local).

## Not started
Phase 7 (demo packaging/polish) and later — awaiting approval.
