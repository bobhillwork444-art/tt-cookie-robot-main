"""
Custom widgets with disabled mouse wheel scrolling.
Prevents accidental value changes when scrolling over spinboxes and comboboxes.
"""
from PyQt5.QtWidgets import QSpinBox, QDoubleSpinBox, QComboBox
from PyQt5.QtCore import Qt


class NoScrollSpinBox(QSpinBox):
    """QSpinBox with disabled mouse wheel scrolling."""
    
    def wheelEvent(self, event):
        """Ignore wheel events to prevent accidental value changes."""
        event.ignore()


class NoScrollDoubleSpinBox(QDoubleSpinBox):
    """QDoubleSpinBox with disabled mouse wheel scrolling."""
    
    def wheelEvent(self, event):
        """Ignore wheel events to prevent accidental value changes."""
        event.ignore()


class NoScrollComboBox(QComboBox):
    """QComboBox with disabled mouse wheel scrolling."""
    
    def wheelEvent(self, event):
        """Ignore wheel events to prevent accidental value changes."""
        event.ignore()
