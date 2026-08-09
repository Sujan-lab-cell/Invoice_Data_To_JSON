import unittest
from app.extraction.item_extractor import ItemExtractor

SAMPLE_4358_OCR_TEXT = """
Sch Sch. Disc GST Taxale
SNo Rack Mfac Particulars Packing HSN Batch Exp Qty MRP Rate
Qty Disc% % % value
1 RHIN DEFSOLONE 6 10's 30043911 MTTA0175A 12/27 10 2 121.88 92.86 0.00 5 928.60
2 RHIN FLUGAIN 10 MG TAB 10's 30044090 RFNT2503 10/27 10 2 45.15 34.40 0.00 5 344.00
"""


class Test4358ItemExtraction(unittest.TestCase):
    """
    Regression test for invoice 4358 line item extraction:
    Layout: [LineNo] [Mfg] [Particulars] [Packing] [HSN] [Batch] [Exp] [Qty] [FreeQty] [MRP] [Rate] [Disc%] [GST%] [Taxable Value]
    """

    def test_extract_items_from_4358_ocr(self):
        items = ItemExtractor.extract_items(SAMPLE_4358_OCR_TEXT)
        self.assertEqual(len(items), 2, f"Expected 2 items, but got {len(items)}")

        # Item 1 assertions
        item1 = items[0]
        self.assertIn("RHIN DEFSOLONE", item1["product"]["description"]["normalized"])
        self.assertEqual(item1["product"]["hsn_code"]["normalized"], "30043911")
        self.assertEqual(item1["batch"]["batch_no"]["normalized"], "MTTA0175A")
        self.assertEqual(item1["batch"]["expiry_date"]["raw"], "12/27")
        self.assertEqual(item1["quantity"]["qty"]["normalized"], 10.0)
        self.assertIsNotNone(item1["quantity"]["free_qty"])
        self.assertEqual(item1["quantity"]["free_qty"]["normalized"], 2.0)
        self.assertEqual(item1["pricing"]["mrp"]["normalized"], 121.88)
        self.assertEqual(item1["pricing"]["purchase_rate"]["normalized"], 92.86)
        if item1["pricing"]["discount_percentage"]:
            self.assertEqual(item1["pricing"]["discount_percentage"]["normalized"], 0.0)
        self.assertEqual(item1["tax"]["gst_percentage"]["normalized"], 5.0)
        self.assertEqual(item1["pricing"]["taxable_amount"]["normalized"], 928.60)

        # Item 2 assertions
        item2 = items[1]
        self.assertEqual(item2["product"]["description"]["normalized"], "RHIN FLUGAIN 10 MG TAB")
        self.assertEqual(item2["product"]["hsn_code"]["normalized"], "30044090")
        self.assertEqual(item2["batch"]["batch_no"]["normalized"], "RFNT2503")
        self.assertEqual(item2["batch"]["expiry_date"]["raw"], "10/27")
        self.assertEqual(item2["quantity"]["qty"]["normalized"], 10.0)
        self.assertIsNotNone(item2["quantity"]["free_qty"])
        self.assertEqual(item2["quantity"]["free_qty"]["normalized"], 2.0)
        self.assertEqual(item2["pricing"]["mrp"]["normalized"], 45.15)
        self.assertEqual(item2["pricing"]["purchase_rate"]["normalized"], 34.40)
        if item2["pricing"]["discount_percentage"]:
            self.assertEqual(item2["pricing"]["discount_percentage"]["normalized"], 0.0)
        self.assertEqual(item2["tax"]["gst_percentage"]["normalized"], 5.0)
        self.assertEqual(item2["pricing"]["taxable_amount"]["normalized"], 344.00)


if __name__ == "__main__":
    unittest.main()
