import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import re
from pathlib import Path
from datetime import datetime
from io import BytesIO

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable, PageBreak,
)

# ==================================================================
# NUMBER FORMATTING — STANDAR INDONESIA (titik "." ribuan, koma "," desimal)
# ==================================================================
def format_number(value, decimals: int = 0) -> str:
    """Format angka standar Indonesia.
    format_number(1500) -> '1.500'
    format_number(25000.5, 1) -> '25.000,5'
    """
    if value is None:
        return "-"
    try:
        value = float(value)
    except (TypeError, ValueError):
        return str(value)
    if pd.isna(value):
        return "-"
    decimals = max(int(decimals), 0)
    text = f"{value:,.{decimals}f}"
    # tukar separator ribuan (",") <-> desimal (".") lewat placeholder aman
    return text.replace(",", "§").replace(".", ",").replace("§", ".")


def format_decimal(value, decimals: int = 2) -> str:
    """Alias eksplisit untuk nilai desimal (IPK, Recommendation Score, dst)."""
    return format_number(value, decimals=decimals)


def format_percentage(value, decimals: int = 1) -> str:
    """Format angka persentase standar Indonesia + akhiran '%'."""
    return f"{format_number(value, decimals=decimals)}%"


#kolom identifier (bukan "angka" secara semantik)
TABLE_ID_LIKE_COLUMNS = {"NIM"}

#override presisi desimal per label kolom formal (default: 0 utk bilangan bulat,
#1 utk desimal umum seperti rate/persentase)
TABLE_COLUMN_DECIMALS = {
    "IPK": 2,
    "Recommendation Score": 3,
    "Recommendation Score (SAW)": 3,
}


def format_table_cell(column_label: str, value):
    """Formatter satu pintu untuk sel numerik tabel — dipakai bersama oleh
    st.table (style_dataframe) dan Export PDF Report supaya format angka
    selalu konsisten di seluruh dashboard, tanpa perlu direvisi satu per satu
    di tiap tabel."""
    if value is None or pd.isna(value):
        return "-"
    if column_label in TABLE_ID_LIKE_COLUMNS:
        try:
            return str(int(value))
        except (TypeError, ValueError):
            return str(value)
    if not isinstance(value, (int, float, np.integer, np.floating)):
        return value
    decimals = TABLE_COLUMN_DECIMALS.get(column_label)
    if decimals is None:
        decimals = 0 if float(value).is_integer() else 1
    return format_number(value, decimals)


# ==================================================================
# PAGE CONFIG
# ==================================================================
st.set_page_config(
    page_title="Student Placement System",
    page_icon="assets/logo.png",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ==================================================================
# ICONOGRAPHY
# ==================================================================
ICONS = {
    "building": '<rect x="4" y="3" width="16" height="18" rx="1"/>'
                '<rect x="7" y="6.3" width="2.4" height="2.4"/>'
                '<rect x="14.6" y="6.3" width="2.4" height="2.4"/>'
                '<rect x="7" y="11" width="2.4" height="2.4"/>'
                '<rect x="14.6" y="11" width="2.4" height="2.4"/>'
                '<rect x="9.8" y="15.7" width="4.4" height="5.3"/>',
    "file": '<path d="M6 2h9l5 5v15H6z"/><path d="M15 2v5h5"/>'
            '<line x1="9" y1="13" x2="15" y2="13"/><line x1="9" y1="17" x2="15" y2="17"/>',
    "graduation": '<path d="M2 9l10-5 10 5-10 5-10-5z"/>'
                  '<path d="M6 11.5v5c0 1.4 2.7 2.5 6 2.5s6-1.1 6-2.5v-5"/>'
                  '<line x1="22" y1="9" x2="22" y2="15.5"/>',
    "target": '<circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="5.2"/>'
              '<circle cx="12" cy="12" r="1.4" fill="currentColor"/>',
    "package": '<path d="M3 8l9-5 9 5-9 5-9-5z"/><path d="M3 8v9l9 5 9-5V8"/>'
               '<line x1="12" y1="13" x2="12" y2="22"/>',
    "check": '<circle cx="12" cy="12" r="9"/><polyline points="8 12.5 11 15.5 16 9"/>',
    "palette": '<path d="M12 3a9 9 0 1 0 0 18c1.1 0 1.6-.8 1.1-1.7-.3-.5-.1-1.1.5-1.3H15a4 4 0 0 0 4-4c0-6-3.1-11-7-11z"/>'
               '<circle cx="8" cy="10" r="1" fill="currentColor"/>'
               '<circle cx="12" cy="7.8" r="1" fill="currentColor"/>'
               '<circle cx="15.8" cy="10" r="1" fill="currentColor"/>',
    "pin": '<path d="M12 21s7-6.3 7-11.5A7 7 0 0 0 5 9.5C5 14.7 12 21 12 21z"/>'
           '<circle cx="12" cy="9.5" r="2.3"/>',
    "refresh": '<path d="M4 4v5h5"/><path d="M20 20v-5h-5"/>'
               '<path d="M5.5 15A8 8 0 0 0 19 9"/><path d="M18.5 9A8 8 0 0 0 5 15"/>',
    "download": '<path d="M12 3v12"/><polyline points="7 11 12 16 17 11"/><path d="M4 19h16"/>',
    "search": '<circle cx="10.5" cy="10.5" r="6.5"/><line x1="20" y1="20" x2="15.5" y2="15.5"/>',
    "moon": '<path d="M20 14.5A8.5 8.5 0 1 1 9.5 4a6.5 6.5 0 0 0 10.5 10.5z"/>',
    "sun": '<circle cx="12" cy="12" r="4.2"/><line x1="12" y1="2.5" x2="12" y2="5"/>'
           '<line x1="12" y1="19" x2="12" y2="21.5"/><line x1="2.5" y1="12" x2="5" y2="12"/>'
           '<line x1="19" y1="12" x2="21.5" y2="12"/><line x1="4.9" y1="4.9" x2="6.6" y2="6.6"/>'
           '<line x1="17.4" y1="17.4" x2="19.1" y2="19.1"/><line x1="4.9" y1="19.1" x2="6.6" y2="17.4"/>'
           '<line x1="17.4" y1="6.6" x2="19.1" y2="4.9"/>',
    "users": '<circle cx="9" cy="8" r="3.2"/><path d="M2.5 20c0-3.6 2.9-6 6.5-6s6.5 2.4 6.5 6"/>'
             '<circle cx="17" cy="9" r="2.6"/><path d="M15.5 14.2c2.7.4 4.5 2.4 4.5 5.8"/>',
    "user-x": '<circle cx="10" cy="8" r="3.2"/><path d="M3.5 20c0-3.6 2.9-6 6.5-6s6.5 2.4 6.5 6"/>'
              '<line x1="17" y1="8" x2="21" y2="12"/><line x1="21" y1="8" x2="17" y2="12"/>',
    "alert": '<path d="M12 3.5l9.5 16.5H2.5z"/><line x1="12" y1="9.5" x2="12" y2="14"/>'
             '<circle cx="12" cy="17" r="0.9" fill="currentColor"/>',
    "funnel": '<path d="M3 4h18l-7 8.5V19l-4 2v-8.5z"/>',
    "chart-line": '<path d="M3 20h18"/><path d="M5 16l4-5 3 3 6-8"/>',
    "list": '<line x1="8" y1="6" x2="21" y2="6"/><line x1="8" y1="12" x2="21" y2="12"/>'
            '<line x1="8" y1="18" x2="21" y2="18"/><circle cx="4" cy="6" r="1" fill="currentColor"/>'
            '<circle cx="4" cy="12" r="1" fill="currentColor"/><circle cx="4" cy="18" r="1" fill="currentColor"/>',
    "clock": '<circle cx="12" cy="12" r="9"/><polyline points="12 7 12 12 16 14"/>',
    "filter": '<path d="M3 4h18l-6.5 8v6l-5 3v-9z"/>',
}

def icon(name: str, color: str = "currentColor", size: int = 18, stroke_width: float = 1.8) -> str:
    """Kembalikan markup SVG inline siap ditempel di HTML manapun (kartu KPI,
    judul section, sidebar). Tidak ada file/emoji eksternal yang dipakai."""
    inner = ICONS.get(name, "")
    return (
        f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" '
        f'stroke="{color}" stroke-width="{stroke_width}" stroke-linecap="round" '
        f'stroke-linejoin="round" style="vertical-align:-3px; flex-shrink:0;">{inner}</svg>'
    )

# ==================================================================
# DESIGN TOKENS — LIGHT_THEME / DARK_THEME
# ==================================================================
# ---- light mode ----
LIGHT_THEME = {
    "name": "Light",
    # --- surfaces ---
    "background": "#F4F6F9",
    "surface": "#FFFFFF",
    "card": "#FFFFFF",
    "sidebar": "#FFFFFF",
    "header_bg": "#FFFFFF",
    "footer_bg": "#F4F6F9",
    "paper_bg": "#FFFFFF",
    "chart_bg": "#FFFFFF",
    # --- text ---
    "text": "#101828",
    "text_secondary": "#475467",
    "caption": "#667085",
    # --- structure ---
    "border": "#D0D5DD",
    "divider": "#E4E7EC",
    "table_header": "#EEF2F6",
    "table_body": "#FFFFFF",
    "table_border": "#E4E7EC",
    "table_stripe": "#F8FAFC",
    # --- brand / semantic ---
    "primary": "#1D4ED8",
    "secondary": "#B45309",
    "accent": "#1D4ED8",
    "success": "#067647",
    "warning": "#B45309",
    "danger": "#B42318",
    "info": "#175CD3",
    # --- interaction states ---
    "hover": "#EFF4FF",
    "selection": "#DBEAFE",
    "focus": "#1D4ED8",
    "shadow": "rgba(16, 24, 40, 0.07)",
    "hover_shadow": "rgba(16, 24, 40, 0.13)",
    # --- buttons ---
    "button": "#1D4ED8",
    "button_hover": "#1E40AF",
    "button_text": "#FFFFFF",
    # --- tooltip / legend ---
    "tooltip_bg": "#101828",
    "tooltip_text": "#FFFFFF",
    "legend": "#344054",
    # --- plotly ---
    "plotly_template": "plotly_white",
    "grid_color": "#E4E7EC",
    "axis_color": "#475467",
    "chart_colors": {
        "primary": "#1D4ED8",
        "secondary": "#B45309",
        "tertiary": "#067647",
        "quaternary": "#B42318",
        "muted": "#98A2B3",
        "fallback": "#7A5CC0",
    },
    "chart_seq": ["#1D4ED8", "#B45309", "#067647", "#B42318",
                  "#6941C6", "#0E7490", "#C11574", "#3B7C0F"],
}

# ---- dark mode ----
DARK_THEME = {
    "name": "Dark",
    # --- surfaces ---
    "background": "#12141A",
    "surface": "#1B1E26",
    "card": "#1E212A",
    "sidebar": "#171A21",
    "header_bg": "#171A21",
    "footer_bg": "#12141A",
    "paper_bg": "#1E212A",
    "chart_bg": "#1E212A",
    # --- text ---
    "text": "#F0F2F5",
    "text_secondary": "#AEB4C2",
    "caption": "#8B93A5",
    # --- structure ---
    "border": "#333846",
    "divider": "#2A2E38",
    "table_header": "#252933",
    "table_body": "#1E212A",
    "table_border": "#333846",
    "table_stripe": "#232630",
    # --- brand / semantic ---
    "primary": "#5B8DEF",
    "secondary": "#E3A24D",
    "accent": "#5B8DEF",
    "success": "#3FC088",
    "warning": "#E3A24D",
    "danger": "#F0685C",
    "info": "#6FA8F5",
    # --- interaction states ---
    "hover": "#232838",
    "selection": "#2C3A5C",
    "focus": "#5B8DEF",
    "shadow": "rgba(0, 0, 0, 0.32)",
    "hover_shadow": "rgba(0, 0, 0, 0.48)",
    # --- buttons ---
    "button": "#5B8DEF",
    "button_hover": "#7CA5F5",
    "button_text": "#0D0F13",
    # --- tooltip / legend ---
    "tooltip_bg": "#F0F2F5",
    "tooltip_text": "#12141A",
    "legend": "#C7CCD8",
    # --- plotly ---
    "plotly_template": "plotly_dark",
    "grid_color": "#2A2E38",
    "axis_color": "#AEB4C2",
    "chart_colors": {
        "primary": "#5B8DEF",
        "secondary": "#E3A24D",
        "tertiary": "#3FC088",
        "quaternary": "#F0685C",
        "muted": "#6C7386",
        "fallback": "#B39DDB",
    },
    "chart_seq": ["#5B8DEF", "#E3A24D", "#3FC088", "#F0685C",
                  "#9B8AFB", "#4DD0E1", "#F172B6", "#8BC34A"],
}

def get_active_theme() -> dict:
    return DARK_THEME if st.session_state.get("dark_mode", True) else LIGHT_THEME

def inject_theme(theme: dict) -> None:
    css = f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

    html, body, [class*="css"] {{
        font-family:'Inter','Segoe UI',sans-serif;
    }}

    :root {{
        color-scheme: {"dark" if theme["name"] == "Dark" else "light"};
    }}

    .stApp {{
        background:{theme['background']} !important;
        color:{theme['text']} !important;
    }}

    .block-container {{
        padding-top:24px;
        padding-left:32px;
        padding-right:32px;
        padding-bottom:32px;
        max-width:1600px;
    }}

    /* ---------- STREAMLIT DEFAULT HEADER BAR ---------- */
    header[data-testid="stHeader"] {{
        background:transparent !important;
        box-shadow:none !important;
    }}
    div[data-testid="stDecoration"] {{
        display:none !important;
    }}
    header[data-testid="stHeader"] svg {{
        fill:{theme['text']} !important;
    }}
    header[data-testid="stHeader"] button {{
        color:{theme['text']} !important;
    }}

    /* ---------- FOCUS VISIBILITY ---------- */
    *:focus-visible {{
        outline:2px solid {theme['focus']} !important;
        outline-offset:2px;
    }}

    /* ---------- SIDEBAR ---------- */
    section[data-testid="stSidebar"],
    div[data-testid="stSidebar"],
    div[data-testid="stSidebarContent"],
    div[data-testid="stSidebarUserContent"] {{
        background:{theme['sidebar']} !important;
        border-right:1px solid {theme['border']};
    }}
    section[data-testid="stSidebar"] *,
    div[data-testid="stSidebar"] * {{
        color:{theme['text']} !important;
    }}
    section[data-testid="stSidebar"] .stCaption,
    section[data-testid="stSidebar"] small,
    div[data-testid="stSidebar"] .stCaption,
    div[data-testid="stSidebar"] small {{
        color:{theme['caption']} !important;
    }}

    /* ---------- TYPOGRAPHY HIERARCHY ---------- */
    h1 {{ color:{theme['text']}; font-weight:800; font-size:28px; letter-spacing:-0.02em; }}
    h2 {{ color:{theme['text']}; font-weight:700; font-size:22px; letter-spacing:-0.01em; }}
    h3 {{ color:{theme['text']}; font-weight:700; font-size:18px; }}
    h4 {{ color:{theme['text']}; font-weight:600; font-size:15px; }}
    h5, h6 {{ color:{theme['text']}; font-weight:600; }}
    p, span, label, .stMarkdown {{ color:{theme['text']}; }}
    .stCaption, [data-testid="stCaptionContainer"] {{
        color:{theme['caption']} !important;
        font-size:13px;
    }}

    /* ---------- DASHBOARD TITLE BLOCK ---------- */
    .dash-title {{
        font-size:26px;
        font-weight:800;
        letter-spacing:-0.02em;
        color:{theme['text']};
        margin-bottom:2px;
        display:flex;
        align-items:center;
        gap:10px;
    }}
    .dash-subtitle {{
        font-size:14px;
        font-weight:500;
        color:{theme['text_secondary']};
        margin-top:0;
    }}

    /* ---------- SECTION TITLE ---------- */
    .section-title {{
        display:flex;
        align-items:center;
        gap:8px;
        font-size:16px;
        font-weight:700;
        color:{theme['text']};
        margin:8px 0 16px 0;
    }}
    .section-caption {{
        font-size:13px;
        color:{theme['caption']};
        margin-top:-12px;
        margin-bottom:16px;
    }}

    /* ---------- ST.METRIC ---------- */
    div[data-testid="stMetric"] {{
        background:{theme['card']};
        border-radius:12px;
        padding:16px;
        border:1px solid {theme['border']};
        box-shadow:0 1px 3px {theme['shadow']};
    }}
    div[data-testid="stMetricLabel"] p {{
        color:{theme['caption']} !important;
        font-size:13px;
        font-weight:500;
    }}
    div[data-testid="stMetricValue"] {{
        color:{theme['text']};
        font-weight:700;
    }}
    div[data-testid="stMetricDelta"] {{
        font-weight:500;
    }}

    /* ---------- CUSTOM KPI CARD ---------- */
    .kpi-card {{
        background:{theme['card']};
        border-radius:12px;
        padding:20px;
        border:1px solid {theme['border']};
        box-shadow:0 1px 3px {theme['shadow']};
        transition:box-shadow .2s ease, transform .2s ease;
        min-height:132px;
        height:100%;
    }}
    .kpi-card:hover {{
        transform:translateY(-2px);
        box-shadow:0 8px 20px {theme['hover_shadow']};
    }}
    .kpi-icon-row {{
        display:flex;
        align-items:center;
        justify-content:space-between;
        margin-bottom:12px;
    }}
    .kpi-icon-badge {{
        width:36px;
        height:36px;
        border-radius:9px;
        display:flex;
        align-items:center;
        justify-content:center;
        background:{theme['hover']};
    }}
    .kpi-title {{
        color:{theme['caption']};
        font-size:13px;
        font-weight:600;
        text-transform:uppercase;
        letter-spacing:0.03em;
    }}
    .kpi-value {{
        font-size:30px;
        font-weight:800;
        line-height:1.15;
        letter-spacing:-0.01em;
    }}
    .kpi-delta {{
        margin-top:10px;
        color:{theme['text_secondary']};
        font-size:12.5px;
        font-weight:500;
    }}

    /* ---------- STUDENT READINESS TAB MENU ---------- */
    div[data-testid="stVerticalBlockBorderWrapper"] {{
        background:{theme['card']};
        border-radius:12px;
        border:1px solid {theme['border']};
    }}

    /* ---------- EXPANDER ---------- */
    div[data-testid="stExpander"] {{
        background:{theme['card']};
        border-radius:12px;
        border:1px solid {theme['border']};
        overflow:hidden;
    }}
    div[data-testid="stExpander"] summary {{
        color:{theme['text']};
        font-weight:600;
    }}

    /* ---------- FORM WIDGETS ---------- */
    div[data-baseweb="select"] > div,
    div[data-baseweb="base-input"],
    div[data-baseweb="input"],
    div[data-baseweb="input"] input,
    div[data-baseweb="datepicker"] input,
    div[data-testid="stDateInput"] input,
    div[data-testid="stTextInput"] input {{
        background:{theme['surface']} !important;
        color:{theme['text']} !important;
        border-color:{theme['border']} !important;
    }}
    input::placeholder, textarea::placeholder {{
        color:{theme['caption']} !important;
        opacity:1 !important;
    }}
 
    /* --------- MULTISELECT/SELECTBOX/DATE PICKER --------- */
    div[data-baseweb="popover"] div[data-baseweb="menu"],
    ul[data-baseweb="menu"] {{
        background:{theme['surface']} !important;
        border:1px solid {theme['border']};
    }}
    li[role="option"] {{
        color:{theme['text']} !important;
    }}
    li[role="option"]:hover, li[aria-selected="true"] {{
        background:{theme['hover']} !important;
    }}

    /* chip/tag terpilih pada multiselect */
    span[data-baseweb="tag"] {{
        border-radius:6px;
    }}

    /* ---------- TABLE ---------- */
    div[data-testid="stTable"] {{
        border-radius:12px;
        overflow:hidden;
        border:1px solid {theme['table_border']};
    }}
    div[data-testid="stTable"] table {{
        background:{theme['table_body']} !important;
        color:{theme['text']} !important;
        width:100%;
    }}
    div[data-testid="stTable"] thead th {{
        background:{theme['table_header']} !important;
        color:{theme['text']} !important;
        font-weight:600 !important;
        border-bottom:1px solid {theme['table_border']} !important;
    }}
    div[data-testid="stTable"] tbody td {{
        border-bottom:1px solid {theme['table_border']} !important;
        color:{theme['text']} !important;
    }}
    div[data-testid="stDataFrame"] {{
        border-radius:12px;
        overflow:hidden;
        border:1px solid {theme['table_border']};
    }}

    /* ---------- BUTTONS ---------- */
    .stButton > button, .stDownloadButton > button {{
        border-radius:8px;
        background:{theme['button']};
        color:{theme['button_text']};
        border:1px solid {theme['button']};
        padding:8px 16px;
        font-weight:600;
        font-size:13.5px;
        transition:background-color .15s ease, border-color .15s ease;
    }}
    .stButton > button:hover, .stDownloadButton > button:hover {{
        background:{theme['button_hover']};
        border-color:{theme['button_hover']};
        color:{theme['button_text']};
    }}
    .stButton > button:focus-visible, .stDownloadButton > button:focus-visible {{
        outline:2px solid {theme['focus']};
        outline-offset:2px;
    }}

    /* ---------- DIVIDER ---------- */
    hr {{ border-color:{theme['divider']}; margin:16px 0; }}

    /* ---------- ALERT / INFO / SUCCESS / WARNING BOX ---------- */
    div[data-testid="stAlert"] {{
        border-radius:10px;
        font-size:13.5px;
    }}

    /* ---------- TABS ---------- */
    div[data-testid="stTabs"] button[data-baseweb="tab"] {{
        color:{theme['text_secondary']};
        font-weight:600;
        font-size:14px;
        height:44px;
    }}
    div[data-testid="stTabs"] button[data-baseweb="tab"][aria-selected="true"] {{
        color:{theme['primary']};
    }}
    div[data-testid="stTabs"] [data-baseweb="tab-highlight"] {{
        background-color:{theme['primary']};
    }}
    div[data-testid="stTabs"] [data-baseweb="tab-border"] {{
        background-color:{theme['divider']};
    }}

    /* ---------- TOGGLE ---------- */
    div[data-testid="stToggle"] label p {{ color:{theme['text']}; font-weight:500; }}

    /* ---------- MISC ---------- */
    footer {{visibility:hidden;}}
    #MainMenu {{visibility:hidden;}}
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)


