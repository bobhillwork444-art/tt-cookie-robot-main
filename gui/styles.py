"""
TT Cookie Robot - UI Styles and Constants
Catppuccin theme with Light mode support
"""

# === CATPPUCCIN MOCHA THEME ===
CATPPUCCIN = {
    # Backgrounds
    "base":      "#1E1E2E",  # Main background
    "mantle":    "#181825",  # Darker (sidebar, header)
    "crust":     "#11111B",  # Darkest (borders)
    "surface0":  "#313244",  # Cards, inputs
    "surface1":  "#45475A",  # Hover states
    "surface2":  "#585B70",  # Active elements
    
    # Text
    "text":      "#CDD6F4",  # Primary text
    "subtext1":  "#BAC2DE",  # Secondary text
    "subtext0":  "#A6ADC8",  # Muted text
    "overlay0":  "#6C7086",  # Placeholders, disabled
    
    # Accents
    "lavender":  "#B4BEFE",  # Primary accent
    "blue":      "#89B4FA",  # Links, info
    "sapphire":  "#74C7EC",  # Secondary accent
    "sky":       "#89DCEB",  # Hover on accents
    "teal":      "#94E2D5",  # Alt success
    "green":     "#A6E3A1",  # Success (proxy OK)
    "yellow":    "#F9E2AF",  # Warning
    "peach":     "#FAB387",  # Pause, pending
    "maroon":    "#EBA0AC",  # Soft error
    "red":       "#F38BA8",  # Error
    "mauve":     "#CBA6F7",  # Special accent
    "pink":      "#F5C2E7",  # Decorative
    "flamingo":  "#F2CDCD",  # Decorative
    "rosewater": "#F5E0DC",  # Decorative
}

# === UI SIZE CONSTANTS (1.5x window, 1.35x elements) ===
UI_SCALE = 1.35
WINDOW_MIN_WIDTH = 1200
WINDOW_MIN_HEIGHT = 900
FONT_SIZE_BASE = 16
FONT_SIZE_SMALL = 14
FONT_SIZE_LARGE = 19
FONT_SIZE_TITLE = 22
ICON_SIZE = 19
BUTTON_HEIGHT = 38
BUTTON_MIN_WIDTH = 90
INPUT_HEIGHT = 32
SPACING = 12
MARGIN = 14
BORDER_RADIUS = 6
PROFILE_ROW_HEIGHT = 44
FLAG_WIDTH = 32
FLAG_HEIGHT = 22


# === COUNTRY MAPPINGS ===

