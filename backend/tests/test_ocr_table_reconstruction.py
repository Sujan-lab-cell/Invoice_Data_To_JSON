import unittest
from pathlib import Path

from app.ocr.easyocr_engine import EasyOCREngine
from app.ocr.ocr_table_reconstructor import (
    OCRTableReconstructor,
    WordBox,
    ColumnHeader,
    TableLayoutProfile,
    clean_cell_text,
    normalize_numeric_token,
    is_valid_numeric_token,
    HEADER_ALIAS_MAP
)
from app.ocr.schemas import OCRResult, OCRPage, OCRLine, OCRWord


class TestOCRTableReconstruction(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = EasyOCREngine()
        cls.sample_dir = Path(__file__).resolve().parent / "sample_invoices"

    def test_header_alias_mapping(self):
        """Test header alias mappings for all canonical invoice column names."""
        self.assertEqual(OCRTableReconstructor.normalize_header_name("Product"), "product_name")
        self.assertEqual(OCRTableReconstructor.normalize_header_name("Item"), "product_name")
        self.assertEqual(OCRTableReconstructor.normalize_header_name("Items"), "product_name")
        self.assertEqual(OCRTableReconstructor.normalize_header_name("Description"), "product_name")
        self.assertEqual(OCRTableReconstructor.normalize_header_name("Product Name"), "product_name")
        self.assertEqual(OCRTableReconstructor.normalize_header_name("Particulars"), "product_name")

        self.assertEqual(OCRTableReconstructor.normalize_header_name("Qty"), "quantity")
        self.assertEqual(OCRTableReconstructor.normalize_header_name("Quantity"), "quantity")
        self.assertEqual(OCRTableReconstructor.normalize_header_name("Quantlty"), "quantity")

        self.assertEqual(OCRTableReconstructor.normalize_header_name("Rate"), "rate")
        self.assertEqual(OCRTableReconstructor.normalize_header_name("Unit Rate"), "rate")
        self.assertEqual(OCRTableReconstructor.normalize_header_name("PTR"), "rate")
        self.assertEqual(OCRTableReconstructor.normalize_header_name("Rate Per Unit"), "rate")
        self.assertEqual(OCRTableReconstructor.normalize_header_name("Rale Per Unlt"), "rate")

        self.assertEqual(OCRTableReconstructor.normalize_header_name("Amount"), "amount")
        self.assertEqual(OCRTableReconstructor.normalize_header_name("Amt"), "amount")
        self.assertEqual(OCRTableReconstructor.normalize_header_name("Total"), "amount")
        self.assertEqual(OCRTableReconstructor.normalize_header_name("Net Amount"), "amount")
        self.assertEqual(OCRTableReconstructor.normalize_header_name("AMount"), "amount")

        self.assertEqual(OCRTableReconstructor.normalize_header_name("Batch"), "batch_no")
        self.assertEqual(OCRTableReconstructor.normalize_header_name("Batch No"), "batch_no")
        self.assertEqual(OCRTableReconstructor.normalize_header_name("Batch No:"), "batch_no")
        self.assertEqual(OCRTableReconstructor.normalize_header_name("Batch Number"), "batch_no")

        self.assertEqual(OCRTableReconstructor.normalize_header_name("Expiry"), "expiry_date")
        self.assertEqual(OCRTableReconstructor.normalize_header_name("Exp Dt"), "expiry_date")
        self.assertEqual(OCRTableReconstructor.normalize_header_name("Expiry Date"), "expiry_date")

        self.assertEqual(OCRTableReconstructor.normalize_header_name("GST"), "gst_pct")
        self.assertEqual(OCRTableReconstructor.normalize_header_name("GST%"), "gst_pct")
        self.assertEqual(OCRTableReconstructor.normalize_header_name("Tax %"), "gst_pct")

        self.assertEqual(OCRTableReconstructor.normalize_header_name("MRP"), "mrp")
        self.assertEqual(OCRTableReconstructor.normalize_header_name("M.R.P"), "mrp")

        self.assertEqual(OCRTableReconstructor.normalize_header_name("HSN"), "hsn")
        self.assertEqual(OCRTableReconstructor.normalize_header_name("HSN Code"), "hsn")
        self.assertEqual(OCRTableReconstructor.normalize_header_name("HSN/SAC"), "hsn")

    def test_step3_normal_column_order_multiple_rows(self):
        """Step 3 Test 1: Normal column order with multiple item rows."""
        # Header: [Product Name: 20..150], [HSN: 200..250], [Qty: 300..350], [Rate: 400..450], [Amount: 500..550]
        h1 = WordBox("Product Name", [[20, 50], [150, 50], [150, 60], [20, 60]])
        h2 = WordBox("HSN", [[200, 50], [250, 50], [250, 60], [200, 60]])
        h3 = WordBox("Qty", [[300, 50], [350, 50], [350, 60], [300, 60]])
        h4 = WordBox("Rate", [[400, 50], [450, 50], [450, 60], [400, 60]])
        h5 = WordBox("Amount", [[500, 50], [550, 50], [550, 60], [500, 60]])

        # Row 1 (y=100)
        r1_w1 = WordBox("Paracetamol 650", [[20, 100], [140, 100], [140, 110], [20, 110]])
        r1_w2 = WordBox("300490", [[200, 100], [245, 100], [245, 110], [200, 110]])
        r1_w3 = WordBox("50", [[305, 100], [335, 100], [335, 110], [305, 110]])
        r1_w4 = WordBox("2.50", [[405, 100], [445, 100], [445, 110], [405, 110]])
        r1_w5 = WordBox("125.00", [[505, 100], [545, 100], [545, 110], [505, 110]])

        # Row 2 (y=140)
        r2_w1 = WordBox("Amoxicillin 500", [[20, 140], [145, 140], [145, 150], [20, 150]])
        r2_w2 = WordBox("300410", [[200, 140], [245, 140], [245, 150], [200, 150]])
        r2_w3 = WordBox("20", [[305, 140], [335, 140], [335, 150], [305, 150]])
        r2_w4 = WordBox("10.00", [[405, 140], [445, 140], [445, 150], [405, 150]])
        r2_w5 = WordBox("200.00", [[505, 140], [545, 140], [545, 150], [505, 150]])

        # Row 3 (y=180)
        r3_w1 = WordBox("Cetirizine 10mg", [[20, 180], [140, 180], [140, 190], [20, 190]])
        r3_w2 = WordBox("300490", [[200, 180], [245, 180], [245, 190], [200, 190]])
        r3_w3 = WordBox("100", [[305, 180], [335, 180], [335, 190], [305, 190]])
        r3_w4 = WordBox("1.20", [[405, 180], [445, 180], [445, 190], [405, 190]])
        r3_w5 = WordBox("120.00", [[505, 180], [545, 180], [545, 190], [505, 190]])

        words = [h1, h2, h3, h4, h5, r1_w1, r1_w2, r1_w3, r1_w4, r1_w5, r2_w1, r2_w2, r2_w3, r2_w4, r2_w5, r3_w1, r3_w2, r3_w3, r3_w4, r3_w5]
        grid = OCRTableReconstructor.reconstruct_item_rows(words, use_canonical_names=True)

        self.assertEqual(len(grid), 3)
        self.assertEqual(grid[0]["product_name"], "Paracetamol 650")
        self.assertEqual(grid[0]["quantity"], "50")
        self.assertEqual(grid[0]["amount"], "125.00")

        self.assertEqual(grid[1]["product_name"], "Amoxicillin 500")
        self.assertEqual(grid[1]["quantity"], "20")
        self.assertEqual(grid[1]["amount"], "200.00")

        self.assertEqual(grid[2]["product_name"], "Cetirizine 10mg")
        self.assertEqual(grid[2]["quantity"], "100")
        self.assertEqual(grid[2]["amount"], "120.00")

    def test_step3_reordered_columns_multiple_rows(self):
        """Step 3 Test 2: Reordered columns (Amount -> Rate -> Qty -> Product -> Batch)."""
        h_amt = WordBox("Amount", [[20, 50], [80, 50], [80, 60], [20, 60]])
        h_rate = WordBox("Rate", [[120, 50], [170, 50], [170, 60], [120, 60]])
        h_qty = WordBox("Qty", [[210, 50], [250, 50], [250, 60], [210, 60]])
        h_prod = WordBox("Product Name", [[290, 50], [420, 50], [420, 60], [290, 60]])
        h_batch = WordBox("Batch No", [[460, 50], [530, 50], [530, 60], [460, 60]])

        # Row 1
        r1_amt = WordBox("300.00", [[25, 100], [75, 100], [75, 110], [25, 110]])
        r1_rate = WordBox("30.00", [[125, 100], [165, 100], [165, 110], [125, 110]])
        r1_qty = WordBox("10", [[215, 100], [245, 100], [245, 110], [215, 110]])
        r1_prod = WordBox("Ibuprofen 400", [[295, 100], [410, 100], [410, 110], [295, 110]])
        r1_batch = WordBox("IB9901", [[465, 100], [520, 100], [520, 110], [465, 110]])

        # Row 2
        r2_amt = WordBox("450.00", [[25, 140], [75, 140], [75, 150], [25, 150]])
        r2_rate = WordBox("15.00", [[125, 140], [165, 140], [165, 150], [125, 150]])
        r2_qty = WordBox("30", [[215, 140], [245, 140], [245, 150], [215, 150]])
        r2_prod = WordBox("Diclofenac Gel", [[295, 140], [410, 140], [410, 150], [295, 150]])
        r2_batch = WordBox("DC2024", [[465, 140], [520, 140], [520, 150], [465, 150]])

        words = [h_amt, h_rate, h_qty, h_prod, h_batch, r1_amt, r1_rate, r1_qty, r1_prod, r1_batch, r2_amt, r2_rate, r2_qty, r2_prod, r2_batch]
        grid = OCRTableReconstructor.reconstruct_item_rows(words, use_canonical_names=True)

        self.assertEqual(len(grid), 2)
        self.assertEqual(grid[0]["product_name"], "Ibuprofen 400")
        self.assertEqual(grid[0]["batch_no"], "IB9901")
        self.assertEqual(grid[0]["quantity"], "10")
        self.assertEqual(grid[0]["rate"], "30.00")
        self.assertEqual(grid[0]["amount"], "300.00")

        self.assertEqual(grid[1]["product_name"], "Diclofenac Gel")
        self.assertEqual(grid[1]["batch_no"], "DC2024")
        self.assertEqual(grid[1]["quantity"], "30")
        self.assertEqual(grid[1]["rate"], "15.00")
        self.assertEqual(grid[1]["amount"], "450.00")

    def test_step3_missing_cells_multiple_rows(self):
        """Step 3 Test 3: Missing cells across multiple rows without column shifting."""
        h1 = WordBox("Item", [[20, 50], [80, 50], [80, 60], [20, 60]])
        h2 = WordBox("HSN", [[140, 50], [190, 50], [190, 60], [140, 60]])
        h3 = WordBox("Qty", [[240, 50], [280, 50], [280, 60], [240, 60]])
        h4 = WordBox("Rate", [[330, 50], [380, 50], [380, 60], [330, 60]])
        h5 = WordBox("Amount", [[430, 50], [490, 50], [490, 60], [430, 60]])

        # Row 1: Missing HSN and Qty (only Item, Rate, Amount)
        r1_w1 = WordBox("Bandage Roll", [[20, 100], [110, 100], [110, 110], [20, 110]])
        r1_w4 = WordBox("50.00", [[335, 100], [375, 100], [375, 110], [335, 110]])
        r1_w5 = WordBox("50.00", [[435, 100], [485, 100], [485, 110], [435, 110]])

        # Row 2: Full row
        r2_w1 = WordBox("Cotton Wool", [[20, 140], [110, 140], [110, 150], [20, 150]])
        r2_w2 = WordBox("520100", [[145, 140], [185, 140], [185, 150], [145, 150]])
        r2_w3 = WordBox("5", [[245, 140], [275, 140], [275, 150], [245, 150]])
        r2_w4 = WordBox("20.00", [[335, 140], [375, 140], [375, 150], [335, 150]])
        r2_w5 = WordBox("100.00", [[435, 140], [485, 140], [485, 150], [435, 150]])

        # Row 3: Missing Rate (Item, HSN, Qty, Amount)
        r3_w1 = WordBox("Surgical Tape", [[20, 180], [115, 180], [115, 190], [20, 190]])
        r3_w2 = WordBox("300590", [[145, 180], [185, 180], [185, 190], [145, 190]])
        r3_w3 = WordBox("12", [[245, 180], [275, 180], [275, 190], [245, 190]])
        r3_w5 = WordBox("240.00", [[435, 180], [485, 180], [485, 190], [435, 190]])

        words = [h1, h2, h3, h4, h5, r1_w1, r1_w4, r1_w5, r2_w1, r2_w2, r2_w3, r2_w4, r2_w5, r3_w1, r3_w2, r3_w3, r3_w5]
        grid = OCRTableReconstructor.reconstruct_item_rows(words, use_canonical_names=True)

        self.assertEqual(len(grid), 3)

        # Row 1 check
        self.assertEqual(grid[0]["product_name"], "Bandage Roll")
        self.assertEqual(grid[0]["hsn"], "")
        self.assertEqual(grid[0]["quantity"], "")
        self.assertEqual(grid[0]["rate"], "50.00")
        self.assertEqual(grid[0]["amount"], "50.00")

        # Row 2 check
        self.assertEqual(grid[1]["product_name"], "Cotton Wool")
        self.assertEqual(grid[1]["hsn"], "520100")
        self.assertEqual(grid[1]["quantity"], "5")
        self.assertEqual(grid[1]["rate"], "20.00")
        self.assertEqual(grid[1]["amount"], "100.00")

        # Row 3 check
        self.assertEqual(grid[2]["product_name"], "Surgical Tape")
        self.assertEqual(grid[2]["hsn"], "300590")
        self.assertEqual(grid[2]["quantity"], "12")
        self.assertEqual(grid[2]["rate"], "")
        self.assertEqual(grid[2]["amount"], "240.00")

    def test_clean_cell_text(self):
        """Test OCR artifact cleaning and numeric normalization."""
        self.assertEqual(clean_cell_text("{150.00"), "150.00")
        self.assertEqual(clean_cell_text("<150,00"), "150.00")
        self.assertEqual(clean_cell_text("{0.00 (0}"), "0.00")
        self.assertEqual(clean_cell_text("{0.00 0"), "0.00")
        self.assertEqual(clean_cell_text("12,999,00"), "12,999.00")
        self.assertEqual(clean_cell_text("{12999"), "12999")
        self.assertEqual(clean_cell_text("₹1,250.50"), "1,250.50")

    def test_semantic_numeric_validation(self):
        """Verify semantic column validation marks non-numeric text in numeric columns as invalid/empty."""
        self.assertTrue(is_valid_numeric_token("150"))
        self.assertTrue(is_valid_numeric_token("150.00"))
        self.assertTrue(is_valid_numeric_token("12,999.00"))
        self.assertFalse(is_valid_numeric_token("Bora"))
        self.assertFalse(is_valid_numeric_token("TSu"))
        self.assertFalse(is_valid_numeric_token("Subject"))

        self.assertEqual(normalize_numeric_token("1C0"), "100")
        self.assertEqual(normalize_numeric_token("579."), "579.00")
        self.assertIsNone(normalize_numeric_token("Bora"))

    def test_reconstruct_png_image_grid(self):
        """Verify grid reconstruction and canonical header resolution on freeinvoice-stylish.png."""
        img_path = self.sample_dir / "freeinvoice-stylish.png"
        if not img_path.exists():
            self.skipTest(f"File not found: {img_path}")

        ocr_res = self.engine.extract_text(str(img_path))
        grid = OCRTableReconstructor.reconstruct_item_rows(ocr_res, use_canonical_names=True)

        self.assertEqual(len(grid), 3)
        descriptions = [r.get("product_name", "") for r in grid]
        self.assertTrue(any("Tnermometer" in d for d in descriptions))
        self.assertTrue(any("SyringelNeedle" in d for d in descriptions))
        self.assertTrue(any("Instnumenis" in d for d in descriptions))

        rates = [r.get("rate", "") for r in grid]
        amounts = [r.get("amount", "") for r in grid]
        self.assertIn("150.00", rates)
        self.assertIn("12,999.00", amounts)

    def test_reconstruct_jpg_image_grid(self):
        """Verify grid reconstruction and canonical header resolution on sample_invoice_test.jpg."""
        img_path = self.sample_dir / "sample_invoice_test.jpg"
        if not img_path.exists():
            self.skipTest(f"File not found: {img_path}")

        ocr_res = self.engine.extract_text(str(img_path))
        grid = OCRTableReconstructor.reconstruct_item_rows(ocr_res, use_canonical_names=True)

        self.assertEqual(len(grid), 3)
        descriptions = [r.get("product_name", "") for r in grid]
        self.assertTrue(any("Tnermomeler" in d or "Tnermometer" in d for d in descriptions))
        self.assertTrue(any("Syringe" in d for d in descriptions))
        self.assertTrue(any("Surgical" in d for d in descriptions))

    def test_reconstruct_pharma_template_grid(self):
        """Verify grid reconstruction on Pharma Invoice Template without column shifting."""
        img_path = self.sample_dir / "Pharma Invoice Template Software for Medicine Distributors.png"
        if not img_path.exists():
            self.skipTest(f"File not found: {img_path}")

        ocr_res = self.engine.extract_text(str(img_path))
        grid = OCRTableReconstructor.reconstruct_item_rows(ocr_res, use_canonical_names=True)

        self.assertGreaterEqual(len(grid), 4)
        
        row1 = grid[0]
        self.assertEqual(row1.get("hsn", ""), "12345678")
        self.assertEqual(row1.get("product_name", ""), "Belladonna30")
        self.assertEqual(row1.get("pack", ""), "100")
        self.assertEqual(row1.get("batch_no", ""), "0254884")
        self.assertEqual(row1.get("rate", ""), "157.14")
        self.assertEqual(row1.get("amount", ""), "1484.98")

        row3 = grid[2]
        self.assertEqual(row3.get("product_name", ""), "Belladonna30")
        self.assertEqual(row3.get("quantity", ""), "100")
        self.assertEqual(row3.get("mrp", ""), "165")


if __name__ == "__main__":
    unittest.main()
