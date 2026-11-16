import os
from pathlib import Path
import sys

from PySide6.QtGui import QFont, QFontDatabase
from PySide6.QtWidgets import QApplication


def ensure_readable_fonts():
    """The Windows offscreen Qt plugin does not enumerate system fonts."""
    if sys.platform == "win32" and not QFontDatabase.families():
        font = Path(os.environ.get("WINDIR", "C:/Windows"))/"Fonts/malgun.ttf"
        if font.is_file():
            QFontDatabase.addApplicationFont(str(font))
    if "Malgun Gothic" in QFontDatabase.families():
        QApplication.instance().setFont(QFont("Malgun Gothic",10))