# Country name to ISO code mapping (API returns full names)
COUNTRY_NAME_TO_CODE = {
    "UNITED STATES": "US", "USA": "US", "UNITED STATES OF AMERICA": "US",
    "UNITED KINGDOM": "GB", "UK": "GB", "GREAT BRITAIN": "GB", "ENGLAND": "GB",
    "GERMANY": "DE", "DEUTSCHLAND": "DE",
    "FRANCE": "FR",
    "ITALY": "IT", "ITALIA": "IT",
    "SPAIN": "ES", "ESPANA": "ES",
    "NETHERLANDS": "NL", "THE NETHERLANDS": "NL", "HOLLAND": "NL",
    "POLAND": "PL", "POLSKA": "PL",
    "RUSSIA": "RU", "RUSSIAN FEDERATION": "RU",
    "UKRAINE": "UA",
    "CANADA": "CA",
    "AUSTRALIA": "AU",
    "JAPAN": "JP",
    "SOUTH KOREA": "KR", "KOREA": "KR",
    "CHINA": "CN",
    "BRAZIL": "BR", "BRASIL": "BR",
    "MEXICO": "MX",
    "ARGENTINA": "AR",
    "INDIA": "IN",
    "SINGAPORE": "SG",
    "SWEDEN": "SE",
    "NORWAY": "NO",
    "FINLAND": "FI",
    "DENMARK": "DK",
    "SWITZERLAND": "CH",
    "AUSTRIA": "AT",
    "BELGIUM": "BE",
    "PORTUGAL": "PT",
    "CZECH REPUBLIC": "CZ", "CZECHIA": "CZ",
    "GREECE": "GR",
    "TURKEY": "TR",
    "ISRAEL": "IL",
    "UNITED ARAB EMIRATES": "AE", "UAE": "AE",
    "SOUTH AFRICA": "ZA",
    "THAILAND": "TH",
    "VIETNAM": "VN",
    "INDONESIA": "ID",
    "MALAYSIA": "MY",
    "PHILIPPINES": "PH",
    "HONG KONG": "HK",
    "TAIWAN": "TW",
    "NEW ZEALAND": "NZ",
    "IRELAND": "IE",
    "ROMANIA": "RO",
    "HUNGARY": "HU",
    "SLOVAKIA": "SK",
    "BULGARIA": "BG",
    "CROATIA": "HR",
    "SERBIA": "RS",
    "LITHUANIA": "LT",
    "LATVIA": "LV",
    "ESTONIA": "EE",
    "CHILE": "CL",
    "COLOMBIA": "CO",
    "PERU": "PE",
    # Additional countries
    "SLOVENIA": "SI",
    "CYPRUS": "CY",
    "MALTA": "MT",
    "LUXEMBOURG": "LU",
    "ICELAND": "IS",
    "MONACO": "MC",
    "ANDORRA": "AD",
    "LIECHTENSTEIN": "LI",
    "SAN MARINO": "SM",
    "MONTENEGRO": "ME",
    "NORTH MACEDONIA": "MK", "MACEDONIA": "MK",
    "ALBANIA": "AL",
    "BOSNIA AND HERZEGOVINA": "BA", "BOSNIA": "BA",
    "KOSOVO": "XK",
    "MOLDOVA": "MD",
    "BELARUS": "BY",
    "GEORGIA": "GE",
    "ARMENIA": "AM",
    "AZERBAIJAN": "AZ",
    "KAZAKHSTAN": "KZ",
    "UZBEKISTAN": "UZ",
    "PAKISTAN": "PK",
    "BANGLADESH": "BD",
    "SRI LANKA": "LK",
    "NEPAL": "NP",
    "CAMBODIA": "KH",
    "MYANMAR": "MM", "BURMA": "MM",
    "LAOS": "LA",
    "MONGOLIA": "MN",
    "NORTH KOREA": "KP",
    "SAUDI ARABIA": "SA",
    "QATAR": "QA",
    "KUWAIT": "KW",
    "BAHRAIN": "BH",
    "OMAN": "OM",
    "JORDAN": "JO",
    "LEBANON": "LB",
    "IRAQ": "IQ",
    "IRAN": "IR",
    "EGYPT": "EG",
    "MOROCCO": "MA",
    "ALGERIA": "DZ",
    "TUNISIA": "TN",
    "LIBYA": "LY",
    "NIGERIA": "NG",
    "KENYA": "KE",
    "GHANA": "GH",
    "ETHIOPIA": "ET",
    "TANZANIA": "TZ",
    "UGANDA": "UG",
    "VENEZUELA": "VE",
    "ECUADOR": "EC",
    "BOLIVIA": "BO",
    "PARAGUAY": "PY",
    "URUGUAY": "UY",
    "COSTA RICA": "CR",
    "PANAMA": "PA",
    "GUATEMALA": "GT",
    "CUBA": "CU",
    "DOMINICAN REPUBLIC": "DO",
    "PUERTO RICO": "PR",
    "JAMAICA": "JM",
}

