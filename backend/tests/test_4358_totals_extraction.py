import unittest
from app.extraction.rule_based_components import TotalsCalculator

OCR_4358_TOTALS_SNIPPET = """
Taxable Amount : 1272.60
Description : Tax Amount : 63.63
Total Items: 2 Adj. Cr.Notes : Local Bill Disc. :
Total Qty : 24 Adj. Db.Notes : Executive. : 10 - DIRECT TDS / TCS Amount :
Tax % Taxable value SGST % AMT CGST % AMTExc. Mob :
Write Off : -0.23
@5% 1272.60 @2.5% 31.82 @2.5% 31.82 Order No. :
Net Amount : 1336.00
Order Dt. :
CreditNote Amt. :
Transport :
DebitNote Amt. :
Route :
Tax Tot ; 1272.60 31.82 31.82 Net Payable : 1336.00
"""


class Test4358TotalsExtraction(unittest.TestCase):
    """
    Regression test for invoice 4358 totals extraction:
    - Subtotal / Taxable Amount == 1272.60
    - Tax Total / Tax Amount == 63.63
    - Round Off / Write Off == -0.23
    - Grand Total / Net Payable == 1336.00
    """

    def test_extract_totals_4358(self):
        totals = TotalsCalculator.extract_totals(OCR_4358_TOTALS_SNIPPET)

        # 1. Subtotal
        self.assertEqual(totals["subtotal"]["raw"], "1272.60")
        self.assertEqual(totals["subtotal"]["normalized"], 1272.60)

        # 2. Tax Total (preserves printed 63.63)
        self.assertEqual(totals["tax_total"]["raw"], "63.63")
        self.assertEqual(totals["tax_total"]["normalized"], 63.63)

        # 3. Round Off / Write Off
        self.assertEqual(totals["round_off"]["raw"], "-0.23")
        self.assertEqual(totals["round_off"]["normalized"], -0.23)

        # 4. Grand Total / Net Payable
        self.assertEqual(totals["grand_total"]["raw"], "1336.00")
        self.assertEqual(totals["grand_total"]["normalized"], 1336.00)


if __name__ == "__main__":
    unittest.main()