# ==================================================================
# CHART / CARD / TABLE HELPER FUNCTIONS
# ==================================================================
def apply_chart_theme(fig, theme, height=340, xaxis_title=None, yaxis_title=None,
                       showlegend=True, legend_orientation=None, legend_y=None,
                       margin=None):
    """Terapkan styling theme-aware (template, warna, grid, font) ke sebuah
    Plotly figure — sumber tunggal styling chart di seluruh dashboard."""

    xaxis = dict(gridcolor=theme["grid_color"], color=theme["axis_color"], linecolor=theme["border"])
    if xaxis_title is not None:
        xaxis["title"] = dict(text=xaxis_title, font=dict(size=12.5, color=theme["text_secondary"]))

    yaxis = dict(gridcolor=theme["grid_color"], color=theme["axis_color"], linecolor=theme["border"])
    if yaxis_title is not None:
        yaxis["title"] = dict(text=yaxis_title, font=dict(size=12.5, color=theme["text_secondary"]))

    legend = dict(font=dict(color=theme["legend"], size=12))
    if legend_orientation:
        legend["orientation"] = legend_orientation
    if legend_y is not None:
        legend["y"] = legend_y

    fig.update_layout(
        height=height,
        template=theme["plotly_template"],
        paper_bgcolor=theme["paper_bg"],
        plot_bgcolor=theme["chart_bg"],
        font=dict(family="Inter, Segoe UI, sans-serif", size=13, color=theme["text"]),
        legend=legend,
        showlegend=showlegend,
        xaxis=xaxis,
        yaxis=yaxis,
        margin=margin or dict(l=16, r=16, t=32, b=16),
        hoverlabel=dict(
            bgcolor=theme["tooltip_bg"],
            font=dict(color=theme["tooltip_text"], size=12.5, family="Inter, Segoe UI, sans-serif"),
            bordercolor=theme["tooltip_bg"],
        ),
    )
    return fig

# ---- render chart ----
def render_chart(fig, theme, height=340, **layout_kwargs):

    fig = apply_chart_theme(
        fig,
        theme,
        height=height,
        **layout_kwargs
    )

    fig.update_layout(
        separators=",."
    )

    with st.container(border=True):
        st.plotly_chart(
            fig,
            use_container_width=True,
            theme=None,
            config={
                "displaylogo": False
            }
        )

# ---- section title ----
def section_title(title: str, theme: dict, icon_name: str = None, caption: str = None) -> None:
    icon_html = icon(icon_name, color=theme["primary"], size=18) if icon_name else ""
    st.markdown(
        f'<div class="section-title">{icon_html}<span>{title}</span></div>',
        unsafe_allow_html=True,
    )
    if caption:
        st.markdown(f'<div class="section-caption">{caption}</div>', unsafe_allow_html=True)

# ---- chart title ----
def chart_title(title: str, theme: dict, icon_name: str = None) -> None:
    section_title(title, theme, icon_name=icon_name)