# Country code to flag emoji mapping
COUNTRY_FLAGS = {
    "US": "🇺🇸", "GB": "🇬🇧", "DE": "🇩🇪", "FR": "🇫🇷", "IT": "🇮🇹",
    "ES": "🇪🇸", "NL": "🇳🇱", "PL": "🇵🇱", "RU": "🇷🇺", "UA": "🇺🇦",
    "CA": "🇨🇦", "AU": "🇦🇺", "JP": "🇯🇵", "KR": "🇰🇷", "CN": "🇨🇳",
    "BR": "🇧🇷", "MX": "🇲🇽", "AR": "🇦🇷", "IN": "🇮🇳", "SG": "🇸🇬",
    "SE": "🇸🇪", "NO": "🇳🇴", "FI": "🇫🇮", "DK": "🇩🇰", "CH": "🇨🇭",
    "AT": "🇦🇹", "BE": "🇧🇪", "PT": "🇵🇹", "CZ": "🇨🇿", "GR": "🇬🇷",
    "TR": "🇹🇷", "IL": "🇮🇱", "AE": "🇦🇪", "ZA": "🇿🇦", "TH": "🇹🇭",
    "VN": "🇻🇳", "ID": "🇮🇩", "MY": "🇲🇾", "PH": "🇵🇭", "HK": "🇭🇰",
    "TW": "🇹🇼", "NZ": "🇳🇿", "IE": "🇮🇪", "RO": "🇷🇴", "HU": "🇭🇺",
    "SK": "🇸🇰", "BG": "🇧🇬", "HR": "🇭🇷", "RS": "🇷🇸", "LT": "🇱🇹",
    "LV": "🇱🇻", "EE": "🇪🇪", "CL": "🇨🇱", "CO": "🇨🇴", "PE": "🇵🇪",
    # Additional countries
    "SI": "🇸🇮", "CY": "🇨🇾", "MT": "🇲🇹", "LU": "🇱🇺", "IS": "🇮🇸",
    "MC": "🇲🇨", "AD": "🇦🇩", "LI": "🇱🇮", "SM": "🇸🇲", "ME": "🇲🇪",
    "MK": "🇲🇰", "AL": "🇦🇱", "BA": "🇧🇦", "XK": "🇽🇰", "MD": "🇲🇩",
    "BY": "🇧🇾", "GE": "🇬🇪", "AM": "🇦🇲", "AZ": "🇦🇿", "KZ": "🇰🇿",
    "UZ": "🇺🇿", "PK": "🇵🇰", "BD": "🇧🇩", "LK": "🇱🇰", "NP": "🇳🇵",
    "KH": "🇰🇭", "MM": "🇲🇲", "LA": "🇱🇦", "MN": "🇲🇳", "KP": "🇰🇵",
    "SA": "🇸🇦", "QA": "🇶🇦", "KW": "🇰🇼", "BH": "🇧🇭", "OM": "🇴🇲",
    "JO": "🇯🇴", "LB": "🇱🇧", "IQ": "🇮🇶", "IR": "🇮🇷", "EG": "🇪🇬",
    "MA": "🇲🇦", "DZ": "🇩🇿", "TN": "🇹🇳", "LY": "🇱🇾", "NG": "🇳🇬",
    "KE": "🇰🇪", "GH": "🇬🇭", "ET": "🇪🇹", "TZ": "🇹🇿", "UG": "🇺🇬",
    "VE": "🇻🇪", "EC": "🇪🇨", "BO": "🇧🇴", "PY": "🇵🇾", "UY": "🇺🇾",
    "CR": "🇨🇷", "PA": "🇵🇦", "GT": "🇬🇹", "CU": "🇨🇺", "DO": "🇩🇴",
    "PR": "🇵🇷", "JM": "🇯🇲",
}


# === GEO DOMAIN CONSTANTS ===

# EU member states TLDs (27 countries)
EU_TLDS = {
    'at', 'be', 'bg', 'hr', 'cy', 'cz', 'dk', 'ee', 'fi', 'fr',
    'de', 'gr', 'hu', 'ie', 'it', 'lv', 'lt', 'lu', 'mt', 'nl',
    'pl', 'pt', 'ro', 'sk', 'si', 'es', 'se'
}

# Generic TLDs (not country-specific)
GENERIC_TLDS = {
    'com', 'org', 'net', 'io', 'xyz', 'info', 'biz', 'co', 'app',
    'dev', 'ai', 'tech', 'online', 'site', 'website', 'blog', 'shop',
    'store', 'cloud', 'digital', 'media', 'news', 'tv', 'fm', 'me'
}

