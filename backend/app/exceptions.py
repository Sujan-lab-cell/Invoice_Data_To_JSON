class AppException(Exception):
    """
    Base exception class for all custom exceptions in the Pharmacy Invoice Parser application.
    """
    def __init__(self, message: str, details: str = None):
        super().__init__(message)
        self.message = message
        self.details = details


class OCRException(AppException):
    """
    Raised when errors occur during text recognition (OCR processing) stages.
    """
    pass


class ParserException(AppException):
    """
    Raised when document parsers fail to extract text or values from spreadsheets, PDFs, or CSVs.
    """
    pass


class UnsupportedFileTypeError(ParserException):
    """
    Raised when a file format supplied to the parser service is not supported.
    """
    pass


class ValidationException(AppException):
    """
    Raised when extracted values violate critical business rules or mathematical checks.
    """
    pass


class InventoryMappingException(AppException):
    """
    Raised when errors occur during the fuzzy master item mapping or database queries.
    """
    pass

