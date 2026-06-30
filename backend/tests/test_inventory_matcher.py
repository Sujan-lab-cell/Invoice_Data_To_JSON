import sys
import unittest
from pathlib import Path

# Add backend folder to sys.path to enable direct app module imports
sys.path.append(str(Path(__file__).parent.parent))

from app.inventory import InventoryMatcher


class TestInventoryMatcherInterface(unittest.TestCase):
    """Unit tests for the InventoryMatcher interface methods and errors."""

    def setUp(self) -> None:
        self.matcher = InventoryMatcher()

    def test_load_inventory_raises_not_implemented(self) -> None:
        with self.assertRaises(NotImplementedError) as context:
            self.matcher.load_inventory("dummy_path.csv")
        self.assertIn("has not yet been provided", str(context.exception))

    def test_match_product_raises_not_implemented(self) -> None:
        with self.assertRaises(NotImplementedError) as context:
            self.matcher.match_product("Paracetamol 500mg")
        self.assertIn("has not yet been provided", str(context.exception))

    def test_match_invoice_items_raises_not_implemented(self) -> None:
        with self.assertRaises(NotImplementedError) as context:
            self.matcher.match_invoice_items([])
        self.assertIn("has not yet been provided", str(context.exception))


if __name__ == "__main__":
    unittest.main()
