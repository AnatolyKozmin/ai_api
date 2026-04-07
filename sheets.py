from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import gspread
from dotenv import load_dotenv
from gspread import Worksheet
from gspread.exceptions import WorksheetNotFound
from google.oauth2.service_account import Credentials

_ROOT = Path(__file__).resolve().parent
load_dotenv(_ROOT / ".env")

_SCOPES = (
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
)


def _credentials_path() -> str | None:
    raw = os.environ.get("GOOGLE_SHEETS_CREDENTIALS") or os.environ.get(
        "GOOGLE_APPLICATION_CREDENTIALS"
    )
    if not raw:
        return None
    p = Path(raw)
    if not p.is_absolute():
        p = _ROOT / p
    return str(p)


def _first_empty_row_from_col_a(ws: Worksheet, start_row: int) -> int:
    """Первая пустая строка в колонке A, начиная с start_row (1-based)."""
    values = ws.col_values(1)
    max_scan = 50000
    for r in range(start_row, start_row + max_scan):
        i = r - 1
        if i >= len(values):
            return r
        cell = values[i] if values[i] is not None else ""
        if not str(cell).strip():
            return r
    return start_row


def _row_from_parsed(parsed: dict[str, Any]) -> list[str]:
    def s(key: str) -> str:
        v = parsed.get(key, "")
        return str(v).strip() if v is not None else ""

    return [
        s("organization"),
        s("division"),
        s("role"),
        s("field"),
        s("salary"),
        s("schedule"),
        s("format"),
        s("description"),
        s("employment_format"),
        s("feature1"),
        s("feature2"),
        s("feature3"),
    ]


def append_vacancy_row(parsed: dict[str, Any]) -> tuple[bool, str | None]:
    path = _credentials_path()
    spreadsheet_id = os.environ.get("GOOGLE_SPREADSHEET_ID", "").strip()

    if not path or not spreadsheet_id:
        return False, "not_configured"

    creds = Credentials.from_service_account_file(path, scopes=_SCOPES)
    gc = gspread.authorize(creds)
    sh = gc.open_by_key(spreadsheet_id)
    sheet_name = (os.environ.get("GOOGLE_SHEET_NAME", "").strip() or "Вакансии")
    try:
        ws = sh.worksheet(sheet_name)
    except WorksheetNotFound:
        ws = sh.add_worksheet(title=sheet_name, rows=5000, cols=15)
    except Exception as e:
        resp = getattr(e, "response", None)
        code = getattr(resp, "status_code", None) if resp is not None else None
        if code == 404:
            ws = sh.add_worksheet(title=sheet_name, rows=5000, cols=15)
        else:
            raise

    first_data_row = int(os.environ.get("GOOGLE_SHEET_FIRST_DATA_ROW", "3"))
    next_row = _first_empty_row_from_col_a(ws, first_data_row)

    row = _row_from_parsed(parsed)
    rng = f"A{next_row}:L{next_row}"
    ws.update(rng, [row], value_input_option="USER_ENTERED")
    return True, None
