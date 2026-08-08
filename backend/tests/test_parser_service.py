import sys
from pathlib import Path

# Add backend folder to sys.path to enable direct app module imports
sys.path.append(str(Path(__file__).parent.parent))

from app.services.parser_service import ParserService


def main():

    parser = ParserService()

    result = parser.parse(
        # r"E:\Ayush_lab\Invoice_Data_To_JSON-1\backend\tests\DEEPA DRUG HOUSE THALASSERY Sales Invoice 3965 (1).xls"
        # r"E:\Ayush_lab\Invoice_Data_To_JSON-1\backend\tests\SUNANDA ASSOCIATES KOZHIKODE Sales Invoice 28053 (1).xls"
        # r"E:\Ayush_lab\Invoice_Data_To_JSON-1\backend\tests\sample_invoices\MCRB PHARMA PILATHARA Sales Invoice 8898.pdf"
        r"E:\Ayush_lab\Invoice_Data_To_JSON-1\backend\tests\sample_invoices\VINAYAKA ENTERPRISES PAYYANUR, KANNUR DISTT Sales Invoice 1758 (1).pdf"
    )

    print("\n")
    print("=" * 80)
    print("FILE TYPE:")
    print(result["source_file_type"])

    print("\n")
    print("=" * 80)
    print("TEXT:")
    print(result["text"][:3000])


if __name__ == "__main__":
    main()
