"""Color palette and stylesheet."""

from __future__ import annotations

from pathlib import Path

ASSETS = (Path(__file__).resolve().parent.parent / "assets").as_posix()

# Base: deep violet, a single bright accent, calm surfaces
BG = "#0B0713"
SURFACE = "#140D22"
SURFACE_2 = "#1B1230"
SURFACE_3 = "#241738"
BORDER = "#2E2046"
BORDER_SOFT = "#221733"

ACCENT = "#A855F7"
ACCENT_DIM = "#7C3AED"
ACCENT_GLOW = "rgba(168, 85, 247, 0.18)"

TEXT = "#EFEAF9"
TEXT_MUTED = "#9C90B8"
TEXT_FAINT = "#6E6488"

SUCCESS = "#4ADE80"
WARNING = "#FBBF24"
DANGER = "#F87171"

RADIUS = 14
FONT = "Segoe UI"


def stylesheet() -> str:
    return f"""
    * {{
        font-family: "{FONT}", "Inter", sans-serif;
        color: {TEXT};
    }}

    QWidget#root {{
        background: {BG};
        border: 1px solid {BORDER};
        border-radius: {RADIUS}px;
    }}

    QWidget#sidebar {{
        background: {SURFACE};
        border-right: 1px solid {BORDER_SOFT};
        border-top-left-radius: {RADIUS}px;
        border-bottom-left-radius: {RADIUS}px;
    }}

    QLabel#wordmark {{
        font-size: 19px;
        font-weight: 700;
        letter-spacing: 0.5px;
    }}
    QLabel#tagline {{ color: {TEXT_FAINT}; font-size: 11px; }}
    QLabel#pageTitle {{ font-size: 22px; font-weight: 700; }}
    QLabel#pageHint {{ color: {TEXT_MUTED}; font-size: 12px; }}
    QLabel#cardTitle {{ font-size: 14px; font-weight: 600; }}
    QLabel#cardHint {{ color: {TEXT_MUTED}; font-size: 11px; }}
    QLabel#muted {{ color: {TEXT_MUTED}; font-size: 12px; }}
    QLabel#faint {{ color: {TEXT_FAINT}; font-size: 11px; }}
    QLabel#valueLabel {{
        color: {ACCENT};
        font-size: 12px;
        font-weight: 600;
        font-family: "Cascadia Mono", "Consolas", monospace;
    }}

    QPushButton#navButton {{
        background: transparent;
        border: none;
        border-radius: 9px;
        padding: 10px 12px;
        text-align: left;
        font-size: 13px;
        color: {TEXT_MUTED};
    }}
    QPushButton#navButton:hover {{ background: {SURFACE_2}; color: {TEXT}; }}
    QPushButton#navButton:checked {{
        background: {ACCENT_GLOW};
        color: {TEXT};
        font-weight: 600;
    }}

    QFrame#card {{
        background: {SURFACE};
        border: 1px solid {BORDER_SOFT};
        border-radius: 12px;
    }}
    QFrame#cardFlat {{
        background: {SURFACE_2};
        border: 1px solid {BORDER_SOFT};
        border-radius: 10px;
    }}
    QFrame#divider {{ background: {BORDER_SOFT}; max-height: 1px; border: none; }}

    QPushButton {{
        background: {SURFACE_2};
        border: 1px solid {BORDER};
        border-radius: 9px;
        padding: 8px 16px;
        font-size: 12px;
        font-weight: 600;
    }}
    QPushButton:hover {{ background: {SURFACE_3}; border-color: {ACCENT_DIM}; }}
    QPushButton:pressed {{ background: {SURFACE}; }}
    QPushButton:disabled {{ color: {TEXT_FAINT}; border-color: {BORDER_SOFT}; }}

    QPushButton#primary {{
        background: {ACCENT};
        border: 1px solid {ACCENT};
        color: #16091F;
    }}
    QPushButton#primary:hover {{ background: #B975F9; border-color: #B975F9; }}
    QPushButton#primary:disabled {{ background: {SURFACE_2}; color: {TEXT_FAINT}; border-color: {BORDER}; }}

    QPushButton#ghost {{
        background: transparent;
        border: 1px solid {BORDER};
        color: {TEXT_MUTED};
    }}
    QPushButton#ghost:hover {{ color: {TEXT}; border-color: {ACCENT_DIM}; }}

    QPushButton#danger:hover {{ border-color: {DANGER}; color: {DANGER}; }}

    QPushButton#windowButton, QPushButton#closeButton {{
        background: transparent;
        border: none;
        border-radius: 7px;
        padding: 4px 10px;
        font-size: 15px;
        font-weight: 500;
        color: {TEXT_MUTED};
    }}
    QPushButton#windowButton:hover {{ background: {SURFACE_2}; color: {TEXT}; }}
    QPushButton#closeButton:hover {{ background: {DANGER}; color: #1A0A0A; }}

    QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox, QPlainTextEdit {{
        background: {SURFACE_2};
        border: 1px solid {BORDER};
        border-radius: 8px;
        padding: 7px 10px;
        font-size: 12px;
        selection-background-color: {ACCENT_DIM};
    }}
    QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QPlainTextEdit:focus {{
        border-color: {ACCENT};
    }}
    QComboBox::drop-down {{ border: none; width: 22px; }}
    QComboBox::down-arrow {{
        image: url({ASSETS}/chevron.svg);
        width: 12px;
        height: 12px;
        margin-right: 9px;
    }}
    QComboBox QAbstractItemView {{
        background: {SURFACE_2};
        border: 1px solid {BORDER};
        border-radius: 8px;
        padding: 4px;
        outline: none;
        selection-background-color: {ACCENT_GLOW};
    }}

    QSlider::groove:horizontal {{
        height: 5px;
        background: {SURFACE_3};
        border-radius: 3px;
    }}
    QSlider::sub-page:horizontal {{
        background: {ACCENT};
        border-radius: 3px;
    }}
    QSlider::handle:horizontal {{
        background: #F4EEFF;
        border: 3px solid {ACCENT};
        width: 10px;
        height: 10px;
        margin: -6px 0;
        border-radius: 8px;
    }}
    QSlider::handle:horizontal:hover {{ border-color: #C68CFF; }}
    QSlider::groove:horizontal:disabled {{ background: {BORDER_SOFT}; }}
    QSlider::sub-page:horizontal:disabled {{ background: {BORDER}; }}
    QSlider::handle:horizontal:disabled {{ background: {TEXT_FAINT}; border-color: {BORDER}; }}

    QListWidget {{
        background: transparent;
        border: none;
        outline: none;
    }}
    QListWidget::item {{
        background: {SURFACE_2};
        border: 1px solid {BORDER_SOFT};
        border-radius: 10px;
        padding: 6px;
        margin-bottom: 6px;
    }}
    QListWidget::item:hover {{ border-color: {ACCENT_DIM}; }}
    QListWidget::item:selected {{
        background: {ACCENT_GLOW};
        border-color: {ACCENT};
    }}

    QListWidget#compactList::item {{
        background: {SURFACE_2};
        border: 1px solid {BORDER_SOFT};
        border-radius: 7px;
        padding: 5px 9px;
        margin-bottom: 4px;
        font-size: 12px;
        font-family: "Cascadia Mono", "Consolas", monospace;
    }}

    QScrollArea {{ background: transparent; border: none; }}
    QScrollBar:vertical {{
        background: transparent; width: 8px; margin: 2px;
    }}
    QScrollBar::handle:vertical {{
        background: {BORDER}; border-radius: 4px; min-height: 30px;
    }}
    QScrollBar::handle:vertical:hover {{ background: {ACCENT_DIM}; }}
    QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; }}
    QScrollBar::add-page, QScrollBar::sub-page {{ background: transparent; }}

    QCheckBox {{ font-size: 12px; spacing: 8px; }}
    QCheckBox::indicator {{
        width: 16px; height: 16px;
        border: 1px solid {BORDER};
        border-radius: 5px;
        background: {SURFACE_2};
    }}
    QCheckBox::indicator:checked {{
        background: {ACCENT};
        border-color: {ACCENT};
    }}

    QToolTip {{
        background: {SURFACE_3};
        border: 1px solid {BORDER};
        border-radius: 6px;
        padding: 5px 8px;
        color: {TEXT};
    }}

    QMenu {{
        background: {SURFACE_2};
        border: 1px solid {BORDER};
        border-radius: 10px;
        padding: 6px;
    }}
    QMenu::item {{ padding: 7px 22px 7px 14px; border-radius: 6px; font-size: 12px; }}
    QMenu::item:selected {{ background: {ACCENT_GLOW}; }}
    QMenu::separator {{ height: 1px; background: {BORDER_SOFT}; margin: 5px 8px; }}
    """
