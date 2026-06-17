import logging
from pathlib import Path
from typing import Any, Dict, List
import pandas as pd

logger = logging.getLogger(__name__)


class CSVParser:
    """
    Parser for CSV invoice files.
    Loads data, normalizes headers, and outputs structured row dictionaries and raw text context.
    """

    def parse(self, file_path: str) -> Dict[str, Any]:
        """
        Parses a CSV file, normalizes header column names, converts rows to dict structures,
        and generates a textual representation of the rows.

        Args:
            file_path (str): Path to the CSV file.

        Returns:
            Dict[str, Any]: Structured dictionary with row text, records, and file metadata.
        """
        logger.info(f"Parsing CSV file: {file_path}")
        try:
            df = pd.read_csv(file_path)
            
            # Fill NaN values with empty string for JSON serialization safety
            df = df.fillna("")

            # Normalize column names: strip whitespace, lowercase, and replace spaces/hyphens with underscores
            df.columns = [
                str(col).strip().lower().replace(" ", "_").replace("-", "_").replace(".", "_")
                for col in df.columns
            ]

            # 1. Convert rows to structured dictionary records
            rows_data = df.to_dict(orient="records")

            # 2. Reconstruct original row text for downstream AI text extraction
            row_texts = []
            for _, row in df.iterrows():
                row_str = " | ".join(
                    [f"{col}: {val}" for col, val in row.items() if str(val).strip() != ""]
                )
                if row_str.strip():
                    row_texts.append(row_str)

            combined_text = "\n".join(row_texts)

            return {
                "text": combined_text,
                "rows": rows_data,
                "source_file_name": Path(file_path).name,
                "source_file_type": "csv"
            }
        except Exception as e:
            logger.error(f"Error parsing CSV file: {e}")
            raise RuntimeError(f"CSV parsing failed: {e}") from e