# ---- kpi card ----
def kpi_card(theme, title, value, delta, color, icon_name):
    html = f"""
    <div class="kpi-card">
        <div class="kpi-icon-row">
            <div class="kpi-title">{title}</div>
            <div class="kpi-icon-badge">{icon(icon_name, color=color, size=18)}</div>
        </div>
        <div class="kpi-value" style="color:{color};">{value}</div>
        <div class="kpi-delta">{delta}</div>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)

# ---- status card ----
def metric_status_card(theme, icon_name, caption, value, value_color, status_type="info", status_value=""):
    with st.container(border=True):
        st.markdown(
            f'<div style="width:34px;height:34px;border-radius:9px;background:{theme["hover"]};'
            f'display:flex;align-items:center;justify-content:center;margin-bottom:8px;">'
            f'{icon(icon_name, color=value_color, size=18)}</div>',
            unsafe_allow_html=True,
        )
        st.caption(caption)
        st.markdown(f"<h2 style='color:{value_color}; margin-top:2px;'>{value}</h2>", unsafe_allow_html=True)
        if status_type == "success":
            st.success(status_value)
        elif status_type == "info":
            st.info(status_value)
        elif status_type == "progress":
            st.progress(status_value)

# ---- data frame ----
def style_dataframe(df: pd.DataFrame, theme: dict):
    # format_table_cell() dipanggil per kolom numerik sehingga judul kolom
    # (mis. "NIM", "IPK", "Recommendation Score") menentukan presisi & separator
    # standar Indonesia — satu sumber format yang sama dipakai Export PDF Report.
    numeric_cols = df.select_dtypes(include=["number"]).columns
    formatters = {col: (lambda v, c=col: format_table_cell(c, v)) for col in numeric_cols}
    return (
        df.style
        .format(formatters, na_rep="-")
        .hide(axis="index")
        .set_table_styles([
            {"selector": "th", "props": [
                ("background-color", theme["table_header"]),
                ("color", theme["text"]),
                ("font-weight", "600"),
                ("border-bottom", f"1px solid {theme['table_border']}"),
            ]},
            {"selector": "td", "props": [
                ("border-bottom", f"1px solid {theme['table_border']}"),
            ]},
        ])
        .apply(lambda col: [
            f"background-color:{theme['table_stripe']}" if i % 2 else f"background-color:{theme['table_body']}"
            for i in range(len(col))
        ], axis=0)
    )

# ------------------------------------------------------------------
# FORMAL COLUMN LABELS (RENAME COLUMN LABELS)
# ------------------------------------------------------------------
COLUMN_LABEL_OVERRIDES = {
    "id_talent_req": "ID Talent Request",
    "id_company": "ID Perusahaan",
    "id_tracking_company": "ID Tracking Perusahaan",
    "id_tracking_student": "ID Tracking Mahasiswa",
    "nama_perusahaan": "Nama Perusahaan",
    "nama_posisi": "Posisi",
    "posisi": "Posisi",
    "position": "Posisi",
    "headcount": "Headcount",
    "request_date": "Tanggal Permintaan",
    "send_date": "Tanggal Pengiriman",
    "progress": "Status Progres",
    "progress_student": "Status Progres Mahasiswa",
    "rejection": "Outcome Seleksi",
    "fu_ghosting_status": "Status Follow-up/Ghosting",
    "outcome_effective": "Outcome Seleksi (Follow-up/Ghosting Otomatis)",
    "is_followup": "Status Follow-up",
    "is_ghosting": "Status Ghosting",
    "student_name": "Nama Mahasiswa",
    "company": "Perusahaan",
    "last_update": "Update Terakhir",
    "nama": "Nama",
    "program_studi": "Program Studi",
    "semester": "Semester",
    "internship_semester": "Semester Magang",
    "alasan": "Alasan Belum Eligible",
    "jumlah_dikirimkan": "Jumlah Dikirimkan",
    "jumlah_permintaan": "Jumlah Permintaan",
    "domisili": "Domisili",
    "ketersediaan": "Ketersediaan",
    "status": "Status",
    "jenis_penempatan": "Jenis Penempatan",
    "bidang_studi_dibutuhkan": "Bidang Studi Dibutuhkan",
    "bidang_studi_dicari": "Bidang Studi Dicari",
    "bidang_minat": "Bidang Minat",
    "minimum_semester": "Minimum Semester",
    "working_arrangement": "Skema Kerja",
    "renumerasi": "Remunerasi",
    "durasi": "Durasi",
}

def to_formal_columns(df: pd.DataFrame) -> pd.DataFrame:
    def _label(col):
        col_str = str(col)
        if col_str in COLUMN_LABEL_OVERRIDES:
            return COLUMN_LABEL_OVERRIDES[col_str]
        if col_str != col_str.lower() or " " in col_str:
            return col_str
        return col_str.replace("_", " ").strip().title()
    return df.rename(columns=_label)

def render_table(df: pd.DataFrame, theme: dict, height=None):
    st.table(style_dataframe(to_formal_columns(df), theme))

# ==================================================================
# DSS / MCDM ENGINE — WEIGHTED SCORING MODEL (SAW)
# ==================================================================
SAW_WEIGHTS_C2S = {  #company -> student (dipakai di Talent Request tertentu)
    "field_match": 0.30,     #kecocokan program studi vs bidang studi yang dibutuhkan
    "readiness": 0.25,       #kelengkapan CV/portofolio/status/ketersediaan
    "ipk": 0.15,             #performa akademik (IPK)
    "semester_fit": 0.10,    #semester vs minimum semester requirement
    "placement_type": 0.10,  #jenis penempatan diminati vs jenis penempatan
    "track_record": 0.10,    #historical placement rate program studi yang bersangkutan
}

SAW_WEIGHTS_S2C = {  #student -> company (dipakai untuk satu mahasiswa tertentu)
    "field_match": 0.30,     #kecocokan program studi vs bidang studi dicari perusahaan
    "opportunity": 0.25,     #historical acceptance rate perusahaan (peluang diterima)
    "placement_type": 0.15,  #jenis penempatan diminati vs jenis penempatan yang dibuka
    "readiness": 0.15,       #kelengkapan CV/portofolio/status/ketersediaan mahasiswa
    "ipk": 0.10,             #performa akademik (IPK)
    "semester_fit": 0.05,    #semester mahasiswa vs minimum semester requirement
}

def _split_field_tokens(text) -> list:
    if not isinstance(text, str) or not text.strip():
        return []
    return [t.strip().lower() for t in text.split(",") if t.strip()]

def field_match_score(program_studi, bidang_minat, required_tokens: list) -> float:
    if not required_tokens:
        return 0.0
    prodi_l = str(program_studi).strip().lower()
    minat_l = str(bidang_minat).strip().lower()
    for token in required_tokens:
        if token and (token in prodi_l or prodi_l in token):
            return 1.0
    for token in required_tokens:
        if token and (token in minat_l or minat_l in token):
            return 0.6
    return 0.0

def readiness_component(cv, portofolio, status, ketersediaan) -> float:
    checks = [cv == "Ada", portofolio == "Ada", status == "Active", ketersediaan == "Available"]
    return sum(checks) / 4.0

def semester_fit_score(semester, minimum_semester) -> float:
    try:
        minsem = float(minimum_semester)
    except (TypeError, ValueError):
        return 1.0
    if minsem <= 0:
        return 1.0
    return min(float(semester) / minsem, 1.0)

def build_prodi_track_record(ts_scope: pd.DataFrame, sa_scope: pd.DataFrame) -> pd.Series:
    merged = ts_scope.merge(sa_scope[["NIM", "program_studi"]], on="NIM", how="left")
    if merged.empty:
        return pd.Series(dtype=float)
    return merged.groupby("program_studi")["progress_student"].apply(
        lambda s: (s == "Placement").sum() / len(s) if len(s) else 0.0
    )

def build_company_track_record(ts_scope: pd.DataFrame):
    if ts_scope.empty:
        return pd.Series(dtype=float), 0.0
    grp = ts_scope.groupby("company").agg(
        total=("id_tracking_student", "size"),
        placement=("progress_student", lambda x: (x == "Placement").sum()),
    )
    rate = grp["placement"] / grp["total"]
    overall = (ts_scope["progress_student"] == "Placement").mean()
    return rate, float(overall)

def score_students_for_request(req_row: pd.Series, candidates: pd.DataFrame,
                                prodi_track: pd.Series) -> pd.DataFrame:
    tokens = _split_field_tokens(req_row.get("bidang_studi_dibutuhkan", ""))
    overall_track = float(prodi_track.mean()) if len(prodi_track) else 0.0
    minimum_semester = req_row.get("minimum_semester")
    jenis_req = str(req_row.get("jenis_penempatan", "")).strip()

    def _score(row):
        field = field_match_score(row["program_studi"], row.get("bidang_minat", ""), tokens)
        readiness = readiness_component(row["CV"], row["portofolio"], row["status"], row["ketersediaan"])
        ipk = min(float(row["IPK"]) / 4.0, 1.0)
        sem = semester_fit_score(row["semester"], minimum_semester)
        ptype = 1.0 if str(row.get("jenis_penempatan_diminati", "")).strip() == jenis_req else 0.0
        track = float(prodi_track.get(row["program_studi"], overall_track))
        total = (
            field * SAW_WEIGHTS_C2S["field_match"]
            + readiness * SAW_WEIGHTS_C2S["readiness"]
            + ipk * SAW_WEIGHTS_C2S["ipk"]
            + sem * SAW_WEIGHTS_C2S["semester_fit"]
            + ptype * SAW_WEIGHTS_C2S["placement_type"]
            + track * SAW_WEIGHTS_C2S["track_record"]
        )
        return pd.Series({
            "field_match": field, "readiness": readiness, "ipk_norm": ipk,
            "semester_fit": sem, "placement_type": ptype, "track_record": track,
            "score": total,
        })

    scored = candidates.apply(_score, axis=1)
    return pd.concat([candidates.reset_index(drop=True), scored.reset_index(drop=True)], axis=1)

def score_companies_for_student(stu_row: pd.Series, requests_pool: pd.DataFrame,
                                 company_track: pd.Series, overall_track: float) -> pd.DataFrame:
    readiness = readiness_component(stu_row["CV"], stu_row["portofolio"], stu_row["status"], stu_row["ketersediaan"])
    ipk = min(float(stu_row["IPK"]) / 4.0, 1.0)
    prodi = stu_row["program_studi"]
    minat = stu_row.get("bidang_minat", "")
    semester = stu_row["semester"]
    jenis_diminati = str(stu_row.get("jenis_penempatan_diminati", "")).strip()

    def _score(row):
        tokens = _split_field_tokens(row.get("bidang_studi_dibutuhkan", ""))
        field = field_match_score(prodi, minat, tokens)
        sem = semester_fit_score(semester, row.get("minimum_semester"))
        ptype = 1.0 if jenis_diminati == str(row.get("jenis_penempatan", "")).strip() else 0.0
        opp = float(company_track.get(row.get("nama_perusahaan"), overall_track))
        total = (
            field * SAW_WEIGHTS_S2C["field_match"]
            + opp * SAW_WEIGHTS_S2C["opportunity"]
            + ptype * SAW_WEIGHTS_S2C["placement_type"]
            + readiness * SAW_WEIGHTS_S2C["readiness"]
            + ipk * SAW_WEIGHTS_S2C["ipk"]
            + sem * SAW_WEIGHTS_S2C["semester_fit"]
        )
        return pd.Series({
            "field_match": field, "opportunity": opp, "placement_type": ptype,
            "readiness": readiness, "ipk_norm": ipk, "semester_fit": sem,
            "score": total,
        })

    scored = requests_pool.apply(_score, axis=1)
    out = pd.concat([requests_pool.reset_index(drop=True), scored.reset_index(drop=True)], axis=1)
    out["readiness"] = readiness
    out["ipk_norm"] = ipk
    return out

def build_reason_c2s(row) -> str:
    parts = []
    if row["field_match"] >= 1.0:
        parts.append(f"program studi {row['program_studi']} sesuai bidang yang dibutuhkan requirement")
    elif row["field_match"] >= 0.6:
        parts.append(f"bidang minat ({row.get('bidang_minat', '-')}) relevan dengan requirement")
    if row["readiness"] >= 1.0:
        parts.append("dokumen (CV/portofolio) dan status sudah lengkap serta siap ditempatkan")
    if row["ipk_norm"] >= 0.875:
        parts.append(f"IPK {format_decimal(row['IPK'], 2)} tergolong tinggi")
    if row["placement_type"] >= 1.0:
        parts.append("jenis penempatan sesuai preferensi mahasiswa")
    if row["track_record"] >= 0.5:
        parts.append(f"riwayat placement program studi ini cukup baik ({format_percentage(row['track_record'] * 100, 0)})")
    if not parts:
        parts.append("kecocokan dasar dengan requirement masih minim, perlu ditinjau manual")
    text = "; ".join(parts)
    return text[:1].upper() + text[1:] + "."

def build_improve_c2s(row) -> str:
    gaps = []
    if row["field_match"] < 0.6:
        gaps.append("kecocokan bidang studi/minat masih rendah")
    if row["readiness"] < 1.0:
        gaps.append("kelengkapan CV/portofolio/status/ketersediaan belum penuh")
    if row["semester_fit"] < 1.0:
        gaps.append("semester belum memenuhi minimum_semester requirement")
    if row["ipk_norm"] < 0.75:
        gaps.append("IPK relatif di bawah standar tinggi (< 3.0)")
    if row["placement_type"] < 1.0:
        gaps.append("jenis penempatan tidak sesuai preferensi mahasiswa")
    if not gaps:
        return "Tidak ada gap signifikan pada kriteria yang tersedia."
    text = "; ".join(gaps)
    return text[:1].upper() + text[1:] + "."

def build_reason_s2c(row) -> str:
    parts = []
    if row["field_match"] >= 1.0:
        parts.append("bidang studi yang dicari perusahaan sesuai dengan program studi mahasiswa")
    elif row["field_match"] >= 0.6:
        parts.append("bidang minat mahasiswa relevan dengan requirement perusahaan")
    if row["opportunity"] >= 0.5:
        parts.append(f"perusahaan ini memiliki riwayat acceptance rate cukup tinggi ({format_percentage(row['opportunity'] * 100, 0)})")
    if row["placement_type"] >= 1.0:
        parts.append("jenis penempatan yang dibuka sesuai preferensi mahasiswa")
    if row["semester_fit"] >= 1.0:
        parts.append("semester mahasiswa memenuhi syarat minimum requirement")
    if not parts:
        parts.append("kecocokan dasar masih minim, perlu ditinjau manual")
    text = "; ".join(parts)
    return text[:1].upper() + text[1:] + "."

# ==================================================================
# EXPORT EXECUTIVE REPORT (PDF)
# ==================================================================
PDF_INK = colors.HexColor("#101828")
PDF_MUTED = colors.HexColor("#667085")
PDF_PRIMARY = colors.HexColor("#1D4ED8")
PDF_BORDER = colors.HexColor("#D0D5DD")
PDF_HEADER_BG = colors.HexColor("#EEF2F6")
PDF_STRIPE = colors.HexColor("#F8FAFC")


def _md_bold_to_html(text: str) -> str:
    return re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", str(text))


def _pdf_styles():
    base = getSampleStyleSheet()
    styles = {
        "title": ParagraphStyle("RptTitle", parent=base["Title"], textColor=PDF_PRIMARY,
                                 fontSize=20, leading=24, spaceAfter=2, alignment=TA_LEFT),
        "subtitle": ParagraphStyle("RptSubtitle", parent=base["Normal"], textColor=PDF_MUTED,
                                    fontSize=10.5, leading=14, spaceAfter=10),
        "h1": ParagraphStyle("RptH1", parent=base["Heading1"], textColor=PDF_PRIMARY,
                              fontSize=14, leading=18, spaceBefore=14, spaceAfter=6),
        "h2": ParagraphStyle("RptH2", parent=base["Heading2"], textColor=PDF_INK,
                              fontSize=11.5, leading=15, spaceBefore=8, spaceAfter=4),
        "body": ParagraphStyle("RptBody", parent=base["Normal"], textColor=PDF_INK,
                                fontSize=9.5, leading=13.5, spaceAfter=4),
        "caption": ParagraphStyle("RptCaption", parent=base["Normal"], textColor=PDF_MUTED,
                                   fontSize=8.5, leading=12, spaceAfter=6),
        "bullet": ParagraphStyle("RptBullet", parent=base["Normal"], textColor=PDF_INK,
                                  fontSize=9.5, leading=13.5, spaceAfter=3, leftIndent=10,
                                  bulletIndent=0),
    }
    return styles


def _pdf_kv_table(pairs):
    rows = [[Paragraph(f"<b>{label}</b>", _pdf_styles()["body"]),
             Paragraph(str(value), _pdf_styles()["body"])] for label, value in pairs]
    t = Table(rows, colWidths=[7 * cm, 8 * cm], hAlign="LEFT")
    t.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("LINEBELOW", (0, 0), (-1, -1), 0.4, PDF_BORDER),
    ]))
    return t


def _pdf_df_table(df, col_widths=None, max_rows=10):
    styles = _pdf_styles()
    df_fmt = to_formal_columns(df.head(max_rows).copy())
    header = [Paragraph(f"<b>{c}</b>", styles["body"]) for c in df_fmt.columns]
    body_rows = []
    for _, row in df_fmt.iterrows():
        cells = []
        for col in df_fmt.columns:
            val = row[col]
            if pd.isna(val):
                text = "-"
            elif isinstance(val, (pd.Timestamp,)):
                text = val.strftime("%d-%m-%Y")
            elif isinstance(val, (int, float, np.integer, np.floating)) and not isinstance(val, bool):
                text = format_table_cell(col, val)
            else:
                text = str(val)
            cells.append(Paragraph(text, styles["body"]))
        body_rows.append(cells)
    data = [header] + body_rows
    n_cols = len(df_fmt.columns)
    widths = col_widths or [15 * cm / n_cols] * n_cols
    t = Table(data, colWidths=widths, repeatRows=1, hAlign="LEFT")
    style_cmds = [
        ("BACKGROUND", (0, 0), (-1, 0), PDF_HEADER_BG),
        ("TEXTCOLOR", (0, 0), (-1, 0), PDF_INK),
        ("GRID", (0, 0), (-1, -1), 0.4, PDF_BORDER),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 3.5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3.5),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
    ]
    for i in range(1, len(data)):
        if i % 2 == 0:
            style_cmds.append(("BACKGROUND", (0, i), (-1, i), PDF_STRIPE))
    t.setStyle(TableStyle(style_cmds))
    return t


def build_executive_report_pdf(data: dict) -> bytes:
    styles = _pdf_styles()
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        topMargin=1.8 * cm, bottomMargin=1.8 * cm, leftMargin=1.8 * cm, rightMargin=1.8 * cm,
        title="Executive Report — Student Placement System",
    )
    story = []

    # ---- Cover / header ----
    story.append(Paragraph("Executive Report", styles["title"]))
    story.append(Paragraph("Student Placement System Dashboard", styles["subtitle"]))
    story.append(HRFlowable(width="100%", thickness=1, color=PDF_BORDER, spaceAfter=8))
    story.append(Paragraph(f"Dibuat pada: {data['generated_at']}", styles["caption"]))
    story.append(Paragraph(f"Filter aktif: {data['filter_summary']}", styles["caption"]))
    story.append(Spacer(1, 8))

    # ---- 1. Executive Overview ----
    ov = data["overview"]
    story.append(Paragraph("1. Executive Overview", styles["h1"]))
    story.append(_pdf_kv_table([
        ("Total Partner Company", format_number(ov["partner_companies"])),
        ("Total Talent Request", format_number(ov["total_talent_request"])),
        ("Total Student", format_number(ov["total_student"])),
        ("Active Talent Requests", format_number(ov["active_talent_requests"])),
        ("Available Students", format_number(ov["available_students"])),
        ("Total Placement", format_number(ov["total_placement"])),
        ("Placement Rate", format_percentage(ov["placement_rate"])),
        ("Fulfillment Rate", format_percentage(ov["fulfillment_rate"])),
        ("Lead Time Rata-rata", f"{format_number(ov['lead_time'], 0)} hari"),
        ("Ghosting Rate", format_percentage(ov["ghosting_rate"])),
    ]))
    story.append(Spacer(1, 6))

    # ---- 2. Talent Demand & Matching Analysis ----
    m = data["matching"]
    story.append(Paragraph("2. Talent Demand & Matching Analysis", styles["h1"]))
    story.append(Paragraph(
        f"Total headcount yang diminta perusahaan sebesar {format_number(m['total_headcount'])}, dengan "
        f"{format_number(m['total_sent'])} kandidat sudah dikirim (fulfillment rata-rata "
        f"{format_percentage(ov['fulfillment_rate'])}, lead time rata-rata {format_number(ov['lead_time'], 0)} hari).",
        styles["body"],
    ))
    story.append(Paragraph("Distribusi Jenis Penempatan", styles["h2"]))
    story.append(_pdf_df_table(m["jenis_distribusi"], col_widths=[9 * cm, 6 * cm]))
    story.append(Spacer(1, 4))
    story.append(Paragraph("Top Talent Request Priority", styles["h2"]))
    if len(m["priority_requests"]):
        story.append(_pdf_df_table(
            m["priority_requests"][["id_talent_req", "nama_perusahaan", "nama_posisi", "headcount",
                                     "request_date", "progress"]],
            col_widths=[2 * cm, 3.8 * cm, 3.5 * cm, 2.3 * cm, 2.7 * cm, 3.1 * cm],
        ))
    else:
        story.append(Paragraph("Tidak ada talent request prioritas pada rentang filter ini.", styles["body"]))
    story.append(Spacer(1, 4))
    story.append(Paragraph("Demand vs Supply Analysis (Program Studi dengan Gap Terbesar)", styles["h2"]))
    gap_df = m["supply_demand"][m["supply_demand"]["gap"] > 0].reset_index().head(10)
    gap_df.columns = ["program_studi", "demand", "supply", "gap"]
    if len(gap_df):
        story.append(_pdf_df_table(gap_df, col_widths=[7 * cm, 2.7 * cm, 2.7 * cm, 2.6 * cm]))
    else:
        story.append(Paragraph("Tidak ada shortage supply mahasiswa pada rentang filter ini.", styles["body"]))

    # ---- 3. Recruitment Pipeline Analysis ----
    story.append(PageBreak())
    p = data["pipeline"]
    story.append(Paragraph("3. Recruitment Pipeline Analysis", styles["h1"]))
    story.append(Paragraph("Tahapan Proses Kandidat (Tracking Student)", styles["h2"]))
    story.append(_pdf_df_table(p["funnel_student"], col_widths=[9 * cm, 6 * cm]))
    story.append(Spacer(1, 4))
    story.append(Paragraph("Tahapan Pengiriman ke Perusahaan (Tracking Company)", styles["h2"]))
    story.append(_pdf_df_table(p["funnel_company"], col_widths=[9 * cm, 6 * cm]))
    story.append(Spacer(1, 4))
    story.append(Paragraph("Top 10 Perusahaan dengan Acceptance Rate Tertinggi", styles["h2"]))
    if len(p["acceptance_top"]):
        acc_df = p["acceptance_top"][["company", "acceptance_rate"]].copy()
        acc_df.columns = ["Perusahaan", "Acceptance Rate (%)"]
        story.append(_pdf_df_table(acc_df, col_widths=[9 * cm, 6 * cm]))
    else:
        story.append(Paragraph("Belum ada perusahaan dengan sampel cukup (min. 15 kandidat).", styles["body"]))
    story.append(Spacer(1, 4))
    story.append(Paragraph("Bottleneck Proses", styles["h2"]))
    story.append(Paragraph(p["bottleneck_text"], styles["body"]))

    # ---- 4. Student Readiness Analysis ----
    story.append(PageBreak())
    r = data["readiness"]
    story.append(Paragraph("4. Student Readiness Analysis", styles["h1"]))
    story.append(_pdf_kv_table([
        ("Mahasiswa Siap Ditempatkan (Available)", format_number(r["available_students"])),
        ("Total Mahasiswa (sesuai filter)", format_number(r["total_student"])),
        ("Eligible", f"{format_number(r['eligible_count'])} ({format_percentage(r['eligible_pct'])})"),
        ("CV Completion", format_percentage(r["cv_completion"])),
        ("Portfolio Completion", format_percentage(r["portfolio_completion"])),
    ]))

    # ---- 5. Recommendation Engine Result ----
    story.append(PageBreak())
    rec = data["recommendation"]
    story.append(Paragraph("5. Recommendation Engine Result", styles["h1"]))
    if rec["top_candidate"] is not None:
        tc = rec["top_candidate"]
        story.append(Paragraph("Top Recommended Candidate", styles["h2"]))
        story.append(_pdf_kv_table([
            ("Nama", tc["nama"]),
            ("Program Studi", tc["program_studi"]),
            ("Recommendation Score", format_decimal(tc["general_score"], 3)),
            ("Faktor Pendukung Rekomendasi", rec["top_candidate_reason"]),
        ]))
        story.append(Spacer(1, 4))
        story.append(Paragraph("Ranking Kandidat (Top 10 General Readiness Score)", styles["h2"]))
        story.append(_pdf_df_table(rec["ranking"], col_widths=[2.5 * cm, 4.5 * cm, 4.5 * cm, 3.5 * cm]))
    else:
        story.append(Paragraph("Tidak ada kandidat pada rentang filter ini.", styles["body"]))

    # ---- 6. Executive Decision Panel ----
    story.append(PageBreak())
    ex = data["executive"]
    story.append(Paragraph("6. Executive Decision Panel", styles["h1"]))
    story.append(_pdf_kv_table([
        ("Priority Talent Request", ex["priority_request_text"]),
        ("Critical Company", ex["critical_company_text"]),
        ("High Opportunity Company", ex["high_opportunity_text"]),
        ("Student Supply Alert", ex["supply_alert_text"]),
    ]))
    story.append(Spacer(1, 6))
    story.append(Paragraph("Recommended Action Today", styles["h2"]))
    for i, action_text in enumerate(ex["actions"], start=1):
        story.append(Paragraph(f"{i}. {_md_bold_to_html(action_text)}", styles["bullet"]))

    doc.build(story)
    return buffer.getvalue()


# ==================================================================
# INIT THEME STATE & INJECT CSS
# ==================================================================
if "dark_mode" not in st.session_state:
    st.session_state.dark_mode = True

theme = get_active_theme()
inject_theme(theme)

DATA_DIR = Path(__file__).parent / "data"

# ==================================================================
# FOLLOW-UP / GHOSTING DETECTION
# ==================================================================
FOLLOWUP_GHOSTING_RESOLVED_OUTCOMES = {
    "Placement",
    "Rejection Screening CV",
    "Rejection Study Case",
    "Rejection Interview User",
    "Rejection Final Interview",
}

def compute_followup_ghosting_status(send_date, rejection_outcome, reference_date=None):
    """Menentukan status Follow-up/Ghosting satu baris tracking_student
    berdasarkan aturan resmi FAQ (selisih reference_date terhadap send_date
    perusahaan). Mengembalikan salah satu dari None, 'FU 1', 'FU 2', 'FU 3',
    atau 'Ghosting'. None berarti belum lewat 1 minggu, atau kandidat sudah
    punya respons/status lanjutan sehingga tidak relevan lagi dihitung FU/
    Ghosting."""
    if rejection_outcome in FOLLOWUP_GHOSTING_RESOLVED_OUTCOMES:
        return None
    if pd.isna(send_date):
        return None
    if reference_date is None:
        reference_date = pd.Timestamp.now().normalize()
    days_elapsed = (reference_date - send_date).days
    if days_elapsed > 28:
        return "Ghosting"
    elif days_elapsed > 21:
        return "FU 3"
    elif days_elapsed > 14:
        return "FU 2"
    elif days_elapsed > 7:
        return "FU 1"
    return None

def apply_followup_ghosting_status(tracking_student_df: pd.DataFrame,
                                    tracking_company_df: pd.DataFrame,
                                    reference_date=None) -> pd.DataFrame:
    """Menempelkan kolom turunan ke tracking_student berdasarkan send_date
    perusahaan pengirim (tracking_company, di-join lewat id_tracking_company)
    dan outcome (`rejection`). Tidak mengubah kolom asli — hanya menambah
    kolom turunan yang dipakai bersama di seluruh dashboard:
      - fu_ghosting_status : None / "FU 1" / "FU 2" / "FU 3" / "Ghosting"
      - is_followup        : True jika fu_ghosting_status in {FU 1, FU 2, FU 3}
      - is_ghosting         : True jika fu_ghosting_status == "Ghosting"
      - outcome_effective   : fu_ghosting_status jika ada, kalau tidak fallback
                               ke kolom `rejection` asli (mis. 'On Progress',
                               'Placement', atau salah satu 'Rejection ...')

    "Tanggal saat ini" (reference_date) memakai `last_update` milik
    masing-masing baris tracking_student — yaitu titik waktu terakhir kali
    status kandidat tersebut benar-benar dicek/tercatat di sistem tracking —
    sebagai acuan "sekarang" untuk baris itu, kecuali di-override lewat
    parameter reference_date (mis. untuk pengujian). Pendekatan per-baris ini
    dipakai supaya hasil FU/Ghosting deterministik & reproducible terhadap
    snapshot data yang sama (tidak bergeser tiap kali dashboard dibuka pada
    hari yang berbeda), sekaligus tetap merepresentasikan "selisih tanggal
    saat ini dengan send_date" sesuai bunyi FAQ untuk setiap kandidat.
    """
    df = tracking_student_df.merge(
        tracking_company_df[["id_tracking_company", "send_date_dt"]],
        on="id_tracking_company", how="left",
    )
    df["fu_ghosting_status"] = df.apply(
        lambda r: compute_followup_ghosting_status(
            r["send_date_dt"], r["rejection"],
            reference_date if reference_date is not None else r["last_update"],
        ),
        axis=1,
    )
    df["is_followup"] = df["fu_ghosting_status"].isin(["FU 1", "FU 2", "FU 3"])
    df["is_ghosting"] = df["fu_ghosting_status"] == "Ghosting"
    df["outcome_effective"] = df["fu_ghosting_status"].fillna(df["rejection"])
    return df.drop(columns=["send_date_dt"])

# ==================================================================
# DATA LOADING
# ==================================================================
REQUIRED_FILES = {
    "company": "company.csv",
    "talent_request": "talent_request.csv",
    "student_all": "student_all.csv",
    "status_student": "status_student.csv",
    "tracking_company": "tracking_company.csv",
    "tracking_student": "tracking_student.csv",
}

@st.cache_data(show_spinner="Memuat & membersihkan data...")
def load_data(uploaded_files=None):
    frames = {}
    for key, filename in REQUIRED_FILES.items():
        path = DATA_DIR / filename
        if uploaded_files and key in uploaded_files and uploaded_files[key] is not None:
            src = uploaded_files[key]
        elif path.exists():
            src = path
        else:
            return None

        sep = ";" if key == "status_student" else ","
        frames[key] = pd.read_csv(src, sep=sep)

    company = frames["company"]
    talent_request = frames["talent_request"]
    student_all = frames["student_all"]
    status_student = frames["status_student"]
    tracking_company = frames["tracking_company"]
    tracking_student = frames["tracking_student"]

    talent_request["request_date"] = pd.to_datetime(talent_request["request_date"])
    tracking_company["request_date_dt"] = pd.to_datetime(tracking_company["request_date"], dayfirst=True)
    tracking_company["send_date_dt"] = pd.to_datetime(tracking_company["send_date"], dayfirst=True, errors="coerce")
    tracking_company["lead_time_days"] = (tracking_company["send_date_dt"] - tracking_company["request_date_dt"]).dt.days
    tracking_company["fulfillment_ratio"] = tracking_company["jumlah_dikirimkan"] / tracking_company["jumlah_permintaan"]
    tracking_student["last_update"] = pd.to_datetime(tracking_student["last_update"])
    status_student["sync_date"] = pd.to_datetime(status_student["sync_date"], dayfirst=True)
    company["created_at"] = pd.to_datetime(company["created_at"])

    status_student["eligible"] = (
        (status_student["CV"] == "Ada")
        & (status_student["portofolio"] == "Ada")
        & (status_student["status"] == "Active")
        & (status_student["ketersediaan"] == "Available")
    )

    #status Follow-up/Ghosting dihitung otomatis di sini (satu-satunya tempat)
    tracking_student = apply_followup_ghosting_status(tracking_student, tracking_company)

    return {
        "company": company,
        "talent_request": talent_request,
        "student_all": student_all,
        "status_student": status_student,
        "tracking_company": tracking_company,
        "tracking_student": tracking_student,
    }

def sidebar_uploader():
    st.sidebar.markdown(
        f'<div style="display:flex;align-items:center;gap:8px;font-weight:700;">'
        f'{icon("alert", color=theme["warning"], size=18)}<span>Data tidak ditemukan</span></div>',
        unsafe_allow_html=True,
    )
    st.sidebar.caption("Letakkan CSV di folder `./data/`, atau upload manual di bawah ini.")
    uploaded = {}
    for key, filename in REQUIRED_FILES.items():
        uploaded[key] = st.sidebar.file_uploader(filename, type="csv", key=f"up_{key}")
    return uploaded

# ==================================================================
# LOAD
# ==================================================================
data = load_data()
if data is None:
    uploaded = sidebar_uploader()
    if all(v is not None for v in uploaded.values()):
        data = load_data(uploaded_files=uploaded)
    else:
        st.markdown(
            f'<div class="dash-title">{icon("graduation", color=theme["primary"], size=26)}'
            f'<span>SSDC — CDC Dashboard</span></div>',
            unsafe_allow_html=True,
        )
        st.info("Silakan letakkan 6 file CSV di folder `./data/` di samping app_cdc.py, "
                "atau upload manual lewat sidebar untuk memulai.")
        st.stop()

company = data["company"]
talent_request = data["talent_request"]
student_all = data["student_all"]
status_student = data["status_student"]
tracking_company = data["tracking_company"]
tracking_student = data["tracking_student"]

# ==================================================================
# SIDEBAR (THEME SWITCHER + BRAND + GLOBAL FILTERS)
# ==================================================================
st.sidebar.markdown(
    f'<div style="display:flex;align-items:center;gap:8px;font-weight:700;font-size:15px;">'
    f'{icon("moon" if st.session_state.dark_mode else "sun", color=theme["primary"], size=18)}'
    f'<span>Appearance</span></div>',
    unsafe_allow_html=True,
)

# ---- dark mode toggle ----
st.sidebar.toggle("Dark Mode", key="dark_mode")
st.sidebar.caption(f"Theme: **{theme['name']}**")
st.sidebar.divider()

# ---- logo ----
st.sidebar.image("assets/logo.png", width=170)
st.sidebar.markdown("## Career Development Center")
st.sidebar.divider()

st.sidebar.markdown(
    f'<div style="display:flex;align-items:center;gap:8px;font-weight:700;font-size:15px;">'
    f'{icon("graduation", color=theme["primary"], size=18)}'
    f'<span>SSDC Dashboard</span></div>',
    unsafe_allow_html=True,
)
st.sidebar.caption("**Career Development Center**")
st.sidebar.divider()

st.sidebar.markdown(
    f'<div style="display:flex;align-items:center;gap:8px;font-weight:700;font-size:15px;">'
    f'{icon("filter", color=theme["primary"], size=18)}<span>Filter</span></div>',
    unsafe_allow_html=True,
)

min_date = talent_request["request_date"].min().date()
max_date = talent_request["request_date"].max().date()
date_range = st.sidebar.date_input(
    "Periode talent request", value=(min_date, max_date), min_value=min_date, max_value=max_date
)
if len(date_range) != 2:
    date_range = (min_date, max_date)

jenis_opts = sorted(talent_request["jenis_penempatan"].unique())
jenis_sel = st.sidebar.multiselect("Jenis penempatan", jenis_opts, default=jenis_opts)

sektor_opts = sorted(talent_request["industri_sektor"].unique())
sektor_sel = st.sidebar.multiselect("Sektor industri", sektor_opts, default=sektor_opts)

prodi_opts = sorted(student_all["program_studi"].unique())
prodi_sel = st.sidebar.multiselect("Program studi", prodi_opts, default=prodi_opts)

st.sidebar.caption("Pencarian")
search_company = st.sidebar.text_input("Search Company", placeholder="Nama perusahaan...")
search_student = st.sidebar.text_input("Search Student", placeholder="Nama mahasiswa...")

st.sidebar.divider()
st.sidebar.caption(f"Sinkronisasi data terakhir: **{status_student['sync_date'].max().strftime('%d %B %Y')}**")

# ==================================================================
# APPLY FILTER SCOPE
# ==================================================================
tr_f = talent_request[
    (talent_request["request_date"].dt.date >= date_range[0])
    & (talent_request["request_date"].dt.date <= date_range[1])
    & (talent_request["jenis_penempatan"].isin(jenis_sel))
    & (talent_request["industri_sektor"].isin(sektor_sel))
]
sa_f = student_all[student_all["program_studi"].isin(prodi_sel)]
ss_f = status_student[status_student["NIM"].isin(sa_f["NIM"])]

tc_f = tracking_company[tracking_company["id_talent_req"].isin(tr_f["id_talent_req"])]
ts_f = tracking_student[
    tracking_student["id_tracking_company"].isin(tc_f["id_tracking_company"])
    & tracking_student["NIM"].isin(sa_f["NIM"])
]

# ---- search ----
if search_company:
    tr_f = tr_f[tr_f["nama_perusahaan"].str.contains(search_company, case=False, na=False)]

if search_student:
    sa_f = sa_f[sa_f["nama"].str.contains(search_student, case=False, na=False)]

if len(tr_f) == 0 or len(sa_f) == 0:
    st.warning("Tidak ada data yang cocok dengan kombinasi filter ini. Coba longgarkan filter di sidebar.")
    st.stop()

# ==================================================================
# SHARED KPI COMPUTATIONS (tidak diubah — rumus & hasil identik)
# ==================================================================
total_placement = int((ts_f["progress_student"] == "Placement").sum())
success_rate = round(total_placement / len(ts_f) * 100, 1) if len(ts_f) else 0

ghosting_count = int(ts_f["is_ghosting"].sum())
ghosting_rate = round(ghosting_count / len(ts_f) * 100, 1) if len(ts_f) else 0

avg_fulfillment = round(tc_f["fulfillment_ratio"].mean() * 100, 1) if len(tc_f) else 0
avg_lead = round(tc_f["lead_time_days"].mean(), 1) if len(tc_f) else 0

active_talent_requests = tc_f[tc_f["progress"] != "Closed"]["id_talent_req"].nunique()
available_students = int((ss_f["ketersediaan"] == "Available").sum())

fu_count = int(ts_f["is_followup"].sum())
ghost_top = ts_f[ts_f["is_ghosting"]]["company"].value_counts()

comp_stats = ts_f.groupby("company").agg(
    total=("id_tracking_student", "size"),
    placement=("progress_student", lambda x: (x == "Placement").sum()),
).reset_index()
comp_stats = comp_stats[comp_stats["total"] >= 15]
comp_stats["acceptance_rate"] = (comp_stats["placement"] / comp_stats["total"] * 100).round(1)

CC = theme["chart_colors"]

# ==================================================================
# SHARED PRECOMPUTE
# ==================================================================
prodi_track_record = build_prodi_track_record(ts_f, sa_f)
company_track_record, overall_track_record = build_company_track_record(ts_f)

candidate_pool = sa_f.merge(
    ss_f[["NIM", "CV", "portofolio", "IPK", "status", "ketersediaan", "eligible"]],
    on="NIM", how="inner",
)

open_talent_pool = tr_f.merge(tc_f[["id_talent_req", "progress"]], on="id_talent_req", how="left")
open_talent_pool = open_talent_pool[open_talent_pool["progress"] != "Closed"]

# ---- ghosting rate per perusahaan ----
comp_ghost_stats = ts_f.groupby("company").agg(
    total=("id_tracking_student", "size"),
    ghosting=("is_ghosting", "sum"),
).reset_index()
comp_ghost_stats = comp_ghost_stats[comp_ghost_stats["total"] >= 15]
comp_ghost_stats["ghosting_rate"] = (comp_ghost_stats["ghosting"] / comp_ghost_stats["total"] * 100).round(1)

# ---- talent request prioritas ----
priority_requests = tr_f.merge(
    tc_f[["id_talent_req", "progress", "jumlah_dikirimkan"]], on="id_talent_req", how="left"
)
priority_requests = priority_requests[priority_requests["progress"].isin(["Draft", "Submitted", "On Review"])] \
    .sort_values(["headcount", "request_date"], ascending=[False, True])

# ---- top candidate secara umum ----
candidate_pool["general_score"] = (
    candidate_pool.apply(
        lambda r: readiness_component(r["CV"], r["portofolio"], r["status"], r["ketersediaan"]), axis=1
    ) * 0.6
    + (candidate_pool["IPK"] / 4.0).clip(upper=1.0) * 0.4
)

# ---- supply vs demand per program studi ----
_supply = ss_f[(ss_f["ketersediaan"] == "Available") & (ss_f["status"] == "Active")]
supply_by_prodi = _supply.groupby("program_studi").size()

_demand_rows = {}
for _prodi in sa_f["program_studi"].unique():
    _prodi_l = str(_prodi).strip().lower()
    _mask = open_talent_pool["bidang_studi_dibutuhkan"].apply(
        lambda t: any(_prodi_l in tok or tok in _prodi_l for tok in _split_field_tokens(t))
    )
    _demand_rows[_prodi] = int(open_talent_pool.loc[_mask, "headcount"].sum())
demand_by_prodi = pd.Series(_demand_rows)

supply_demand = pd.DataFrame({
    "program_studi": demand_by_prodi.index,
    "demand": demand_by_prodi.values,
}).set_index("program_studi")
supply_demand["supply"] = supply_by_prodi.reindex(supply_demand.index).fillna(0).astype(int)
supply_demand["gap"] = supply_demand["demand"] - supply_demand["supply"]
supply_demand = supply_demand.sort_values("gap", ascending=False)

# ==================================================================
# PDF PRECOMPUTE — Executive Report (dipakai tombol "Export" di header)
# ==================================================================
_pdf_jp = tr_f["jenis_penempatan"].value_counts().reset_index()
_pdf_jp.columns = ["Jenis", "Jumlah"]

_pdf_funnel_order = ["Selecting Student by Company", "Study Case", "CDC Briefing Student",
                      "Interview User", "Final Interview", "Placement"]
_pdf_fc = ts_f["progress_student"].value_counts()
_pdf_fdf = pd.DataFrame({"stage": _pdf_funnel_order, "count": [int(_pdf_fc.get(s, 0)) for s in _pdf_funnel_order]})

_pdf_tc_order = ["Draft", "Submitted", "On Review", "Shortlisted", "Closed"]
_pdf_tcc = tc_f["progress"].value_counts()
_pdf_tcdf = pd.DataFrame({"stage": _pdf_tc_order, "count": [int(_pdf_tcc.get(s, 0)) for s in _pdf_tc_order]})

_pdf_top_acc = comp_stats.sort_values("acceptance_rate", ascending=False).head(10)

_pdf_total_student = len(ss_f)
_pdf_eligible_count = int(ss_f["eligible"].sum())
_pdf_eligible_pct = round((_pdf_eligible_count / _pdf_total_student) * 100, 1) if _pdf_total_student else 0
_pdf_cv_completion = round((ss_f["CV"] == "Ada").mean() * 100, 1)
_pdf_portfolio_completion = round((ss_f["portofolio"] == "Ada").mean() * 100, 1)

_pdf_top_priority_req = priority_requests.iloc[0] if len(priority_requests) else None
_pdf_top_candidate = candidate_pool.sort_values("general_score", ascending=False).iloc[0] \
    if len(candidate_pool) else None
_pdf_critical_company = comp_ghost_stats.sort_values("ghosting_rate", ascending=False).iloc[0] \
    if len(comp_ghost_stats) else None
_pdf_high_opportunity_company = comp_stats.sort_values("acceptance_rate", ascending=False).iloc[0] \
    if len(comp_stats) else None
_pdf_supply_alert = supply_demand.iloc[0] if len(supply_demand) and supply_demand.iloc[0]["gap"] > 0 else None

_pdf_actions = []
if _pdf_top_priority_req is not None:
    _pdf_actions.append(
        f"Prioritaskan proses **{_pdf_top_priority_req['id_talent_req']}** dari "
        f"**{_pdf_top_priority_req['nama_perusahaan']}** ({_pdf_top_priority_req['nama_posisi']}, "
        f"headcount {format_number(_pdf_top_priority_req['headcount'])}) — masih berstatus "
        f"'{_pdf_top_priority_req['progress']}' sejak "
        f"{pd.to_datetime(_pdf_top_priority_req['request_date']).strftime('%d %b %Y')}."
    )
if _pdf_critical_company is not None:
    _pdf_actions.append(
        f"Tinjau ulang kerja sama dengan **{_pdf_critical_company['company']}** — ghosting rate historis "
        f"tertinggi ({format_percentage(_pdf_critical_company['ghosting_rate'])} dari "
        f"{format_number(_pdf_critical_company['total'])} kandidat yang pernah dikirim), pertimbangkan "
        "follow-up personal ke PIC perusahaan."
    )
if _pdf_high_opportunity_company is not None:
    _pdf_actions.append(
        f"Prioritaskan pengiriman kandidat baru ke **{_pdf_high_opportunity_company['company']}** — "
        f"acceptance rate historis tertinggi ({format_percentage(_pdf_high_opportunity_company['acceptance_rate'])}), "
        "peluang placement besar."
    )
if _pdf_supply_alert is not None:
    _pdf_actions.append(
        f"Buka campaign rekrutmen mahasiswa program studi **{_pdf_supply_alert.name}** — demand aktif "
        f"({format_number(_pdf_supply_alert['demand'])}) melebihi supply mahasiswa Available "
        f"({format_number(_pdf_supply_alert['supply'])})."
    )
_pdf_not_ready_count = int((~ss_f["eligible"]).sum())
if _pdf_not_ready_count > 0:
    _pdf_actions.append(
        f"Kirim reminder pelengkapan dokumen ke **{format_number(_pdf_not_ready_count)} mahasiswa** yang "
        "belum eligible (CV/portofolio belum lengkap, status tidak aktif, atau belum tersedia)."
    )
if fu_count > 0:
    _pdf_actions.append(
        f"Tindak lanjuti **{format_number(fu_count)} mahasiswa** yang masih berstatus Follow-up "
        "(FU 1/FU 2/FU 3) sebelum berubah menjadi kasus ghosting."
    )
if ghosting_count > 0:
    _pdf_actions.append(
        f"Evaluasi pola ghosting — total **{format_number(ghosting_count)} kasus** "
        f"({format_percentage(ghosting_rate)} dari seluruh proses) pada rentang filter ini, cek apakah "
        "terkonsentrasi pada perusahaan/posisi tertentu."
    )

_pdf_funnel_non_final = _pdf_fdf[_pdf_fdf["stage"] != "Placement"]
if len(_pdf_funnel_non_final) and _pdf_funnel_non_final["count"].sum() > 0:
    _pdf_bn = _pdf_funnel_non_final.loc[_pdf_funnel_non_final["count"].idxmax()]
    _pdf_bottleneck_text = (
        f"Tahapan dengan jumlah kandidat terbanyak yang belum lanjut ke tahap berikutnya adalah "
        f"'{_pdf_bn['stage']}' dengan {format_number(_pdf_bn['count'])} kandidat — tahapan ini berpotensi "
        "menjadi bottleneck proses seleksi dan perlu menjadi prioritas evaluasi CDC."
    )
else:
    _pdf_bottleneck_text = "Tidak ada indikasi bottleneck signifikan pada pipeline seleksi saat ini."

if _pdf_top_candidate is not None:
    _pdf_readiness_val = readiness_component(
        _pdf_top_candidate["CV"], _pdf_top_candidate["portofolio"],
        _pdf_top_candidate["status"], _pdf_top_candidate["ketersediaan"],
    )
    _pdf_top_candidate_reason = (
        f"Kelengkapan readiness (CV/portofolio/status/ketersediaan) {format_percentage(_pdf_readiness_val * 100, 0)} "
        f"dan IPK {format_decimal(float(_pdf_top_candidate['IPK']), 2)} menghasilkan General Readiness Score "
        "tertinggi di antara seluruh kandidat pada rentang filter ini."
    )
    _pdf_ranking_df = (
        candidate_pool.sort_values("general_score", ascending=False)
        .head(10)[["nama", "program_studi", "IPK", "general_score"]]
        .rename(columns={"general_score": "Recommendation Score"})
    )
else:
    _pdf_top_candidate_reason = "-"
    _pdf_ranking_df = pd.DataFrame(columns=["nama", "program_studi", "IPK", "Recommendation Score"])

_pdf_priority_request_text = (
    f"{_pdf_top_priority_req['id_talent_req']} — {_pdf_top_priority_req['nama_perusahaan']} "
    f"({_pdf_top_priority_req['nama_posisi']}, headcount {format_number(_pdf_top_priority_req['headcount'])})"
) if _pdf_top_priority_req is not None else "Tidak ada request prioritas pada rentang filter ini."
_pdf_critical_company_text = (
    f"{_pdf_critical_company['company']} — ghosting rate {format_percentage(_pdf_critical_company['ghosting_rate'])}"
) if _pdf_critical_company is not None else "Belum ada perusahaan dengan sampel cukup (min. 15 kandidat)."
_pdf_high_opportunity_text = (
    f"{_pdf_high_opportunity_company['company']} — acceptance rate "
    f"{format_percentage(_pdf_high_opportunity_company['acceptance_rate'])}"
) if _pdf_high_opportunity_company is not None else "Belum ada perusahaan dengan sampel cukup (min. 15 kandidat)."
_pdf_supply_alert_text = (
    f"{_pdf_supply_alert.name} — gap {format_number(_pdf_supply_alert['gap'])} kandidat "
    f"(demand {format_number(_pdf_supply_alert['demand'])} vs supply {format_number(_pdf_supply_alert['supply'])})"
) if _pdf_supply_alert is not None else "Tidak ada shortage supply signifikan pada rentang filter ini."

_pdf_report_data = {
    "generated_at": datetime.now().strftime("%d %B %Y, %H:%M"),
    "filter_summary": (
        f"Periode {date_range[0].strftime('%d %b %Y')} – {date_range[1].strftime('%d %b %Y')} · "
        f"Jenis Penempatan: {', '.join(jenis_sel) if jenis_sel else '-'} · "
        f"Sektor Industri: {len(sektor_sel)} dari {len(sektor_opts)} dipilih · "
        f"Program Studi: {len(prodi_sel)} dari {len(prodi_opts)} dipilih"
    ),
    "overview": {
        "partner_companies": tr_f["id_company"].nunique(),
        "total_talent_request": len(tr_f),
        "total_student": _pdf_total_student,
        "active_talent_requests": active_talent_requests,
        "available_students": available_students,
        "total_placement": total_placement,
        "placement_rate": success_rate,
        "fulfillment_rate": avg_fulfillment,
        "lead_time": avg_lead,
        "ghosting_rate": ghosting_rate,
    },
    "matching": {
        "total_headcount": int(tr_f["headcount"].sum()),
        "total_sent": int(tc_f["jumlah_dikirimkan"].sum()),
        "jenis_distribusi": _pdf_jp,
        "priority_requests": priority_requests,
        "supply_demand": supply_demand,
    },
    "pipeline": {
        "funnel_student": _pdf_fdf.rename(columns={"stage": "Tahapan Seleksi", "count": "Jumlah"}),
        "funnel_company": _pdf_tcdf.rename(columns={"stage": "Tahapan Pengiriman", "count": "Jumlah"}),
        "acceptance_top": _pdf_top_acc,
        "bottleneck_text": _pdf_bottleneck_text,
    },
    "readiness": {
        "available_students": available_students,
        "total_student": _pdf_total_student,
        "eligible_count": _pdf_eligible_count,
        "eligible_pct": _pdf_eligible_pct,
        "cv_completion": _pdf_cv_completion,
        "portfolio_completion": _pdf_portfolio_completion,
    },
    "recommendation": {
        "top_candidate": _pdf_top_candidate,
        "top_candidate_reason": _pdf_top_candidate_reason,
        "ranking": _pdf_ranking_df,
    },
    "executive": {
        "priority_request_text": _pdf_priority_request_text,
        "critical_company_text": _pdf_critical_company_text,
        "high_opportunity_text": _pdf_high_opportunity_text,
        "supply_alert_text": _pdf_supply_alert_text,
        "actions": _pdf_actions,
    },
}
_pdf_bytes = build_executive_report_pdf(_pdf_report_data)
_pdf_filename = f"Executive_Report_{datetime.now().strftime('%Y-%m-%d_%H-%M')}.pdf"

# ==================================================================
# HEADER
# ==================================================================
header1, header2 = st.columns([7, 3])

with header1:
    st.markdown(
        f'<div class="dash-title">{icon("graduation", color=theme["primary"], size=28)}'
        f'<span>Student Placement System</span></div>'
        f'<div class="dash-subtitle">Career Development Center Dashboard</div>',
        unsafe_allow_html=True,
    )

with header2:
    st.markdown(
        f'<div style="display:flex;align-items:center;gap:8px;justify-content:flex-end;'
        f'color:{theme["text_secondary"]};font-size:13px;font-weight:500;">'
        f'{icon("clock", color=theme["text_secondary"], size=16)}'
        f'<span>Last Refresh &nbsp;·&nbsp; {datetime.now().strftime("%d %B %Y")}</span></div>',
        unsafe_allow_html=True,
    )

st.divider()

left, right = st.columns([8, 2])
with right:
    rcol, ecol = st.columns(2)
    refresh = rcol.button("Refresh", use_container_width=True)
    ecol.download_button(
        "Export",
        data=_pdf_bytes,
        file_name=_pdf_filename,
        mime="application/pdf",
        use_container_width=True,
    )

if refresh:
    st.cache_data.clear()
    st.rerun()

tab_overview, tab_matching, tab_pipeline, tab_student, tab_recommendation, tab_executive = st.tabs(
    ["Executive Overview", "Talent Demand & Matching", "Recruitment Pipeline", "Student Readiness",
     "Recommendation Engine", "Executive Decision Panel"]
)

# ==================================================================
# TAB 1 — EXECUTIVE OVERVIEW
# ==================================================================
with tab_overview:
    section_title("Executive Overview", theme, icon_name="chart-line")

    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        kpi_card(theme, "Partner Companies", format_number(tr_f["id_company"].nunique()),
                 "+8% vs periode lalu", theme["primary"], "building"
        )

    with c2:
        kpi_card(theme, "Active Talent Requests", format_number(active_talent_requests),
                 "+15% vs periode lalu", theme["primary"], "file"
        )

    with c3:
        kpi_card(theme, "Available Students", format_number(available_students),
                 "+3% vs periode lalu", theme["success"], "graduation"
        )

    with c4:
        kpi_card(theme, "Placement Rate", format_percentage(success_rate),
                 "+4% vs periode lalu", theme["success"], "target"
        )

    with c5:
        kpi_card(theme, "Fulfillment Rate", format_percentage(avg_fulfillment),
                 "+2% vs periode lalu", theme["warning"], "package"
        )

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
    section_title("Alur Volume Talent", theme, icon_name="funnel")
    sent = int(tc_f["jumlah_dikirimkan"].sum())
    in_process = len(ts_f) - total_placement - ghosting_count
    f1, f2, f3, f4 = st.columns(4)
    f1.metric("Talent Request", format_number(len(tr_f)))
    f2.metric("Kandidat Dikirim", format_number(sent))
    f3.metric("Sedang Proses / FU", format_number(in_process))
    f4.metric("Placement", format_number(total_placement))

    colA, colB = st.columns([1.3, 1])
    with colA:
        section_title("Trend Talent Request vs Placement per Bulan", theme, icon_name="chart-line")
        req_trend = tr_f.copy()
        req_trend["ym"] = req_trend["request_date"].dt.to_period("M").astype(str)
        req_trend = req_trend.groupby("ym").size().reset_index(name="Talent Request")

        plc = ts_f[ts_f["progress_student"] == "Placement"].copy()
        plc["ym"] = plc["last_update"].dt.to_period("M").astype(str)
        plc_trend = plc.groupby("ym").size().reset_index(name="Placement")

        trend = req_trend.merge(plc_trend, on="ym", how="left").fillna(0).sort_values("ym")
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=trend["ym"], y=trend["Talent Request"], name="Talent Request",
                                  line=dict(color=CC["primary"], width=2.5)))
        fig.add_trace(go.Scatter(x=trend["ym"], y=trend["Placement"], name="Placement",
                                  line=dict(color=CC["secondary"], width=2.5)))
        render_chart(fig, theme, height=340, legend_orientation="h", legend_y=1.12)

    with colB:
        section_title("Proporsi Jenis Penempatan", theme, icon_name="target")
        jp = tr_f["jenis_penempatan"].value_counts().reset_index()
        jp.columns = ["Jenis", "Jumlah"]
        fig = px.pie(jp, names="Jenis", values="Jumlah", hole=0.55,
                     color_discrete_sequence=[CC["primary"], CC["secondary"], CC["tertiary"]])
        render_chart(fig, theme, height=340)

    section_title("Top 10 Program Studi dengan Placement Terbanyak", theme, icon_name="graduation")
    ts_prodi = ts_f.merge(sa_f[["NIM", "program_studi"]], on="NIM", how="left")
    placement_prodi = (
        ts_prodi[ts_prodi["progress_student"] == "Placement"]
        .groupby("program_studi").size().reset_index(name="Placement")
        .sort_values("Placement", ascending=False).head(10)
    )
    fig = px.bar(placement_prodi.sort_values("Placement"), x="Placement", y="program_studi", orientation="h",
                 color_discrete_sequence=[CC["secondary"]])
    render_chart(fig, theme, height=360, yaxis_title="", xaxis_title="Jumlah Placement")

# ==================================================================
# TAB 2 — TALENT DEMAND & MATCHING
# ==================================================================
with tab_matching:
    section_title("Talent Demand & Matching", theme, icon_name="target")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Rata-rata Fulfillment", format_percentage(avg_fulfillment), "kandidat dikirim vs diminta")
    c2.metric("Rata-rata Lead Time", f"{format_number(avg_lead, 0)} hari", "request → kandidat dikirim")
    c3.metric("Total Headcount Diminta", format_number(tr_f["headcount"].sum()))
    c4.metric("Total Kandidat Dikirim", format_number(tc_f["jumlah_dikirimkan"].sum()))

    colA, colB = st.columns(2)
    with colA:
        section_title("Volume Headcount per Sektor Industri (Top 10)", theme, icon_name="building")
        sec = tr_f.groupby("industri_sektor")["headcount"].sum().reset_index().sort_values("headcount", ascending=False).head(10)
        fig = px.bar(sec.sort_values("headcount"), x="headcount", y="industri_sektor", orientation="h",
                     color_discrete_sequence=[CC["primary"]])
        render_chart(fig, theme, height=380, yaxis_title="", xaxis_title="Headcount")

    with colB:
        section_title("Skema Kerja yang Ditawarkan", theme, icon_name="package")
        wa = tr_f["working_arrangement"].value_counts().reset_index()
        wa.columns = ["Skema", "Jumlah"]
        fig = px.pie(wa, names="Skema", values="Jumlah",
                     color_discrete_sequence=[CC["primary"], CC["tertiary"], CC["secondary"]])
        render_chart(fig, theme, height=380)

    colC, colD = st.columns(2)
    with colC:
        section_title("10 Posisi Paling Sering Diminta", theme, icon_name="file")
        pos = tr_f["nama_posisi"].value_counts().reset_index().head(10)
        pos.columns = ["Posisi", "Jumlah"]
        fig = px.bar(pos.sort_values("Jumlah"), x="Jumlah", y="Posisi", orientation="h",
                     color_discrete_sequence=[CC["tertiary"]])
        render_chart(fig, theme, height=340, yaxis_title="")

    with colD:
        section_title("Daftar Talent Request Perlu Diprioritaskan", theme, icon_name="list")
        prio = tr_f.merge(
            tc_f[["id_talent_req", "progress", "jumlah_dikirimkan"]], on="id_talent_req", how="left"
        )
        prio = prio[prio["progress"].isin(["Draft", "Submitted", "On Review"])].sort_values(
            ["headcount", "request_date"], ascending=[False, True]
        )
        render_table(
            prio[["id_talent_req", "nama_perusahaan", "nama_posisi", "headcount", "request_date", "progress"]].head(15),
            theme,
        )

    st.download_button(
        "Download talent request (sesuai filter) — CSV",
        tr_f.to_csv(index=False).encode("utf-8"),
        file_name="talent_request_filtered.csv",
        mime="text/csv",
    )

# ==================================================================
# TAB 3 — RECRUITMENT PIPELINE
# ==================================================================
with tab_pipeline:
    section_title("Monitoring Pipeline Seleksi", theme, icon_name="funnel")

    placement_col_a = int((ts_f["progress_student"] == "Placement").sum())
    placement_col_b = int((ts_f["rejection"] == "Placement").sum())
    if placement_col_a != placement_col_b:
        st.warning(
            f"**Catatan kualitas data:** jumlah status *Placement* pada kolom `progress_student` "
            f"({format_number(placement_col_a)}) berbeda dari kolom `rejection` ({format_number(placement_col_b)}). "
            "Kedua kolom perlu direkonsiliasi sebagai satu sumber kebenaran sebelum dipakai untuk "
            "laporan resmi."
        )

    # ---------------- PIPELINE FUNNELS ----------------
    colA, colB = st.columns(2)
    with colA:
        section_title("Tahapan Seleksi Mahasiswa (TRACKING STUDENT)", theme)
        funnel_order = ["Selecting Student by Company", "Study Case", "CDC Briefing Student",
                         "Interview User", "Final Interview", "Placement"]
        fc = ts_f["progress_student"].value_counts()
        fdf = pd.DataFrame({"stage": funnel_order, "count": [int(fc.get(s, 0)) for s in funnel_order]})
        colors = [CC["primary"]] * (len(fdf) - 1) + [CC["secondary"]]
        fig = px.bar(fdf.sort_values("count"), x="count", y="stage", orientation="h")
        fig.update_traces(marker_color=[colors[funnel_order.index(s)] for s in fdf.sort_values("count")["stage"]])
        render_chart(fig, theme, height=360, yaxis_title="")

    with colB:
        section_title("Tahapan Pengiriman ke Perusahaan (TRACKING COMPANY)", theme)
        tc_order = ["Draft", "Submitted", "On Review", "Shortlisted", "Closed"]
        tcc = tc_f["progress"].value_counts()
        tcdf = pd.DataFrame({"stage": tc_order, "count": [int(tcc.get(s, 0)) for s in tc_order]})
        colors2 = [CC["tertiary"]] * (len(tcdf) - 1) + [CC["secondary"]]
        fig = px.bar(tcdf.sort_values("count"), x="count", y="stage", orientation="h")
        fig.update_traces(marker_color=[colors2[tc_order.index(s)] for s in tcdf.sort_values("count")["stage"]])
        render_chart(fig, theme, height=360, yaxis_title="")

    section_title("Distribusi Outcome Akhir Seleksi (status Follow-up/Ghosting otomatis)", theme)
    oc = ts_f["outcome_effective"].value_counts().reset_index()
    oc.columns = ["Outcome", "Jumlah"]
    color_map = {
        "Placement": CC["secondary"], "Ghosting": CC["quaternary"], "On Progress": CC["tertiary"],
        "FU 1": CC["tertiary"], "FU 2": CC["tertiary"], "FU 3": CC["tertiary"],
    }
    oc["color"] = oc["Outcome"].map(lambda x: color_map.get(x, CC["fallback"]))
    fig = px.bar(oc, x="Outcome", y="Jumlah", color="Outcome",
                 color_discrete_map={r.Outcome: r.color for r in oc.itertuples()})
    render_chart(fig, theme, height=380, showlegend=False)

    st.divider()

    section_title("Candidate Outcome Analysis", theme, icon_name="user-x")

    oc1, oc2, oc3 = st.columns(3)
    oc1.metric("Total Kasus Ghosting", format_number(ghosting_count),
               f"{format_percentage(ghosting_rate)} dari seluruh proses", delta_color="inverse")
    oc2.metric("Sedang Follow-up", format_number(fu_count), "FU 1 / FU 2 / FU 3")
    if len(ghost_top):
        oc3.metric("Ghosting Tertinggi", ghost_top.index[0], f"{format_number(ghost_top.iloc[0])} kasus", delta_color="inverse")

    colE, colF = st.columns(2)
    with colE:
        section_title("10 Perusahaan dengan Ghosting Terbanyak", theme)
        gt = ghost_top.head(10).reset_index()
        gt.columns = ["Perusahaan", "Jumlah"]
        if len(gt):
            fig = px.bar(gt.sort_values("Jumlah"), x="Jumlah", y="Perusahaan", orientation="h",
                         color_discrete_sequence=[CC["quaternary"]])
            render_chart(fig, theme, height=380, yaxis_title="")
        else:
            st.info("Tidak ada kasus ghosting pada rentang filter ini.")

    with colF:
        section_title("10 Perusahaan dengan Acceptance Rate Tertinggi", theme)
        top_acc = comp_stats.sort_values("acceptance_rate", ascending=False).head(10)
        if len(top_acc):
            fig = px.bar(top_acc.sort_values("acceptance_rate"), x="acceptance_rate", y="company", orientation="h",
                         color_discrete_sequence=[CC["tertiary"]])
            render_chart(fig, theme, height=380, yaxis_title="", xaxis_title="Acceptance Rate (%)")
        else:
            st.info("Belum ada perusahaan dengan minimal 15 kandidat pada rentang filter ini.")

    st.divider()

    section_title("Follow-up List", theme, icon_name="list")
    with st.expander("Lihat mahasiswa yang butuh follow-up (FU 1 / FU 2 / FU 3)", expanded=False):
        fu = ts_f[ts_f["is_followup"]].sort_values("last_update")
        render_table(
            fu[["student_name", "company", "position", "fu_ghosting_status", "last_update"]],
            theme,
        )

# ==================================================================
# TAB 4 — STUDENT READINESS
# ==================================================================
with tab_student:
    section_title("Kelayakan & Kesiapan Mahasiswa", theme, icon_name="graduation")

    total_student = len(ss_f)
    eligible_count = int(ss_f["eligible"].sum())
    eligible_pct = round((eligible_count / total_student) * 100, 1) if total_student else 0
    cv_completion = round((ss_f["CV"] == "Ada").mean() * 100, 1)
    portfolio_completion = round((ss_f["portofolio"] == "Ada").mean() * 100, 1)

    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        metric_status_card(theme, "users", "Total Student", format_number(total_student), theme["primary"],
                            status_type="success", status_value="Mahasiswa Aktif")
    with c2:
        metric_status_card(theme, "check", "Eligible", format_number(eligible_count), theme["success"],
                            status_type="info", status_value=f"{format_percentage(eligible_pct)} Eligible")
    with c3:
        metric_status_card(theme, "file", "CV Completion", format_percentage(cv_completion), theme["warning"],
                            status_type="progress", status_value=cv_completion / 100)
    with c4:
        metric_status_card(theme, "palette", "Portfolio", format_percentage(portfolio_completion), CC["muted"],
                            status_type="progress", status_value=portfolio_completion / 100)
    with c5:
        metric_status_card(theme, "pin", "Available", format_number(available_students), theme["danger"],
                            status_type="info", status_value="Ready to Placement")
    colA, colB, colC = st.columns(3)
    with colA:
        section_title("Status Keaktifan", theme)
        sdf = ss_f["status"].value_counts().reset_index()
        sdf.columns = ["Status", "Jumlah"]
        fig = px.pie(sdf, names="Status", values="Jumlah", hole=0.55, color_discrete_sequence=theme["chart_seq"])
        render_chart(fig, theme, height=300)

    with colB:
        section_title("Ketersediaan", theme)
        kdf = ss_f["ketersediaan"].value_counts().reset_index()
        kdf.columns = ["Ketersediaan", "Jumlah"]
        fig = px.pie(kdf, names="Ketersediaan", values="Jumlah", hole=0.55,
                     color_discrete_sequence=[CC["primary"], CC["muted"], CC["secondary"]])
        render_chart(fig, theme, height=300)

    with colC:
        section_title("Distribusi IPK", theme)
        bins = [2.0, 2.5, 3.0, 3.25, 3.5, 3.75, 4.01]
        labels = ["2.0-2.49", "2.5-2.99", "3.0-3.24", "3.25-3.49", "3.5-3.74", "3.75-4.0"]
        ipk_bucket = pd.cut(ss_f["IPK"], bins=bins, labels=labels, right=False)
        idf = ipk_bucket.value_counts().sort_index().reset_index()
        idf.columns = ["Rentang IPK", "Jumlah"]
        fig = px.bar(idf, x="Rentang IPK", y="Jumlah", color_discrete_sequence=[CC["primary"]])
        render_chart(fig, theme, height=300)

    section_title("Top 10 Domisili Mahasiswa", theme, icon_name="pin")
    dom = ss_f["domisili"].value_counts().reset_index().head(10)
    dom.columns = ["Kota", "Jumlah"]
    fig = px.bar(dom.sort_values("Jumlah"), x="Jumlah", y="Kota", orientation="h",
                 color_discrete_sequence=[CC["tertiary"]])
    render_chart(fig, theme, height=360, yaxis_title="")

    with st.expander("Lihat mahasiswa yang belum eligible & alasannya"):
        not_elig = ss_f[~ss_f["eligible"]].copy()
        not_elig["alasan"] = ""
        not_elig.loc[not_elig["CV"] != "Ada", "alasan"] += "CV belum ada; "
        not_elig.loc[not_elig["portofolio"] != "Ada", "alasan"] += "Portofolio belum ada; "
        not_elig.loc[not_elig["status"] != "Active", "alasan"] += "Status tidak aktif; "
        not_elig.loc[not_elig["ketersediaan"] != "Available", "alasan"] += "Belum tersedia; "
        render_table(not_elig[["nama", "program_studi", "semester", "alasan"]].head(50), theme)

    st.download_button(
        "Download daftar mahasiswa eligible (sesuai filter) — CSV",
        ss_f[ss_f["eligible"]].to_csv(index=False).encode("utf-8"),
        file_name="mahasiswa_eligible_filtered.csv",
        mime="text/csv",
    )

# ==================================================================
# TAB 5 — RECOMMENDATION ENGINE
# ==================================================================
with tab_recommendation:
    section_title(
        "Bidirectional Recommendation Engine", theme, icon_name="target",
        caption="Decision Support System berbasis Weighted Scoring Model (SAW). "
                "Skor dihitung berdasarkan atribut dataset yang tersedia dan mengikuti filter aktif di sidebar.",
    )

    rec_mode = st.radio(
        "Arah rekomendasi", ["Company → Student", "Student → Company"],
        horizontal=True, label_visibility="collapsed",
    )
    st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)

    if rec_mode == "Company → Student":
        req_options = tr_f.sort_values("request_date", ascending=False)
        req_labels = {
            row.id_talent_req: f"{row.id_talent_req} — {row.nama_perusahaan} — {row.nama_posisi} "
                                f"(headcount {row.headcount})"
            for row in req_options.itertuples()
        }
        sel_req_id = st.selectbox(
            "Pilih Talent Request", options=list(req_labels.keys()),
            format_func=lambda x: req_labels[x],
        )
        req_row = tr_f[tr_f["id_talent_req"] == sel_req_id].iloc[0]

        if candidate_pool.empty:
            st.info("Tidak ada kandidat mahasiswa pada rentang filter ini.")
        else:
            with st.spinner("Menghitung Recommendation Score (SAW)..."):
                scored = score_students_for_request(req_row, candidate_pool, prodi_track_record)
            scored["matching_pct"] = (scored["score"] * 100).round(1)
            scored["reason"] = scored.apply(build_reason_c2s, axis=1)
            scored["improve"] = scored.apply(build_improve_c2s, axis=1)
            top10 = scored.sort_values("score", ascending=False).head(10).reset_index(drop=True)
            top10.index = top10.index + 1

            k1, k2, k3 = st.columns(3)
            with k1:
                kpi_card(theme, "Kandidat Dievaluasi", format_number(len(scored)),
                        f"untuk {req_row['nama_posisi']}", theme["primary"], "users")
            with k2:
                kpi_card(theme, "Best Match Score", format_percentage(top10.iloc[0]["matching_pct"]) if len(top10) else "-",
                        top10.iloc[0]["nama"] if len(top10) else "-", theme["success"], "target")
            with k3:
                kpi_card(theme, "Rata-rata Top 10", format_percentage(top10["matching_pct"].mean()) if len(top10) else "-",
                        "matching percentage", theme["warning"], "chart-line")

            st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)
            section_title(
                f"Top 10 Recommended Candidates — {req_row['nama_perusahaan']} / {req_row['nama_posisi']}",
                theme, icon_name="graduation",
            )
            display_cols = pd.DataFrame({
                "NIM": top10["NIM"], "Nama": top10["nama"], "Program Studi": top10["program_studi"],
                "Semester": top10["semester"], "IPK": top10["IPK"],
                "Recommendation Score (SAW)": top10["score"].round(3),
                "Matching %": top10["matching_pct"],
                "Alasan Rekomendasi": top10["reason"],
                "Faktor Perlu Ditingkatkan": top10["improve"],
            })
            render_table(display_cols, theme)

    else:  # Student - Company
        stu_options = sa_f.sort_values("nama")
        stu_labels = {
            row.NIM: f"{row.NIM} — {row.nama} ({row.program_studi})"
            for row in stu_options.itertuples()
        }
        sel_nim = st.selectbox(
            "Pilih Mahasiswa", options=list(stu_labels.keys()),
            format_func=lambda x: stu_labels[x],
        )
        stu_row = candidate_pool[candidate_pool["NIM"] == sel_nim]

        if stu_row.empty or open_talent_pool.empty:
            st.info("Data status mahasiswa ini tidak tersedia, atau tidak ada Talent Request terbuka pada rentang filter ini.")
        else:
            stu_row = stu_row.iloc[0]
            with st.spinner("Menghitung Recommendation Score (SAW)..."):
                scored = score_companies_for_student(stu_row, open_talent_pool, company_track_record, overall_track_record)
            scored["opportunity_pct"] = (scored["opportunity"] * 100).round(1)
            scored["matching_pct"] = (scored["score"] * 100).round(1)
            scored["reason"] = scored.apply(build_reason_s2c, axis=1)

            #mengambil skor terbaik per perusahaan (id_company) sehingga Top 10 = 10 perusahaan berbeda
            best_per_company = (
                scored.sort_values("score", ascending=False)
                .drop_duplicates(subset=["id_company"], keep="first")
            )
            top10 = best_per_company.sort_values("score", ascending=False).head(10).reset_index(drop=True)
            top10.index = top10.index + 1

            k1, k2, k3 = st.columns(3)
            with k1:
                kpi_card(theme, "Perusahaan Dievaluasi", format_number(scored["id_company"].nunique()),
                         f"untuk {stu_row['nama']}", theme["primary"], "building")
            with k2:
                kpi_card(theme, "Best Match Score", format_percentage(top10.iloc[0]["matching_pct"]) if len(top10) else "-",
                         top10.iloc[0]["nama_perusahaan"] if len(top10) else "-", theme["success"], "target")
            with k3:
                kpi_card(theme, "Rata-rata Opportunity Top 10", format_percentage(top10["opportunity_pct"].mean()) if len(top10) else "-",
                         "estimated acceptance opportunity", theme["warning"], "package")

            st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)
            section_title(f"Top 10 Recommended Companies — {stu_row['nama']}", theme, icon_name="building")
            display_cols = pd.DataFrame({
                "Perusahaan": top10["nama_perusahaan"], "Posisi": top10["nama_posisi"],
                "Jenis Penempatan": top10["jenis_penempatan"], "Headcount": top10["headcount"],
                "Recommendation Score": top10["score"].round(3),
                "Matching %": top10["matching_pct"],
                "Estimated Acceptance Opportunity (%)": top10["opportunity_pct"],
                "Alasan Rekomendasi": top10["reason"],
            })
            render_table(display_cols, theme)

# ==================================================================
# TAB 6 — EXECUTIVE DECISION PANEL
# ==================================================================
with tab_executive:
    section_title(
        "Executive Decision Panel", theme, icon_name="list",
        caption="Ringkasan keputusan otomatis hasil analisis data pada rentang filter aktif.",
    )

    top_priority_req = priority_requests.iloc[0] if len(priority_requests) else None
    top_candidate = candidate_pool.sort_values("general_score", ascending=False).iloc[0] \
        if len(candidate_pool) else None
    critical_company = comp_ghost_stats.sort_values("ghosting_rate", ascending=False).iloc[0] \
        if len(comp_ghost_stats) else None
    high_opportunity_company = comp_stats.sort_values("acceptance_rate", ascending=False).iloc[0] \
        if len(comp_stats) else None
    supply_alert = supply_demand.iloc[0] if len(supply_demand) and supply_demand.iloc[0]["gap"] > 0 else None

    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        kpi_card(
            theme, "Top Recommended Candidate",
            top_candidate["nama"] if top_candidate is not None else "-",
            f"{top_candidate['program_studi']} · readiness {format_percentage(top_candidate['general_score'] * 100, 0)}"
            if top_candidate is not None else "Data tidak tersedia",
            theme["success"], "graduation",
        )
    with c2:
        kpi_card(
            theme, "High Opportunity Company",
            high_opportunity_company["company"] if high_opportunity_company is not None else "-",
            f"Acceptance rate {format_percentage(high_opportunity_company['acceptance_rate'])}" if high_opportunity_company is not None
            else "Belum ada perusahaan dengan sampel cukup (min. 15 kandidat)",
            theme["success"], "package",
        )
    with c3:
        kpi_card(
            theme, "Student Supply Alert",
            supply_alert.name if supply_alert is not None else "Supply mencukupi",
            f"Gap {format_number(supply_alert['gap'])} kandidat (demand {format_number(supply_alert['demand'])} vs supply {format_number(supply_alert['supply'])})"
            if supply_alert is not None else "Tidak ada shortage signifikan pada rentang filter ini",
            theme["warning"], "user-x",
        )
    with c4:
       kpi_card(
            theme, "Top Priority Talent Request",
            top_priority_req["id_talent_req"] if top_priority_req is not None else "-",
            f"{top_priority_req['nama_perusahaan']} · headcount {format_number(top_priority_req['headcount'])}"
            if top_priority_req is not None else "Tidak ada request prioritas",
            theme["danger"], "file",
        )
    with c5:
        kpi_card(
            theme, "Critical Company",
            critical_company["company"] if critical_company is not None else "-",
            f"Ghosting rate {format_percentage(critical_company['ghosting_rate'])}" if critical_company is not None
            else "Belum ada perusahaan dengan sampel cukup (min. 15 kandidat)",
            theme["danger"], "alert",
        )

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
    section_title("Recommended Action Today", theme, icon_name="check",
                  caption="Diturunkan otomatis dari kondisi data pada rentang filter aktif.")

    actions = []
    if top_priority_req is not None:
        actions.append(
            f"Prioritaskan proses **{top_priority_req['id_talent_req']}** dari "
            f"**{top_priority_req['nama_perusahaan']}** ({top_priority_req['nama_posisi']}, "
            f"headcount {format_number(top_priority_req['headcount'])}), masih berstatus "
            f"'{top_priority_req['progress']}' sejak {pd.to_datetime(top_priority_req['request_date']).strftime('%d %b %Y')}."
        )
    if critical_company is not None:
        actions.append(
            f"Tinjau ulang kerja sama dengan **{critical_company['company']}**, ghosting rate historis "
            f"tertinggi ({format_percentage(critical_company['ghosting_rate'])} dari {format_number(critical_company['total'])} kandidat "
            "yang pernah dikirim), pertimbangkan follow-up personal ke PIC perusahaan."
        )
    if high_opportunity_company is not None:
        actions.append(
            f"Prioritaskan pengiriman kandidat baru ke **{high_opportunity_company['company']}**, acceptance "
            f"rate historis tertinggi ({format_percentage(high_opportunity_company['acceptance_rate'])}), peluang placement besar."
        )
    if supply_alert is not None:
        actions.append(
            f"Buka campaign rekrutmen mahasiswa program studi **{supply_alert.name}**, demand aktif "
            f"({format_number(supply_alert['demand'])}) melebihi supply mahasiswa Available ({format_number(supply_alert['supply'])})."
        )
    not_ready_count = int((~ss_f["eligible"]).sum())
    if not_ready_count > 0:
        actions.append(
            f"Kirim reminder pelengkapan dokumen ke **{format_number(not_ready_count)} mahasiswa** yang belum eligible "
            "(CV/portofolio belum lengkap, status tidak aktif, atau belum tersedia)."
        )
    if fu_count > 0:
        actions.append(
            f"Tindak lanjuti **{format_number(fu_count)} mahasiswa** yang masih berstatus Follow-up (FU 1/FU 2/FU 3) "
            "sebelum berubah menjadi kasus ghosting."
        )
    if ghosting_count > 0:
        actions.append(
            f"Evaluasi pola ghosting, total **{format_number(ghosting_count)} kasus** ({format_percentage(ghosting_rate)} dari seluruh proses) "
            "pada rentang filter ini, cek apakah terkonsentrasi pada perusahaan/posisi tertentu."
        )

    if actions:
        for a in actions[:8]:
            st.markdown(f"- {a}")
    else:
        st.info("Tidak ada rekomendasi aksi signifikan pada rentang filter ini.")

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
    colE1, colE2 = st.columns(2)
    with colE1:
        section_title("Talent Request Prioritas (Top 10)", theme, icon_name="list")
        if len(priority_requests):
            render_table(
                priority_requests[["id_talent_req", "nama_perusahaan", "nama_posisi", "headcount",
                                    "request_date", "progress"]].head(10),
                theme,
            )
        else:
            st.info("Tidak ada talent request prioritas pada rentang filter ini.")
    with colE2:
        section_title("Program Studi dengan Supply Gap Terbesar (Top 10)", theme, icon_name="user-x")
        gap_table = supply_demand[supply_demand["gap"] > 0].head(10).reset_index()
        gap_table.columns = ["Program Studi", "Demand", "Supply", "Gap"]
        if len(gap_table):
            render_table(gap_table, theme)
        else:
            st.info("Tidak ada shortage supply mahasiswa pada rentang filter ini.")

# ==================================================================
# FOOTER
# ==================================================================
st.divider()
st.markdown(
    f"""
    <div style="text-align:center; color:{theme['caption']}; font-size:13px; padding:16px 0;">
        <b style="color:{theme['text_secondary']};">Student Placement System</b><br/>
        Career Development Center &nbsp;·&nbsp; Sebelas Maret Statistics Fair</b><br/>
        Build by Jaret & Matthew - Ini Jaret's Team
    </div>
    """,
    unsafe_allow_html=True,
)