# Country code to TLD mapping
COUNTRY_TO_TLD = {
    'US': ['us', 'com'],
    'GB': ['uk', 'co.uk'],
    'CA': ['ca'],
    'AU': ['au', 'com.au'],
    'DE': ['de'],
    'FR': ['fr'],
    'IT': ['it'],
    'ES': ['es'],
    'NL': ['nl'],
    'PL': ['pl'],
    'PT': ['pt'],
    'AT': ['at'],
    'BE': ['be'],
    'SE': ['se'],
    'NO': ['no'],
    'FI': ['fi'],
    'DK': ['dk'],
    'CH': ['ch'],
    'CZ': ['cz'],
    'GR': ['gr'],
    'RO': ['ro'],
    'HU': ['hu'],
    'SK': ['sk'],
    'BG': ['bg'],
    'HR': ['hr'],
    'SI': ['si'],
    'LT': ['lt'],
    'LV': ['lv'],
    'EE': ['ee'],
    'IE': ['ie'],
    'CY': ['cy'],
    'MT': ['mt'],
    'LU': ['lu'],
    'RU': ['ru'],
    'UA': ['ua'],
    'TR': ['tr'],
    'JP': ['jp'],
    'KR': ['kr'],
    'CN': ['cn'],
    'IN': ['in'],
    'BR': ['br'],
    'MX': ['mx'],
    'AR': ['ar'],
}


# === HELPER FUNCTIONS ===

def normalize_country(country_raw: str) -> str:
    """Convert country name or code to ISO 2-letter code."""
    if not country_raw:
        return ""
    country_upper = country_raw.upper().strip()
    # If already a 2-letter code
    if len(country_upper) == 2 and country_upper in COUNTRY_FLAGS:
        return country_upper
    # Look up in name mapping
    return COUNTRY_NAME_TO_CODE.get(country_upper, "")


def get_site_tld(url: str) -> str:
    """Extract TLD from URL (e.g., 'example.com' -> 'com', 'site.co.uk' -> 'co.uk')."""
    try:
        # Remove protocol
        domain = url.lower().replace('https://', '').replace('http://', '')
        # Remove path
        domain = domain.split('/')[0]
        # Remove port
        domain = domain.split(':')[0]
        # Get TLD
        parts = domain.split('.')
        if len(parts) >= 2:
            # Check for compound TLDs like co.uk, com.au
            if len(parts) >= 3 and parts[-2] in ('co', 'com', 'org', 'net', 'gov', 'ac'):
                return f"{parts[-2]}.{parts[-1]}"
            return parts[-1]
        return ''
    except:
        return ''


def get_site_geo_category(url: str) -> str:
    """Categorize site by geo: 'us', 'uk', 'ca', 'eu', 'generic', or specific country code."""
    tld = get_site_tld(url)
    if not tld:
        return 'generic'
    
    # US
    if tld in ('us', 'com'):
        return 'us'
    # UK
    if tld in ('uk', 'co.uk'):
        return 'uk'
    # CA
    if tld == 'ca':
        return 'ca'
    # EU
    if tld in EU_TLDS:
        return 'eu'
    # Generic
    if tld in GENERIC_TLDS:
        return 'generic'
    # Specific country TLD
    return tld


