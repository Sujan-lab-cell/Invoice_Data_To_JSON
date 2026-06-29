from pathlib import Path

import pandas as pd


class ExcelParser:

    def parse(self, file_path: str) -> dict:

        excel_file = pd.ExcelFile(file_path)

        sheet_text = []

        for sheet in excel_file.sheet_names:

            df = pd.read_excel(
                file_path,
                sheet_name=sheet
            )

            sheet_text.append(
                f"\n===== SHEET: {sheet} =====\n"
            )

            sheet_text.append(
                df.to_csv(index=False, sep="|")
            )

        return {
            "text": "\n".join(sheet_text),
            "source_file_name": Path(file_path).name,
            "source_file_type": "excel"
        }