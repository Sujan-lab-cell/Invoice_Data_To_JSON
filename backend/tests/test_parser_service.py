from app.services.parser_service import (
    ParserService
)


def main():

    parser = ParserService()

    result = parser.parse(
        r"E:\Ayush_lab\Invoice_Data_To_JSON-1\backend\tests\4220 (1).pdf"
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