def generate_dark_theme_stylesheet() -> str:
    """Generate Catppuccin Mocha (Dark) theme stylesheet."""
    c = CATPPUCCIN
    font_base = f"{FONT_SIZE_BASE}px"
    font_small = f"{FONT_SIZE_SMALL}px"
    
    return f"""
        /* === GLOBAL === */
        QMainWindow, QWidget {{
            background-color: {c['base']};
            color: {c['text']};
            font-family: 'Segoe UI', 'SF Pro Display', Arial, sans-serif;
            font-size: {font_base};
        }}
        
        QLabel {{
            color: {c['text']};
            font-size: {font_base};
        }}
        
        /* === BUTTONS === */
        QPushButton {{
            background-color: {c['surface0']};
            border: 1px solid {c['surface1']};
            border-radius: {BORDER_RADIUS}px;
            padding: 4px 10px;
            min-height: {BUTTON_HEIGHT - 8}px;
            color: {c['text']};
            font-size: {font_base};
        }}
        QPushButton:hover {{
            background-color: {c['surface1']};
            border-color: {c['lavender']};
        }}
        QPushButton:pressed {{
            background-color: {c['surface2']};
        }}
        QPushButton:checked {{
            background-color: {c['lavender']};
            color: {c['crust']};
            border-color: {c['lavender']};
        }}
        QPushButton:disabled {{
            background-color: {c['surface0']};
            color: {c['overlay0']};
            border-color: {c['surface0']};
        }}
        
        /* === INPUTS === */
        QLineEdit, QSpinBox, QDoubleSpinBox {{
            background-color: {c['surface0']};
            border: 1px solid {c['surface1']};
            border-radius: {BORDER_RADIUS}px;
            padding: 8px 12px;
            min-height: {INPUT_HEIGHT - 16}px;
            color: {c['text']};
            font-size: {font_base};
            selection-background-color: {c['lavender']};
            selection-color: {c['crust']};
        }}
        QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus {{
            border-color: {c['lavender']};
            background-color: {c['surface1']};
        }}
        QLineEdit:disabled, QSpinBox:disabled {{
            background-color: {c['mantle']};
            color: {c['overlay0']};
        }}
        QLineEdit::placeholder {{
            color: {c['overlay0']};
        }}
        
        /* === COMBOBOX === */
        QComboBox {{
            background-color: {c['surface0']};
            border: 1px solid {c['surface1']};
            border-radius: {BORDER_RADIUS}px;
            padding: 8px 12px;
            min-height: {INPUT_HEIGHT - 16}px;
            color: {c['text']};
            font-size: {font_base};
        }}
        QComboBox:hover {{
            border-color: {c['lavender']};
        }}
        QComboBox::drop-down {{
            border: none;
            padding-right: 10px;
        }}
        QComboBox::down-arrow {{
            width: 12px;
            height: 12px;
        }}
        QComboBox QAbstractItemView {{
            background-color: {c['surface0']};
            border: 1px solid {c['surface1']};
            border-radius: {BORDER_RADIUS}px;
            color: {c['text']};
            selection-background-color: {c['lavender']};
            selection-color: {c['crust']};
            padding: 4px;
        }}
        
        /* === TEXT EDIT (LOG) === */
        QTextEdit {{
            background-color: {c['crust']};
            border: 1px solid {c['surface0']};
            border-radius: {BORDER_RADIUS}px;
            color: {c['green']};
            font-family: 'Cascadia Code', 'Fira Code', 'Consolas', monospace;
            font-size: {font_small};
            padding: 8px;
        }}
        
        /* === LISTS === */
        QListWidget {{
            background-color: {c['surface0']};
            border: 1px solid {c['surface1']};
            border-radius: {BORDER_RADIUS}px;
            padding: 4px;
            outline: none;
        }}
        QListWidget::item {{
            padding: 4px;
            border-radius: 4px;
            margin: 2px;
        }}
        QListWidget::item:hover {{
            background-color: {c['surface1']};
        }}
        QListWidget::item:selected {{
            background-color: {c['lavender']};
            color: {c['crust']};
        }}
        
        /* === TABS === */
        QTabWidget::pane {{
            border: 1px solid {c['surface1']};
            border-radius: {BORDER_RADIUS}px;
            background-color: {c['base']};
            margin-top: -1px;
        }}
        QTabBar::tab {{
            background-color: {c['surface0']};
            border: 1px solid {c['surface1']};
            border-bottom: none;
            border-top-left-radius: {BORDER_RADIUS}px;
            border-top-right-radius: {BORDER_RADIUS}px;
            padding: 10px 24px;
            margin-right: 4px;
            color: {c['subtext0']};
            font-size: {font_base};
            font-weight: 500;
            min-width: 80px;
        }}
        QTabBar::tab:selected {{
            background-color: {c['base']};
            color: {c['lavender']};
            border-color: {c['surface1']};
        }}
        QTabBar::tab:hover:!selected {{
            background-color: {c['surface1']};
            color: {c['text']};
        }}
        
        /* === GROUP BOX === */
        QGroupBox {{
            border: 1px solid {c['surface1']};
            border-radius: {BORDER_RADIUS}px;
            margin-top: 16px;
            padding-top: 16px;
            font-size: {font_base};
        }}
        QGroupBox::title {{
            subcontrol-origin: margin;
            left: 12px;
            padding: 0 8px;
            color: {c['blue']};
            font-weight: 600;
            font-size: {font_base};
        }}
        
        /* === CHECKBOX === */
        QCheckBox {{
            spacing: 10px;
            font-size: {font_base};
            color: {c['text']};
        }}
        QCheckBox::indicator {{
            width: 20px;
            height: 20px;
            border-radius: 4px;
            border: 2px solid {c['surface2']};
            background-color: {c['surface0']};
        }}
        QCheckBox::indicator:hover {{
            border-color: {c['lavender']};
        }}
        QCheckBox::indicator:checked {{
            background-color: {c['green']};
            border-color: {c['green']};
        }}
        QCheckBox::indicator:disabled {{
            background-color: {c['surface0']};
            border-color: {c['surface1']};
        }}
        
        /* === RADIO BUTTON === */
        QRadioButton {{
            spacing: 10px;
            font-size: {font_base};
            color: {c['text']};
        }}
        QRadioButton::indicator {{
            width: 20px;
            height: 20px;
            border-radius: 10px;
            border: 2px solid {c['surface2']};
            background-color: {c['surface0']};
        }}
        QRadioButton::indicator:hover {{
            border-color: {c['lavender']};
        }}
        QRadioButton::indicator:checked {{
            background-color: {c['lavender']};
            border-color: {c['lavender']};
        }}
        
        /* === SCROLLBAR === */
        QScrollBar:vertical {{
            background-color: {c['mantle']};
            width: 12px;
            border-radius: 6px;
            margin: 2px;
        }}
        QScrollBar::handle:vertical {{
            background-color: {c['surface1']};
            border-radius: 5px;
            min-height: 30px;
            margin: 2px;
        }}
        QScrollBar::handle:vertical:hover {{
            background-color: {c['surface2']};
        }}
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
            height: 0px;
        }}
        QScrollBar:horizontal {{
            background-color: {c['mantle']};
            height: 12px;
            border-radius: 6px;
            margin: 2px;
        }}
        QScrollBar::handle:horizontal {{
            background-color: {c['surface1']};
            border-radius: 5px;
            min-width: 30px;
            margin: 2px;
        }}
        QScrollBar::handle:horizontal:hover {{
            background-color: {c['surface2']};
        }}
        QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
            width: 0px;
        }}
        
        /* === SCROLL AREA === */
        QScrollArea {{
            border: none;
            background-color: transparent;
        }}
        
        /* === TOOLTIP === */
        QToolTip {{
            background-color: {c['surface1']};
            color: {c['text']};
            border: 1px solid {c['surface2']};
            border-radius: 4px;
            padding: 6px 10px;
            font-size: {font_small};
        }}
        
        /* === PROGRESS BAR === */
        QProgressBar {{
            background-color: {c['surface0']};
            border: 1px solid {c['surface1']};
            border-radius: {BORDER_RADIUS}px;
            text-align: center;
            color: {c['text']};
            font-size: {font_small};
            height: 24px;
        }}
        QProgressBar::chunk {{
            background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 {c['lavender']}, stop:1 {c['mauve']});
            border-radius: 5px;
        }}
        
        /* === SLIDER === */
        QSlider::groove:horizontal {{
            background-color: {c['surface1']};
            height: 8px;
            border-radius: 4px;
        }}
        QSlider::handle:horizontal {{
            background-color: {c['lavender']};
            width: 20px;
            height: 20px;
            margin: -6px 0;
            border-radius: 10px;
        }}
        QSlider::handle:horizontal:hover {{
            background-color: {c['sky']};
        }}
        
        /* === MENU === */
        QMenu {{
            background-color: {c['surface0']};
            border: 1px solid {c['surface1']};
            border-radius: {BORDER_RADIUS}px;
            padding: 4px;
        }}
        QMenu::item {{
            padding: 8px 24px;
            border-radius: 4px;
            color: {c['text']};
        }}
        QMenu::item:selected {{
            background-color: {c['surface1']};
        }}
        QMenu::separator {{
            height: 1px;
            background-color: {c['surface1']};
            margin: 4px 8px;
        }}
        
        /* === DIALOG === */
        QDialog {{
            background-color: {c['base']};
            color: {c['text']};
        }}
        
        /* === MESSAGE BOX === */
        QMessageBox {{
            background-color: {c['base']};
        }}
        QMessageBox QLabel {{
            color: {c['text']};
            font-size: {font_base};
        }}
        QMessageBox QPushButton {{
            min-width: 80px;
        }}
        
        /* === SPLITTER === */
        QSplitter::handle {{
            background-color: {c['surface1']};
        }}
        QSplitter::handle:hover {{
            background-color: {c['lavender']};
        }}
        
        /* === FRAME === */
        QFrame {{
            border: none;
        }}
        QFrame[frameShape="4"] /* HLine */ {{
            background-color: {c['surface1']};
            max-height: 1px;
        }}
        QFrame[frameShape="5"] /* VLine */ {{
            background-color: {c['surface1']};
            max-width: 1px;
        }}
    """


