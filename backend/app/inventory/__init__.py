"""
Inventory matching module for the Pharmacy Invoice Parser.

This module provides structures and logic to align extracted product line items 
from supplier invoices with the client's internal Inventory Master database.
"""

from .inventory_matcher import InventoryMatcher

__all__ = ["InventoryMatcher"]
