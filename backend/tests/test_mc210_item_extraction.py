import unittest
from app.extraction.item_extractor import ItemExtractor

MC210_OCR_TEXT = """
                                MEDICARE PHARMA
                            PHARMACEUTICAL DISTRIBUTORS
                        MUZHAPPILANGAD MADAM, THALASSERY
                    PH: 0490 2326443, 2326444, 2326445, 9847593760
                    GSTIN: 32AGHPR0323G1ZU  STATE: KERALA (32)
====================================================================================================
Invoice No: MC-210          Date: 14/05/26          Due Date: 14/06/26
Buyer: GERMAN PHARMACY      Payment: CREDIT
====================================================================================================
Mfg HSN     Item Name           Pack Qty     Batch       Exp   MRP    Rate    Dis% Disc Sch CGST  SGST  Amount
----------------------------------------------------------------------------------------------------
LIFE 30049099 AMPICARE DS TAB   1    10.000  LBT2403026  02-27 225.00 179.000 0.00 0.00 0.00 2.5 44.75 2.5 44.75 1790.00
LIFE 30049099 AMPICARE DS TAB   1    0 + 1.000LBT2403026 02-27 225.00 179.000 0.00 0.00 0.00 2.5 0.00  2.5 0.00  0.00
LIFE 3004     NERVONAS TABLETS  1    10.000  TN8751      02-28 111.00 87.790  0.00 0.00 0.00 2.5 21.95 2.5 21.95 877.90
LIFE 3004     NERVONAS TABLETS  1    0 + 1.000TN8751     02-28 111.00 87.790  0.00 0.00 0.00 2.5 0.00  2.5 0.00  0.00
LIFE 21069099 D2K CAL TABLETS   1    10.000  APT04870    11-27 75.00  59.520  0.00 0.00 0.00 2.5 14.88 2.5 14.88 595.20
LIFE 21069099 D2K CAL TABLETS   1    0 + 1.000APT04870   11-27 75.00  59.520  0.00 0.00 0.00 2.5 0.00  2.5 0.00  0.00
LIFE 30049069 TRIPCARE TABLETS  1X10 10.000  UGT25296G   02-27 183.00 145.080 0.00 0.00 0.00 2.5 36.27 2.5 36.27 1450.80
LIFE 30049069 TRIPCARE TABLETS  1X10 0 + 1.000UGT25296G  02-27 183.00 145.080 0.00 0.00 0.00 2.5 0.00  2.5 0.00  0.00
----------------------------------------------------------------------------------------------------
Sub Total : 4713.90   CGST : 117.85   SGST : 117.85   Grand Total : 4949.60
"""


class TestMC210ItemExtraction(unittest.TestCase):
    """
    Tests rule-based extraction of all 8 line items from MC-210 text.
    """

    def test_extract_8_items_from_mc210_ocr(self):
        items = ItemExtractor.extract_items(MC210_OCR_TEXT)
        self.assertEqual(len(items), 8, f"Expected 8 items, but got {len(items)}")

        # Verify Item 1: AMPICARE DS TAB (billed)
        item1 = items[0]
        self.assertEqual(item1["product"]["description"]["normalized"], "AMPICARE DS TAB")
        self.assertEqual(item1["product"]["hsn_code"]["normalized"], "30049099")
        self.assertEqual(item1["batch"]["batch_no"]["normalized"], "LBT2403026")
        self.assertEqual(item1["batch"]["expiry_date"]["normalized"], "02-27")
        self.assertEqual(item1["quantity"]["qty"]["normalized"], 10.0)
        self.assertIsNone(item1["quantity"]["free_qty"])
        self.assertEqual(item1["pricing"]["mrp"]["normalized"], 225.0)
        self.assertEqual(item1["pricing"]["purchase_rate"]["normalized"], 179.0)
        self.assertEqual(item1["pricing"]["taxable_amount"]["normalized"], 1790.0)
        self.assertEqual(item1["tax"]["gst_percentage"]["normalized"], 5.0)
        self.assertEqual(item1["tax"]["gst_amount"]["normalized"], 89.50)

        # Verify Item 2: AMPICARE DS TAB (free scheme)
        item2 = items[1]
        self.assertEqual(item2["product"]["description"]["normalized"], "AMPICARE DS TAB")
        self.assertEqual(item2["quantity"]["qty"]["normalized"], 0.0)
        self.assertIsNotNone(item2["quantity"]["free_qty"])
        self.assertEqual(item2["quantity"]["free_qty"]["normalized"], 1.0)
        self.assertEqual(item2["pricing"]["taxable_amount"]["normalized"], 0.0)

        # Verify Item 7: TRIPCARE TABLETS (1X10 pack)
        item7 = items[6]
        self.assertEqual(item7["product"]["description"]["normalized"], "TRIPCARE TABLETS")
        self.assertEqual(item7["packaging"]["pack_size"], "1X10")
        self.assertEqual(item7["packaging"]["unit_count"], 10)
        self.assertEqual(item7["quantity"]["total_qty"], 100.0)
        self.assertEqual(item7["pricing"]["taxable_amount"]["normalized"], 1450.80)


if __name__ == "__main__":
    unittest.main()
