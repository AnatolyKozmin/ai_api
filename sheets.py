from __future__ import annotations

import os
from typing import Any

import gspread
from google.oauth2.service_account import Credentials

_SCOPES = (
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
)


def _credentials_path() -> str | None:
    return os.environ.get("GOOGLE_SHEETS_CREDENTIALS") or os.environ.get(
        "GOOGLE_APPLICATION_CREDENTIALS"
    )


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
    sheet_name = os.environ.get("GOOGLE_SHEET_NAME", "").strip()
    ws = sh.worksheet(sheet_name) if sheet_name else sh.sheet1

    row = _row_from_parsed(parsed)
    ws.append_row(row, value_input_option="USER_ENTERED")
    return True, None
