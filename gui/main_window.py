"""
TT Cookie Robot - GUI for Octo Browser automation
Two modes: Cookie Mode and Google Warm-up Mode
"""
import json
import asyncio
import os
from datetime import datetime
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QTabWidget,
    QLabel, QPushButton, QLineEdit, QTextEdit, QListWidget, QListWidgetItem,
    QSpinBox, QDoubleSpinBox, QCheckBox, QGroupBox, QFormLayout, QMessageBox, QFileDialog,
    QStackedWidget, QFrame, QScrollArea, QSplitter, QApplication, QComboBox,
    QSizePolicy
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QSize
from PyQt5.QtGui import QFont, QPixmap

from core.octo_api import OctoAPI
from core.automation import BrowserAutomation
from core.translator import load_translation, tr


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

# Country code to flag emoji mapping (for systems that support it)
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

# Country code to TLD mapping (most use lowercase country code)
COUNTRY_TO_TLD = {
    'US': ['us', 'com'],  # US includes .com as local
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


class ProfileItemWidget(QWidget):
    """Custom widget for profile list item with flag and copy button"""
    copy_clicked = pyqtSignal(str)  # Emits UUID when copy clicked
    migrate_clicked = pyqtSignal(str, int, bool)  # Emits UUID, age_days, google_authorized
    check_changed = pyqtSignal(str, bool)  # Emits UUID and check state
    google_auth_changed = pyqtSignal(str, bool)  # Emits UUID and auth state
    ads_changed = pyqtSignal(str, bool)  # Google Ads registration state
    payment_changed = pyqtSignal(str, bool)  # Payment method state
    campaign_changed = pyqtSignal(str, bool)  # Ad campaign state
    ready_changed = pyqtSignal(str, bool)  # Profile ready state
    
    def __init__(self, uuid: str, country: str = "", first_run: str = "", mode: str = "cookie", 
                 google_authorized: bool = False, ads_registered: bool = False,
                 payment_linked: bool = False, campaign_launched: bool = False,
                 profile_ready: bool = False,
                 ads_timestamp: str = "", payment_timestamp: str = "", 
                 campaign_timestamp: str = "", ready_timestamp: str = "",
                 parent=None):
        super().__init__(parent)
        self.uuid = uuid
        self.mode = mode
        self.google_authorized = google_authorized
        self.ads_registered = ads_registered
        self.payment_linked = payment_linked
        self.campaign_launched = campaign_launched
        self.profile_ready = profile_ready
        # Timestamps for activation time tracking
        self.ads_timestamp = ads_timestamp
        self.payment_timestamp = payment_timestamp
        self.campaign_timestamp = campaign_timestamp
        self.ready_timestamp = ready_timestamp
        # Normalize country name to ISO code
        self.country_code = normalize_country(country)
        self.first_run = first_run  # ISO date string
        self.age_days = self._get_age_days()
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 2, 4, 2)
        layout.setSpacing(6)
        
        # Checkbox for selection
        self.checkbox = QCheckBox()
        self.checkbox.stateChanged.connect(self._on_check_changed)
        layout.addWidget(self.checkbox)
        
        # Flag icon using QLabel with pixmap or emoji fallback
        self.flag_label = QLabel()
        flag_loaded = False
        
        if self.country_code:
            # Try to load flag PNG from assets folder
            app_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            flag_path = os.path.join(app_dir, "assets", "flags", f"{self.country_code.lower()}.png")
            if os.path.exists(flag_path):
                pixmap = QPixmap(flag_path)
                if not pixmap.isNull():
                    self.flag_label.setPixmap(pixmap.scaled(24, 16, Qt.KeepAspectRatio, Qt.SmoothTransformation))
                    flag_loaded = True
        
        if not flag_loaded:
            # Fallback to emoji (may not render on Windows)
            flag_emoji = COUNTRY_FLAGS.get(self.country_code, "🌐") if self.country_code else "🌐"
            self.flag_label.setText(flag_emoji)
        
        self.flag_label.setFixedWidth(28)
        layout.addWidget(self.flag_label)
        
        # Country code label (e.g., "GB", "NL")
        if self.country_code:
            self.code_label = QLabel(f"({self.country_code})")
            self.code_label.setStyleSheet("color: #888; font-size: 11px;")
            self.code_label.setFixedWidth(32)
            layout.addWidget(self.code_label)
        
        # UUID label (truncated)
        self.uuid_label = QLabel(f"{uuid[:8]}...")
        self.uuid_label.setToolTip(uuid)
        layout.addWidget(self.uuid_label, 1)
        
        # Google authorization button (only for cookie mode)
        if mode == "cookie":
            self.google_btn = QPushButton("G")
            self.google_btn.setMinimumWidth(32)
            self.google_btn.setMaximumWidth(40)
            self.google_btn.setToolTip(tr("Google authorization status"))
            self._update_google_btn_style()
            self.google_btn.clicked.connect(self._on_google_click)
            layout.addWidget(self.google_btn)
        
        # Google mode buttons: Ads, Payment, Campaign, Ready
        if mode == "google":
            # Google Ads registration button
            self.ads_btn = QPushButton("Ads")
            self.ads_btn.setMinimumWidth(40)
            self.ads_btn.setMaximumWidth(50)
            self._update_ads_btn_style()
            self.ads_btn.clicked.connect(self._on_ads_click)
            layout.addWidget(self.ads_btn)
            
            # Payment method button
            self.payment_btn = QPushButton("💳")
            self.payment_btn.setMinimumWidth(36)
            self.payment_btn.setMaximumWidth(44)
            self._update_payment_btn_style()
            self.payment_btn.clicked.connect(self._on_payment_click)
            layout.addWidget(self.payment_btn)
            
            # Ad campaign button (РК = Рекламная Кампания in Russian)
            self.campaign_btn = QPushButton(tr("Ad"))
            self.campaign_btn.setMinimumWidth(36)
            self.campaign_btn.setMaximumWidth(44)
            self._update_campaign_btn_style()
            self.campaign_btn.clicked.connect(self._on_campaign_click)
            layout.addWidget(self.campaign_btn)
            
            # Profile ready button (profile warmed up and ready)
            self.ready_btn = QPushButton("✓")
            self.ready_btn.setMinimumWidth(36)
            self.ready_btn.setMaximumWidth(44)
            self._update_ready_btn_style()
            self.ready_btn.clicked.connect(self._on_ready_click)
            layout.addWidget(self.ready_btn)
        
        # Migration button (only for cookie mode) - arrow pointing right
        if mode == "cookie":
            self.migrate_btn = QPushButton("→")
            self.migrate_btn.setMinimumWidth(32)
            self.migrate_btn.setMaximumWidth(40)
            self.migrate_btn.setToolTip(tr("Migrate to Google mode"))
            self.migrate_btn.setStyleSheet("font-weight: bold;")
            self.migrate_btn.clicked.connect(self._on_migrate)
            layout.addWidget(self.migrate_btn)
        
        # Profile age in days (from first run)
        age_text = self._calculate_age()
        self.age_label = QLabel(age_text)
        self.age_label.setStyleSheet("color: #666; font-size: 11px;")
        self.age_label.setFixedWidth(50)
        self.age_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        if self.first_run:
            self.age_label.setToolTip(f"First run: {self.first_run}")
        layout.addWidget(self.age_label)
        
        # Copy button
        self.copy_btn = QPushButton("⧉")
        self.copy_btn.setMinimumWidth(36)
        self.copy_btn.setMaximumWidth(44)
        self.copy_btn.setToolTip(tr("Copy UUID"))
        self.copy_btn.clicked.connect(self._on_copy)
        layout.addWidget(self.copy_btn)
    
    def _update_google_btn_style(self):
        """Update Google button style based on authorization state."""
        if self.google_authorized:
            # Colored - Google colors
            self.google_btn.setStyleSheet("""
                QPushButton {
                    font-weight: bold;
                    color: #4285f4;
                    border: 2px solid #4285f4;
                    border-radius: 4px;
                    background: transparent;
                }
                QPushButton:hover {
                    background: rgba(66, 133, 244, 0.1);
                }
            """)
            self.google_btn.setToolTip(tr("Google authorized") + " ✓")
        else:
            # Grayed out
            self.google_btn.setStyleSheet("""
                QPushButton {
                    font-weight: bold;
                    color: #666;
                    border: 2px solid #444;
                    border-radius: 4px;
                    background: transparent;
                }
                QPushButton:hover {
                    background: rgba(100, 100, 100, 0.1);
                }
            """)
            self.google_btn.setToolTip(tr("Google not authorized"))
    
    def _get_profile_info_text(self) -> str:
        """Get profile info string for alerts: flag + code + UUID"""
        flag = COUNTRY_FLAGS.get(self.country_code, "🌐") if self.country_code else "🌐"
        code_str = f" ({self.country_code})" if self.country_code else ""
        return f"{flag}{code_str} {self.uuid[:8]}..."
    
    def _on_google_click(self):
        """Handle Google button click - activate or deactivate."""
        profile_info = self._get_profile_info_text()
        
        if self.google_authorized:
            # Already active - ask to deactivate
            reply = QMessageBox.question(
                self,
                tr("Deactivate Google Authorization"),
                tr("Deactivate Google authorization for this profile?") + f"\n\n{profile_info}",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                self.google_authorized = False
                self._update_google_btn_style()
                self.google_auth_changed.emit(self.uuid, False)
        else:
            # Not active - ask to activate
            reply = QMessageBox.question(
                self,
                tr("Google Authorization"),
                tr("Did you authorize Google in this profile?") + f"\n\n{profile_info}",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                self.google_authorized = True
                self._update_google_btn_style()
                self.google_auth_changed.emit(self.uuid, True)
            else:
                QMessageBox.information(
                    self,
                    tr("Authorization Required"),
                    tr("Please authorize Google account in this profile first.") + f"\n\n{profile_info}"
                )
    
    # === Google Mode Buttons ===
    def _format_time_ago(self, timestamp_str: str) -> str:
        """Format timestamp as 'Xд Yч назад' string."""
        if not timestamp_str:
            return ""
        try:
            ts = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
            now = datetime.now(ts.tzinfo) if ts.tzinfo else datetime.now()
            diff = now - ts
            
            total_hours = int(diff.total_seconds() / 3600)
            days = total_hours // 24
            hours = total_hours % 24
            
            if days > 0:
                return f" {days}д {hours}ч назад"
            elif hours > 0:
                return f" {hours}ч назад"
            else:
                minutes = int(diff.total_seconds() / 60)
                return f" {minutes}м назад" if minutes > 0 else " только что"
        except:
            return ""
    
    def _update_ads_btn_style(self):
        """Update Google Ads button style based on registration state."""
        if self.ads_registered:
            self.ads_btn.setStyleSheet("""
                QPushButton {
                    font-weight: bold;
                    font-size: 10px;
                    color: #fbbc04;
                    border: 2px solid #fbbc04;
                    border-radius: 4px;
                    background: transparent;
                }
                QPushButton:hover { background: rgba(251, 188, 4, 0.1); }
            """)
            time_ago = self._format_time_ago(self.ads_timestamp)
            self.ads_btn.setToolTip(tr("Google Ads registered") + f" ✓{time_ago}")
        else:
            self.ads_btn.setStyleSheet("""
                QPushButton {
                    font-weight: bold;
                    font-size: 10px;
                    color: #666;
                    border: 2px solid #444;
                    border-radius: 4px;
                    background: transparent;
                }
                QPushButton:hover { background: rgba(100, 100, 100, 0.1); }
            """)
            self.ads_btn.setToolTip(tr("Google Ads not registered"))
    
    def _update_payment_btn_style(self):
        """Update payment button style based on link state."""
        if self.payment_linked:
            self.payment_btn.setStyleSheet("""
                QPushButton {
                    font-size: 14px;
                    color: #34a853;
                    border: 2px solid #34a853;
                    border-radius: 4px;
                    background: transparent;
                }
                QPushButton:hover { background: rgba(52, 168, 83, 0.1); }
            """)
            time_ago = self._format_time_ago(self.payment_timestamp)
            self.payment_btn.setToolTip(tr("Payment method linked") + f" ✓{time_ago}")
        else:
            self.payment_btn.setStyleSheet("""
                QPushButton {
                    font-size: 14px;
                    color: #666;
                    border: 2px solid #444;
                    border-radius: 4px;
                    background: transparent;
                }
                QPushButton:hover { background: rgba(100, 100, 100, 0.1); }
            """)
            self.payment_btn.setToolTip(tr("Payment method not linked"))
    
    def _update_campaign_btn_style(self):
        """Update campaign button style based on launch state."""
        if self.campaign_launched:
            self.campaign_btn.setStyleSheet("""
                QPushButton {
                    font-weight: bold;
                    font-size: 10px;
                    color: #ea4335;
                    border: 2px solid #ea4335;
                    border-radius: 4px;
                    background: transparent;
                }
                QPushButton:hover { background: rgba(234, 67, 53, 0.1); }
            """)
            time_ago = self._format_time_ago(self.campaign_timestamp)
            self.campaign_btn.setToolTip(tr("Ad campaign launched") + f" ✓{time_ago}")
        else:
            self.campaign_btn.setStyleSheet("""
                QPushButton {
                    font-weight: bold;
                    font-size: 10px;
                    color: #666;
                    border: 2px solid #444;
                    border-radius: 4px;
                    background: transparent;
                }
                QPushButton:hover { background: rgba(100, 100, 100, 0.1); }
            """)
            self.campaign_btn.setToolTip(tr("Ad campaign not launched"))
    
    def _update_ready_btn_style(self):
        """Update ready button style based on profile ready state."""
        if self.profile_ready:
            self.ready_btn.setStyleSheet("""
                QPushButton {
                    font-weight: bold;
                    font-size: 14px;
                    color: #00c853;
                    border: 2px solid #00c853;
                    border-radius: 4px;
                    background: transparent;
                }
                QPushButton:hover { background: rgba(0, 200, 83, 0.1); }
            """)
            time_ago = self._format_time_ago(self.ready_timestamp)
            self.ready_btn.setToolTip(tr("Profile warmed up and ready") + f" ✓{time_ago}")
        else:
            self.ready_btn.setStyleSheet("""
                QPushButton {
                    font-weight: bold;
                    font-size: 14px;
                    color: #666;
                    border: 2px solid #444;
                    border-radius: 4px;
                    background: transparent;
                }
                QPushButton:hover { background: rgba(100, 100, 100, 0.1); }
            """)
            self.ready_btn.setToolTip(tr("Profile not ready"))
    
    def _on_ads_click(self):
        """Handle Google Ads button click - activate or deactivate."""
        profile_info = self._get_profile_info_text()
        
        if self.ads_registered:
            # Already active - ask to deactivate
            reply = QMessageBox.question(
                self,
                tr("Deactivate Google Ads"),
                tr("Deactivate Google Ads registration for this profile?") + f"\n\n{profile_info}",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                self.ads_registered = False
                self._update_ads_btn_style()
                self.ads_changed.emit(self.uuid, False)
        else:
            # Not active - ask to activate
            reply = QMessageBox.question(
                self,
                tr("Google Ads"),
                tr("Did you register Google Ads account?") + f"\n\n{profile_info}",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                self.ads_registered = True
                self._update_ads_btn_style()
                self.ads_changed.emit(self.uuid, True)
            else:
                QMessageBox.information(
                    self,
                    tr("Registration Required"),
                    tr("Please register Google Ads account first.") + f"\n\n{profile_info}"
                )
    
    def _on_payment_click(self):
        """Handle payment button click - activate or deactivate."""
        profile_info = self._get_profile_info_text()
        
        if self.payment_linked:
            # Already active - ask to deactivate
            reply = QMessageBox.question(
                self,
                tr("Deactivate Payment Method"),
                tr("Deactivate payment method for this profile?") + f"\n\n{profile_info}",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                self.payment_linked = False
                self._update_payment_btn_style()
                self.payment_changed.emit(self.uuid, False)
        else:
            # Not active - ask to activate
            reply = QMessageBox.question(
                self,
                tr("Payment Method"),
                tr("Did you link payment method in Google Ads?") + f"\n\n{profile_info}",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                self.payment_linked = True
                self._update_payment_btn_style()
                self.payment_changed.emit(self.uuid, True)
            else:
                QMessageBox.information(
                    self,
                    tr("Payment Required"),
                    tr("Please link payment method in Google Ads first!") + f"\n\n{profile_info}"
                )
    
    def _on_campaign_click(self):
        """Handle campaign button click - activate or deactivate."""
        profile_info = self._get_profile_info_text()
        
        if self.campaign_launched:
            # Already active - ask to deactivate
            reply = QMessageBox.question(
                self,
                tr("Deactivate Ad Campaign"),
                tr("Deactivate ad campaign for this profile?") + f"\n\n{profile_info}",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                self.campaign_launched = False
                self._update_campaign_btn_style()
                self.campaign_changed.emit(self.uuid, False)
        else:
            # Not active - ask to activate
            reply = QMessageBox.question(
                self,
                tr("Ad Campaign"),
                tr("Did you launch an ad campaign in Google Ads?") + f"\n\n{profile_info}",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                self.campaign_launched = True
                self._update_campaign_btn_style()
                self.campaign_changed.emit(self.uuid, True)
            else:
                QMessageBox.information(
                    self,
                    tr("Campaign Required"),
                    tr("Please launch an ad campaign in Google Ads first!") + f"\n\n{profile_info}"
                )
    
    def _on_ready_click(self):
        """Handle ready button click - activate or deactivate."""
        profile_info = self._get_profile_info_text()
        
        if self.profile_ready:
            # Already active - ask to deactivate
            reply = QMessageBox.question(
                self,
                tr("Deactivate Ready Status"),
                tr("Deactivate 'ready' status for this profile?") + f"\n\n{profile_info}",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                self.profile_ready = False
                self._update_ready_btn_style()
                self.ready_changed.emit(self.uuid, False)
        else:
            # Not active - ask to activate
            reply = QMessageBox.question(
                self,
                tr("Profile Ready"),
                tr("Is the profile warmed up and ready for work?") + f"\n\n{profile_info}",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                self.profile_ready = True
                self._update_ready_btn_style()
                self.ready_changed.emit(self.uuid, True)
    
    def _get_age_days(self) -> int:
        """Get profile age in days."""
        if not self.first_run:
            return -1  # Unknown age
        try:
            first_date = datetime.fromisoformat(self.first_run.replace("Z", "+00:00"))
            now = datetime.now(first_date.tzinfo) if first_date.tzinfo else datetime.now()
            return (now - first_date).days
        except:
            return -1
    
    def _calculate_age(self) -> str:
        """Calculate profile age in days from first run date."""
        if self.age_days < 0:
            return ""
        return f"{self.age_days}d"
    
    def _on_copy(self):
        QApplication.clipboard().setText(self.uuid)
        self.copy_clicked.emit(self.uuid)
    
    def _on_migrate(self):
        self.migrate_clicked.emit(self.uuid, self.age_days, self.google_authorized)
    
    def _on_check_changed(self, state):
        self.check_changed.emit(self.uuid, state == Qt.Checked)
    
    def setChecked(self, checked: bool):
        self.checkbox.setChecked(checked)
    
    def isChecked(self) -> bool:
        return self.checkbox.isChecked()


class WorkerThread(QThread):
    log_signal = pyqtSignal(str)
    finished_signal = pyqtSignal(str)
    error_signal = pyqtSignal(str, str)
    country_detected = pyqtSignal(str, str)  # uuid, country_code
    
    def __init__(self, profile_uuid, sites, settings, octo_api, mode="cookie", start_minimized=True):
        super().__init__()
        self.profile_uuid = profile_uuid
        self.sites = sites
        self.settings = settings
        self.octo_api = octo_api
        self.mode = mode
        self.start_minimized = start_minimized
        self.should_stop = False
        self.automation = None
    
    def run(self):
        asyncio.run(self._run_async())
    
    async def _run_async(self):
        try:
            self.log_signal.emit(f"[{self.profile_uuid[:8]}] Starting ({self.mode})...")
            connection = self.octo_api.start_profile(self.profile_uuid, minimized=self.start_minimized)
            
            if not connection:
                self.log_signal.emit(f"[{self.profile_uuid[:8]}] Failed to start")
                self.error_signal.emit(self.profile_uuid, "Failed to start profile")
                return
            
            if "error" in connection:
                self.log_signal.emit(f"[{self.profile_uuid[:8]}] Error: {connection.get('error')}")
                self.error_signal.emit(self.profile_uuid, connection.get("error"))
                return
            
            proxy_info = connection.get("proxy_info", "")
            
            # Extract and emit country from connection_data
            connection_data = connection.get("connection_data", {})
            country = connection_data.get("country", "")
            if country:
                self.country_detected.emit(self.profile_uuid, country)
            
            if connection.get("proxy_status") == "error" or not connection.get("ws_endpoint"):
                self.log_signal.emit(f"[{self.profile_uuid[:8]}] PROXY ERROR")
                self.octo_api.stop_profile(self.profile_uuid)
                return
            
            self.log_signal.emit(f"[{self.profile_uuid[:8]}] Proxy: {proxy_info}")
            
            ws_endpoint = connection.get("ws_endpoint")
            debug_port = connection.get("debug_port")
            
            if ws_endpoint or debug_port:
                self.automation = BrowserAutomation(
                    log_callback=lambda x: self.log_signal.emit(f"[{self.profile_uuid[:8]}] {x}")
                )
                
                try:
                    connected = await self.automation.connect_to_octo(ws_endpoint=ws_endpoint, debug_port=debug_port)
                except Exception as e:
                    self.log_signal.emit(f"[{self.profile_uuid[:8]}] Connection failed: {e}")
                    self.octo_api.stop_profile(self.profile_uuid)
                    return
                
                if connected:
                    # Try to minimize browser window if setting enabled
                    if self.start_minimized:
                        await self._try_minimize_browser()
                    
                    self.automation.should_stop = self.should_stop
                    try:
                        if self.mode == "cookie":
                            await self.automation.run_session(
                                sites=self.sites.copy(),
                                settings=self.settings
                            )
                        elif self.mode == "google":
                            await self.automation.run_google_warmup(
                                sites=self.sites.copy(),
                                settings=self.settings
                            )
                    except Exception as e:
                        self.log_signal.emit(f"[{self.profile_uuid[:8]}] Error: {e}")
                    await self.automation.disconnect()
            
            self.octo_api.stop_profile(self.profile_uuid)
            self.log_signal.emit(f"[{self.profile_uuid[:8]}] Done")
            
        except Exception as e:
            self.log_signal.emit(f"[{self.profile_uuid[:8]}] Error: {e}")
        finally:
            self.finished_signal.emit(self.profile_uuid)
    
    async def _try_minimize_browser(self):
        """Try to minimize browser window using CDP or pywin32."""
        try:
            if self.automation and self.automation.page:
                # Method 1: Use CDP to minimize window
                cdp = await self.automation.page.context.new_cdp_session(self.automation.page)
                try:
                    # Get window bounds
                    window_id = await cdp.send("Browser.getWindowForTarget")
                    if window_id:
                        # Set window state to minimized
                        await cdp.send("Browser.setWindowBounds", {
                            "windowId": window_id.get("windowId"),
                            "bounds": {"windowState": "minimized"}
                        })
                        self.log_signal.emit(f"[{self.profile_uuid[:8]}] Window minimized via CDP")
                        return
                except Exception as e:
                    pass  # CDP method failed, try alternatives
                
                # Method 2: Use pywin32 on Windows
                try:
                    import win32gui
                    import win32con
                    
                    def minimize_by_title(title_part):
                        def callback(hwnd, results):
                            if win32gui.IsWindowVisible(hwnd):
                                window_title = win32gui.GetWindowText(hwnd)
                                if title_part.lower() in window_title.lower():
                                    win32gui.ShowWindow(hwnd, win32con.SW_MINIMIZE)
                                    return False  # Stop enumeration
                            return True
                        win32gui.EnumWindows(callback, None)
                    
                    # Try to find Octo Browser window by profile UUID
                    minimize_by_title(self.profile_uuid[:8])
                    self.log_signal.emit(f"[{self.profile_uuid[:8]}] Window minimized via pywin32")
                except ImportError:
                    pass  # pywin32 not available
                    
        except Exception as e:
            self.log_signal.emit(f"[{self.profile_uuid[:8]}] Minimize failed: {e}")
    
    def stop(self):
        self.should_stop = True
        if self.automation:
            self.automation.should_stop = True


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.config = self.load_config()
        self.octo_api = None
        self.workers = {}
        self.current_mode = "cookie"
        self.pending_queue = []  # Queue of profiles waiting to start
        self.running_count = 0   # Number of currently running profiles
        
        # Load language from config
        self.current_language = self.config.get("language", "English")
        self.current_theme = self.config.get("theme", "Dark")
        
        # Load translation before building UI
        app_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        load_translation(self.current_language, app_dir)
        
        self.init_ui()
        self.apply_theme(self.current_theme)
        
    def init_ui(self):
        self.setWindowTitle("TT Cookie Robot")
        self.setMinimumSize(800, 600)
        
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setSpacing(8)
        main_layout.setContentsMargins(10, 10, 10, 10)
        
        # === TOP BAR: Connection + Mode ===
        top_bar = QHBoxLayout()
        top_bar.setSpacing(10)
        
        # Connection
        top_bar.addWidget(QLabel("API:"))
        self.api_url_input = QLineEdit()
        self.api_url_input.setText(self.config.get("api_url", "http://localhost:58888"))
        self.api_url_input.setFixedWidth(180)
        top_bar.addWidget(self.api_url_input)
        
        self.connect_btn = QPushButton(tr("Connect"))
        self.connect_btn.setMinimumWidth(80)
        self.connect_btn.clicked.connect(self.connect_to_octo)
        top_bar.addWidget(self.connect_btn)
        
        self.connection_status = QLabel("●")
        self.connection_status.setStyleSheet("color: #f38ba8; font-size: 16px;")
        self.connection_status.setFixedWidth(20)
        top_bar.addWidget(self.connection_status)
        
        top_bar.addStretch()
        
        # Mode buttons
        self.mode_label = QLabel(tr("Mode:"))
        top_bar.addWidget(self.mode_label)
        
        self.cookie_mode_btn = QPushButton("🍪 Cookie")
        self.cookie_mode_btn.setCheckable(True)
        self.cookie_mode_btn.setChecked(True)
        self.cookie_mode_btn.setMinimumWidth(100)
        self.cookie_mode_btn.clicked.connect(lambda: self.switch_mode("cookie"))
        top_bar.addWidget(self.cookie_mode_btn)
        
        self.google_mode_btn = QPushButton("📧 Google")
        self.google_mode_btn.setCheckable(True)
        self.google_mode_btn.setMinimumWidth(100)
        self.google_mode_btn.clicked.connect(lambda: self.switch_mode("google"))
        top_bar.addWidget(self.google_mode_btn)
        
        # Global settings button
        self.global_settings_btn = QPushButton("⚙️")
        self.global_settings_btn.setFixedWidth(40)
        self.global_settings_btn.setToolTip(tr("Global Settings"))
        self.global_settings_btn.clicked.connect(self.show_global_settings)
        top_bar.addWidget(self.global_settings_btn)
        
        main_layout.addLayout(top_bar)
        
        # === MAIN CONTENT: Stacked modes ===
        self.mode_stack = QStackedWidget()
        self.mode_stack.addWidget(self.create_cookie_mode())
        self.mode_stack.addWidget(self.create_google_mode())
        main_layout.addWidget(self.mode_stack, 1)
        
        # === CONTROL BUTTONS ===
        control_layout = QHBoxLayout()
        
        self.start_btn = QPushButton("▶ " + tr("START"))
        self.start_btn.setMinimumHeight(40)
        self.start_btn.setEnabled(False)
        self.start_btn.clicked.connect(self.start_automation)
        self.start_btn.setStyleSheet("""
            QPushButton { background-color: #a6e3a1; color: #1e1e2e; font-weight: bold; font-size: 14px; }
            QPushButton:hover { background-color: #94d990; }
            QPushButton:disabled { background-color: #4a5a48; color: #6c7086; }
        """)
        control_layout.addWidget(self.start_btn)
        
        self.stop_btn = QPushButton("⏹ " + tr("STOP"))
        self.stop_btn.setMinimumHeight(40)
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self.stop_automation)
        self.stop_btn.setStyleSheet("""
            QPushButton { background-color: #f38ba8; color: #1e1e2e; font-weight: bold; font-size: 14px; }
            QPushButton:hover { background-color: #e879a0; }
            QPushButton:disabled { background-color: #5a4a50; color: #6c7086; }
        """)
        control_layout.addWidget(self.stop_btn)
        
        main_layout.addLayout(control_layout)
        
        # === STATUS ===
        self.status_label = QLabel(tr("Ready"))
        self.status_label.setStyleSheet("color: #6c7086;")
        main_layout.addWidget(self.status_label)
        
        # === LOGS ===
        self.log_area = QTextEdit()
        self.log_area.setReadOnly(True)
        self.log_area.setMaximumHeight(120)
        self.log_area.setFont(QFont("Consolas", 9))
        main_layout.addWidget(self.log_area)
    
    def create_cookie_mode(self):
        """Cookie Mode with tabs: Profiles | Sites | Settings"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        
        tabs = QTabWidget()
        tabs.addTab(self.create_cookie_profiles_tab(), tr("Profiles"))
        tabs.addTab(self.create_cookie_sites_tab(), tr("Sites"))
        tabs.addTab(self.create_cookie_settings_tab(), tr("Settings"))
        layout.addWidget(tabs)
        
        return widget
    
    def create_cookie_profiles_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Search profiles
        search_layout = QHBoxLayout()
        search_label = QLabel("🔍")
        search_layout.addWidget(search_label)
        self.cookie_search_input = QLineEdit()
        self.cookie_search_input.setPlaceholderText(tr("Search by UUID..."))
        self.cookie_search_input.textChanged.connect(lambda text: self.filter_profiles("cookie", text))
        search_layout.addWidget(self.cookie_search_input)
        
        # Sort by status dropdown
        self.cookie_sort_combo = QComboBox()
        self.cookie_sort_combo.addItem(tr("All"), "all")
        self.cookie_sort_combo.addItem(tr("Google Auth") + " ✓", "google_auth")
        self.cookie_sort_combo.addItem(tr("Google Auth") + " ✗", "no_google_auth")
        self.cookie_sort_combo.setMinimumWidth(120)
        self.cookie_sort_combo.currentIndexChanged.connect(lambda: self.filter_profiles_by_status("cookie"))
        search_layout.addWidget(self.cookie_sort_combo)
        
        layout.addLayout(search_layout)
        
        # Add profile
        add_layout = QHBoxLayout()
        self.cookie_profile_input = QLineEdit()
        self.cookie_profile_input.setPlaceholderText("UUID")
        add_layout.addWidget(self.cookie_profile_input)
        
        add_btn = QPushButton(tr("Add"))
        add_btn.setMinimumWidth(60)
        add_btn.clicked.connect(lambda: self.add_profile("cookie"))
        add_layout.addWidget(add_btn)
        layout.addLayout(add_layout)
        
        # List
        self.cookie_profiles_list = QListWidget()
        layout.addWidget(self.cookie_profiles_list)
        
        # Buttons
        btn_layout = QHBoxLayout()
        for text, func in [(tr("Select All"), lambda: self.select_all_profiles("cookie")),
                           (tr("Deselect"), lambda: self.deselect_all_profiles("cookie")),
                           (tr("Remove"), lambda: self.remove_selected_profiles("cookie")),
                           ("🔄", lambda: self.refresh_profiles_info("cookie"))]:
            btn = QPushButton(text)
            btn.clicked.connect(func)
            if text == "🔄":
                btn.setFixedWidth(36)
                btn.setToolTip(tr("Refresh proxy info"))
            btn_layout.addWidget(btn)
        layout.addLayout(btn_layout)
        
        self.load_profiles_list("cookie")
        return widget
    
    def create_cookie_sites_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Add site
        add_layout = QHBoxLayout()
        self.cookie_site_input = QLineEdit()
        self.cookie_site_input.setPlaceholderText("https://example.com")
        add_layout.addWidget(self.cookie_site_input)
        
        add_btn = QPushButton(tr("Add"))
        add_btn.setMinimumWidth(60)
        add_btn.clicked.connect(lambda: self.add_site("cookie"))
        add_layout.addWidget(add_btn)
        
        bulk_add_btn = QPushButton(tr("Bulk Add"))
        bulk_add_btn.setMinimumWidth(80)
        bulk_add_btn.clicked.connect(lambda: self._show_bulk_add_dialog("cookie"))
        add_layout.addWidget(bulk_add_btn)
        
        layout.addLayout(add_layout)
        
        # Geo filter row
        geo_filter_layout = QHBoxLayout()
        geo_filter_layout.addWidget(QLabel("🌍"))
        self.cookie_geo_filter = QComboBox()
        self.cookie_geo_filter.setEditable(True)
        self.cookie_geo_filter.setInsertPolicy(QComboBox.NoInsert)
        self._populate_geo_filter(self.cookie_geo_filter)
        self.cookie_geo_filter.setMinimumWidth(180)
        self.cookie_geo_filter.currentIndexChanged.connect(lambda: self._filter_sites_by_geo("cookie"))
        self.cookie_geo_filter.lineEdit().textChanged.connect(lambda t: self._filter_sites_by_geo_text("cookie", t))
        geo_filter_layout.addWidget(self.cookie_geo_filter)
        geo_filter_layout.addStretch()
        layout.addLayout(geo_filter_layout)
        
        # List
        self.cookie_sites_list = QListWidget()
        layout.addWidget(self.cookie_sites_list)
        
        # Count + buttons
        bottom = QHBoxLayout()
        self.cookie_sites_count = QLabel("0 " + tr("sites"))
        bottom.addWidget(self.cookie_sites_count)
        bottom.addStretch()
        
        for text, func in [(tr("Remove"), lambda: self.remove_site("cookie")),
                           (tr("Clear"), lambda: self.clear_sites("cookie")),
                           (tr("Import"), lambda: self.import_sites("cookie")),
                           (tr("Edit"), lambda: self._show_sites_editor("cookie"))]:
            btn = QPushButton(text)
            btn.clicked.connect(func)
            bottom.addWidget(btn)
        layout.addLayout(bottom)
        
        self.load_sites_list("cookie")
        return widget
    
    def create_cookie_settings_tab(self):
        # Create scroll area for settings
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        
        content = QWidget()
        layout = QFormLayout(content)
        layout.setSpacing(12)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Style for consistent input heights and widths
        input_style = "min-height: 28px; min-width: 90px;"
        
        self.cookie_min_time = QSpinBox()
        self.cookie_min_time.setRange(10, 600)
        self.cookie_min_time.setValue(self.get_mode_config("cookie").get("settings", {}).get("min_time_on_site", 30))
        self.cookie_min_time.setSuffix(" sec")
        self.cookie_min_time.setStyleSheet(input_style)
        layout.addRow(tr("Min time on site:"), self.cookie_min_time)
        
        self.cookie_max_time = QSpinBox()
        self.cookie_max_time.setRange(30, 1800)
        self.cookie_max_time.setValue(self.get_mode_config("cookie").get("settings", {}).get("max_time_on_site", 120))
        self.cookie_max_time.setSuffix(" sec")
        self.cookie_max_time.setStyleSheet(input_style)
        layout.addRow(tr("Max time on site:"), self.cookie_max_time)
        
        # Google Search navigation percentage
        self.cookie_search_percent = QSpinBox()
        self.cookie_search_percent.setRange(0, 100)
        self.cookie_search_percent.setValue(self.get_mode_config("cookie").get("settings", {}).get("google_search_percent", 70))
        self.cookie_search_percent.setSuffix(" %")
        self.cookie_search_percent.setStyleSheet(input_style)
        layout.addRow(tr("Google Search navigation:"), self.cookie_search_percent)
        
        # Sites per session (min-max)
        cookie_sites_layout = QHBoxLayout()
        self.cookie_sites_min = QSpinBox()
        self.cookie_sites_min.setRange(1, 100)
        self.cookie_sites_min.setValue(self.get_mode_config("cookie").get("settings", {}).get("sites_per_session_min", 1))
        self.cookie_sites_min.setStyleSheet(input_style)
        cookie_sites_layout.addWidget(self.cookie_sites_min)
        cookie_sites_layout.addWidget(QLabel("-"))
        self.cookie_sites_max = QSpinBox()
        self.cookie_sites_max.setRange(1, 100)
        self.cookie_sites_max.setValue(self.get_mode_config("cookie").get("settings", {}).get("sites_per_session_max", 100))
        self.cookie_sites_max.setStyleSheet(input_style)
        cookie_sites_layout.addWidget(self.cookie_sites_max)
        cookie_sites_layout.addStretch()
        layout.addRow(tr("Sites per session:"), cookie_sites_layout)
        
        # Separator
        sep1 = QFrame()
        sep1.setFrameShape(QFrame.HLine)
        sep1.setStyleSheet("background-color: #444;")
        layout.addRow(sep1)
        
        self.cookie_scroll = QCheckBox(tr("Enable scrolling"))
        self.cookie_scroll.setChecked(self.get_mode_config("cookie").get("settings", {}).get("scroll_enabled", True))
        layout.addRow(self.cookie_scroll)
        
        # Scroll settings
        self.cookie_scroll_percent = QSpinBox()
        self.cookie_scroll_percent.setRange(0, 100)
        self.cookie_scroll_percent.setValue(self.get_mode_config("cookie").get("settings", {}).get("scroll_percent", 70))
        self.cookie_scroll_percent.setSuffix(" %")
        self.cookie_scroll_percent.setStyleSheet(input_style)
        layout.addRow(tr("Scroll probability:"), self.cookie_scroll_percent)
        
        # Scroll iterations (min-max)
        cookie_scroll_iter_layout = QHBoxLayout()
        self.cookie_scroll_iter_min = QSpinBox()
        self.cookie_scroll_iter_min.setRange(1, 20)
        self.cookie_scroll_iter_min.setValue(self.get_mode_config("cookie").get("settings", {}).get("scroll_iterations_min", 3))
        self.cookie_scroll_iter_min.setStyleSheet(input_style)
        cookie_scroll_iter_layout.addWidget(self.cookie_scroll_iter_min)
        cookie_scroll_iter_layout.addWidget(QLabel("-"))
        self.cookie_scroll_iter_max = QSpinBox()
        self.cookie_scroll_iter_max.setRange(1, 20)
        self.cookie_scroll_iter_max.setValue(self.get_mode_config("cookie").get("settings", {}).get("scroll_iterations_max", 6))
        self.cookie_scroll_iter_max.setStyleSheet(input_style)
        cookie_scroll_iter_layout.addWidget(self.cookie_scroll_iter_max)
        cookie_scroll_iter_layout.addStretch()
        layout.addRow(tr("Scroll iterations:"), cookie_scroll_iter_layout)
        
        # Scroll pixels (min-max)
        cookie_scroll_px_layout = QHBoxLayout()
        self.cookie_scroll_px_min = QSpinBox()
        self.cookie_scroll_px_min.setRange(10, 500)
        self.cookie_scroll_px_min.setValue(self.get_mode_config("cookie").get("settings", {}).get("scroll_pixels_min", 50))
        self.cookie_scroll_px_min.setSuffix(" px")
        self.cookie_scroll_px_min.setStyleSheet(input_style)
        cookie_scroll_px_layout.addWidget(self.cookie_scroll_px_min)
        cookie_scroll_px_layout.addWidget(QLabel("-"))
        self.cookie_scroll_px_max = QSpinBox()
        self.cookie_scroll_px_max.setRange(10, 500)
        self.cookie_scroll_px_max.setValue(self.get_mode_config("cookie").get("settings", {}).get("scroll_pixels_max", 150))
        self.cookie_scroll_px_max.setSuffix(" px")
        self.cookie_scroll_px_max.setStyleSheet(input_style)
        cookie_scroll_px_layout.addWidget(self.cookie_scroll_px_max)
        cookie_scroll_px_layout.addStretch()
        layout.addRow(tr("Scroll pixels:"), cookie_scroll_px_layout)
        
        # Scroll pause (min-max) in seconds
        cookie_scroll_pause_layout = QHBoxLayout()
        self.cookie_scroll_pause_min = QDoubleSpinBox()
        self.cookie_scroll_pause_min.setRange(0.05, 2.0)
        self.cookie_scroll_pause_min.setSingleStep(0.05)
        self.cookie_scroll_pause_min.setValue(self.get_mode_config("cookie").get("settings", {}).get("scroll_pause_min", 0.1))
        self.cookie_scroll_pause_min.setSuffix(" s")
        self.cookie_scroll_pause_min.setStyleSheet(input_style)
        cookie_scroll_pause_layout.addWidget(self.cookie_scroll_pause_min)
        cookie_scroll_pause_layout.addWidget(QLabel("-"))
        self.cookie_scroll_pause_max = QDoubleSpinBox()
        self.cookie_scroll_pause_max.setRange(0.05, 2.0)
        self.cookie_scroll_pause_max.setSingleStep(0.05)
        self.cookie_scroll_pause_max.setValue(self.get_mode_config("cookie").get("settings", {}).get("scroll_pause_max", 0.3))
        self.cookie_scroll_pause_max.setSuffix(" s")
        self.cookie_scroll_pause_max.setStyleSheet(input_style)
        cookie_scroll_pause_layout.addWidget(self.cookie_scroll_pause_max)
        cookie_scroll_pause_layout.addStretch()
        layout.addRow(tr("Scroll pause:"), cookie_scroll_pause_layout)
        
        # Scroll direction (down %)
        self.cookie_scroll_down_percent = QSpinBox()
        self.cookie_scroll_down_percent.setRange(0, 100)
        self.cookie_scroll_down_percent.setValue(self.get_mode_config("cookie").get("settings", {}).get("scroll_down_percent", 66))
        self.cookie_scroll_down_percent.setSuffix(" %")
        self.cookie_scroll_down_percent.setStyleSheet(input_style)
        layout.addRow(tr("Scroll down chance:"), self.cookie_scroll_down_percent)
        
        # Separator
        sep2 = QFrame()
        sep2.setFrameShape(QFrame.HLine)
        sep2.setStyleSheet("background-color: #444;")
        layout.addRow(sep2)
        
        self.cookie_click = QCheckBox(tr("Click random links"))
        self.cookie_click.setChecked(self.get_mode_config("cookie").get("settings", {}).get("click_links_enabled", True))
        layout.addRow(self.cookie_click)
        
        # Click settings
        self.cookie_click_percent = QSpinBox()
        self.cookie_click_percent.setRange(0, 100)
        self.cookie_click_percent.setValue(self.get_mode_config("cookie").get("settings", {}).get("click_percent", 20))
        self.cookie_click_percent.setSuffix(" %")
        self.cookie_click_percent.setStyleSheet(input_style)
        layout.addRow(tr("Click probability:"), self.cookie_click_percent)
        
        self.cookie_max_clicks = QSpinBox()
        self.cookie_max_clicks.setRange(0, 10)
        self.cookie_max_clicks.setValue(self.get_mode_config("cookie").get("settings", {}).get("max_clicks_per_site", 2))
        self.cookie_max_clicks.setStyleSheet(input_style)
        layout.addRow(tr("Max clicks per site:"), self.cookie_max_clicks)
        
        # Separator
        sep3 = QFrame()
        sep3.setFrameShape(QFrame.HLine)
        sep3.setStyleSheet("background-color: #444;")
        layout.addRow(sep3)
        
        self.cookie_human = QCheckBox(tr("Human behavior simulation"))
        self.cookie_human.setChecked(self.get_mode_config("cookie").get("settings", {}).get("human_behavior_enabled", True))
        layout.addRow(self.cookie_human)
        
        save_btn = QPushButton(tr("Save Settings"))
        save_btn.setStyleSheet("min-height: 35px; font-weight: bold;")
        save_btn.clicked.connect(lambda: self.save_mode_settings("cookie"))
        layout.addRow(save_btn)
        
        scroll.setWidget(content)
        return scroll
    
    def create_google_mode(self):
        """Google Mode with tabs: Profiles | Sites | Settings"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        
        tabs = QTabWidget()
        tabs.addTab(self.create_google_profiles_tab(), tr("Profiles"))
        tabs.addTab(self.create_google_sites_tab(), tr("Sites"))
        tabs.addTab(self.create_google_settings_tab(), tr("Settings"))
        layout.addWidget(tabs)
        
        return widget
    
    def create_google_profiles_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        info = QLabel(tr("Add profiles with authorized Google accounts"))
        info.setStyleSheet("color: #6c7086; font-size: 11px;")
        layout.addWidget(info)
        
        # Search profiles
        search_layout = QHBoxLayout()
        search_label = QLabel("🔍")
        search_layout.addWidget(search_label)
        self.google_search_input = QLineEdit()
        self.google_search_input.setPlaceholderText(tr("Search by UUID..."))
        self.google_search_input.textChanged.connect(lambda text: self.filter_profiles("google", text))
        search_layout.addWidget(self.google_search_input)
        
        # Sort by status dropdown for Google mode
        self.google_sort_combo = QComboBox()
        self.google_sort_combo.addItem(tr("All"), "all")
        self.google_sort_combo.addItem("Ads ✓", "ads")
        self.google_sort_combo.addItem("Ads ✗", "no_ads")
        self.google_sort_combo.addItem(tr("Payment") + " ✓", "payment")
        self.google_sort_combo.addItem(tr("Payment") + " ✗", "no_payment")
        self.google_sort_combo.addItem(tr("Ad") + " ✓", "campaign")
        self.google_sort_combo.addItem(tr("Ad") + " ✗", "no_campaign")
        self.google_sort_combo.addItem(tr("Ready") + " ✓", "ready")
        self.google_sort_combo.addItem(tr("Ready") + " ✗", "no_ready")
        self.google_sort_combo.setMinimumWidth(120)
        self.google_sort_combo.currentIndexChanged.connect(lambda: self.filter_profiles_by_status("google"))
        search_layout.addWidget(self.google_sort_combo)
        
        layout.addLayout(search_layout)
        
        add_layout = QHBoxLayout()
        self.google_profile_input = QLineEdit()
        self.google_profile_input.setPlaceholderText(tr("Profile UUID (with Google account)"))
        add_layout.addWidget(self.google_profile_input)
        
        add_btn = QPushButton(tr("Add"))
        add_btn.setMinimumWidth(60)
        add_btn.clicked.connect(lambda: self.add_profile("google"))
        add_layout.addWidget(add_btn)
        layout.addLayout(add_layout)
        
        self.google_profiles_list = QListWidget()
        layout.addWidget(self.google_profiles_list)
        
        btn_layout = QHBoxLayout()
        for text, func in [(tr("Select All"), lambda: self.select_all_profiles("google")),
                           (tr("Deselect"), lambda: self.deselect_all_profiles("google")),
                           (tr("Remove"), lambda: self.remove_selected_profiles("google")),
                           ("🔄", lambda: self.refresh_profiles_info("google"))]:
            btn = QPushButton(text)
            btn.clicked.connect(func)
            if text == "🔄":
                btn.setFixedWidth(36)
                btn.setToolTip(tr("Refresh proxy info"))
            btn_layout.addWidget(btn)
        layout.addLayout(btn_layout)
        
        self.load_profiles_list("google")
        return widget
    
    def create_google_sites_tab(self):
        widget = QWidget()
        main_layout = QVBoxLayout(widget)
        main_layout.setSpacing(10)
        
        # Create scroll area for all sections
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll_widget = QWidget()
        layout = QVBoxLayout(scroll_widget)
        layout.setSpacing(15)
        
        # === SECTION 1: Regular Sites (browse only) ===
        sites_label = QLabel(tr("🌐 Sites (browse only)"))
        sites_label.setStyleSheet("font-weight: bold; font-size: 12px; color: #89b4fa;")
        layout.addWidget(sites_label)
        
        sites_info = QLabel(tr("Sites for browsing without Google authorization"))
        sites_info.setStyleSheet("color: #6c7086; font-size: 10px;")
        layout.addWidget(sites_info)
        
        # Sites input
        sites_add_layout = QHBoxLayout()
        self.google_sites_input = QLineEdit()
        self.google_sites_input.setPlaceholderText("https://example.com")
        sites_add_layout.addWidget(self.google_sites_input)
        sites_add_btn = QPushButton(tr("Add"))
        sites_add_btn.setMinimumWidth(60)
        sites_add_btn.clicked.connect(lambda: self._add_site_to_list("sites"))
        sites_add_layout.addWidget(sites_add_btn)
        sites_bulk_btn = QPushButton(tr("Bulk Add"))
        sites_bulk_btn.setMinimumWidth(80)
        sites_bulk_btn.clicked.connect(lambda: self._show_bulk_add_dialog("google_sites"))
        sites_add_layout.addWidget(sites_bulk_btn)
        layout.addLayout(sites_add_layout)
        
        # Geo filter for sites
        sites_geo_layout = QHBoxLayout()
        sites_geo_layout.addWidget(QLabel("🌍"))
        self.google_sites_geo_filter = QComboBox()
        self.google_sites_geo_filter.setEditable(True)
        self.google_sites_geo_filter.setInsertPolicy(QComboBox.NoInsert)
        self._populate_geo_filter(self.google_sites_geo_filter)
        self.google_sites_geo_filter.setMinimumWidth(180)
        self.google_sites_geo_filter.currentIndexChanged.connect(lambda: self._filter_sites_by_geo("google_sites"))
        self.google_sites_geo_filter.lineEdit().textChanged.connect(lambda t: self._filter_sites_by_geo_text("google_sites", t))
        sites_geo_layout.addWidget(self.google_sites_geo_filter)
        sites_geo_layout.addStretch()
        layout.addLayout(sites_geo_layout)
        
        self.google_sites_list = QListWidget()
        self.google_sites_list.setMaximumHeight(120)
        layout.addWidget(self.google_sites_list)
        
        sites_bottom = QHBoxLayout()
        self.google_sites_count = QLabel("0 " + tr("sites"))
        sites_bottom.addWidget(self.google_sites_count)
        sites_bottom.addStretch()
        for text, func in [(tr("Remove"), lambda: self._remove_site_from_list("sites")),
                           (tr("Clear"), lambda: self._clear_site_list("sites")),
                           (tr("Import"), lambda: self._import_sites_to_list("sites")),
                           (tr("Edit"), lambda: self._show_sites_editor("google_sites"))]:
            btn = QPushButton(text)
            btn.setMinimumWidth(60)
            btn.clicked.connect(func)
            sites_bottom.addWidget(btn)
        layout.addLayout(sites_bottom)
        
        # === SECTION 2: One Tap Sites (with Google auth) ===
        onetap_label = QLabel(tr("🔐 Sites with Google One Tap"))
        onetap_label.setStyleSheet("font-weight: bold; font-size: 12px; color: #89b4fa; margin-top: 10px;")
        layout.addWidget(onetap_label)
        
        onetap_info = QLabel(tr("Sites where bot will authorize via Google One Tap"))
        onetap_info.setStyleSheet("color: #6c7086; font-size: 10px;")
        layout.addWidget(onetap_info)
        
        onetap_add_layout = QHBoxLayout()
        self.google_onetap_input = QLineEdit()
        self.google_onetap_input.setPlaceholderText("https://site-with-google-login.com")
        onetap_add_layout.addWidget(self.google_onetap_input)
        onetap_add_btn = QPushButton(tr("Add"))
        onetap_add_btn.setMinimumWidth(60)
        onetap_add_btn.clicked.connect(lambda: self._add_site_to_list("onetap"))
        onetap_add_layout.addWidget(onetap_add_btn)
        onetap_bulk_btn = QPushButton(tr("Bulk Add"))
        onetap_bulk_btn.setMinimumWidth(80)
        onetap_bulk_btn.clicked.connect(lambda: self._show_bulk_add_dialog("google_onetap"))
        onetap_add_layout.addWidget(onetap_bulk_btn)
        layout.addLayout(onetap_add_layout)
        
        # Geo filter for One Tap sites
        onetap_geo_layout = QHBoxLayout()
        onetap_geo_layout.addWidget(QLabel("🌍"))
        self.google_onetap_geo_filter = QComboBox()
        self.google_onetap_geo_filter.setEditable(True)
        self.google_onetap_geo_filter.setInsertPolicy(QComboBox.NoInsert)
        self._populate_geo_filter(self.google_onetap_geo_filter)
        self.google_onetap_geo_filter.setMinimumWidth(180)
        self.google_onetap_geo_filter.currentIndexChanged.connect(lambda: self._filter_sites_by_geo("google_onetap"))
        self.google_onetap_geo_filter.lineEdit().textChanged.connect(lambda t: self._filter_sites_by_geo_text("google_onetap", t))
        onetap_geo_layout.addWidget(self.google_onetap_geo_filter)
        onetap_geo_layout.addStretch()
        layout.addLayout(onetap_geo_layout)
        
        self.google_onetap_list = QListWidget()
        self.google_onetap_list.setMaximumHeight(120)
        layout.addWidget(self.google_onetap_list)
        
        onetap_bottom = QHBoxLayout()
        self.google_onetap_count = QLabel("0 " + tr("sites"))
        onetap_bottom.addWidget(self.google_onetap_count)
        onetap_bottom.addStretch()
        for text, func in [(tr("Remove"), lambda: self._remove_site_from_list("onetap")),
                           (tr("Clear"), lambda: self._clear_site_list("onetap")),
                           (tr("Import"), lambda: self._import_sites_to_list("onetap")),
                           (tr("Edit"), lambda: self._show_sites_editor("google_onetap"))]:
            btn = QPushButton(text)
            btn.setMinimumWidth(60)
            btn.clicked.connect(func)
            onetap_bottom.addWidget(btn)
        layout.addLayout(onetap_bottom)
        
        # === YouTube ===
        youtube_section_label = QLabel(tr("📺 YouTube"))
        youtube_section_label.setStyleSheet("font-weight: bold; font-size: 12px; color: #89b4fa; margin-top: 10px;")
        layout.addWidget(youtube_section_label)
        
        self.google_youtube_checkbox = QCheckBox(tr("Add YouTube to session"))
        self.google_youtube_checkbox.setChecked(self.get_mode_config("google").get("youtube_enabled", True))
        self.google_youtube_checkbox.stateChanged.connect(self._on_youtube_checkbox_changed)
        layout.addWidget(self.google_youtube_checkbox)
        
        # === SECTION 3: Google Services ===
        services_label = QLabel(tr("📊 Google Services"))
        services_label.setStyleSheet("font-weight: bold; font-size: 12px; color: #89b4fa; margin-top: 10px;")
        layout.addWidget(services_label)
        
        services_info = QLabel(tr("Google services to visit during session"))
        services_info.setStyleSheet("color: #6c7086; font-size: 10px;")
        layout.addWidget(services_info)
        
        # Google services checkboxes (names kept as-is - brand names)
        services_grid = QHBoxLayout()
        
        self.google_service_drive = QCheckBox("Google Drive")
        self.google_service_drive.setChecked(self.get_mode_config("google").get("services", {}).get("drive", False))
        services_grid.addWidget(self.google_service_drive)
        
        self.google_service_sheets = QCheckBox("Google Sheets")
        self.google_service_sheets.setChecked(self.get_mode_config("google").get("services", {}).get("sheets", False))
        services_grid.addWidget(self.google_service_sheets)
        
        self.google_service_docs = QCheckBox("Google Docs")
        self.google_service_docs.setChecked(self.get_mode_config("google").get("services", {}).get("docs", False))
        services_grid.addWidget(self.google_service_docs)
        
        layout.addLayout(services_grid)
        
        services_grid2 = QHBoxLayout()
        
        self.google_service_calendar = QCheckBox("Google Calendar")
        self.google_service_calendar.setChecked(self.get_mode_config("google").get("services", {}).get("calendar", False))
        services_grid2.addWidget(self.google_service_calendar)
        
        self.google_service_photos = QCheckBox("Google Photos")
        self.google_service_photos.setChecked(self.get_mode_config("google").get("services", {}).get("photos", False))
        services_grid2.addWidget(self.google_service_photos)
        
        self.google_service_maps = QCheckBox("Google Maps")
        self.google_service_maps.setChecked(self.get_mode_config("google").get("services", {}).get("maps", False))
        services_grid2.addWidget(self.google_service_maps)
        
        layout.addLayout(services_grid2)
        
        # Save button for sites
        layout.addStretch()
        save_sites_btn = QPushButton(tr("Save Sites Configuration"))
        save_sites_btn.clicked.connect(self._save_google_sites_config)
        layout.addWidget(save_sites_btn)
        
        scroll_widget.setLayout(layout)
        scroll.setWidget(scroll_widget)
        main_layout.addWidget(scroll)
        
        # Load existing data
        self._load_google_sites_lists()
        
        return widget
    
    def _on_youtube_checkbox_changed(self, state):
        """Handle YouTube checkbox state change"""
        cfg = self.get_mode_config("google")
        cfg["youtube_enabled"] = (state == Qt.Checked)
        self.set_mode_config("google", cfg)
    
    def _get_google_list_widget(self, list_type):
        """Get list widget by type"""
        if list_type == "sites":
            return self.google_sites_list
        elif list_type == "onetap":
            return self.google_onetap_list
        return None
    
    def _get_google_input_widget(self, list_type):
        """Get input widget by type"""
        if list_type == "sites":
            return self.google_sites_input
        elif list_type == "onetap":
            return self.google_onetap_input
        return None
    
    def _get_google_count_widget(self, list_type):
        """Get count label by type"""
        if list_type == "sites":
            return self.google_sites_count
        elif list_type == "onetap":
            return self.google_onetap_count
        return None
    
    def _get_google_config_key(self, list_type):
        """Get config key for list type"""
        if list_type == "sites":
            return "browse_sites"
        elif list_type == "onetap":
            return "onetap_sites"
        return None
    
    def _add_site_to_list(self, list_type):
        """Add site to specified list"""
        inp = self._get_google_input_widget(list_type)
        lst = self._get_google_list_widget(list_type)
        count_lbl = self._get_google_count_widget(list_type)
        config_key = self._get_google_config_key(list_type)
        
        url = inp.text().strip()
        if url:
            if not url.startswith(("http://", "https://")):
                url = "https://" + url
            cfg = self.get_mode_config("google")
            if url not in cfg.get(config_key, []):
                cfg.setdefault(config_key, []).append(url)
                self.set_mode_config("google", cfg)
                lst.addItem(url)
                count_lbl.setText(f"{len(cfg[config_key])} sites")
                self.log(f"[google/{list_type}] Added: {url}")
            inp.clear()
    
    def _remove_site_from_list(self, list_type):
        """Remove selected site from list"""
        lst = self._get_google_list_widget(list_type)
        count_lbl = self._get_google_count_widget(list_type)
        config_key = self._get_google_config_key(list_type)
        
        cur = lst.currentItem()
        if cur:
            cfg = self.get_mode_config("google")
            cfg[config_key].remove(cur.text())
            self.set_mode_config("google", cfg)
            lst.takeItem(lst.row(cur))
            count_lbl.setText(f"{len(cfg.get(config_key, []))} sites")
    
    def _clear_site_list(self, list_type):
        """Clear all sites from list"""
        lst = self._get_google_list_widget(list_type)
        count_lbl = self._get_google_count_widget(list_type)
        config_key = self._get_google_config_key(list_type)
        
        if QMessageBox.question(self, "Confirm", f"Clear all {list_type} sites?") == QMessageBox.Yes:
            cfg = self.get_mode_config("google")
            cfg[config_key] = []
            self.set_mode_config("google", cfg)
            lst.clear()
            count_lbl.setText("0 sites")
    
    def _import_sites_to_list(self, list_type):
        """Import sites from file to list"""
        lst = self._get_google_list_widget(list_type)
        count_lbl = self._get_google_count_widget(list_type)
        config_key = self._get_google_config_key(list_type)
        
        path, _ = QFileDialog.getOpenFileName(self, "Import", "", "Text (*.txt)")
        if path:
            cfg = self.get_mode_config("google")
            count = 0
            with open(path, "r", encoding="utf-8") as f:
                for line in f:
                    url = line.strip()
                    if url and url not in cfg.get(config_key, []):
                        if not url.startswith(("http://", "https://")):
                            url = "https://" + url
                        cfg.setdefault(config_key, []).append(url)
                        lst.addItem(url)
                        count += 1
            self.set_mode_config("google", cfg)
            count_lbl.setText(f"{len(cfg.get(config_key, []))} sites")
            self.log(f"[google/{list_type}] Imported {count} sites")
    
    def _load_google_sites_lists(self):
        """Load all Google sites lists from config"""
        cfg = self.get_mode_config("google")
        
        # Load browse sites
        self.google_sites_list.clear()
        browse_sites = cfg.get("browse_sites", [])
        for s in browse_sites:
            self.google_sites_list.addItem(s)
        self.google_sites_count.setText(f"{len(browse_sites)} sites")
        
        # Load onetap sites
        self.google_onetap_list.clear()
        onetap_sites = cfg.get("onetap_sites", [])
        for s in onetap_sites:
            self.google_onetap_list.addItem(s)
        self.google_onetap_count.setText(f"{len(onetap_sites)} sites")
        
        # Migrate old "sites" to "onetap_sites" if needed
        if cfg.get("sites") and not cfg.get("onetap_sites"):
            cfg["onetap_sites"] = cfg.get("sites", [])
            self.set_mode_config("google", cfg)
            self._load_google_sites_lists()
    
    def _save_google_sites_config(self):
        """Save Google sites configuration including services"""
        cfg = self.get_mode_config("google")
        
        # Save YouTube enabled state
        cfg["youtube_enabled"] = self.google_youtube_checkbox.isChecked()
        
        # Save Google services (stored separately, NOT added to sites list)
        cfg["services"] = {
            "drive": self.google_service_drive.isChecked(),
            "sheets": self.google_service_sheets.isChecked(),
            "docs": self.google_service_docs.isChecked(),
            "calendar": self.google_service_calendar.isChecked(),
            "photos": self.google_service_photos.isChecked(),
            "maps": self.google_service_maps.isChecked(),
        }
        
        # Sites list contains ONLY user-added sites (browse + onetap)
        # YouTube and Google services are handled separately by automation
        cfg["sites"] = cfg.get("browse_sites", []) + cfg.get("onetap_sites", [])
        
        self.set_mode_config("google", cfg)
        
        self.log("[google] Sites configuration saved")
        QMessageBox.information(self, "OK", "Sites configuration saved!")
    
    def create_google_settings_tab(self):
        widget = QWidget()
        main_layout = QVBoxLayout(widget)
        
        # Scroll area for settings
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll_widget = QWidget()
        layout = QFormLayout(scroll_widget)
        layout.setSpacing(10)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Style for consistent input heights and widths
        input_style = "min-height: 28px; min-width: 90px;"
        
        # === SITES SECTION ===
        sites_label = QLabel(tr("🌐 Sites"))
        sites_label.setStyleSheet("font-weight: bold; font-size: 12px; color: #89b4fa; margin-top: 5px;")
        layout.addRow(sites_label)
        
        self.google_min_time = QSpinBox()
        self.google_min_time.setRange(10, 600)
        self.google_min_time.setValue(self.get_mode_config("google").get("settings", {}).get("min_time_on_site", 30))
        self.google_min_time.setSuffix(" sec")
        self.google_min_time.setStyleSheet(input_style)
        layout.addRow(tr("Min time on site:"), self.google_min_time)
        
        self.google_max_time = QSpinBox()
        self.google_max_time.setRange(10, 1800)
        self.google_max_time.setValue(self.get_mode_config("google").get("settings", {}).get("max_time_on_site", 60))
        self.google_max_time.setSuffix(" sec")
        self.google_max_time.setStyleSheet(input_style)
        layout.addRow(tr("Max time on site:"), self.google_max_time)
        
        self.google_auth_sites = QCheckBox(tr("Authorize on sites via Google"))
        self.google_auth_sites.setChecked(self.get_mode_config("google").get("settings", {}).get("auth_on_sites", True))
        layout.addRow(self.google_auth_sites)
        
        # Google Search percentage
        self.google_search_percent = QSpinBox()
        self.google_search_percent.setRange(0, 100)
        self.google_search_percent.setValue(self.get_mode_config("google").get("settings", {}).get("google_search_percent", 70))
        self.google_search_percent.setSuffix(" %")
        self.google_search_percent.setStyleSheet(input_style)
        layout.addRow(tr("Google Search navigation:"), self.google_search_percent)
        
        # Sites per session (min-max)
        sites_per_session_layout = QHBoxLayout()
        self.sites_per_session_min = QSpinBox()
        self.sites_per_session_min.setRange(1, 100)
        self.sites_per_session_min.setValue(self.get_mode_config("google").get("settings", {}).get("sites_per_session_min", 1))
        self.sites_per_session_min.setStyleSheet(input_style)
        sites_per_session_layout.addWidget(self.sites_per_session_min)
        sites_per_session_layout.addWidget(QLabel("-"))
        self.sites_per_session_max = QSpinBox()
        self.sites_per_session_max.setRange(1, 100)
        self.sites_per_session_max.setValue(self.get_mode_config("google").get("settings", {}).get("sites_per_session_max", 100))
        self.sites_per_session_max.setStyleSheet(input_style)
        sites_per_session_layout.addWidget(self.sites_per_session_max)
        sites_per_session_layout.addStretch()
        layout.addRow(tr("Sites per session:"), sites_per_session_layout)
        
        # === GMAIL SECTION ===
        gmail_label = QLabel(tr("📧 Gmail"))
        gmail_label.setStyleSheet("font-weight: bold; font-size: 12px; color: #89b4fa; margin-top: 10px;")
        layout.addRow(gmail_label)
        
        self.google_read_gmail = QCheckBox(tr("Read Gmail"))
        self.google_read_gmail.setChecked(self.get_mode_config("google").get("settings", {}).get("read_gmail", True))
        layout.addRow(self.google_read_gmail)
        
        self.gmail_read_percent = QSpinBox()
        self.gmail_read_percent.setRange(10, 100)
        self.gmail_read_percent.setValue(self.get_mode_config("google").get("settings", {}).get("gmail_read_percent", 40))
        self.gmail_read_percent.setSuffix(" %")
        self.gmail_read_percent.setStyleSheet(input_style)
        layout.addRow(tr("% of emails to read:"), self.gmail_read_percent)
        
        # Time per email (min-max range)
        gmail_time_layout = QHBoxLayout()
        self.gmail_read_time_min = QSpinBox()
        self.gmail_read_time_min.setRange(5, 120)
        self.gmail_read_time_min.setValue(self.get_mode_config("google").get("settings", {}).get("gmail_read_time_min", 15))
        self.gmail_read_time_min.setSuffix(" sec")
        self.gmail_read_time_min.setStyleSheet(input_style)
        gmail_time_layout.addWidget(self.gmail_read_time_min)
        gmail_time_layout.addWidget(QLabel("-"))
        self.gmail_read_time_max = QSpinBox()
        self.gmail_read_time_max.setRange(5, 300)
        self.gmail_read_time_max.setValue(self.get_mode_config("google").get("settings", {}).get("gmail_read_time_max", 45))
        self.gmail_read_time_max.setSuffix(" sec")
        self.gmail_read_time_max.setStyleSheet(input_style)
        gmail_time_layout.addWidget(self.gmail_read_time_max)
        gmail_time_layout.addStretch()
        layout.addRow(tr("Time per email:"), gmail_time_layout)
        
        # Promotions/Spam check chance
        self.gmail_promo_spam_percent = QSpinBox()
        self.gmail_promo_spam_percent.setRange(0, 100)
        self.gmail_promo_spam_percent.setValue(self.get_mode_config("google").get("settings", {}).get("gmail_promo_spam_percent", 10))
        self.gmail_promo_spam_percent.setSuffix(" %")
        self.gmail_promo_spam_percent.setStyleSheet(input_style)
        layout.addRow(tr("Promotions/Spam chance:"), self.gmail_promo_spam_percent)
        
        # Click links in emails
        self.gmail_click_links = QCheckBox(tr("Click links in emails"))
        self.gmail_click_links.setChecked(self.get_mode_config("google").get("settings", {}).get("gmail_click_links", True))
        layout.addRow(self.gmail_click_links)
        
        # Check Gmail every N sites (min-max range)
        gmail_sites_layout = QHBoxLayout()
        self.gmail_check_sites_min = QSpinBox()
        self.gmail_check_sites_min.setRange(1, 20)
        self.gmail_check_sites_min.setValue(self.get_mode_config("google").get("settings", {}).get("gmail_check_sites_min", 4))
        self.gmail_check_sites_min.setStyleSheet(input_style)
        gmail_sites_layout.addWidget(self.gmail_check_sites_min)
        gmail_sites_layout.addWidget(QLabel("-"))
        self.gmail_check_sites_max = QSpinBox()
        self.gmail_check_sites_max.setRange(1, 30)
        self.gmail_check_sites_max.setValue(self.get_mode_config("google").get("settings", {}).get("gmail_check_sites_max", 6))
        self.gmail_check_sites_max.setStyleSheet(input_style)
        gmail_sites_layout.addWidget(self.gmail_check_sites_max)
        gmail_sites_layout.addStretch()
        layout.addRow(tr("Check mail every N sites:"), gmail_sites_layout)
        
        # Final Gmail check at end of session
        self.gmail_final_check = QCheckBox(tr("Check mail at end of session"))
        self.gmail_final_check.setChecked(self.get_mode_config("google").get("settings", {}).get("gmail_final_check", True))
        layout.addRow(self.gmail_final_check)
        
        # Final check probability
        self.gmail_final_check_percent = QSpinBox()
        self.gmail_final_check_percent.setRange(0, 100)
        self.gmail_final_check_percent.setValue(self.get_mode_config("google").get("settings", {}).get("gmail_final_check_percent", 80))
        self.gmail_final_check_percent.setSuffix(" %")
        self.gmail_final_check_percent.setStyleSheet(input_style)
        layout.addRow(tr("Final check probability:"), self.gmail_final_check_percent)
        
        # === YOUTUBE SECTION ===
        youtube_label = QLabel(tr("📺 YouTube"))
        youtube_label.setStyleSheet("font-weight: bold; font-size: 12px; color: #89b4fa; margin-top: 10px;")
        layout.addRow(youtube_label)
        
        # YouTube activity percentage
        self.youtube_activity_percent = QSpinBox()
        self.youtube_activity_percent.setRange(0, 100)
        self.youtube_activity_percent.setValue(self.get_mode_config("google").get("settings", {}).get("youtube_activity_percent", 100))
        self.youtube_activity_percent.setSuffix(" %")
        self.youtube_activity_percent.setStyleSheet(input_style)
        layout.addRow(tr("Activity chance:"), self.youtube_activity_percent)
        
        # YouTube videos count (min-max)
        yt_videos_layout = QHBoxLayout()
        self.youtube_videos_min = QSpinBox()
        self.youtube_videos_min.setRange(1, 10)
        self.youtube_videos_min.setValue(self.get_mode_config("google").get("settings", {}).get("youtube_videos_min", 1))
        self.youtube_videos_min.setStyleSheet(input_style)
        yt_videos_layout.addWidget(self.youtube_videos_min)
        yt_videos_layout.addWidget(QLabel("-"))
        self.youtube_videos_max = QSpinBox()
        self.youtube_videos_max.setRange(1, 10)
        self.youtube_videos_max.setValue(self.get_mode_config("google").get("settings", {}).get("youtube_videos_max", 3))
        self.youtube_videos_max.setStyleSheet(input_style)
        yt_videos_layout.addWidget(self.youtube_videos_max)
        yt_videos_layout.addStretch()
        layout.addRow(tr("Videos to watch:"), yt_videos_layout)
        
        # YouTube watch time (min-max)
        yt_time_layout = QHBoxLayout()
        self.youtube_watch_min = QSpinBox()
        self.youtube_watch_min.setRange(5, 300)
        self.youtube_watch_min.setValue(self.get_mode_config("google").get("settings", {}).get("youtube_watch_min", 15))
        self.youtube_watch_min.setSuffix(" sec")
        self.youtube_watch_min.setStyleSheet(input_style)
        yt_time_layout.addWidget(self.youtube_watch_min)
        yt_time_layout.addWidget(QLabel("-"))
        self.youtube_watch_max = QSpinBox()
        self.youtube_watch_max.setRange(5, 300)
        self.youtube_watch_max.setValue(self.get_mode_config("google").get("settings", {}).get("youtube_watch_max", 60))
        self.youtube_watch_max.setSuffix(" sec")
        self.youtube_watch_max.setStyleSheet(input_style)
        yt_time_layout.addWidget(self.youtube_watch_max)
        yt_time_layout.addStretch()
        layout.addRow(tr("Watch time:"), yt_time_layout)
        
        # YouTube like chance
        self.youtube_like_percent = QSpinBox()
        self.youtube_like_percent.setRange(0, 100)
        self.youtube_like_percent.setValue(self.get_mode_config("google").get("settings", {}).get("youtube_like_percent", 25))
        self.youtube_like_percent.setSuffix(" %")
        self.youtube_like_percent.setStyleSheet(input_style)
        layout.addRow(tr("Like chance:"), self.youtube_like_percent)
        
        # YouTube Watch Later chance
        self.youtube_watchlater_percent = QSpinBox()
        self.youtube_watchlater_percent.setRange(0, 100)
        self.youtube_watchlater_percent.setValue(self.get_mode_config("google").get("settings", {}).get("youtube_watchlater_percent", 20))
        self.youtube_watchlater_percent.setSuffix(" %")
        self.youtube_watchlater_percent.setStyleSheet(input_style)
        layout.addRow(tr("Watch Later chance:"), self.youtube_watchlater_percent)
        
        # === BROWSING BEHAVIOR ===
        browsing_label = QLabel(tr("🖱️ Browsing Behavior"))
        browsing_label.setStyleSheet("font-weight: bold; font-size: 12px; color: #89b4fa; margin-top: 10px;")
        layout.addRow(browsing_label)
        
        self.google_scroll_enabled = QCheckBox(tr("Enable scrolling"))
        self.google_scroll_enabled.setChecked(self.get_mode_config("google").get("settings", {}).get("scroll_enabled", True))
        layout.addRow(self.google_scroll_enabled)
        
        self.google_scroll_percent = QSpinBox()
        self.google_scroll_percent.setRange(0, 100)
        self.google_scroll_percent.setValue(self.get_mode_config("google").get("settings", {}).get("scroll_percent", 70))
        self.google_scroll_percent.setSuffix(" %")
        self.google_scroll_percent.setStyleSheet(input_style)
        layout.addRow(tr("Scroll probability:"), self.google_scroll_percent)
        
        # Scroll iterations (min-max)
        google_scroll_iter_layout = QHBoxLayout()
        self.google_scroll_iter_min = QSpinBox()
        self.google_scroll_iter_min.setRange(1, 20)
        self.google_scroll_iter_min.setValue(self.get_mode_config("google").get("settings", {}).get("scroll_iterations_min", 3))
        self.google_scroll_iter_min.setStyleSheet(input_style)
        google_scroll_iter_layout.addWidget(self.google_scroll_iter_min)
        google_scroll_iter_layout.addWidget(QLabel("-"))
        self.google_scroll_iter_max = QSpinBox()
        self.google_scroll_iter_max.setRange(1, 20)
        self.google_scroll_iter_max.setValue(self.get_mode_config("google").get("settings", {}).get("scroll_iterations_max", 6))
        self.google_scroll_iter_max.setStyleSheet(input_style)
        google_scroll_iter_layout.addWidget(self.google_scroll_iter_max)
        google_scroll_iter_layout.addStretch()
        layout.addRow(tr("Scroll iterations:"), google_scroll_iter_layout)
        
        # Scroll pixels (min-max)
        google_scroll_px_layout = QHBoxLayout()
        self.google_scroll_px_min = QSpinBox()
        self.google_scroll_px_min.setRange(10, 500)
        self.google_scroll_px_min.setValue(self.get_mode_config("google").get("settings", {}).get("scroll_pixels_min", 50))
        self.google_scroll_px_min.setSuffix(" px")
        self.google_scroll_px_min.setStyleSheet(input_style)
        google_scroll_px_layout.addWidget(self.google_scroll_px_min)
        google_scroll_px_layout.addWidget(QLabel("-"))
        self.google_scroll_px_max = QSpinBox()
        self.google_scroll_px_max.setRange(10, 500)
        self.google_scroll_px_max.setValue(self.get_mode_config("google").get("settings", {}).get("scroll_pixels_max", 150))
        self.google_scroll_px_max.setSuffix(" px")
        self.google_scroll_px_max.setStyleSheet(input_style)
        google_scroll_px_layout.addWidget(self.google_scroll_px_max)
        google_scroll_px_layout.addStretch()
        layout.addRow(tr("Scroll pixels:"), google_scroll_px_layout)
        
        # Scroll pause (min-max)
        google_scroll_pause_layout = QHBoxLayout()
        self.google_scroll_pause_min = QDoubleSpinBox()
        self.google_scroll_pause_min.setRange(0.05, 2.0)
        self.google_scroll_pause_min.setSingleStep(0.05)
        self.google_scroll_pause_min.setValue(self.get_mode_config("google").get("settings", {}).get("scroll_pause_min", 0.1))
        self.google_scroll_pause_min.setSuffix(" s")
        self.google_scroll_pause_min.setStyleSheet(input_style)
        google_scroll_pause_layout.addWidget(self.google_scroll_pause_min)
        google_scroll_pause_layout.addWidget(QLabel("-"))
        self.google_scroll_pause_max = QDoubleSpinBox()
        self.google_scroll_pause_max.setRange(0.05, 2.0)
        self.google_scroll_pause_max.setSingleStep(0.05)
        self.google_scroll_pause_max.setValue(self.get_mode_config("google").get("settings", {}).get("scroll_pause_max", 0.3))
        self.google_scroll_pause_max.setSuffix(" s")
        self.google_scroll_pause_max.setStyleSheet(input_style)
        google_scroll_pause_layout.addWidget(self.google_scroll_pause_max)
        google_scroll_pause_layout.addStretch()
        layout.addRow(tr("Scroll pause:"), google_scroll_pause_layout)
        
        # Scroll direction
        self.google_scroll_down_percent = QSpinBox()
        self.google_scroll_down_percent.setRange(0, 100)
        self.google_scroll_down_percent.setValue(self.get_mode_config("google").get("settings", {}).get("scroll_down_percent", 66))
        self.google_scroll_down_percent.setSuffix(" %")
        self.google_scroll_down_percent.setStyleSheet(input_style)
        layout.addRow(tr("Scroll down chance:"), self.google_scroll_down_percent)
        
        self.google_click_enabled = QCheckBox(tr("Click random links"))
        self.google_click_enabled.setChecked(self.get_mode_config("google").get("settings", {}).get("click_links_enabled", True))
        layout.addRow(self.google_click_enabled)
        
        self.google_click_percent = QSpinBox()
        self.google_click_percent.setRange(0, 100)
        self.google_click_percent.setValue(self.get_mode_config("google").get("settings", {}).get("click_percent", 20))
        self.google_click_percent.setSuffix(" %")
        self.google_click_percent.setStyleSheet(input_style)
        layout.addRow(tr("Click probability:"), self.google_click_percent)
        
        self.google_max_clicks = QSpinBox()
        self.google_max_clicks.setRange(0, 10)
        self.google_max_clicks.setValue(self.get_mode_config("google").get("settings", {}).get("max_clicks_per_site", 2))
        self.google_max_clicks.setStyleSheet(input_style)
        layout.addRow(tr("Max clicks per site:"), self.google_max_clicks)
        
        scroll_widget.setLayout(layout)
        scroll.setWidget(scroll_widget)
        main_layout.addWidget(scroll)
        
        # Save button at bottom
        save_btn = QPushButton(tr("Save Settings"))
        save_btn.clicked.connect(lambda: self.save_mode_settings("google"))
        main_layout.addWidget(save_btn)
        
        return widget
    
    def show_global_settings(self):
        """Show global settings dialog"""
        from PyQt5.QtWidgets import QDialog, QDialogButtonBox
        
        dialog = QDialog(self)
        dialog.setWindowTitle(tr("Global Settings"))
        dialog.setMinimumWidth(400)
        dialog_layout = QVBoxLayout(dialog)
        
        form = QFormLayout()
        
        # === CONNECTION ===
        conn_label = QLabel(tr("🔌 Connection"))
        conn_label.setStyleSheet("font-weight: bold; font-size: 12px; color: #89b4fa;")
        form.addRow(conn_label)
        
        self.global_api_url = QLineEdit()
        self.global_api_url.setText(self.config.get("api_url", "http://localhost:58888"))
        form.addRow("Octo Browser API:", self.global_api_url)
        
        # === INTERFACE ===
        iface_label = QLabel(tr("🎨 Interface"))
        iface_label.setStyleSheet("font-weight: bold; font-size: 12px; color: #89b4fa; margin-top: 10px;")
        form.addRow(iface_label)
        
        self.global_language = QComboBox()
        self.global_language.addItems(["English", "Русский"])
        self.global_language.setCurrentText(self.config.get("language", "English"))
        form.addRow(tr("Language:"), self.global_language)
        
        self.global_theme = QComboBox()
        self.global_theme.addItems(["Dark", "Light"])
        self.global_theme.setCurrentText(self.config.get("theme", "Dark"))
        form.addRow(tr("Theme:"), self.global_theme)
        
        # === EXECUTION ===
        exec_label = QLabel(tr("⚡ Execution"))
        exec_label.setStyleSheet("font-weight: bold; font-size: 12px; color: #89b4fa; margin-top: 10px;")
        form.addRow(exec_label)
        
        self.global_max_parallel = QSpinBox()
        self.global_max_parallel.setRange(1, 20)
        self.global_max_parallel.setValue(self.config.get("max_parallel_profiles", 5))
        form.addRow(tr("Max parallel profiles:"), self.global_max_parallel)
        
        # Base delay (min-max)
        delay_layout = QHBoxLayout()
        self.global_delay_min = QSpinBox()
        self.global_delay_min.setRange(0, 10)
        self.global_delay_min.setValue(self.config.get("base_delay_min", 1))
        self.global_delay_min.setSuffix(" sec")
        delay_layout.addWidget(self.global_delay_min)
        delay_layout.addWidget(QLabel("-"))
        self.global_delay_max = QSpinBox()
        self.global_delay_max.setRange(1, 30)
        self.global_delay_max.setValue(self.config.get("base_delay_max", 3))
        self.global_delay_max.setSuffix(" sec")
        delay_layout.addWidget(self.global_delay_max)
        form.addRow(tr("Base action delay:"), delay_layout)
        
        # === ADDITIONAL ===
        add_label = QLabel(tr("📋 Additional"))
        add_label.setStyleSheet("font-weight: bold; font-size: 12px; color: #89b4fa; margin-top: 10px;")
        form.addRow(add_label)
        
        self.global_autosave_logs = QCheckBox(tr("Auto-save logs to file"))
        self.global_autosave_logs.setChecked(self.config.get("autosave_logs", False))
        form.addRow(self.global_autosave_logs)
        
        self.global_sound_finish = QCheckBox(tr("Sound on completion"))
        self.global_sound_finish.setChecked(self.config.get("sound_on_finish", False))
        form.addRow(self.global_sound_finish)
        
        self.global_start_minimized = QCheckBox(tr("Start profiles minimized"))
        self.global_start_minimized.setChecked(self.config.get("start_minimized", True))
        form.addRow(self.global_start_minimized)
        
        # === GEO-BASED VISITING ===
        geo_label = QLabel(tr("🌍 Geo-based visiting"))
        geo_label.setStyleSheet("font-weight: bold; font-size: 12px; color: #89b4fa; margin-top: 10px;")
        form.addRow(geo_label)
        
        self.global_geo_enabled = QCheckBox(tr("Enable geo-based site visiting"))
        self.global_geo_enabled.setChecked(self.config.get("geo_visiting_enabled", False))
        self.global_geo_enabled.stateChanged.connect(self._toggle_geo_percent)
        form.addRow(self.global_geo_enabled)
        
        geo_percent_layout = QHBoxLayout()
        self.global_geo_percent = QSpinBox()
        self.global_geo_percent.setRange(0, 100)
        self.global_geo_percent.setValue(self.config.get("geo_visiting_percent", 70))
        self.global_geo_percent.setSuffix(" %")
        self.global_geo_percent.setEnabled(self.config.get("geo_visiting_enabled", False))
        geo_percent_layout.addWidget(self.global_geo_percent)
        geo_percent_layout.addStretch()
        form.addRow(tr("Local geo sites percent:"), geo_percent_layout)
        
        geo_hint = QLabel(tr("Bot will visit X% sites matching profile's proxy geo"))
        geo_hint.setStyleSheet("color: #6c7086; font-size: 10px;")
        form.addRow(geo_hint)
        
        # === YOUTUBE ===
        yt_label = QLabel(tr("📺 YouTube"))
        yt_label.setStyleSheet("font-weight: bold; font-size: 12px; color: #89b4fa; margin-top: 10px;")
        form.addRow(yt_label)
        
        yt_queries_btn = QPushButton(tr("Edit YouTube Queries"))
        yt_queries_btn.clicked.connect(self._show_youtube_queries_editor)
        form.addRow(yt_queries_btn)
        
        dialog_layout.addLayout(form)
        
        # Buttons
        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(lambda: self._save_global_settings(dialog))
        buttons.rejected.connect(dialog.reject)
        dialog_layout.addWidget(buttons)
        
        dialog.exec_()
    
    def _save_global_settings(self, dialog):
        """Save global settings"""
        self.config["api_url"] = self.global_api_url.text()
        self.config["language"] = self.global_language.currentText()
        self.config["theme"] = self.global_theme.currentText()
        self.config["max_parallel_profiles"] = self.global_max_parallel.value()
        self.config["base_delay_min"] = self.global_delay_min.value()
        self.config["base_delay_max"] = self.global_delay_max.value()
        self.config["autosave_logs"] = self.global_autosave_logs.isChecked()
        self.config["sound_on_finish"] = self.global_sound_finish.isChecked()
        self.config["start_minimized"] = self.global_start_minimized.isChecked()
        # Geo-based visiting settings
        self.config["geo_visiting_enabled"] = self.global_geo_enabled.isChecked()
        self.config["geo_visiting_percent"] = self.global_geo_percent.value()
        
        # Update API URL in top bar
        self.api_url_input.setText(self.config["api_url"])
        
        # Apply theme immediately
        self.current_theme = self.config["theme"]
        self.apply_theme(self.current_theme)
        
        # Save config
        self.current_language = self.config["language"]
        self.save_config()
        self.log("[global] Settings saved")
        
        # Show message that restart is needed for language change
        QMessageBox.information(self, "OK", tr("Settings saved!") + "\n" + tr("Restart app for language change."))
        dialog.accept()
    
    def _toggle_geo_percent(self, state):
        """Enable/disable geo percent spinner based on checkbox."""
        self.global_geo_percent.setEnabled(state == Qt.Checked)
    
    def _show_youtube_queries_editor(self):
        """Show dialog to edit YouTube search queries."""
        from PyQt5.QtWidgets import QDialog, QDialogButtonBox, QTextEdit
        
        dialog = QDialog(self)
        dialog.setWindowTitle(tr("YouTube Search Queries"))
        dialog.setMinimumWidth(500)
        dialog.setMinimumHeight(400)
        layout = QVBoxLayout(dialog)
        
        # Instructions
        info_label = QLabel(tr("Enter search queries separated by commas:"))
        layout.addWidget(info_label)
        
        # Text editor for queries
        self.yt_queries_edit = QTextEdit()
        self.yt_queries_edit.setPlaceholderText("music, gaming, tutorial, cooking, travel, ...")
        
        # Load saved queries or default
        default_queries = "music, gaming, vlog, tutorial, review, unboxing, podcast, documentary, cooking, travel, animation, news, highlights, compilation, technology, programming, design, photography, finance, motivation, education, nature, wildlife, space, gadgets, smartphones, cars, fashion, makeup, fitness, yoga, football, basketball, esports, minecraft, fortnite, tips, memes, shorts, lofi, jazz, rock, pop, classical, hiphop, rap, piano, guitar, dance, kpop, anime, marvel, disney, netflix, movie, comedy, drama, action, diy, crafts, gardening, productivity, startup, asmr, relaxation"
        saved_queries = self.config.get("youtube_queries", default_queries)
        self.yt_queries_edit.setText(saved_queries)
        
        layout.addWidget(self.yt_queries_edit)
        
        # Query count label
        self.yt_count_label = QLabel()
        self._update_yt_query_count()
        self.yt_queries_edit.textChanged.connect(self._update_yt_query_count)
        layout.addWidget(self.yt_count_label)
        
        # Buttons
        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(lambda: self._save_youtube_queries(dialog))
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)
        
        dialog.exec_()
    
    def _update_yt_query_count(self):
        """Update the count of YouTube queries."""
        text = self.yt_queries_edit.toPlainText()
        queries = [q.strip() for q in text.split(",") if q.strip()]
        self.yt_count_label.setText(tr("Total queries:") + f" {len(queries)}")
    
    def _save_youtube_queries(self, dialog):
        """Save YouTube queries to config."""
        text = self.yt_queries_edit.toPlainText()
        # Clean up: remove extra spaces, empty items
        queries = [q.strip() for q in text.split(",") if q.strip()]
        cleaned = ", ".join(queries)
        
        self.config["youtube_queries"] = cleaned
        self.save_config()
        self.log(f"[global] YouTube queries saved ({len(queries)} queries)")
        dialog.accept()
    
    def switch_mode(self, mode):
        self.current_mode = mode
        self.cookie_mode_btn.setChecked(mode == "cookie")
        self.google_mode_btn.setChecked(mode == "google")
        self.mode_stack.setCurrentIndex(0 if mode == "cookie" else 1)
        self.log(f"Mode: {mode.upper()}")
    
    def get_mode_config(self, mode):
        key = "cookie_mode" if mode == "cookie" else "google_mode"
        return self.config.get(key, {"profiles": [], "sites": [], "settings": {}})
    
    def set_mode_config(self, mode, data):
        key = "cookie_mode" if mode == "cookie" else "google_mode"
        self.config[key] = data
        self.save_config()
    
    def apply_theme(self, theme="Dark"):
        """Apply dark or light theme"""
        if theme == "Dark":
            self.setStyleSheet("""
                QMainWindow, QWidget { background-color: #1e1e2e; color: #cdd6f4; font-family: 'Segoe UI', Arial; }
                QGroupBox { border: 1px solid #45475a; border-radius: 6px; margin-top: 8px; padding-top: 8px; }
                QGroupBox::title { color: #89b4fa; }
                QPushButton {
                    background-color: #45475a; border: none; border-radius: 4px;
                    padding: 6px 12px; color: #cdd6f4;
                }
                QPushButton:hover { background-color: #585b70; }
                QPushButton:checked { background-color: #89b4fa; color: #1e1e2e; }
                QPushButton:disabled { background-color: #313244; color: #6c7086; }
                QLineEdit, QSpinBox, QComboBox {
                    background-color: #313244; border: 1px solid #45475a;
                    border-radius: 4px; padding: 5px; color: #cdd6f4;
                }
                QLineEdit:focus, QSpinBox:focus { border-color: #89b4fa; }
                QTextEdit {
                    background-color: #11111b; border: 1px solid #45475a;
                    border-radius: 4px; color: #a6e3a1;
                }
                QListWidget {
                    background-color: #313244; border: 1px solid #45475a; border-radius: 4px;
                }
                QListWidget::item:selected { background-color: #89b4fa; color: #1e1e2e; }
                QTabWidget::pane { border: 1px solid #45475a; border-radius: 4px; }
                QTabBar::tab {
                    background-color: #313244; border: 1px solid #45475a;
                    padding: 6px 16px; margin-right: 2px;
                }
                QTabBar::tab:selected { background-color: #45475a; color: #89b4fa; }
                QCheckBox::indicator { width: 16px; height: 16px; border-radius: 3px; border: 1px solid #45475a; }
                QCheckBox::indicator:checked { background-color: #89b4fa; }
                QScrollArea { border: none; }
                QDialog { background-color: #1e1e2e; color: #cdd6f4; }
            """)
        else:  # Light theme
            self.setStyleSheet("""
                QMainWindow, QWidget { background-color: #f5f5f5; color: #333333; font-family: 'Segoe UI', Arial; }
                QGroupBox { border: 1px solid #cccccc; border-radius: 6px; margin-top: 8px; padding-top: 8px; }
                QGroupBox::title { color: #1a73e8; }
                QPushButton {
                    background-color: #e0e0e0; border: none; border-radius: 4px;
                    padding: 6px 12px; color: #333333;
                }
                QPushButton:hover { background-color: #d0d0d0; }
                QPushButton:checked { background-color: #1a73e8; color: #ffffff; }
                QPushButton:disabled { background-color: #f0f0f0; color: #999999; }
                QLineEdit, QSpinBox, QComboBox {
                    background-color: #ffffff; border: 1px solid #cccccc;
                    border-radius: 4px; padding: 5px; color: #333333;
                }
                QLineEdit:focus, QSpinBox:focus { border-color: #1a73e8; }
                QTextEdit {
                    background-color: #ffffff; border: 1px solid #cccccc;
                    border-radius: 4px; color: #2e7d32;
                }
                QListWidget {
                    background-color: #ffffff; border: 1px solid #cccccc; border-radius: 4px;
                }
                QListWidget::item:selected { background-color: #1a73e8; color: #ffffff; }
                QTabWidget::pane { border: 1px solid #cccccc; border-radius: 4px; }
                QTabBar::tab {
                    background-color: #e8e8e8; border: 1px solid #cccccc;
                    padding: 6px 16px; margin-right: 2px;
                }
                QTabBar::tab:selected { background-color: #ffffff; color: #1a73e8; }
                QCheckBox::indicator { width: 16px; height: 16px; border-radius: 3px; border: 1px solid #cccccc; }
                QCheckBox::indicator:checked { background-color: #1a73e8; }
                QScrollArea { border: none; }
                QDialog { background-color: #f5f5f5; color: #333333; }
            """)
    
    def load_config(self):
        try:
            with open("config.json", "r", encoding="utf-8") as f:
                config = json.load(f)
                if "cookie_mode" not in config:
                    config = self.migrate_config(config)
                return config
        except:
            return self.get_default_config()
    
    def migrate_config(self, old):
        return {
            "api_url": old.get("api_url", "http://localhost:58888"),
            "cookie_mode": {
                "profiles": old.get("profiles", []),
                "sites": old.get("sites", []),
                "settings": old.get("settings", {"min_time_on_site": 30, "max_time_on_site": 120,
                    "scroll_enabled": True, "click_links_enabled": True, "human_behavior_enabled": True})
            },
            "google_mode": {
                "profiles": [], "sites": [],
                "settings": {"min_time_on_site": 30, "max_time_on_site": 60,
                    "read_gmail": True, "gmail_letters_count": 5, "gmail_read_time": 30, "auth_on_sites": True}
            }
        }
    
    def get_default_config(self):
        return {
            "api_url": "http://localhost:58888",
            "cookie_mode": {"profiles": [], "sites": [], "settings": {
                "min_time_on_site": 30, "max_time_on_site": 120,
                "scroll_enabled": True, "click_links_enabled": True, "human_behavior_enabled": True}},
            "google_mode": {"profiles": [], "sites": [], "settings": {
                "min_time_on_site": 30, "max_time_on_site": 60,
                "read_gmail": True, "gmail_read_percent": 40, "gmail_read_time": 30, "auth_on_sites": True}}
        }
    
    def save_config(self):
        with open("config.json", "w", encoding="utf-8") as f:
            json.dump(self.config, f, indent=2, ensure_ascii=False)
    
    def log(self, msg):
        timestamp = datetime.now().strftime('%H:%M:%S')
        log_line = f"[{timestamp}] {msg}"
        self.log_area.append(log_line)
        
        # Auto-save logs to file if enabled
        if self.config.get("autosave_logs", False):
            self._save_log_to_file(log_line)
    
    def connect_to_octo(self):
        url = self.api_url_input.text()
        self.config["api_url"] = url
        self.save_config()
        
        port = int(url.split(":")[-1]) if ":" in url else 58888
        self.octo_api = OctoAPI(local_port=port)
        
        if self.octo_api.test_connection():
            self.connection_status.setText("●")
            self.connection_status.setStyleSheet("color: #a6e3a1; font-size: 16px;")
            self.start_btn.setEnabled(True)
            self.log("Connected to Octo Browser")
        else:
            self.connection_status.setStyleSheet("color: #f38ba8; font-size: 16px;")
            self.log("Connection failed")
    
    # === PROFILES ===
    def get_profiles_list(self, mode):
        return self.cookie_profiles_list if mode == "cookie" else self.google_profiles_list
    
    def get_profile_input(self, mode):
        return self.cookie_profile_input if mode == "cookie" else self.google_profile_input
    
    def filter_profiles(self, mode, search_text: str):
        """Filter profiles list by UUID search text (also applies status filter)."""
        # Call the combined filter that handles both search and status
        self.filter_profiles_by_status(mode)
    
    def filter_profiles_by_status(self, mode):
        """Filter profiles list by status from dropdown."""
        lst = self.get_profiles_list(mode)
        profile_info = self.get_mode_config(mode).get("profile_info", {})
        
        # Get selected filter
        if mode == "cookie":
            combo = self.cookie_sort_combo
            search_text = self.cookie_search_input.text().lower().strip()
        else:
            combo = self.google_sort_combo
            search_text = self.google_search_input.text().lower().strip()
        
        filter_type = combo.currentData()
        
        for i in range(lst.count()):
            item = lst.item(i)
            uuid = item.data(Qt.UserRole)
            info = profile_info.get(uuid, {})
            
            # First check search text filter
            if search_text and search_text not in uuid.lower():
                item.setHidden(True)
                continue
            
            # Then apply status filter
            show = True
            if filter_type == "all":
                show = True
            elif filter_type == "google_auth":
                show = info.get("google_authorized", False)
            elif filter_type == "no_google_auth":
                show = not info.get("google_authorized", False)
            elif filter_type == "ads":
                show = info.get("ads_registered", False)
            elif filter_type == "no_ads":
                show = not info.get("ads_registered", False)
            elif filter_type == "payment":
                show = info.get("payment_linked", False)
            elif filter_type == "no_payment":
                show = not info.get("payment_linked", False)
            elif filter_type == "campaign":
                show = info.get("campaign_launched", False)
            elif filter_type == "no_campaign":
                show = not info.get("campaign_launched", False)
            elif filter_type == "ready":
                show = info.get("profile_ready", False)
            elif filter_type == "no_ready":
                show = not info.get("profile_ready", False)
            
            item.setHidden(not show)
    
    def _populate_geo_filter(self, combo: QComboBox):
        """Populate geo filter dropdown with all countries."""
        combo.addItem(tr("All"), "all")
        combo.addItem("🌐 " + tr("Generic") + " (.org, .net, .io...)", "generic")
        combo.addItem("─────────────", "separator")
        # Main countries
        combo.addItem("🇺🇸 US (.us, .com)", "us")
        combo.addItem("🇨🇦 CA (.ca)", "ca")
        combo.addItem("🇬🇧 UK (.uk)", "uk")
        combo.addItem("🇦🇺 AU (.au)", "au")
        combo.addItem("─────────────", "separator2")
        # EU countries (sorted)
        eu_countries = [
            ("🇦🇹", "AT", "at"), ("🇧🇪", "BE", "be"), ("🇧🇬", "BG", "bg"),
            ("🇭🇷", "HR", "hr"), ("🇨🇾", "CY", "cy"), ("🇨🇿", "CZ", "cz"),
            ("🇩🇰", "DK", "dk"), ("🇪🇪", "EE", "ee"), ("🇫🇮", "FI", "fi"),
            ("🇫🇷", "FR", "fr"), ("🇩🇪", "DE", "de"), ("🇬🇷", "GR", "gr"),
            ("🇭🇺", "HU", "hu"), ("🇮🇪", "IE", "ie"), ("🇮🇹", "IT", "it"),
            ("🇱🇻", "LV", "lv"), ("🇱🇹", "LT", "lt"), ("🇱🇺", "LU", "lu"),
            ("🇲🇹", "MT", "mt"), ("🇳🇱", "NL", "nl"), ("🇵🇱", "PL", "pl"),
            ("🇵🇹", "PT", "pt"), ("🇷🇴", "RO", "ro"), ("🇸🇰", "SK", "sk"),
            ("🇸🇮", "SI", "si"), ("🇪🇸", "ES", "es"), ("🇸🇪", "SE", "se"),
        ]
        for flag, code, tld in eu_countries:
            combo.addItem(f"{flag} {code} (.{tld})", tld)
        combo.addItem("─────────────", "separator3")
        # Other countries
        other_countries = [
            ("🇷🇺", "RU", "ru"), ("🇺🇦", "UA", "ua"), ("🇹🇷", "TR", "tr"),
            ("🇯🇵", "JP", "jp"), ("🇰🇷", "KR", "kr"), ("🇨🇳", "CN", "cn"),
            ("🇮🇳", "IN", "in"), ("🇧🇷", "BR", "br"), ("🇲🇽", "MX", "mx"),
            ("🇦🇷", "AR", "ar"), ("🇨🇭", "CH", "ch"), ("🇳🇴", "NO", "no"),
        ]
        for flag, code, tld in other_countries:
            combo.addItem(f"{flag} {code} (.{tld})", tld)
    
    def _filter_sites_by_geo(self, target: str):
        """Filter sites list by geo (TLD) using dropdown selection."""
        # Get the appropriate widgets
        if target == "cookie":
            lst = self.cookie_sites_list
            combo = self.cookie_geo_filter
        elif target == "google_sites":
            lst = self.google_sites_list
            combo = self.google_sites_geo_filter
        elif target == "google_onetap":
            lst = self.google_onetap_list
            combo = self.google_onetap_geo_filter
        else:
            return
        
        filter_data = combo.currentData()
        
        # Skip separators
        if filter_data and filter_data.startswith("separator"):
            return
        
        for i in range(lst.count()):
            item = lst.item(i)
            url = item.text()
            tld = get_site_tld(url)
            geo_cat = get_site_geo_category(url)
            
            show = True
            
            if filter_data == "all":
                show = True
            elif filter_data == "us":
                show = geo_cat == "us" or tld in ('us', 'com')
            elif filter_data == "uk":
                show = tld in ('uk', 'co.uk')
            elif filter_data == "ca":
                show = tld == "ca"
            elif filter_data == "au":
                show = tld in ('au', 'com.au')
            elif filter_data == "generic":
                show = tld in GENERIC_TLDS
            elif filter_data:
                # Specific country TLD (e.g., 'de', 'fr', 'it')
                show = tld == filter_data
            
            item.setHidden(not show)
    
    def _filter_sites_by_geo_text(self, target: str, search_text: str):
        """Filter sites list by text input (dynamic search by TLD)."""
        if target == "cookie":
            lst = self.cookie_sites_list
        elif target == "google_sites":
            lst = self.google_sites_list
        elif target == "google_onetap":
            lst = self.google_onetap_list
        else:
            return
        
        search_lower = search_text.lower().strip()
        
        # If empty, show all sites
        if not search_lower:
            for i in range(lst.count()):
                lst.item(i).setHidden(False)
            return
        
        # Filter by TLD - search_lower should match the TLD
        for i in range(lst.count()):
            item = lst.item(i)
            url = item.text()
            tld = get_site_tld(url)
            
            # Show if TLD matches or starts with search text
            # e.g., "si" matches ".si", "co" matches ".co.uk"
            show = (tld == search_lower or 
                    tld.startswith(search_lower) or 
                    search_lower in tld)
            item.setHidden(not show)
    
    def load_profiles_list(self, mode):
        lst = self.get_profiles_list(mode)
        lst.clear()
        profile_info = self.get_mode_config(mode).get("profile_info", {})
        
        for uuid in self.get_mode_config(mode).get("profiles", []):
            # Get profile data from profile_info
            info = profile_info.get(uuid, {})
            country = info.get("country", "")
            first_run = info.get("first_run", "")
            google_authorized = info.get("google_authorized", False)
            ads_registered = info.get("ads_registered", False)
            payment_linked = info.get("payment_linked", False)
            campaign_launched = info.get("campaign_launched", False)
            profile_ready = info.get("profile_ready", False)
            # Timestamps for time-ago display
            ads_timestamp = info.get("ads_timestamp", "")
            payment_timestamp = info.get("payment_timestamp", "")
            campaign_timestamp = info.get("campaign_timestamp", "")
            ready_timestamp = info.get("ready_timestamp", "")
            
            item = QListWidgetItem()
            item.setData(Qt.UserRole, uuid)  # Store UUID in item data
            
            # Create custom widget with mode and states
            widget = ProfileItemWidget(
                uuid, country, first_run, mode, 
                google_authorized, ads_registered, payment_linked, campaign_launched,
                profile_ready, ads_timestamp, payment_timestamp, campaign_timestamp, ready_timestamp
            )
            widget.copy_clicked.connect(lambda u: self.log(f"Copied: {u}"))
            if mode == "cookie":
                widget.migrate_clicked.connect(self._on_migrate_profile)
                widget.google_auth_changed.connect(self._on_google_auth_changed)
            elif mode == "google":
                widget.ads_changed.connect(self._on_ads_changed)
                widget.payment_changed.connect(self._on_payment_changed)
                widget.campaign_changed.connect(self._on_campaign_changed)
                widget.ready_changed.connect(self._on_ready_changed)
            
            item.setSizeHint(widget.sizeHint())
            lst.addItem(item)
            lst.setItemWidget(item, widget)
    
    def add_profile(self, mode):
        inp = self.get_profile_input(mode)
        uuid = inp.text().strip()
        if uuid:
            cfg = self.get_mode_config(mode)
            profiles = cfg.get("profiles", [])
            if uuid not in profiles:
                profiles.append(uuid)
                cfg["profiles"] = profiles
                
                # Try to get profile info from API
                country = ""
                if self.octo_api:
                    info = self.octo_api.get_profile_info(uuid)
                    if info:
                        country = info.get("country", "")
                        # Store profile info
                        profile_info = cfg.setdefault("profile_info", {})
                        profile_info[uuid] = {"country": country}
                
                self.set_mode_config(mode, cfg)
                
                # Add item with custom widget
                lst = self.get_profiles_list(mode)
                item = QListWidgetItem()
                item.setData(Qt.UserRole, uuid)
                
                widget = ProfileItemWidget(uuid, country, "", mode, False, False, False, False, False)
                widget.copy_clicked.connect(lambda u: self.log(f"Copied: {u}"))
                if mode == "cookie":
                    widget.migrate_clicked.connect(self._on_migrate_profile)
                    widget.google_auth_changed.connect(self._on_google_auth_changed)
                elif mode == "google":
                    widget.ads_changed.connect(self._on_ads_changed)
                    widget.payment_changed.connect(self._on_payment_changed)
                    widget.campaign_changed.connect(self._on_campaign_changed)
                    widget.ready_changed.connect(self._on_ready_changed)
                
                item.setSizeHint(widget.sizeHint())
                lst.addItem(item)
                lst.setItemWidget(item, widget)
                
                flag = COUNTRY_FLAGS.get(country.upper(), "🌐") if country else ""
                self.log(f"[{mode}] Added: {flag} {uuid[:8]}...")
            inp.clear()
    
    def select_all_profiles(self, mode):
        lst = self.get_profiles_list(mode)
        for i in range(lst.count()):
            widget = lst.itemWidget(lst.item(i))
            if widget and hasattr(widget, 'setChecked'):
                widget.setChecked(True)
    
    def deselect_all_profiles(self, mode):
        lst = self.get_profiles_list(mode)
        for i in range(lst.count()):
            widget = lst.itemWidget(lst.item(i))
            if widget and hasattr(widget, 'setChecked'):
                widget.setChecked(False)
    
    def remove_selected_profiles(self, mode):
        lst = self.get_profiles_list(mode)
        cfg = self.get_mode_config(mode)
        
        # Get selected UUIDs from widget checkboxes
        to_remove = []
        for i in range(lst.count()):
            widget = lst.itemWidget(lst.item(i))
            if widget and hasattr(widget, 'isChecked') and widget.isChecked():
                to_remove.append(lst.item(i).data(Qt.UserRole))
        
        profiles = cfg.get("profiles", [])
        profile_info = cfg.get("profile_info", {})
        for uuid in to_remove:
            if uuid in profiles:
                profiles.remove(uuid)
            if uuid in profile_info:
                del profile_info[uuid]
        
        cfg["profiles"] = profiles
        cfg["profile_info"] = profile_info
        self.set_mode_config(mode, cfg)
        self.load_profiles_list(mode)
        self.log(f"[{mode}] Removed {len(to_remove)} profiles")
    
    def get_selected_profiles(self, mode):
        lst = self.get_profiles_list(mode)
        selected = []
        for i in range(lst.count()):
            widget = lst.itemWidget(lst.item(i))
            if widget and hasattr(widget, 'isChecked') and widget.isChecked():
                selected.append(lst.item(i).data(Qt.UserRole))
        return selected
    
    def _on_migrate_profile(self, uuid: str, age_days: int, google_authorized: bool):
        """Handle profile migration from Cookie to Google mode."""
        # Check if Google is authorized first
        if not google_authorized:
            QMessageBox.warning(
                self,
                tr("Authorization Required"),
                tr("First authorize Google account in the selected profile!")
            )
            return
        
        # First confirmation dialog
        reply = QMessageBox.question(
            self,
            tr("Confirm Migration"),
            tr("Migrate profile to Google mode?") + f"\n\nUUID: {uuid[:8]}...",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply != QMessageBox.Yes:
            return
        
        # Additional warning for profiles younger than 2 days
        if 0 <= age_days < 2:
            warning_reply = QMessageBox.warning(
                self,
                tr("Warning"),
                tr("This profile is less than 2 days old!") + f"\n\n" +
                tr("Profile age:") + f" {age_days}d\n\n" +
                tr("Are you sure you want to migrate?"),
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            
            if warning_reply != QMessageBox.Yes:
                return
        
        # Perform migration
        self._migrate_profile_to_google(uuid)
    
    def _on_google_auth_changed(self, uuid: str, authorized: bool):
        """Save Google authorization state for profile."""
        cfg = self.get_mode_config("cookie")
        profile_info = cfg.setdefault("profile_info", {})
        
        if uuid not in profile_info:
            profile_info[uuid] = {}
        
        profile_info[uuid]["google_authorized"] = authorized
        self.set_mode_config("cookie", cfg)
        
        status = "✓" if authorized else "✗"
        self.log(f"[{uuid[:8]}] Google auth: {status}")
    
    def _on_ads_changed(self, uuid: str, registered: bool):
        """Save Google Ads registration state for profile."""
        cfg = self.get_mode_config("google")
        profile_info = cfg.setdefault("profile_info", {})
        
        if uuid not in profile_info:
            profile_info[uuid] = {}
        
        profile_info[uuid]["ads_registered"] = registered
        # Save timestamp on activation, clear on deactivation
        if registered:
            profile_info[uuid]["ads_timestamp"] = datetime.now().isoformat()
        else:
            profile_info[uuid]["ads_timestamp"] = ""
        self.set_mode_config("google", cfg)
        
        status = "✓" if registered else "✗"
        self.log(f"[{uuid[:8]}] Google Ads: {status}")
    
    def _on_payment_changed(self, uuid: str, linked: bool):
        """Save payment method state for profile."""
        cfg = self.get_mode_config("google")
        profile_info = cfg.setdefault("profile_info", {})
        
        if uuid not in profile_info:
            profile_info[uuid] = {}
        
        profile_info[uuid]["payment_linked"] = linked
        # Save timestamp on activation, clear on deactivation
        if linked:
            profile_info[uuid]["payment_timestamp"] = datetime.now().isoformat()
        else:
            profile_info[uuid]["payment_timestamp"] = ""
        self.set_mode_config("google", cfg)
        
        status = "✓" if linked else "✗"
        self.log(f"[{uuid[:8]}] Payment: {status}")
    
    def _on_campaign_changed(self, uuid: str, launched: bool):
        """Save ad campaign state for profile."""
        cfg = self.get_mode_config("google")
        profile_info = cfg.setdefault("profile_info", {})
        
        if uuid not in profile_info:
            profile_info[uuid] = {}
        
        profile_info[uuid]["campaign_launched"] = launched
        # Save timestamp on activation, clear on deactivation
        if launched:
            profile_info[uuid]["campaign_timestamp"] = datetime.now().isoformat()
        else:
            profile_info[uuid]["campaign_timestamp"] = ""
        self.set_mode_config("google", cfg)
        
        status = "✓" if launched else "✗"
        self.log(f"[{uuid[:8]}] Campaign: {status}")
    
    def _on_ready_changed(self, uuid: str, ready: bool):
        """Save profile ready state."""
        cfg = self.get_mode_config("google")
        profile_info = cfg.setdefault("profile_info", {})
        
        if uuid not in profile_info:
            profile_info[uuid] = {}
        
        profile_info[uuid]["profile_ready"] = ready
        # Save timestamp on activation, clear on deactivation
        if ready:
            profile_info[uuid]["ready_timestamp"] = datetime.now().isoformat()
        else:
            profile_info[uuid]["ready_timestamp"] = ""
        self.set_mode_config("google", cfg)
        
        status = "✓" if ready else "✗"
        self.log(f"[{uuid[:8]}] Ready: {status}")
    
    def _migrate_profile_to_google(self, uuid: str):
        """Move profile from Cookie mode to Google mode."""
        # Get cookie config
        cookie_cfg = self.get_mode_config("cookie")
        cookie_profiles = cookie_cfg.get("profiles", [])
        cookie_profile_info = cookie_cfg.get("profile_info", {})
        
        if uuid not in cookie_profiles:
            return
        
        # Get profile info to preserve
        profile_data = cookie_profile_info.get(uuid, {})
        
        # Remove from Cookie mode
        cookie_profiles.remove(uuid)
        if uuid in cookie_profile_info:
            del cookie_profile_info[uuid]
        
        cookie_cfg["profiles"] = cookie_profiles
        cookie_cfg["profile_info"] = cookie_profile_info
        self.set_mode_config("cookie", cookie_cfg)
        
        # Add to Google mode
        google_cfg = self.get_mode_config("google")
        google_profiles = google_cfg.get("profiles", [])
        google_profile_info = google_cfg.setdefault("profile_info", {})
        
        if uuid not in google_profiles:
            google_profiles.append(uuid)
            google_profile_info[uuid] = profile_data
        
        google_cfg["profiles"] = google_profiles
        google_cfg["profile_info"] = google_profile_info
        self.set_mode_config("google", google_cfg)
        
        # Refresh lists
        self.load_profiles_list("cookie")
        self.load_profiles_list("google")
        
        self.log(f"✅ Migrated {uuid[:8]}... to Google mode")
    
    def refresh_profiles_info(self, mode):
        """Refresh proxy info for all profiles from Octo API"""
        if not self.octo_api:
            QMessageBox.warning(self, "Error", tr("Not connected to Octo Browser"))
            return
        
        cfg = self.get_mode_config(mode)
        profiles = cfg.get("profiles", [])
        profile_info = cfg.setdefault("profile_info", {})
        
        updated = 0
        for uuid in profiles:
            info = self.octo_api.get_profile_info(uuid)
            if info:
                country = info.get("country", "")
                profile_info[uuid] = {"country": country}
                updated += 1
        
        cfg["profile_info"] = profile_info
        self.set_mode_config(mode, cfg)
        self.load_profiles_list(mode)
        self.log(f"[{mode}] Refreshed {updated}/{len(profiles)} profiles")

    # === SITES ===
    def get_sites_list(self, mode):
        return self.cookie_sites_list if mode == "cookie" else self.google_sites_list
    
    def get_site_input(self, mode):
        return self.cookie_site_input if mode == "cookie" else self.google_site_input
    
    def get_sites_count(self, mode):
        return self.cookie_sites_count if mode == "cookie" else self.google_sites_count
    
    def load_sites_list(self, mode):
        lst = self.get_sites_list(mode)
        lst.clear()
        sites = self.get_mode_config(mode).get("sites", [])
        for s in sites:
            lst.addItem(s)
        self.get_sites_count(mode).setText(f"{len(sites)} sites")
    
    def add_site(self, mode):
        inp = self.get_site_input(mode)
        url = inp.text().strip()
        if url:
            if not url.startswith(("http://", "https://")):
                url = "https://" + url
            cfg = self.get_mode_config(mode)
            if url not in cfg.get("sites", []):
                cfg.setdefault("sites", []).append(url)
                self.set_mode_config(mode, cfg)
                self.get_sites_list(mode).addItem(url)
                self.get_sites_count(mode).setText(f"{len(cfg['sites'])} sites")
                self.log(f"[{mode}] Added: {url}")
            inp.clear()
    
    def remove_site(self, mode):
        lst = self.get_sites_list(mode)
        cur = lst.currentItem()
        if cur:
            cfg = self.get_mode_config(mode)
            cfg["sites"].remove(cur.text())
            self.set_mode_config(mode, cfg)
            lst.takeItem(lst.row(cur))
            self.get_sites_count(mode).setText(f"{len(cfg['sites'])} sites")
    
    def clear_sites(self, mode):
        if QMessageBox.question(self, "Confirm", f"Clear all {mode} sites?") == QMessageBox.Yes:
            cfg = self.get_mode_config(mode)
            cfg["sites"] = []
            self.set_mode_config(mode, cfg)
            self.get_sites_list(mode).clear()
            self.get_sites_count(mode).setText("0 sites")
    
    def import_sites(self, mode):
        path, _ = QFileDialog.getOpenFileName(self, "Import", "", "Text (*.txt)")
        if path:
            cfg = self.get_mode_config(mode)
            lst = self.get_sites_list(mode)
            count = 0
            with open(path, "r", encoding="utf-8") as f:
                for line in f:
                    url = line.strip()
                    if url and url not in cfg.get("sites", []):
                        if not url.startswith(("http://", "https://")):
                            url = "https://" + url
                        cfg.setdefault("sites", []).append(url)
                        lst.addItem(url)
                        count += 1
            self.set_mode_config(mode, cfg)
            self.get_sites_count(mode).setText(f"{len(cfg['sites'])} sites")
            self.log(f"[{mode}] Imported {count} sites")
    
    def _show_bulk_add_dialog(self, target: str):
        """Show dialog to bulk add sites (one per line)."""
        from PyQt5.QtWidgets import QDialog, QDialogButtonBox, QTextEdit
        
        dialog = QDialog(self)
        dialog.setWindowTitle(tr("Bulk Add Sites"))
        dialog.setMinimumWidth(500)
        dialog.setMinimumHeight(400)
        layout = QVBoxLayout(dialog)
        
        # Instructions
        info_label = QLabel(tr("Enter sites, one per line:"))
        layout.addWidget(info_label)
        
        # Text editor for sites
        text_edit = QTextEdit()
        text_edit.setPlaceholderText("https://example1.com\nhttps://example2.com\nexample3.com")
        layout.addWidget(text_edit)
        
        # Count label
        count_label = QLabel(tr("Sites to add:") + " 0")
        def update_count():
            lines = [line.strip() for line in text_edit.toPlainText().split("\n") if line.strip()]
            count_label.setText(tr("Sites to add:") + f" {len(lines)}")
        text_edit.textChanged.connect(update_count)
        layout.addWidget(count_label)
        
        # Buttons
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(lambda: self._process_bulk_add(dialog, text_edit.toPlainText(), target))
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)
        
        dialog.exec_()
    
    def _process_bulk_add(self, dialog, text: str, target: str):
        """Process bulk add of sites."""
        lines = [line.strip() for line in text.split("\n") if line.strip()]
        if not lines:
            dialog.reject()
            return
        
        added = 0
        
        if target == "cookie":
            # Cookie mode sites
            cfg = self.get_mode_config("cookie")
            sites = cfg.get("sites", [])
            lst = self.get_sites_list("cookie")
            
            for url in lines:
                if not url.startswith(("http://", "https://")):
                    url = "https://" + url
                if url not in sites:
                    sites.append(url)
                    lst.addItem(url)
                    added += 1
            
            cfg["sites"] = sites
            self.set_mode_config("cookie", cfg)
            self.get_sites_count("cookie").setText(f"{len(sites)} " + tr("sites"))
            self.log(f"[cookie] Bulk added {added} sites")
            
        elif target == "google_sites":
            # Google mode - regular sites
            cfg = self.get_mode_config("google")
            sites = cfg.get("browse_sites", [])
            
            for url in lines:
                if not url.startswith(("http://", "https://")):
                    url = "https://" + url
                if url not in sites:
                    sites.append(url)
                    self.google_sites_list.addItem(url)
                    added += 1
            
            cfg["browse_sites"] = sites
            self.set_mode_config("google", cfg)
            self.google_sites_count.setText(f"{len(sites)} " + tr("sites"))
            self.log(f"[google] Bulk added {added} browse sites")
            
        elif target == "google_onetap":
            # Google mode - One Tap sites
            cfg = self.get_mode_config("google")
            sites = cfg.get("onetap_sites", [])
            
            for url in lines:
                if not url.startswith(("http://", "https://")):
                    url = "https://" + url
                if url not in sites:
                    sites.append(url)
                    self.google_onetap_list.addItem(url)
                    added += 1
            
            cfg["onetap_sites"] = sites
            self.set_mode_config("google", cfg)
            self.google_onetap_count.setText(f"{len(sites)} " + tr("sites"))
            self.log(f"[google] Bulk added {added} One Tap sites")
        
        dialog.accept()
    
    def _show_sites_editor(self, target: str):
        """Show full sites editor dialog."""
        from PyQt5.QtWidgets import QDialog, QDialogButtonBox, QTextEdit
        
        dialog = QDialog(self)
        dialog.setWindowTitle(tr("Edit Sites"))
        dialog.setMinimumWidth(550)
        dialog.setMinimumHeight(450)
        layout = QVBoxLayout(dialog)
        
        # Instructions
        info_label = QLabel(tr("Edit sites list (one site per line):"))
        layout.addWidget(info_label)
        
        # Text editor
        text_edit = QTextEdit()
        text_edit.setPlaceholderText("https://example1.com\nhttps://example2.com\nexample3.com")
        
        # Load current sites
        current_sites = []
        if target == "cookie":
            current_sites = self.get_mode_config("cookie").get("sites", [])
        elif target == "google_sites":
            current_sites = self.get_mode_config("google").get("browse_sites", [])
        elif target == "google_onetap":
            current_sites = self.get_mode_config("google").get("onetap_sites", [])
        
        text_edit.setText("\n".join(current_sites))
        layout.addWidget(text_edit)
        
        # Count label
        count_label = QLabel(tr("Total sites:") + f" {len(current_sites)}")
        def update_count():
            lines = [line.strip() for line in text_edit.toPlainText().split("\n") if line.strip()]
            count_label.setText(tr("Total sites:") + f" {len(lines)}")
        text_edit.textChanged.connect(update_count)
        layout.addWidget(count_label)
        
        # Hint
        hint_label = QLabel(tr("Tip: You can add, remove or edit sites. Empty lines will be ignored."))
        hint_label.setStyleSheet("color: #6c7086; font-size: 10px;")
        layout.addWidget(hint_label)
        
        # Buttons
        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(lambda: self._save_sites_from_editor(dialog, text_edit.toPlainText(), target))
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)
        
        dialog.exec_()
    
    def _save_sites_from_editor(self, dialog, text: str, target: str):
        """Save sites from editor."""
        # Parse and clean sites
        sites = []
        for line in text.split("\n"):
            url = line.strip()
            if url:
                if not url.startswith(("http://", "https://")):
                    url = "https://" + url
                if url not in sites:  # Avoid duplicates
                    sites.append(url)
        
        if target == "cookie":
            cfg = self.get_mode_config("cookie")
            cfg["sites"] = sites
            self.set_mode_config("cookie", cfg)
            # Refresh list widget
            self.cookie_sites_list.clear()
            for site in sites:
                self.cookie_sites_list.addItem(site)
            self.cookie_sites_count.setText(f"{len(sites)} " + tr("sites"))
            self.log(f"[cookie] Sites updated: {len(sites)} total")
            
        elif target == "google_sites":
            cfg = self.get_mode_config("google")
            cfg["browse_sites"] = sites
            self.set_mode_config("google", cfg)
            # Refresh list widget
            self.google_sites_list.clear()
            for site in sites:
                self.google_sites_list.addItem(site)
            self.google_sites_count.setText(f"{len(sites)} " + tr("sites"))
            self.log(f"[google] Browse sites updated: {len(sites)} total")
            
        elif target == "google_onetap":
            cfg = self.get_mode_config("google")
            cfg["onetap_sites"] = sites
            self.set_mode_config("google", cfg)
            # Refresh list widget
            self.google_onetap_list.clear()
            for site in sites:
                self.google_onetap_list.addItem(site)
            self.google_onetap_count.setText(f"{len(sites)} " + tr("sites"))
            self.log(f"[google] One Tap sites updated: {len(sites)} total")
        
        dialog.accept()
    
    # === SETTINGS ===
    def save_mode_settings(self, mode):
        cfg = self.get_mode_config(mode)
        if mode == "cookie":
            cfg["settings"] = {
                "min_time_on_site": self.cookie_min_time.value(),
                "max_time_on_site": self.cookie_max_time.value(),
                "google_search_percent": self.cookie_search_percent.value(),
                "sites_per_session_min": self.cookie_sites_min.value(),
                "sites_per_session_max": self.cookie_sites_max.value(),
                "scroll_enabled": self.cookie_scroll.isChecked(),
                "scroll_percent": self.cookie_scroll_percent.value(),
                "scroll_iterations_min": self.cookie_scroll_iter_min.value(),
                "scroll_iterations_max": self.cookie_scroll_iter_max.value(),
                "scroll_pixels_min": self.cookie_scroll_px_min.value(),
                "scroll_pixels_max": self.cookie_scroll_px_max.value(),
                "scroll_pause_min": self.cookie_scroll_pause_min.value(),
                "scroll_pause_max": self.cookie_scroll_pause_max.value(),
                "scroll_down_percent": self.cookie_scroll_down_percent.value(),
                "click_links_enabled": self.cookie_click.isChecked(),
                "click_percent": self.cookie_click_percent.value(),
                "max_clicks_per_site": self.cookie_max_clicks.value(),
                "human_behavior_enabled": self.cookie_human.isChecked()
            }
        else:
            cfg["settings"] = {
                # Sites
                "min_time_on_site": self.google_min_time.value(),
                "max_time_on_site": self.google_max_time.value(),
                "auth_on_sites": self.google_auth_sites.isChecked(),
                "google_search_percent": self.google_search_percent.value(),
                "sites_per_session_min": self.sites_per_session_min.value(),
                "sites_per_session_max": self.sites_per_session_max.value(),
                # Gmail
                "read_gmail": self.google_read_gmail.isChecked(),
                "gmail_read_percent": self.gmail_read_percent.value(),
                "gmail_read_time_min": self.gmail_read_time_min.value(),
                "gmail_read_time_max": self.gmail_read_time_max.value(),
                "gmail_promo_spam_percent": self.gmail_promo_spam_percent.value(),
                "gmail_click_links": self.gmail_click_links.isChecked(),
                "gmail_check_sites_min": self.gmail_check_sites_min.value(),
                "gmail_check_sites_max": self.gmail_check_sites_max.value(),
                "gmail_final_check": self.gmail_final_check.isChecked(),
                "gmail_final_check_percent": self.gmail_final_check_percent.value(),
                # YouTube
                "youtube_activity_percent": self.youtube_activity_percent.value(),
                "youtube_videos_min": self.youtube_videos_min.value(),
                "youtube_videos_max": self.youtube_videos_max.value(),
                "youtube_watch_min": self.youtube_watch_min.value(),
                "youtube_watch_max": self.youtube_watch_max.value(),
                "youtube_like_percent": self.youtube_like_percent.value(),
                "youtube_watchlater_percent": self.youtube_watchlater_percent.value(),
                # Browsing behavior
                "scroll_enabled": self.google_scroll_enabled.isChecked(),
                "scroll_percent": self.google_scroll_percent.value(),
                "scroll_iterations_min": self.google_scroll_iter_min.value(),
                "scroll_iterations_max": self.google_scroll_iter_max.value(),
                "scroll_pixels_min": self.google_scroll_px_min.value(),
                "scroll_pixels_max": self.google_scroll_px_max.value(),
                "scroll_pause_min": self.google_scroll_pause_min.value(),
                "scroll_pause_max": self.google_scroll_pause_max.value(),
                "scroll_down_percent": self.google_scroll_down_percent.value(),
                "click_links_enabled": self.google_click_enabled.isChecked(),
                "click_percent": self.google_click_percent.value(),
                "max_clicks_per_site": self.google_max_clicks.value(),
            }
        self.set_mode_config(mode, cfg)
        self.log(f"[{mode}] Settings saved")
        QMessageBox.information(self, "OK", tr("Settings saved!"))
    
    # === AUTOMATION ===
    def start_automation(self):
        if not self.octo_api:
            QMessageBox.warning(self, "Error", "Not connected")
            return
        
        mode = self.current_mode
        selected = self.get_selected_profiles(mode)
        if not selected:
            QMessageBox.warning(self, "Error", "No profiles selected")
            return
        
        cfg = self.get_mode_config(mode)
        if not cfg.get("sites") and mode == "cookie":
            QMessageBox.warning(self, "Error", "No sites")
            return
        
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        
        # Merge site lists into settings for automation
        settings = cfg.get("settings", {}).copy()
        if mode == "google":
            settings["browse_sites"] = cfg.get("browse_sites", [])
            settings["onetap_sites"] = cfg.get("onetap_sites", [])
            settings["services"] = cfg.get("services", {})
            # Include YouTube checkbox state (stored at cfg level, not in settings)
            settings["youtube_enabled"] = cfg.get("youtube_enabled", True)
        
        # Add global delay settings
        settings["base_delay_min"] = self.config.get("base_delay_min", 1)
        settings["base_delay_max"] = self.config.get("base_delay_max", 3)
        # Add YouTube queries from global settings
        settings["youtube_queries"] = self.config.get("youtube_queries", "")
        # Add geo-visiting settings
        settings["geo_visiting_enabled"] = self.config.get("geo_visiting_enabled", False)
        settings["geo_visiting_percent"] = self.config.get("geo_visiting_percent", 70)
        # Get max parallel profiles from config
        max_parallel = self.config.get("max_parallel_profiles", 5)
        
        # Clear any old pending queue
        self.pending_queue = []
        
        # Get profile info for geo data
        profile_info = cfg.get("profile_info", {})
        
        # Add all selected profiles to queue with their settings
        for uuid in selected:
            # Get profile's country for geo-based visiting
            info = profile_info.get(uuid, {})
            profile_country = info.get("country", "")
            # Normalize country to 2-letter code (country may be full name like "Slovenia")
            if profile_country and len(profile_country) > 2:
                profile_country = normalize_country(profile_country)
            
            # Create a copy of settings with profile-specific country
            profile_settings = settings.copy()
            profile_settings["profile_country"] = profile_country
            
            self.pending_queue.append({
                "uuid": uuid,
                "sites": cfg.get("sites", []),
                "settings": profile_settings,
                "mode": mode
            })
        
        total_profiles = len(self.pending_queue)
        self.log(f"Queued {total_profiles} profiles (max parallel: {max_parallel})")
        
        # Start initial batch up to max_parallel
        self._start_next_workers()
        
        self.status_label.setText(f"Running ({mode}) - {self.running_count}/{total_profiles}")
    
    def _start_next_workers(self):
        """Start workers from queue respecting max_parallel limit."""
        max_parallel = self.config.get("max_parallel_profiles", 5)
        start_minimized = self.config.get("start_minimized", True)
        
        while self.pending_queue and self.running_count < max_parallel:
            item = self.pending_queue.pop(0)
            uuid = item["uuid"]
            
            w = WorkerThread(uuid, item["sites"], item["settings"], self.octo_api, item["mode"], start_minimized)
            w.log_signal.connect(self.log)
            w.finished_signal.connect(self.on_finished)
            w.error_signal.connect(lambda u, e: self.log(f"[{u[:8]}] ERROR: {e}"))
            w.country_detected.connect(self._on_country_detected)
            self.workers[uuid] = w
            self.running_count += 1
            w.start()
            self.log(f"[{uuid[:8]}] Started (running: {self.running_count})")
    
    def _on_country_detected(self, uuid: str, country: str):
        """Save detected country and first_run date to profile info when profile starts."""
        mode = self.current_mode
        cfg = self.get_mode_config(mode)
        profile_info = cfg.setdefault("profile_info", {})
        
        # Get existing info or create new
        existing = profile_info.get(uuid, {})
        existing["country"] = country
        
        # Set first_run only if not already set (preserve original date)
        if not existing.get("first_run"):
            existing["first_run"] = datetime.now().isoformat()
        
        profile_info[uuid] = existing
        self.set_mode_config(mode, cfg)
        self.log(f"[{uuid[:8]}] Country detected: {country}")
        # Refresh list to show new country and age
        self.load_profiles_list(mode)
    
    def stop_automation(self):
        # Clear pending queue
        self.pending_queue = []
        
        for uuid, w in self.workers.items():
            w.stop()
            if self.octo_api:
                self.octo_api.force_stop_profile(uuid)
        self.log("Stopping...")
    
    def on_finished(self, uuid):
        if uuid in self.workers:
            del self.workers[uuid]
            self.running_count = max(0, self.running_count - 1)
            self.log(f"[{uuid[:8]}] Done (running: {self.running_count}, pending: {len(self.pending_queue)})")
        
        # Start next worker from queue
        if self.pending_queue:
            self._start_next_workers()
            total = self.running_count + len(self.pending_queue)
            self.status_label.setText(f"Running - {self.running_count}/{total}")
        elif not self.workers:
            self.start_btn.setEnabled(True)
            self.stop_btn.setEnabled(False)
            self.status_label.setText("Ready")
            self.running_count = 0
            self.log("All done")
            
            # Play sound on completion if enabled
            if self.config.get("sound_on_finish", False):
                self._play_completion_sound()
    
    def _play_completion_sound(self):
        """Play system beep/sound when all tasks complete."""
        try:
            import winsound
            # Play Windows system sound
            winsound.MessageBeep(winsound.MB_OK)
        except ImportError:
            # Not Windows - try other methods
            try:
                # macOS
                os.system('afplay /System/Library/Sounds/Glass.aiff &')
            except:
                try:
                    # Linux
                    os.system('paplay /usr/share/sounds/freedesktop/stereo/complete.oga &')
                except:
                    pass
    
    def _save_log_to_file(self, log_line: str):
        """Save log line to daily log file."""
        try:
            # Create logs folder if not exists
            app_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            logs_dir = os.path.join(app_dir, "logs")
            os.makedirs(logs_dir, exist_ok=True)
            
            # Daily log file: logs/2025-01-15.log
            today = datetime.now().strftime('%Y-%m-%d')
            log_file = os.path.join(logs_dir, f"{today}.log")
            
            with open(log_file, 'a', encoding='utf-8') as f:
                f.write(log_line + '\n')
        except Exception as e:
            print(f"Log save error: {e}")
    
    def closeEvent(self, e):
        self.stop_automation()
        self.save_config()
        e.accept()