def generate_light_theme_stylesheet() -> str:
    """Generate Catppuccin Latte (Light) theme stylesheet."""
    font_base = f"{FONT_SIZE_BASE}px"
    font_small = f"{FONT_SIZE_SMALL}px"
    
    return f"""
        QMainWindow, QWidget {{
            background-color: #EFF1F5;
            color: #4C4F69;
            font-family: 'Segoe UI', 'SF Pro Display', Arial, sans-serif;
            font-size: {font_base};
        }}
        QLabel {{ color: #4C4F69; font-size: {font_base}; }}
        QPushButton {{
            background-color: #E6E9EF;
            border: 1px solid #DCE0E8;
            border-radius: {BORDER_RADIUS}px;
            padding: 8px 16px;
            min-height: {BUTTON_HEIGHT - 16}px;
            color: #4C4F69;
            font-size: {font_base};
        }}
        QPushButton:hover {{ background-color: #DCE0E8; border-color: #7287FD; }}
        QPushButton:checked {{ background-color: #7287FD; color: #EFF1F5; }}
        QPushButton:disabled {{ background-color: #E6E9EF; color: #9CA0B0; }}
        QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox {{
            background-color: #FFFFFF;
            border: 1px solid #DCE0E8;
            border-radius: {BORDER_RADIUS}px;
            padding: 8px 12px;
            min-height: {INPUT_HEIGHT - 16}px;
            color: #4C4F69;
            font-size: {font_base};
        }}
        QLineEdit:focus, QSpinBox:focus {{ border-color: #7287FD; }}
        QTextEdit {{
            background-color: #FFFFFF;
            border: 1px solid #DCE0E8;
            border-radius: {BORDER_RADIUS}px;
            color: #40A02B;
            font-family: 'Cascadia Code', monospace;
            font-size: {font_small};
        }}
        QListWidget {{
            background-color: #FFFFFF;
            border: 1px solid #DCE0E8;
            border-radius: {BORDER_RADIUS}px;
        }}
        QListWidget::item:selected {{ background-color: #7287FD; color: #EFF1F5; }}
        QTabWidget::pane {{ border: 1px solid #DCE0E8; border-radius: {BORDER_RADIUS}px; }}
        QTabBar::tab {{
            background-color: #E6E9EF;
            border: 1px solid #DCE0E8;
            padding: 10px 24px;
            font-size: {font_base};
            min-width: 80px;
        }}
        QTabBar::tab:selected {{ background-color: #EFF1F5; color: #7287FD; }}
        QGroupBox {{
            border: 1px solid #DCE0E8;
            border-radius: {BORDER_RADIUS}px;
            margin-top: 16px;
            padding-top: 16px;
        }}
        QGroupBox::title {{ color: #1E66F5; font-weight: 600; }}
        QCheckBox::indicator {{
            width: 20px; height: 20px;
            border-radius: 4px;
            border: 2px solid #9CA0B0;
            background-color: #FFFFFF;
        }}
        QCheckBox::indicator:checked {{ background-color: #40A02B; border-color: #40A02B; }}
        QScrollArea {{ border: none; }}
        QDialog {{ background-color: #EFF1F5; color: #4C4F69; }}
        QScrollBar:vertical {{
            background-color: #E6E9EF; width: 12px; border-radius: 6px;
        }}
        QScrollBar::handle:vertical {{
            background-color: #BCC0CC; border-radius: 5px; min-height: 30px;
        }}
        QScrollBar::handle:vertical:hover {{ background-color: #9CA0B0; }}
        QToolTip {{
            background-color: #E6E9EF; color: #4C4F69;
            border: 1px solid #DCE0E8; border-radius: 4px;
            padding: 6px 10px; font-size: {font_small};
        }}
    """


def get_theme_stylesheet(theme: str = "Light") -> str:
    """Get stylesheet for specified theme."""
    if theme == "Dark":
        return generate_dark_theme_stylesheet()
    return generate_light_theme_stylesheet()
