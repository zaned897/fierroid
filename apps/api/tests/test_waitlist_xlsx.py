from __future__ import annotations

from io import BytesIO
from zipfile import ZipFile

from fierro_api.waitlist import build_xlsx


def test_waitlist_xlsx_has_excel_workbook_parts() -> None:
    data = build_xlsx(
        [
            {
                "id": 7,
                "name": "Ana Fierro",
                "email": "ana@example.test",
                "state": "Chihuahua",
                "stations": 3,
                "created_at": "2026-10-13T10:00:00+00:00",
                "confirmation_sent_at": "2026-10-13T10:00:00+00:00",
                "confirmed_at": "2026-10-13T10:05:00+00:00",
            }
        ]
    )

    with ZipFile(BytesIO(data)) as workbook:
        assert "xl/workbook.xml" in workbook.namelist()
        assert "xl/worksheets/sheet1.xml" in workbook.namelist()
        sheet = workbook.read("xl/worksheets/sheet1.xml").decode("utf-8")

    assert "ana@example.test" in sheet
    assert "Chihuahua" in sheet
    assert "Confirmado" in sheet
