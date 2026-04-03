"""
Profile Item Widget - Custom widget for profile list item
"""
import os
from datetime import datetime
from PyQt5.QtWidgets import (
    QWidget, QHBoxLayout, QLabel, QPushButton, QCheckBox, 
    QMessageBox, QApplication, QGraphicsOpacityEffect
)
from PyQt5.QtCore import Qt, pyqtSignal, QTimer, QPropertyAnimation, QEasingCurve
from PyQt5.QtGui import QPixmap

from core.translator import tr
from gui.styles import (
    CATPPUCCIN, COUNTRY_FLAGS, COUNTRY_NAME_TO_CODE,
    FONT_SIZE_BASE, FONT_SIZE_SMALL, FONT_SIZE_LARGE,
    FLAG_WIDTH, FLAG_HEIGHT
)


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
    play_clicked = pyqtSignal(str)  # Emits UUID when play clicked for manual profile launch
    proxy_check_clicked = pyqtSignal(str)  # Emits UUID when proxy check clicked
    paused_changed = pyqtSignal(str, bool)  # Emits UUID and paused state for auto mode exclusion
    proxy_status_changed = pyqtSignal(str, object)  # Emits UUID and proxy status (True/False/None)
    
    def __init__(self, uuid: str, country: str = "", first_run: str = "", mode: str = "cookie", 
                 google_authorized: bool = False, ads_registered: bool = False,
                 payment_linked: bool = False, campaign_launched: bool = False,
                 profile_ready: bool = False,
                 ads_timestamp: str = "", payment_timestamp: str = "", 
                 campaign_timestamp: str = "", ready_timestamp: str = "",
                 paused: bool = False, proxy_status: object = None,
                 working: bool = False,
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
        # Pause state for auto mode exclusion
        self._paused = paused
        # Proxy status: None = unchecked, True = ok, False = error (restored from DB)
        self._proxy_status = proxy_status
        self._proxy_checking = False
        # Working state: True = profile is running, False = idle/pending
        self._working = working
        
        # Use theme colors
        c = CATPPUCCIN
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(6, 2, 6, 2)
        layout.setSpacing(8)
        
        # Checkbox for selection
        self.checkbox = QCheckBox()
        self.checkbox.stateChanged.connect(self._on_check_changed)
        layout.addWidget(self.checkbox)
        
        # Working status indicator container (white background, no pulse on container)
        self.status_container = QWidget()
        self.status_container.setFixedSize(20, 20)
        self.status_container.setStyleSheet("background: white; border-radius: 3px;")
        
        # Status indicator dot (inside container)
        self.status_indicator = QLabel("●", self.status_container)
        self.status_indicator.setFixedSize(20, 20)
        self.status_indicator.setAlignment(Qt.AlignCenter)
        self.status_indicator.move(0, 0)
        
        # Setup pulse animation for working state (applies only to the dot, not container)
        self._pulse_animation = None
        self._opacity_effect = QGraphicsOpacityEffect(self.status_indicator)
        self.status_indicator.setGraphicsEffect(self._opacity_effect)
        self._opacity_effect.setOpacity(1.0)
        
        self._update_status_indicator()
        layout.addWidget(self.status_container)
        
        # Flag icon using QLabel with pixmap or emoji fallback
        self.flag_label = QLabel()
        flag_loaded = False
        
        if self.country_code:
            # Try to load flag PNG from assets folder
            # Go up 3 levels: gui/widgets/profile_item.py -> gui/widgets -> gui -> project_root
            widget_dir = os.path.dirname(os.path.abspath(__file__))  # gui/widgets
            gui_dir = os.path.dirname(widget_dir)  # gui
            app_dir = os.path.dirname(gui_dir)  # project_root
            flag_path = os.path.join(app_dir, "assets", "flags", f"{self.country_code.lower()}.png")
            if os.path.exists(flag_path):
                pixmap = QPixmap(flag_path)
                if not pixmap.isNull():
                    self.flag_label.setPixmap(pixmap.scaled(FLAG_WIDTH, FLAG_HEIGHT, Qt.KeepAspectRatio, Qt.SmoothTransformation))
                    flag_loaded = True
        
        if not flag_loaded:
            # Fallback to emoji (may not render on Windows)
            flag_emoji = COUNTRY_FLAGS.get(self.country_code, "🌐") if self.country_code else "🌐"
            self.flag_label.setText(flag_emoji)
            self.flag_label.setStyleSheet(f"font-size: {FONT_SIZE_LARGE}px;")
        
        self.flag_label.setFixedWidth(FLAG_WIDTH + 4)
        layout.addWidget(self.flag_label)
        
        # Country code label (e.g., "GB", "NL") - always create, hide if empty
        self.code_label = QLabel(f"({self.country_code})" if self.country_code else "")
        self.code_label.setStyleSheet(f"color: {c['subtext0']}; font-size: {FONT_SIZE_SMALL}px;")
        self.code_label.setFixedWidth(40)
        if not self.country_code:
            self.code_label.hide()
        layout.addWidget(self.code_label)
        
        # Pause/Play button for auto mode exclusion (between country code and UUID)
        self.pause_btn = QPushButton("⏸" if not self._paused else "▶")
        self.pause_btn.setFixedSize(36, 30)
        self._update_pause_btn_style()
        self.pause_btn.clicked.connect(self._on_pause_click)
        layout.addWidget(self.pause_btn)
        
        # UUID label (truncated)
        self.uuid_label = QLabel(f"{uuid[:8]}...")
        self.uuid_label.setStyleSheet(f"font-size: {FONT_SIZE_BASE}px; font-family: 'Cascadia Code', 'Consolas', monospace;")
        self.uuid_label.setToolTip(uuid)
        layout.addWidget(self.uuid_label, 1)
        
        # Button dimensions for profile row - increased for better visibility
        btn_w, btn_h = 40, 30
        
        # Google authorization button (only for cookie mode)
        if mode == "cookie":
            self.google_btn = QPushButton("G")
            self.google_btn.setFixedSize(btn_w, btn_h)
            self.google_btn.setToolTip(tr("Google authorization status"))
            self._update_google_btn_style()
            self.google_btn.clicked.connect(self._on_google_click)
            layout.addWidget(self.google_btn)
        
        # Google mode buttons: Ads, Payment, Campaign, Ready
        if mode == "google":
            # Google Ads registration button
            self.ads_btn = QPushButton("Ads")
            self.ads_btn.setFixedSize(52, btn_h)
            self._update_ads_btn_style()
            self.ads_btn.clicked.connect(self._on_ads_click)
            layout.addWidget(self.ads_btn)
            
            # Payment method button
            self.payment_btn = QPushButton("💳")
            self.payment_btn.setFixedSize(btn_w, btn_h)
            self._update_payment_btn_style()
            self.payment_btn.clicked.connect(self._on_payment_click)
            layout.addWidget(self.payment_btn)
            
            # Ad campaign button (РК = Рекламная Кампания in Russian)
            self.campaign_btn = QPushButton(tr("Ad"))
            self.campaign_btn.setFixedSize(btn_w, btn_h)
            self._update_campaign_btn_style()
            self.campaign_btn.clicked.connect(self._on_campaign_click)
            layout.addWidget(self.campaign_btn)
            
            # Profile ready button (profile warmed up and ready)
            self.ready_btn = QPushButton("✓")
            self.ready_btn.setFixedSize(btn_w, btn_h)
            self._update_ready_btn_style()
            self.ready_btn.clicked.connect(self._on_ready_click)
            layout.addWidget(self.ready_btn)
        
        # Migration button (only for cookie mode) - arrow pointing right
        if mode == "cookie":
            self.migrate_btn = QPushButton("→")
            self.migrate_btn.setFixedSize(btn_w, btn_h)
            self.migrate_btn.setToolTip(tr("Migrate to Google mode"))
            self.migrate_btn.setStyleSheet(f"font-size: 16px; padding: 0px;")
            self.migrate_btn.clicked.connect(self._on_migrate)
            layout.addWidget(self.migrate_btn)
        
        # Profile age in days (from first run)
        age_text = self._calculate_age()
        self.age_label = QLabel(age_text)
        self.age_label.setStyleSheet(f"color: {c['subtext0']}; font-size: {FONT_SIZE_SMALL}px;")
        self.age_label.setFixedWidth(60)
        self.age_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        if self.first_run:
            self.age_label.setToolTip(f"First run: {self.first_run}")
        layout.addWidget(self.age_label)
        
        # Proxy check button
        self.proxy_btn = QPushButton("⇄")
        self.proxy_btn.setFixedSize(btn_w, btn_h)
        self.proxy_btn.setToolTip(tr("Check proxy"))
        # Note: _proxy_status and _proxy_checking are initialized in __init__ above
        self.proxy_btn.clicked.connect(self._on_proxy_check)
        layout.addWidget(self.proxy_btn)
        
        # Proxy warning label (hidden by default) - must be created before _update_proxy_btn_style
        self.proxy_warning = QLabel("⚠")
        self.proxy_warning.setStyleSheet(f"color: {c['red']}; font-size: {FONT_SIZE_BASE}px; font-weight: bold;")
        self.proxy_warning.setFixedWidth(20)
        self.proxy_warning.setToolTip(tr("Proxy error"))
        self.proxy_warning.hide()
        layout.addWidget(self.proxy_warning)
        
        # Now update style (after proxy_warning is created)
        self._update_proxy_btn_style()
        
        # Copy button
        self.copy_btn = QPushButton("📋")
        self.copy_btn.setFixedSize(btn_w, btn_h)
        self.copy_btn.setToolTip(tr("Copy UUID"))
        self.copy_btn.setStyleSheet(f"""
            QPushButton {{
                font-size: 14px;
                padding: 0px;
                border: 1px solid {c['surface1']};
                border-radius: 4px;
                background: white;
            }}
            QPushButton:hover {{
                background: {c['surface0']};
            }}
        """)
        self.copy_btn.clicked.connect(self._on_copy)
        layout.addWidget(self.copy_btn)
        
        # Play button - manual profile launch without bot logic
        self.play_btn = QPushButton("↗")
        self.play_btn.setFixedSize(btn_w, btn_h)
        self.play_btn.setToolTip(tr("Open profile manually"))
        c = CATPPUCCIN
        self.play_btn.setStyleSheet(f"""
            QPushButton {{
                font-size: 16px;
                font-weight: bold;
                color: {c['green']};
                border: 2px solid {c['green']};
                border-radius: 4px;
                background: transparent;
                padding: 0px;
            }}
            QPushButton:hover {{
                background: rgba(64, 160, 43, 0.15);
                border-color: #2d8a1e;
                color: #2d8a1e;
            }}
        """)
        self.play_btn.clicked.connect(self._on_play)
        layout.addWidget(self.play_btn)
        
        # Track if profile is manually running
        self._is_manually_running = False
    
    def set_manually_running(self, running: bool):
        """Set the manual running state and update Play button appearance."""
        self._is_manually_running = running
        c = CATPPUCCIN
        if running:
            # Red color - profile is running
            self.play_btn.setText("⏹")
            self.play_btn.setStyleSheet(f"""
                QPushButton {{
                    font-size: 14px;
                    color: {c['red']};
                    border: 1px solid {c['red']};
                    border-radius: 4px;
                    background: rgba(243, 139, 168, 0.1);
                    padding: 0px;
                }}
                QPushButton:hover {{
                    background: rgba(243, 139, 168, 0.25);
                }}
            """)
            self.play_btn.setToolTip(tr("Profile is running (click to stop)"))
        else:
            # Green color - ready to start
            self.play_btn.setText("↗")
            self.play_btn.setStyleSheet(f"""
                QPushButton {{
                    font-size: 18px;
                    font-weight: bold;
                    color: {c['green']};
                    border: 2px solid {c['green']};
                    border-radius: 4px;
                    background: transparent;
                }}
                QPushButton:hover {{
                    background: rgba(64, 160, 43, 0.15);
                    border-color: #2d8a1e;
                    color: #2d8a1e;
                }}
            """)
            self.play_btn.setToolTip(tr("Open profile manually"))
    
    def is_manually_running(self) -> bool:
        """Check if profile is manually running."""
        return self._is_manually_running
    
    def _start_pulse_animation(self):
        """Start pulsing animation for working indicator."""
        if self._pulse_animation is not None:
            self._pulse_animation.stop()
        
        self._pulse_animation = QPropertyAnimation(self._opacity_effect, b"opacity")
        self._pulse_animation.setDuration(1000)  # 1 second per cycle
        self._pulse_animation.setStartValue(1.0)
        self._pulse_animation.setKeyValueAt(0.5, 0.3)  # Fade to 30% at midpoint
        self._pulse_animation.setEndValue(1.0)
        self._pulse_animation.setEasingCurve(QEasingCurve.InOutSine)
        self._pulse_animation.setLoopCount(-1)  # Infinite loop
        self._pulse_animation.start()
    
    def _stop_pulse_animation(self):
        """Stop pulsing animation."""
        if self._pulse_animation is not None:
            self._pulse_animation.stop()
            self._pulse_animation = None
        self._opacity_effect.setOpacity(1.0)
    
    def _update_status_indicator(self):
        """Update the working status indicator (bright green pulsing dot = working, light gray = idle)."""
        if self._working:
            # Bright green pulsing dot - profile is working
            self.status_indicator.setText("●")
            self.status_indicator.setStyleSheet(f"""
                QLabel {{
                    color: #4ADE80;
                    font-size: 16px;
                    font-weight: bold;
                    background: transparent;
                }}
            """)
            self.status_indicator.setToolTip(tr("Working - profile is running"))
            self._start_pulse_animation()
        else:
            # Light gray filled dot - profile is idle/pending
            self._stop_pulse_animation()
            self.status_indicator.setText("●")
            self.status_indicator.setStyleSheet(f"""
                QLabel {{
                    color: #D1D5DB;
                    font-size: 16px;
                    background: transparent;
                }}
            """)
            self.status_indicator.setToolTip(tr("Idle - waiting"))
    
    def set_working(self, working: bool):
        """Set the working state and update indicator."""
        self._working = working
        self._update_status_indicator()
    
    def is_working(self) -> bool:
        """Check if profile is currently working."""
        return self._working
    
    def _update_proxy_btn_style(self):
        """Update proxy button style based on status."""
        c = CATPPUCCIN
        if self._proxy_checking:
            self.proxy_btn.setText("...")
            self.proxy_btn.setStyleSheet(f"""
                QPushButton {{
                    color: {c['overlay0']};
                    border: 1px solid {c['overlay0']};
                    border-radius: 4px;
                    background: transparent;
                    font-size: 12px;
                    padding: 0px;
                }}
            """)
            self.proxy_btn.setToolTip(tr("Checking proxy..."))
            self.proxy_warning.hide()
        elif self._proxy_status is None:
            self.proxy_btn.setText("⇄")
            self.proxy_btn.setStyleSheet(f"""
                QPushButton {{
                    color: {c['overlay0']};
                    border: 1px solid {c['surface2']};
                    border-radius: 4px;
                    background: transparent;
                    font-size: 14px;
                    padding: 0px;
                }}
                QPushButton:hover {{
                    background: rgba(108, 112, 134, 0.15);
                }}
            """)
            self.proxy_btn.setToolTip(tr("Check proxy"))
            self.proxy_warning.hide()
        elif self._proxy_status:
            self.proxy_btn.setText("⇄")
            self.proxy_btn.setStyleSheet(f"""
                QPushButton {{
                    color: {c['green']};
                    border: 1px solid {c['green']};
                    border-radius: 4px;
                    background: transparent;
                    font-size: 14px;
                    padding: 0px;
                }}
                QPushButton:hover {{
                    background: rgba(166, 227, 161, 0.15);
                }}
            """)
            self.proxy_btn.setToolTip(tr("Proxy OK (click to recheck)"))
            self.proxy_warning.hide()
        else:
            self.proxy_btn.setText("⇄")
            self.proxy_btn.setStyleSheet(f"""
                QPushButton {{
                    color: {c['red']};
                    border: 1px solid {c['red']};
                    border-radius: 4px;
                    background: rgba(243, 139, 168, 0.1);
                    font-size: 14px;
                    padding: 0px;
                }}
                QPushButton:hover {{
                    background: rgba(243, 139, 168, 0.25);
                }}
            """)
            self.proxy_btn.setToolTip(tr("Proxy error (click to recheck)"))
            self.proxy_warning.show()
    
    def set_proxy_checking(self, checking: bool):
        """Set proxy checking state."""
        self._proxy_checking = checking
        self._update_proxy_btn_style()
    
    def set_proxy_status(self, success: bool, message: str = ""):
        """Set proxy check result and emit signal to persist state."""
        self._proxy_checking = False
        self._proxy_status = success
        if message:
            if success:
                self.proxy_btn.setToolTip(f"Proxy OK: {message}")
            else:
                self.proxy_btn.setToolTip(f"Proxy error: {message}")
                self.proxy_warning.setToolTip(f"Error: {message}")
        self._update_proxy_btn_style()
        # Emit signal to save state to database
        self.proxy_status_changed.emit(self.uuid, success)
    
    def get_proxy_status(self):
        """Get current proxy status."""
        return self._proxy_status
    
    def _on_proxy_check(self):
        """Handle proxy check button click."""
        if not self._proxy_checking:
            self.proxy_check_clicked.emit(self.uuid)
    
    # === Pause/Play button for Auto mode exclusion ===
    def _update_pause_btn_style(self):
        """Update pause button style based on paused state."""
        c = CATPPUCCIN
        if self._paused:
            self.pause_btn.setText("▶")
            self.pause_btn.setStyleSheet(f"""
                QPushButton {{
                    font-size: 14px;
                    color: {c['peach']};
                    border: 1px solid {c['peach']};
                    border-radius: 4px;
                    background: rgba(250, 179, 135, 0.1);
                    padding: 0px;
                }}
                QPushButton:hover {{
                    background: rgba(250, 179, 135, 0.25);
                }}
            """)
            self.pause_btn.setToolTip(tr("Profile paused (excluded from Auto mode). Click to resume."))
        else:
            self.pause_btn.setText("⏸")
            self.pause_btn.setStyleSheet(f"""
                QPushButton {{
                    font-size: 14px;
                    color: {c['overlay0']};
                    border: 1px solid {c['surface2']};
                    border-radius: 4px;
                    background: transparent;
                    padding: 0px;
                }}
                QPushButton:hover {{
                    background: rgba(108, 112, 134, 0.15);
                }}
            """)
            self.pause_btn.setToolTip(tr("Profile active in Auto mode. Click to pause."))
    
    def _on_pause_click(self):
        """Handle pause button click - toggle paused state."""
        self._paused = not self._paused
        self._update_pause_btn_style()
        self.paused_changed.emit(self.uuid, self._paused)
    
    def is_paused(self) -> bool:
        """Check if profile is paused (excluded from Auto mode)."""
        return self._paused
    
    def set_paused(self, paused: bool):
        """Set paused state without emitting signal (for loading from DB)."""
        self._paused = paused
        self._update_pause_btn_style()
    
    def _update_google_btn_style(self):
        """Update Google button style based on authorization state."""
        c = CATPPUCCIN
        if self.google_authorized:
            self.google_btn.setStyleSheet(f"""
                QPushButton {{
                    font-size: 13px;
                    font-weight: bold;
                    color: {c['blue']};
                    border: 2px solid {c['blue']};
                    border-radius: 4px;
                    background: transparent;
                    padding: 0px;
                }}
                QPushButton:hover {{
                    background: rgba(137, 180, 250, 0.15);
                }}
            """)
            self.google_btn.setToolTip(tr("Google authorized") + " ✓")
        else:
            self.google_btn.setStyleSheet(f"""
                QPushButton {{
                    font-size: 13px;
                    font-weight: bold;
                    color: {c['overlay0']};
                    border: 2px solid {c['surface1']};
                    border-radius: 4px;
                    background: transparent;
                    padding: 0px;
                }}
                QPushButton:hover {{
                    background: rgba(108, 112, 134, 0.1);
                }}
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
        c = CATPPUCCIN
        if self.ads_registered:
            self.ads_btn.setStyleSheet(f"""
                QPushButton {{
                    font-size: 11px;
                    font-weight: bold;
                    color: {c['yellow']};
                    border: 2px solid {c['yellow']};
                    border-radius: 4px;
                    background: transparent;
                    padding: 0px;
                }}
                QPushButton:hover {{ background: rgba(249, 226, 175, 0.15); }}
            """)
            time_ago = self._format_time_ago(self.ads_timestamp)
            self.ads_btn.setToolTip(tr("Google Ads registered") + f" ✓{time_ago}")
        else:
            self.ads_btn.setStyleSheet(f"""
                QPushButton {{
                    font-size: 11px;
                    font-weight: bold;
                    color: {c['overlay0']};
                    border: 2px solid {c['surface1']};
                    border-radius: 4px;
                    background: transparent;
                    padding: 0px;
                }}
                QPushButton:hover {{ background: rgba(108, 112, 134, 0.1); }}
            """)
            self.ads_btn.setToolTip(tr("Google Ads not registered"))
    
    def _update_payment_btn_style(self):
        """Update payment button style based on link state."""
        c = CATPPUCCIN
        if self.payment_linked:
            self.payment_btn.setStyleSheet(f"""
                QPushButton {{
                    font-size: 14px;
                    color: {c['green']};
                    border: 2px solid {c['green']};
                    border-radius: 4px;
                    background: transparent;
                    padding: 0px;
                }}
                QPushButton:hover {{ background: rgba(166, 227, 161, 0.15); }}
            """)
            time_ago = self._format_time_ago(self.payment_timestamp)
            self.payment_btn.setToolTip(tr("Payment method linked") + f" ✓{time_ago}")
        else:
            self.payment_btn.setStyleSheet(f"""
                QPushButton {{
                    font-size: 14px;
                    color: {c['overlay0']};
                    border: 2px solid {c['surface1']};
                    border-radius: 4px;
                    background: transparent;
                    padding: 0px;
                }}
                QPushButton:hover {{ background: rgba(108, 112, 134, 0.1); }}
            """)
            self.payment_btn.setToolTip(tr("Payment method not linked"))
    
    def _update_campaign_btn_style(self):
        """Update campaign button style based on launch state."""
        c = CATPPUCCIN
        if self.campaign_launched:
            self.campaign_btn.setStyleSheet(f"""
                QPushButton {{
                    font-size: 11px;
                    font-weight: bold;
                    color: {c['red']};
                    border: 2px solid {c['red']};
                    border-radius: 4px;
                    background: transparent;
                    padding: 0px;
                }}
                QPushButton:hover {{ background: rgba(243, 139, 168, 0.15); }}
            """)
            time_ago = self._format_time_ago(self.campaign_timestamp)
            self.campaign_btn.setToolTip(tr("Ad campaign launched") + f" ✓{time_ago}")
        else:
            self.campaign_btn.setStyleSheet(f"""
                QPushButton {{
                    font-size: 11px;
                    font-weight: bold;
                    color: {c['overlay0']};
                    border: 2px solid {c['surface1']};
                    border-radius: 4px;
                    background: transparent;
                    padding: 0px;
                }}
                QPushButton:hover {{ background: rgba(108, 112, 134, 0.1); }}
            """)
            self.campaign_btn.setToolTip(tr("Ad campaign not launched"))
    
    def _update_ready_btn_style(self):
        """Update ready button style based on profile ready state."""
        c = CATPPUCCIN
        if self.profile_ready:
            self.ready_btn.setStyleSheet(f"""
                QPushButton {{
                    font-size: 14px;
                    font-weight: bold;
                    color: {c['teal']};
                    border: 2px solid {c['teal']};
                    border-radius: 4px;
                    background: transparent;
                    padding: 0px;
                }}
                QPushButton:hover {{ background: rgba(148, 226, 213, 0.15); }}
            """)
            time_ago = self._format_time_ago(self.ready_timestamp)
            self.ready_btn.setToolTip(tr("Profile warmed up and ready") + f" ✓{time_ago}")
        else:
            self.ready_btn.setStyleSheet(f"""
                QPushButton {{
                    font-size: 14px;
                    font-weight: bold;
                    color: {c['overlay0']};
                    border: 2px solid {c['surface1']};
                    border-radius: 4px;
                    background: transparent;
                    padding: 0px;
                }}
                QPushButton:hover {{ background: rgba(108, 112, 134, 0.1); }}
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
    
    def _on_play(self):
        """Emit signal to open profile manually without bot logic."""
        self.play_clicked.emit(self.uuid)
    
    def _on_check_changed(self, state):
        self.check_changed.emit(self.uuid, state == Qt.Checked)
    
    def setChecked(self, checked: bool):
        self.checkbox.setChecked(checked)
    
    def isChecked(self) -> bool:
        return self.checkbox.isChecked()
