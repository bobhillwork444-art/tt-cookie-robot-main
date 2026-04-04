"""
TT Cookie Robot - GUI for Octo Browser automation
Two modes: Cookie Mode and Google Warm-up Mode
"""
import json
import asyncio
import os
import logging
import random
from datetime import datetime
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QTabWidget,
    QLabel, QPushButton, QLineEdit, QTextEdit, QListWidget, QListWidgetItem,
    QCheckBox, QGroupBox, QFormLayout, QMessageBox, QFileDialog,
    QStackedWidget, QFrame, QScrollArea, QSplitter, QApplication,
    QSizePolicy, QProgressDialog
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QSize, pyqtSlot, QTimer
from PyQt5.QtGui import QFont, QPixmap

from core.octo_api import OctoAPI
from core.octo_api_async import OctoApiManager
from core.browser import BrowserAutomation
from core.translator import load_translation, tr
from core.auto_state import AutoStateManager
from core.notifications import NotificationManager, NotificationType
from core.auto_scheduler import AutoScheduler, ProfileStatus
from core.database import get_database, DatabaseManager

# Import refactored components
from gui.styles import (
    CATPPUCCIN, COUNTRY_NAME_TO_CODE, COUNTRY_FLAGS,
    COUNTRY_TO_TLD, EU_TLDS, GENERIC_TLDS,
    UI_SCALE, WINDOW_MIN_WIDTH, WINDOW_MIN_HEIGHT,
    FONT_SIZE_BASE, FONT_SIZE_SMALL, FONT_SIZE_LARGE, FONT_SIZE_TITLE,
    ICON_SIZE, BUTTON_HEIGHT, BUTTON_MIN_WIDTH, INPUT_HEIGHT,
    SPACING, MARGIN, BORDER_RADIUS, PROFILE_ROW_HEIGHT,
    FLAG_WIDTH, FLAG_HEIGHT,
    normalize_country, get_site_tld, get_site_geo_category,
    get_theme_stylesheet
)
from gui.widgets.profile_item import ProfileItemWidget
from gui.widgets.worker_thread import WorkerThread
from gui.widgets.no_scroll import NoScrollSpinBox as QSpinBox, NoScrollDoubleSpinBox as QDoubleSpinBox, NoScrollComboBox as QComboBox


class DownloadThread(QThread):
    """Thread for downloading updates without blocking UI."""
    progress = pyqtSignal(int, str)  # percent, status
    finished_signal = pyqtSignal(str, str)  # file_path, version
    error = pyqtSignal(str)  # error_message
    
    def __init__(self, download_url: str, version: str):
        super().__init__()
        self.download_url = download_url
        self.version = version
        self._cancelled = False
    
    def cancel(self):
        """Request cancellation."""
        self._cancelled = True
    
    def run(self):
        """Download the update file."""
        import tempfile
        import os
        from urllib.request import urlopen, Request
        
        try:
            # Determine file extension
            if self.download_url.endswith(".dmg"):
                ext = ".dmg"
            elif self.download_url.endswith(".zip"):
                ext = ".zip"
            else:
                ext = ".exe"
            
            # Create temp file
            temp_dir = tempfile.gettempdir()
            temp_file = os.path.join(temp_dir, f"TTCookieRobot_Update_{self.version}{ext}")
            
            # Build request
            headers = {"User-Agent": "TT-Cookie-Robot-Updater"}
            request = Request(self.download_url, headers=headers)
            
            self.progress.emit(0, "Connecting...")
            
            # Download with progress
            with urlopen(request, timeout=300) as response:
                total_size = int(response.headers.get("Content-Length", 0))
                downloaded = 0
                chunk_size = 65536  # 64KB chunks
                
                with open(temp_file, "wb") as f:
                    while True:
                        if self._cancelled:
                            self.progress.emit(0, "Cancelled")
                            return
                        
                        chunk = response.read(chunk_size)
                        if not chunk:
                            break
                        
                        f.write(chunk)
                        downloaded += len(chunk)
                        
                        if total_size > 0:
                            percent = int(downloaded * 100 / total_size)
                            size_mb = downloaded / (1024 * 1024)
                            total_mb = total_size / (1024 * 1024)
                            self.progress.emit(percent, f"Downloading: {size_mb:.1f}/{total_mb:.1f} MB")
            
            self.progress.emit(100, "Download complete")
            self.finished_signal.emit(temp_file, self.version)
            
        except Exception as e:
            self.error.emit(str(e))


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.config = self.load_config()
        self.octo_api = None
        self.api_manager = None  # Async API manager (initialized when connected)
        self.workers = {}
        self.current_mode = "cookie"
        self.pending_queue = []  # Queue of profiles waiting to start
        self.running_count = 0   # Number of currently running profiles
        
        # Progress dialog for async operations
        self._async_progress_dialog = None
        self._current_async_task = None
        
        # Initialize Auto Mode managers
        app_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.auto_state = AutoStateManager(app_dir)
        self.notifications = NotificationManager(app_dir)
        self.notifications.on_change(self._update_notification_badge)
        
        # Initialize Auto Mode scheduler (with auto_state for persistence)
        self.auto_scheduler = AutoScheduler(auto_state=self.auto_state)
        self.auto_workers = {}  # Workers running in auto mode {uuid: worker}
        self.auto_scheduler_timer = None
        self._manually_running_profiles = set()  # Profiles opened manually via Play button
        self._manual_profile_start_times = {}  # UUID -> start timestamp for grace period
        
        # Load language from config
        self.current_language = self.config.get("language", "English")
        self.current_theme = "Light"  # Always use Light theme
        
        # Load translation before building UI
        app_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        load_translation(self.current_language, app_dir)
        
        # Import QTimer early (needed for all timers)
        from PyQt5.QtCore import QTimer
        
        # Debounced save timer - MUST init before _reset_all_working_states which calls save_config
        self._save_pending = False
        self._save_timer = QTimer(self)
        self._save_timer.setSingleShot(True)
        self._save_timer.timeout.connect(self._do_save_config)
        
        self.init_ui()
        self.apply_theme("Light")
        
        # Reset all working states on startup (in case app was closed while running)
        self._reset_all_working_states()
        
        # Set initial mode to update button text (START TEST / STOP TEST)
        self.switch_mode("cookie")
        
        # Start clock update timer (every 30 seconds)
        self.clock_timer = QTimer(self)
        self.clock_timer.timeout.connect(self._update_world_clock)
        self.clock_timer.start(30000)  # 30 seconds
        
        # Timer to check manually running profiles status (every 3 seconds)
        self._manual_profile_check_timer = QTimer(self)
        self._manual_profile_check_timer.timeout.connect(self._check_manual_profiles_status)
        self._manual_profile_check_timer.start(3000)  # 3 seconds
        
        # Check for updates on startup (after 3 seconds delay)
        QTimer.singleShot(3000, self._check_updates_on_startup)
    
    def _check_updates_on_startup(self):
        """Check for updates silently on startup."""
        from PyQt5.QtWidgets import QMessageBox
        
        try:
            from core.updater import UpdateChecker
            from version import VERSION
            
            checker = UpdateChecker()
            result = checker.check_sync()
            
            if result.get("available"):
                new_version = result["version"]
                
                reply = QMessageBox.question(
                    self,
                    tr("Update Available"),
                    f"🎉 {tr('New version available')}: v{new_version}\n"
                    f"{tr('Current version')}: v{VERSION}\n\n"
                    f"{tr('Do you want to download and install the update?')}",
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.No
                )
                
                if reply == QMessageBox.Yes:
                    self._start_download_update(result)
        except Exception as e:
            # Silent fail on startup
            logging.debug(f"Update check failed: {e}")
        
    def init_ui(self):
        self.setWindowTitle("TT Cookie Robot")
        self.setMinimumSize(WINDOW_MIN_WIDTH, WINDOW_MIN_HEIGHT)
        self.resize(WINDOW_MIN_WIDTH, WINDOW_MIN_HEIGHT)
        
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setSpacing(SPACING)
        main_layout.setContentsMargins(MARGIN, MARGIN, MARGIN, MARGIN)
        
        # === TOP BAR: Connection + Mode ===
        top_bar = QHBoxLayout()
        top_bar.setSpacing(SPACING)
        
        # Refresh all proxies button (left of API URL)
        self.refresh_all_btn = QPushButton("🔄")
        self.refresh_all_btn.setFixedSize(44, 40)
        self.refresh_all_btn.setStyleSheet(f"font-size: 18px; padding: 2px;")
        self.refresh_all_btn.setToolTip(tr("Refresh all proxies & update geo"))
        self.refresh_all_btn.clicked.connect(self._refresh_all_proxies_and_geo)
        top_bar.addWidget(self.refresh_all_btn)
        
        # Connection
        api_label = QLabel("API:")
        api_label.setStyleSheet(f"font-size: {FONT_SIZE_BASE}px; font-weight: 600;")
        top_bar.addWidget(api_label)
        self.api_url_input = QLineEdit()
        self.api_url_input.setText(self.config.get("api_url", "http://localhost:58888"))
        self.api_url_input.setFixedWidth(220)
        self.api_url_input.setFixedHeight(INPUT_HEIGHT)
        top_bar.addWidget(self.api_url_input)
        
        self.connect_btn = QPushButton(tr("Connect"))
        self.connect_btn.setMinimumWidth(BUTTON_MIN_WIDTH)
        self.connect_btn.setFixedHeight(BUTTON_HEIGHT)
        self.connect_btn.clicked.connect(self.connect_to_octo)
        top_bar.addWidget(self.connect_btn)
        
        self.connection_status = QLabel("●")
        self.connection_status.setStyleSheet(f"color: {CATPPUCCIN['red']}; font-size: {FONT_SIZE_LARGE}px;")
        self.connection_status.setFixedWidth(24)
        top_bar.addWidget(self.connection_status)
        
        top_bar.addStretch()
        
        # Mode buttons
        self.mode_label = QLabel(tr("Mode:"))
        self.mode_label.setStyleSheet(f"font-size: {FONT_SIZE_BASE}px; font-weight: 600;")
        top_bar.addWidget(self.mode_label)
        
        self.cookie_mode_btn = QPushButton("🍪 Cookie")
        self.cookie_mode_btn.setCheckable(True)
        self.cookie_mode_btn.setChecked(True)
        self.cookie_mode_btn.setMinimumWidth(120)
        self.cookie_mode_btn.setFixedHeight(BUTTON_HEIGHT)
        self.cookie_mode_btn.clicked.connect(lambda: self.switch_mode("cookie"))
        top_bar.addWidget(self.cookie_mode_btn)
        
        self.google_mode_btn = QPushButton("📧 Google")
        self.google_mode_btn.setCheckable(True)
        self.google_mode_btn.setMinimumWidth(120)
        self.google_mode_btn.setFixedHeight(BUTTON_HEIGHT)
        self.google_mode_btn.clicked.connect(lambda: self.switch_mode("google"))
        top_bar.addWidget(self.google_mode_btn)
        
        self.auto_mode_btn = QPushButton("🤖 Auto")
        self.auto_mode_btn.setCheckable(True)
        self.auto_mode_btn.setMinimumWidth(120)
        self.auto_mode_btn.setFixedHeight(BUTTON_HEIGHT)
        self.auto_mode_btn.clicked.connect(lambda: self.switch_mode("auto"))
        top_bar.addWidget(self.auto_mode_btn)
        
        # Global settings button
        self.global_settings_btn = QPushButton("⚙️")
        self.global_settings_btn.setFixedSize(44, 40)
        self.global_settings_btn.setStyleSheet(f"font-size: 18px; padding: 2px;")
        self.global_settings_btn.setToolTip(tr("Global Settings"))
        self.global_settings_btn.clicked.connect(self.show_global_settings)
        top_bar.addWidget(self.global_settings_btn)
        
        # Notifications button with badge
        self.notifications_btn = QPushButton("🔔")
        self.notifications_btn.setFixedSize(50, 40)
        self.notifications_btn.setToolTip(tr("Notifications"))
        self.notifications_btn.clicked.connect(self.show_notifications)
        self.notifications_btn.setStyleSheet("font-size: 22px; padding: 0px; border: none;")
        top_bar.addWidget(self.notifications_btn)
        self._update_notification_badge()
        
        main_layout.addLayout(top_bar)
        
        # === MAIN CONTENT: Stacked modes ===
        self.mode_stack = QStackedWidget()
        self.mode_stack.addWidget(self.create_cookie_mode())
        self.mode_stack.addWidget(self.create_google_mode())
        self.mode_stack.addWidget(self.create_auto_mode())
        main_layout.addWidget(self.mode_stack, 1)
        
        # === CONTROL BUTTONS ===
        control_layout = QHBoxLayout()
        control_layout.setSpacing(SPACING)
        
        c = CATPPUCCIN
        self.start_btn = QPushButton("▶ " + tr("START"))
        self.start_btn.setMinimumHeight(50)
        self.start_btn.setEnabled(False)
        self.start_btn.clicked.connect(self.start_automation)
        self.start_btn.setStyleSheet(f"""
            QPushButton {{ 
                background-color: {c['green']}; 
                color: {c['crust']}; 
                font-weight: bold; 
                font-size: {FONT_SIZE_LARGE}px;
                border-radius: {BORDER_RADIUS}px;
            }}
            QPushButton:hover {{ background-color: #96D391; }}
            QPushButton:disabled {{ background-color: {c['surface1']}; color: {c['overlay0']}; }}
        """)
        control_layout.addWidget(self.start_btn)
        
        self.stop_btn = QPushButton("⏹ " + tr("STOP"))
        self.stop_btn.setMinimumHeight(50)
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(lambda: self.stop_automation(sync=False))
        self.stop_btn.setStyleSheet(f"""
            QPushButton {{ 
                background-color: {c['red']}; 
                color: {c['crust']}; 
                font-weight: bold; 
                font-size: {FONT_SIZE_LARGE}px;
                border-radius: {BORDER_RADIUS}px;
            }}
            QPushButton:hover {{ background-color: #E37B98; }}
            QPushButton:disabled {{ background-color: {c['surface1']}; color: {c['overlay0']}; }}
        """)
        control_layout.addWidget(self.stop_btn)
        
        main_layout.addLayout(control_layout)
        
        # === STATUS ===
        self.status_label = QLabel(tr("Ready"))
        self.status_label.setStyleSheet(f"color: {CATPPUCCIN['subtext0']}; font-size: {FONT_SIZE_BASE}px;")
        main_layout.addWidget(self.status_label)
        
        # === LOGS ===
        self.log_area = QTextEdit()
        self.log_area.setReadOnly(True)
        self.log_area.setMinimumHeight(160)
        self.log_area.setMaximumHeight(200)
        self.log_area.setFont(QFont("Cascadia Code", 11))
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
                btn.setFixedSize(40, 36)
                btn.setStyleSheet("font-size: 16px; padding: 2px;")
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
        save_btn.setStyleSheet("min-height: 36px;")
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
        info.setStyleSheet(f"color: {CATPPUCCIN['subtext0']}; font-size: {FONT_SIZE_SMALL}px;")
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
                btn.setFixedSize(40, 36)
                btn.setStyleSheet("font-size: 16px; padding: 2px;")
                btn.setToolTip(tr("Refresh proxy info"))
            btn_layout.addWidget(btn)
        layout.addLayout(btn_layout)
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
        sites_label.setStyleSheet(f"font-weight: bold; font-size: 16px; color: {CATPPUCCIN['blue']};")
        layout.addWidget(sites_label)
        
        sites_info = QLabel(tr("Sites for browsing without Google authorization"))
        sites_info.setStyleSheet(f"color: {CATPPUCCIN['subtext0']}; font-size: {FONT_SIZE_SMALL}px;")
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
        onetap_label.setStyleSheet(f"font-weight: bold; font-size: 16px; color: {CATPPUCCIN['blue']}; margin-top: 10px;")
        layout.addWidget(onetap_label)
        
        onetap_info = QLabel(tr("Sites where bot will authorize via Google One Tap"))
        onetap_info.setStyleSheet(f"color: {CATPPUCCIN['subtext0']}; font-size: {FONT_SIZE_SMALL}px;")
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
        youtube_section_label.setStyleSheet(f"font-weight: bold; font-size: 16px; color: {CATPPUCCIN['blue']}; margin-top: 10px;")
        layout.addWidget(youtube_section_label)
        
        self.google_youtube_checkbox = QCheckBox(tr("Add YouTube to session"))
        self.google_youtube_checkbox.setChecked(self.get_mode_config("google").get("youtube_enabled", True))
        self.google_youtube_checkbox.stateChanged.connect(self._on_youtube_checkbox_changed)
        layout.addWidget(self.google_youtube_checkbox)
        
        # === SECTION 3: Google Services ===
        services_label = QLabel(tr("📊 Google Services"))
        services_label.setStyleSheet(f"font-weight: bold; font-size: 16px; color: {CATPPUCCIN['blue']}; margin-top: 10px;")
        layout.addWidget(services_label)
        
        services_info = QLabel(tr("Google services to visit during session"))
        services_info.setStyleSheet(f"color: {CATPPUCCIN['subtext0']}; font-size: {FONT_SIZE_SMALL}px;")
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
        sites_label.setStyleSheet(f"font-weight: bold; font-size: 16px; color: {CATPPUCCIN['blue']}; margin-top: 5px;")
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
        
        # === ONE TAP SITES SECTION ===
        onetap_section_label = QLabel(tr("🔐 One Tap Sites"))
        onetap_section_label.setStyleSheet(f"font-weight: bold; font-size: 16px; color: {CATPPUCCIN['blue']}; margin-top: 10px;")
        layout.addRow(onetap_section_label)
        
        # Checkbox: Visit One Tap sites
        self.onetap_visit_enabled = QCheckBox(tr("Visit One Tap sites"))
        self.onetap_visit_enabled.setChecked(self.get_mode_config("google").get("settings", {}).get("onetap_visit_enabled", True))
        self.onetap_visit_enabled.setToolTip(tr("Enable visiting sites with Google One Tap authorization"))
        layout.addRow(self.onetap_visit_enabled)
        
        # Range: One Tap sites per session (min-max)
        onetap_per_session_layout = QHBoxLayout()
        self.onetap_sites_min = QSpinBox()
        self.onetap_sites_min.setRange(0, 50)
        self.onetap_sites_min.setValue(self.get_mode_config("google").get("settings", {}).get("onetap_sites_min", 1))
        self.onetap_sites_min.setStyleSheet(input_style)
        onetap_per_session_layout.addWidget(self.onetap_sites_min)
        onetap_per_session_layout.addWidget(QLabel("-"))
        self.onetap_sites_max = QSpinBox()
        self.onetap_sites_max.setRange(0, 50)
        self.onetap_sites_max.setValue(self.get_mode_config("google").get("settings", {}).get("onetap_sites_max", 3))
        self.onetap_sites_max.setStyleSheet(input_style)
        onetap_per_session_layout.addWidget(self.onetap_sites_max)
        onetap_per_session_layout.addStretch()
        layout.addRow(tr("One Tap sites per session:"), onetap_per_session_layout)
        
        # === GMAIL SECTION ===
        gmail_label = QLabel(tr("📧 Gmail"))
        gmail_label.setStyleSheet(f"font-weight: bold; font-size: 16px; color: {CATPPUCCIN['blue']}; margin-top: 10px;")
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
        youtube_label.setStyleSheet(f"font-weight: bold; font-size: 16px; color: {CATPPUCCIN['blue']}; margin-top: 10px;")
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
        browsing_label.setStyleSheet(f"font-weight: bold; font-size: 16px; color: {CATPPUCCIN['blue']}; margin-top: 10px;")
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
    
    # === AUTO MODE ===
    
    def create_auto_mode(self):
        """Create Auto Mode tab with settings and statistics."""
        widget = QWidget()
        main_layout = QHBoxLayout(widget)
        main_layout.setSpacing(10)
        
        # === LEFT PANEL: Settings ===
        settings_group = QGroupBox(tr("Auto Mode Settings"))
        settings_layout = QVBoxLayout(settings_group)
        
        # Create scroll area for settings
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_widget = QWidget()
        form_layout = QFormLayout(scroll_widget)
        form_layout.setSpacing(8)
        
        input_style = "min-height: 28px; min-width: 90px;"
        
        # --- Schedule Section ---
        schedule_label = QLabel(tr("📅 Schedule"))
        schedule_label.setStyleSheet("font-weight: bold; font-size: 13px; margin-top: 10px;")
        form_layout.addRow(schedule_label)
        
        # Weekday hours
        weekday_layout = QHBoxLayout()
        self.auto_work_start_weekday = QSpinBox()
        self.auto_work_start_weekday.setRange(0, 23)
        self.auto_work_start_weekday.setValue(self.config.get("auto_mode", {}).get("work_start_weekday", 7))
        self.auto_work_start_weekday.setSuffix(":00")
        self.auto_work_start_weekday.setStyleSheet(input_style)
        weekday_layout.addWidget(self.auto_work_start_weekday)
        weekday_layout.addWidget(QLabel("-"))
        self.auto_work_end_weekday = QSpinBox()
        self.auto_work_end_weekday.setRange(0, 24)
        self.auto_work_end_weekday.setValue(self.config.get("auto_mode", {}).get("work_end_weekday", 23))
        self.auto_work_end_weekday.setSuffix(":00")
        self.auto_work_end_weekday.setStyleSheet(input_style)
        weekday_layout.addWidget(self.auto_work_end_weekday)
        weekday_layout.addStretch()
        form_layout.addRow(tr("Weekdays:"), weekday_layout)
        
        # Weekend hours
        weekend_layout = QHBoxLayout()
        self.auto_work_start_weekend = QSpinBox()
        self.auto_work_start_weekend.setRange(0, 23)
        self.auto_work_start_weekend.setValue(self.config.get("auto_mode", {}).get("work_start_weekend", 9))
        self.auto_work_start_weekend.setSuffix(":00")
        self.auto_work_start_weekend.setStyleSheet(input_style)
        weekend_layout.addWidget(self.auto_work_start_weekend)
        weekend_layout.addWidget(QLabel("-"))
        self.auto_work_end_weekend = QSpinBox()
        self.auto_work_end_weekend.setRange(0, 25)  # 25 = 01:00 next day
        self.auto_work_end_weekend.setValue(self.config.get("auto_mode", {}).get("work_end_weekend", 25))
        self.auto_work_end_weekend.setSuffix(":00")
        self.auto_work_end_weekend.setStyleSheet(input_style)
        self.auto_work_end_weekend.setToolTip(tr("25 = 01:00 next day"))
        weekend_layout.addWidget(self.auto_work_end_weekend)
        weekend_layout.addStretch()
        form_layout.addRow(tr("Weekends:"), weekend_layout)
        
        # Start randomization
        self.auto_start_random = QSpinBox()
        self.auto_start_random.setRange(0, 60)
        self.auto_start_random.setValue(self.config.get("auto_mode", {}).get("start_randomization", 30))
        self.auto_start_random.setSuffix(" " + tr("min"))
        self.auto_start_random.setStyleSheet(input_style)
        self.auto_start_random.setToolTip(tr("Random offset for wake-up time"))
        form_layout.addRow(tr("Start randomization:"), self.auto_start_random)
        
        # Staggered start delay (delay between profile launches)
        stagger_layout = QHBoxLayout()
        self.auto_stagger_min = QSpinBox()
        self.auto_stagger_min.setRange(0, 120)
        self.auto_stagger_min.setValue(self.config.get("auto_mode", {}).get("stagger_delay_min", 15))
        self.auto_stagger_min.setSuffix(" " + tr("sec"))
        self.auto_stagger_min.setStyleSheet(input_style)
        stagger_layout.addWidget(self.auto_stagger_min)
        stagger_layout.addWidget(QLabel("-"))
        self.auto_stagger_max = QSpinBox()
        self.auto_stagger_max.setRange(0, 120)
        self.auto_stagger_max.setValue(self.config.get("auto_mode", {}).get("stagger_delay_max", 30))
        self.auto_stagger_max.setSuffix(" " + tr("sec"))
        self.auto_stagger_max.setStyleSheet(input_style)
        stagger_layout.addWidget(self.auto_stagger_max)
        stagger_layout.addStretch()
        form_layout.addRow(tr("Launch delay:"), stagger_layout)
        
        # --- Sessions Section ---
        sessions_label = QLabel(tr("🔄 Sessions"))
        sessions_label.setStyleSheet("font-weight: bold; font-size: 13px; margin-top: 10px;")
        form_layout.addRow(sessions_label)
        
        # Sessions per profile
        sessions_layout = QHBoxLayout()
        self.auto_sessions_min = QSpinBox()
        self.auto_sessions_min.setRange(1, 10)
        self.auto_sessions_min.setValue(self.config.get("auto_mode", {}).get("sessions_per_profile_min", 2))
        self.auto_sessions_min.setStyleSheet(input_style)
        sessions_layout.addWidget(self.auto_sessions_min)
        sessions_layout.addWidget(QLabel("-"))
        self.auto_sessions_max = QSpinBox()
        self.auto_sessions_max.setRange(1, 10)
        self.auto_sessions_max.setValue(self.config.get("auto_mode", {}).get("sessions_per_profile_max", 4))
        self.auto_sessions_max.setStyleSheet(input_style)
        sessions_layout.addWidget(self.auto_sessions_max)
        sessions_layout.addStretch()
        form_layout.addRow(tr("Sessions per profile:"), sessions_layout)
        
        # Cooldown between sessions
        cooldown_layout = QHBoxLayout()
        self.auto_cooldown_min = QSpinBox()
        self.auto_cooldown_min.setRange(1, 240)
        self.auto_cooldown_min.setValue(self.config.get("auto_mode", {}).get("cooldown_min", 30))
        self.auto_cooldown_min.setSuffix(" " + tr("min"))
        self.auto_cooldown_min.setStyleSheet(input_style)
        cooldown_layout.addWidget(self.auto_cooldown_min)
        cooldown_layout.addWidget(QLabel("-"))
        self.auto_cooldown_max = QSpinBox()
        self.auto_cooldown_max.setRange(1, 240)
        self.auto_cooldown_max.setValue(self.config.get("auto_mode", {}).get("cooldown_max", 120))
        self.auto_cooldown_max.setSuffix(" " + tr("min"))
        self.auto_cooldown_max.setStyleSheet(input_style)
        cooldown_layout.addWidget(self.auto_cooldown_max)
        cooldown_layout.addStretch()
        form_layout.addRow(tr("Cooldown between sessions:"), cooldown_layout)
        
        # --- Error Handling Section ---
        errors_label = QLabel(tr("⚠️ Error Handling"))
        errors_label.setStyleSheet("font-weight: bold; font-size: 13px; margin-top: 10px;")
        form_layout.addRow(errors_label)
        
        # Max errors
        self.auto_max_errors = QSpinBox()
        self.auto_max_errors.setRange(1, 10)
        self.auto_max_errors.setValue(self.config.get("auto_mode", {}).get("max_errors", 3))
        self.auto_max_errors.setStyleSheet(input_style)
        form_layout.addRow(tr("Max errors per profile:"), self.auto_max_errors)
        
        # Error action
        self.auto_error_action = QComboBox()
        self.auto_error_action.addItems([
            tr("Skip for today"),
            tr("Skip for 1 hour"),
            tr("Only notify")
        ])
        error_action_map = {"skip_today": 0, "skip_hour": 1, "notify": 2}
        current_action = self.config.get("auto_mode", {}).get("error_action", "skip_today")
        self.auto_error_action.setCurrentIndex(error_action_map.get(current_action, 0))
        self.auto_error_action.setStyleSheet(input_style)
        form_layout.addRow(tr("After max errors:"), self.auto_error_action)
        
        # Session timeout (watchdog)
        self.auto_session_timeout = QSpinBox()
        self.auto_session_timeout.setRange(3, 30)  # 3-30 minutes
        self.auto_session_timeout.setValue(self.config.get("auto_mode", {}).get("max_session_duration", 600) // 60)
        self.auto_session_timeout.setSuffix(" " + tr("min"))
        self.auto_session_timeout.setToolTip(tr("Max session duration before force stop (for hung profiles)"))
        self.auto_session_timeout.setStyleSheet(input_style)
        form_layout.addRow(tr("Session timeout:"), self.auto_session_timeout)
        
        # --- Notifications Section ---
        notif_label = QLabel(tr("🔔 Notifications"))
        notif_label.setStyleSheet("font-weight: bold; font-size: 13px; margin-top: 10px;")
        form_layout.addRow(notif_label)
        
        self.auto_notify_cycle_complete = QCheckBox(tr("Daily cycle complete"))
        self.auto_notify_cycle_complete.setChecked(self.config.get("auto_mode", {}).get("notify_cycle_complete", True))
        form_layout.addRow(self.auto_notify_cycle_complete)
        
        self.auto_notify_profile_errors = QCheckBox(tr("Profile errors"))
        self.auto_notify_profile_errors.setChecked(self.config.get("auto_mode", {}).get("notify_profile_errors", True))
        form_layout.addRow(self.auto_notify_profile_errors)
        
        self.auto_notify_time_shortage = QCheckBox(tr("Not enough time"))
        self.auto_notify_time_shortage.setChecked(self.config.get("auto_mode", {}).get("notify_time_shortage", True))
        form_layout.addRow(self.auto_notify_time_shortage)
        
        scroll.setWidget(scroll_widget)
        settings_layout.addWidget(scroll)
        
        # Save settings button
        save_auto_btn = QPushButton(tr("Save Settings"))
        save_auto_btn.clicked.connect(self.save_auto_settings)
        settings_layout.addWidget(save_auto_btn)
        
        main_layout.addWidget(settings_group, 1)
        
        # === RIGHT PANEL: Statistics & Control ===
        right_panel = QVBoxLayout()
        
        # World Clock Panel - две колонки по 3 региона
        clock_group = QGroupBox(tr("🌍 Regional Time"))
        clock_layout = QHBoxLayout(clock_group)
        clock_layout.setContentsMargins(8, 12, 8, 8)
        clock_layout.setSpacing(12)
        
        # Левая колонка (US, UK, EU)
        self.auto_clock_left = QLabel()
        self.auto_clock_left.setStyleSheet(f"font-size: 14px; line-height: 1.5;")
        clock_layout.addWidget(self.auto_clock_left)
        
        # Правая колонка (RU, JP, AU)
        self.auto_clock_right = QLabel()
        self.auto_clock_right.setStyleSheet(f"font-size: 14px; line-height: 1.5;")
        clock_layout.addWidget(self.auto_clock_right)
        
        self._update_world_clock()
        
        right_panel.addWidget(clock_group)
        
        # Statistics Group - две колонки: Progress слева, State справа
        stats_group = QGroupBox(tr("📊 Statistics"))
        stats_main_layout = QVBoxLayout(stats_group)
        stats_main_layout.setContentsMargins(8, 10, 8, 8)
        stats_main_layout.setSpacing(6)
        
        # Две колонки для статистики
        stats_columns = QHBoxLayout()
        stats_columns.setSpacing(12)
        
        # Левая колонка - Progress
        self.auto_stats_progress_label = QLabel()
        self.auto_stats_progress_label.setStyleSheet(f"font-size: 13px; line-height: 1.4;")
        stats_columns.addWidget(self.auto_stats_progress_label)
        
        # Разделитель
        separator = QFrame()
        separator.setFrameShape(QFrame.VLine)
        separator.setStyleSheet(f"color: {CATPPUCCIN['surface1']};")
        stats_columns.addWidget(separator)
        
        # Правая колонка - Current State
        self.auto_stats_state_label = QLabel()
        self.auto_stats_state_label.setStyleSheet(f"font-size: 13px; line-height: 1.4;")
        stats_columns.addWidget(self.auto_stats_state_label)
        
        stats_main_layout.addLayout(stats_columns)
        
        # Инициализация статистики
        self._update_auto_stats_display()
        
        # Buttons row
        stats_buttons = QHBoxLayout()
        stats_buttons.setSpacing(8)
        
        # History button
        history_btn = QPushButton(tr("📅 History"))
        history_btn.setStyleSheet("font-size: 13px; padding: 5px 10px;")
        history_btn.clicked.connect(self.show_auto_history)
        stats_buttons.addWidget(history_btn)
        
        # Reset progress button
        reset_btn = QPushButton(tr("🔄 Reset"))
        reset_btn.setStyleSheet("font-size: 13px; padding: 5px 10px;")
        reset_btn.setToolTip(tr("Reset today's progress (for testing)"))
        reset_btn.clicked.connect(self.reset_auto_progress)
        stats_buttons.addWidget(reset_btn)
        
        stats_main_layout.addLayout(stats_buttons)
        
        right_panel.addWidget(stats_group)
        
        # Control Group
        control_group = QGroupBox(tr("🎮 Control"))
        control_layout = QVBoxLayout(control_group)
        
        # Status label
        self.auto_status_label = QLabel(tr("Status: Stopped"))
        self.auto_status_label.setStyleSheet(f"font-weight: bold; font-size: {FONT_SIZE_LARGE}px; padding: 12px;")
        self.auto_status_label.setAlignment(Qt.AlignCenter)
        control_layout.addWidget(self.auto_status_label)
        
        # Control buttons
        buttons_layout = QHBoxLayout()
        
        c = CATPPUCCIN
        
        self.auto_start_btn = QPushButton("▶ " + tr("START"))
        self.auto_start_btn.setMinimumHeight(50)
        self.auto_start_btn.clicked.connect(self.start_auto_mode)
        self.auto_start_btn.setStyleSheet(f"""
            QPushButton {{ background-color: {c['green']}; color: {c['crust']}; font-weight: bold; font-size: {FONT_SIZE_LARGE}px; border-radius: {BORDER_RADIUS}px; }}
            QPushButton:hover {{ background-color: #96D391; }}
            QPushButton:disabled {{ background-color: {c['surface1']}; color: {c['overlay0']}; }}
        """)
        buttons_layout.addWidget(self.auto_start_btn)
        
        self.auto_stop_btn = QPushButton("⏹ " + tr("STOP"))
        self.auto_stop_btn.setMinimumHeight(50)
        self.auto_stop_btn.setEnabled(False)
        self.auto_stop_btn.clicked.connect(self.stop_auto_mode)
        self.auto_stop_btn.setStyleSheet(f"""
            QPushButton {{ background-color: {c['red']}; color: {c['crust']}; font-weight: bold; font-size: {FONT_SIZE_LARGE}px; border-radius: {BORDER_RADIUS}px; }}
            QPushButton:hover {{ background-color: #E37B98; }}
            QPushButton:disabled {{ background-color: {c['surface1']}; color: {c['overlay0']}; }}
        """)
        buttons_layout.addWidget(self.auto_stop_btn)
        
        control_layout.addLayout(buttons_layout)
        
        # Next action info
        self.auto_next_action_label = QLabel(tr("Next action: -"))
        self.auto_next_action_label.setStyleSheet(f"color: {c['subtext0']}; padding: 6px; font-size: {FONT_SIZE_BASE}px;")
        control_layout.addWidget(self.auto_next_action_label)
        
        right_panel.addWidget(control_group)
        right_panel.addStretch()
        
        main_layout.addLayout(right_panel, 1)
        
        return widget
    
    def _update_auto_stats_display(self):
        """Update the auto mode statistics display (two columns)."""
        summary = self.auto_state.get_today_summary()
        
        # Get scheduler info if running
        running_count = len(self.auto_workers)
        
        # Get scheduler summary if available
        if hasattr(self, 'auto_scheduler') and self.auto_scheduler:
            sched_summary = self.auto_scheduler.get_summary()
            waiting = sched_summary.get("by_status", {}).get("waiting", 0)
            sleeping = sched_summary.get("by_status", {}).get("sleeping", 0)
            cooldown = sched_summary.get("by_status", {}).get("cooldown", 0)
            completed = sched_summary.get("by_status", {}).get("completed", 0)
            skipped = sched_summary.get("by_status", {}).get("skipped", 0)
            planned = sched_summary.get("planned_sessions", 0)
        else:
            waiting = sleeping = cooldown = completed = skipped = planned = 0
        
        # Calculate progress percentage
        total_done = summary['total_sessions']
        if planned > 0:
            progress_pct = min(100, int(total_done / planned * 100))
            progress_str = f"{total_done} / ~{planned} ({progress_pct}%)"
        else:
            progress_str = str(total_done)
        
        # Estimate completion time
        completion_str = self._estimate_completion_time()
        
        # Left column - Progress
        progress_text = f"""<b>{tr("Today's Progress")}</b><br>
{tr("Total Sessions")}: {progress_str}<br>
• Cookie: {summary['cookie_sessions']}<br>
• Google: {summary['google_sessions']}<br><br>
🏁 {tr("Est. finish")}: {completion_str}<br>
{tr("Errors")}: {summary['total_errors']}"""
        
        # Right column - Current State
        state_text = f"""<b>{tr("Current State")}</b><br>
▶ {tr("Running")}: {running_count}<br>
⏳ {tr("Waiting")}: {waiting}<br>
❄️ {tr("Cooldown")}: {cooldown}<br>
😴 {tr("Sleeping")}: {sleeping}<br>
✅ {tr("Completed")}: {completed}<br>
⏭️ {tr("Skipped")}: {skipped}"""
        
        # Update both labels
        if hasattr(self, 'auto_stats_progress_label'):
            self.auto_stats_progress_label.setText(progress_text)
        if hasattr(self, 'auto_stats_state_label'):
            self.auto_stats_state_label.setText(state_text)
    
    def _estimate_completion_time(self) -> str:
        """Estimate when all sessions will be completed."""
        if not hasattr(self, 'auto_scheduler') or not self.auto_scheduler:
            return "-"
        
        from datetime import datetime, timezone, timedelta
        
        # Find the latest sleep time among all profiles
        latest_end = None
        
        for profile in self.auto_scheduler.get_all_profiles():
            if profile.status.value in ('completed', 'skipped'):
                continue
            
            sleep_time = self.auto_scheduler.get_sleep_time(profile.country)
            if sleep_time:
                if latest_end is None or sleep_time > latest_end:
                    latest_end = sleep_time
        
        if latest_end:
            now = datetime.now(timezone.utc)
            diff = latest_end - now
            
            if diff.total_seconds() < 0:
                return tr("Today")
            
            hours = int(diff.total_seconds() // 3600)
            minutes = int((diff.total_seconds() % 3600) // 60)
            
            # Format as local time
            local_end = latest_end.astimezone()
            time_str = local_end.strftime("%H:%M")
            
            if hours > 0:
                return f"~{time_str} ({hours}h {minutes}m)"
            else:
                return f"~{time_str} ({minutes}m)"
        
        return tr("Unknown")
    
    def _update_world_clock(self):
        """Update the world clock display (two columns)."""
        from datetime import datetime, timezone, timedelta
        
        # Key regions with their UTC offsets - split into two columns
        left_regions = [
            ("🇺🇸 US (CST)", -6),
            ("🇬🇧 UK", 0),
            ("🇪🇺 EU (CET)", 1),
        ]
        right_regions = [
            ("🇷🇺 RU (MSK)", 3),
            ("🇯🇵 JP", 9),
            ("🇦🇺 AU", 10),
        ]
        
        utc_now = datetime.now(timezone.utc)
        
        # Get auto mode settings for working hours
        auto_cfg = self.config.get("auto_mode", {})
        work_start = auto_cfg.get("work_start_weekday", 7)
        work_end = auto_cfg.get("work_end_weekday", 23)
        
        def format_region(name, offset):
            local_time = utc_now + timedelta(hours=offset)
            hour = local_time.hour
            time_str = local_time.strftime("%H:%M")
            
            # Check if within working hours
            is_weekend = local_time.weekday() >= 5
            if is_weekend:
                ws = auto_cfg.get("work_start_weekend", 9)
                we = auto_cfg.get("work_end_weekend", 25)
            else:
                ws = work_start
                we = work_end
            
            if we > 24:
                awake = ws <= hour < 24
            else:
                awake = ws <= hour < we
            
            status = "✅" if awake else "😴"
            return f"{name}: <b>{time_str}</b> {status}"
        
        # Format left column
        left_lines = [format_region(name, offset) for name, offset in left_regions]
        # Format right column
        right_lines = [format_region(name, offset) for name, offset in right_regions]
        
        # Update both labels
        if hasattr(self, 'auto_clock_left'):
            self.auto_clock_left.setText("<br>".join(left_lines))
        if hasattr(self, 'auto_clock_right'):
            self.auto_clock_right.setText("<br>".join(right_lines))
    
    def save_auto_settings(self):
        """Save auto mode settings."""
        error_actions = ["skip_today", "skip_hour", "notify"]
        
        auto_config = {
            "work_start_weekday": self.auto_work_start_weekday.value(),
            "work_end_weekday": self.auto_work_end_weekday.value(),
            "work_start_weekend": self.auto_work_start_weekend.value(),
            "work_end_weekend": self.auto_work_end_weekend.value(),
            "start_randomization": self.auto_start_random.value(),
            "stagger_delay_min": self.auto_stagger_min.value(),
            "stagger_delay_max": self.auto_stagger_max.value(),
            "sessions_per_profile_min": self.auto_sessions_min.value(),
            "sessions_per_profile_max": self.auto_sessions_max.value(),
            "cooldown_min": self.auto_cooldown_min.value(),
            "cooldown_max": self.auto_cooldown_max.value(),
            "max_errors": self.auto_max_errors.value(),
            "error_action": error_actions[self.auto_error_action.currentIndex()],
            "max_session_duration": self.auto_session_timeout.value() * 60,  # Convert minutes to seconds
            "notify_cycle_complete": self.auto_notify_cycle_complete.isChecked(),
            "notify_profile_errors": self.auto_notify_profile_errors.isChecked(),
            "notify_time_shortage": self.auto_notify_time_shortage.isChecked(),
        }
        
        self.config["auto_mode"] = auto_config
        self.save_config()
        self.log("✅ Auto mode settings saved")
    
    def reset_auto_progress(self):
        """Reset today's auto mode progress for testing."""
        from PyQt5.QtWidgets import QDialog, QDialogButtonBox
        
        dialog = QDialog(self)
        dialog.setWindowTitle(tr("Reset Progress"))
        layout = QVBoxLayout(dialog)
        
        layout.addWidget(QLabel(tr("Reset all session counters for today?") + "\n\n" + tr("This is useful for testing.")))
        
        buttons = QHBoxLayout()
        yes_btn = QPushButton(tr("Yes"))
        no_btn = QPushButton(tr("No"))
        yes_btn.clicked.connect(dialog.accept)
        no_btn.clicked.connect(dialog.reject)
        buttons.addWidget(yes_btn)
        buttons.addWidget(no_btn)
        layout.addLayout(buttons)
        
        if dialog.exec_() == QDialog.Accepted:
            # Reset state file
            self.auto_state._state["profiles"] = {}
            self.auto_state._state["skipped_profiles"] = {}
            self.auto_state._save_state()
            
            # Reload profiles into scheduler with reset counters
            if self.auto_state.is_auto_running():
                self._load_profiles_to_scheduler()
            
            self._update_auto_stats_display()
            self.log("🔄 Auto mode progress reset")
    
    def show_auto_history(self):
        """Show auto mode history dialog."""
        from PyQt5.QtWidgets import QDialog
        
        dialog = QDialog(self)
        dialog.setWindowTitle(tr("Auto Mode History"))
        dialog.setMinimumSize(500, 400)
        layout = QVBoxLayout(dialog)
        
        # Date selector
        date_layout = QHBoxLayout()
        date_layout.addWidget(QLabel(tr("Select date:")))
        
        date_combo = QComboBox()
        available_dates = self.auto_state.get_available_stats_dates()
        if available_dates:
            date_combo.addItems(available_dates)
        else:
            date_combo.addItem(tr("No history available"))
        date_layout.addWidget(date_combo)
        date_layout.addStretch()
        layout.addLayout(date_layout)
        
        # Stats display
        stats_display = QTextEdit()
        stats_display.setReadOnly(True)
        
        def load_stats():
            date_str = date_combo.currentText()
            if date_str and date_str != tr("No history available"):
                content = self.auto_state.get_stats_for_date(date_str)
                if content:
                    stats_display.setPlainText(content)
                else:
                    stats_display.setPlainText(tr("No data for this date"))
            else:
                stats_display.setPlainText(tr("No history available"))
        
        date_combo.currentTextChanged.connect(load_stats)
        load_stats()  # Load initial
        
        layout.addWidget(stats_display)
        
        # Close button
        close_btn = QPushButton(tr("Close"))
        close_btn.clicked.connect(dialog.close)
        layout.addWidget(close_btn)
        
        dialog.exec_()
    
    def start_auto_mode(self):
        """Start auto mode."""
        if not self.octo_api:
            QMessageBox.warning(self, tr("Error"), tr("Not connected to Octo Browser"))
            return
        
        # Load profiles into scheduler
        self._load_profiles_to_scheduler()
        
        # Check if there are profiles
        all_profiles = self.auto_scheduler.get_all_profiles()
        if not all_profiles:
            QMessageBox.warning(
                self, 
                tr("No Profiles"),
                tr("No profiles found in Cookie or Google modes.\nAdd profiles first.")
            )
            return
        
        # Check proxies before starting auto mode
        self._check_proxies_before_start("auto", [p.uuid for p in all_profiles])
        
        # Update scheduler settings
        auto_cfg = self.config.get("auto_mode", {})
        auto_cfg["max_parallel"] = self.config.get("max_parallel_profiles", 5)
        self.auto_scheduler.update_settings(auto_cfg)
        
        # Check capacity and warn if needed
        capacity = self.auto_scheduler.estimate_daily_capacity()
        summary = self.auto_scheduler.get_summary()
        
        if capacity.get("profiles_insufficient_time", 0) > 0:
            if self.config.get("auto_mode", {}).get("notify_time_shortage", True):
                self.notifications.notify_not_enough_time(
                    summary.get("planned_sessions", 0),
                    capacity.get("remaining_sessions", 0),
                    summary.get("planned_sessions", 0) - capacity.get("remaining_sessions", 0)
                )
        
        self.auto_state.set_auto_running(True)
        self.auto_state.set_auto_paused(False)
        
        self.auto_start_btn.setEnabled(False)
        self.auto_stop_btn.setEnabled(True)
        self.auto_status_label.setText(tr("Status: Running"))
        self.auto_status_label.setStyleSheet(f"font-weight: bold; font-size: {FONT_SIZE_LARGE}px; padding: 12px; color: {CATPPUCCIN['green']};")
        
        # Start scheduler timer (check every 30 seconds)
        from PyQt5.QtCore import QTimer
        self.auto_scheduler_timer = QTimer(self)
        self.auto_scheduler_timer.timeout.connect(self._auto_scheduler_tick)
        self.auto_scheduler_timer.start(30000)  # 30 seconds
        
        # Session timeout watchdog timer (every 60 seconds, async)
        self.auto_watchdog_timer = QTimer(self)
        self.auto_watchdog_timer.timeout.connect(self._async_check_session_timeouts)
        self.auto_watchdog_timer.start(60000)  # 60 seconds
        
        # Immediate first tick
        self._auto_scheduler_tick()
        
        # Disable Play buttons during Auto mode (after profiles are loaded)
        # Use singleShot to ensure UI is fully rendered
        from PyQt5.QtCore import QTimer
        QTimer.singleShot(100, lambda: self._set_play_buttons_enabled(False))
        
        self.log("🤖 Auto mode STARTED")
        self.log(f"   📊 Profiles: {summary.get('cookie_profiles', 0)} Cookie + {summary.get('google_profiles', 0)} Google")
    
    def _load_profiles_to_scheduler(self):
        """Load all profiles from Cookie and Google modes into scheduler."""
        self.auto_scheduler.clear_profiles()
        
        # Load Cookie profiles
        cookie_cfg = self.get_mode_config("cookie")
        cookie_profiles = cookie_cfg.get("profiles", [])
        cookie_info = cookie_cfg.get("profile_info", {})
        
        paused_count = 0
        loaded_count = 0
        
        self.log(f"[Auto] Loading {len(cookie_profiles)} cookie profiles to scheduler...")
        
        for uuid in cookie_profiles:
            info = cookie_info.get(uuid, {})
            
            # Skip paused profiles
            if info.get("paused", False):
                paused_count += 1
                self.log(f"[Auto]   {uuid[:8]}... ⏸ PAUSED (skipped)")
                continue
            
            country = info.get("country", "")
            
            # If country is empty/unknown, mark as UNKNOWN to force detection
            if not country or country == "Unknown":
                country = "UNKNOWN"
            
            # Get state from auto_state
            sessions = self.auto_state.get_profile_sessions_today(uuid)
            errors = self.auto_state.get_profile_errors_today(uuid)
            last_session = self.auto_state.get_last_session_time(uuid)
            target_sessions = self.auto_state.get_profile_target_sessions(uuid)
            
            self.log(f"[Auto]   {uuid[:8]}... country={country}, target={target_sessions}")
            
            self.auto_scheduler.add_profile(
                uuid=uuid,
                mode="cookie",
                country=country,
                sessions_today=sessions,
                errors_today=errors,
                target_sessions=target_sessions,
                last_session_end=last_session
            )
            loaded_count += 1
        
        # Load Google profiles
        google_cfg = self.get_mode_config("google")
        google_profiles = google_cfg.get("profiles", [])
        google_info = google_cfg.get("profile_info", {})
        
        self.log(f"[Auto] Loading {len(google_profiles)} google profiles to scheduler...")
        
        for uuid in google_profiles:
            info = google_info.get(uuid, {})
            
            # Skip paused profiles
            if info.get("paused", False):
                paused_count += 1
                self.log(f"[Auto]   {uuid[:8]}... ⏸ PAUSED (skipped)")
                continue
            
            country = info.get("country", "")
            
            # If country is empty/unknown, mark as UNKNOWN to force detection
            if not country or country == "Unknown":
                country = "UNKNOWN"
            
            sessions = self.auto_state.get_profile_sessions_today(uuid)
            errors = self.auto_state.get_profile_errors_today(uuid)
            last_session = self.auto_state.get_last_session_time(uuid)
            target_sessions = self.auto_state.get_profile_target_sessions(uuid)
            
            self.log(f"[Auto]   {uuid[:8]}... country={country}, target={target_sessions}")
            
            self.auto_scheduler.add_profile(
                uuid=uuid,
                mode="google",
                country=country,
                sessions_today=sessions,
                errors_today=errors,
                target_sessions=target_sessions,
                last_session_end=last_session
            )
            loaded_count += 1
        
        # Log summary
        if paused_count > 0:
            self.log(f"[Auto] ⏸ {paused_count} profile(s) paused (excluded from queue)")


    def _refresh_all_auto_profiles_geo(self):
        """
        Refresh geo-data for ALL profiles in the auto scheduler from Octo API.
        This MUST run BEFORE get_profiles_to_start() to ensure scheduling decisions
        use the latest country/proxy data.
        """
        if not self.octo_api:
            return
        
        all_profiles = self.auto_scheduler.get_all_profiles()
        if not all_profiles:
            return
        
        geo_updated = False
        
        for profile in all_profiles:
            uuid = profile.uuid
            mode = profile.mode
            old_country = profile.country
            
            # Fetch fresh info from Octo API
            fresh_info = self.octo_api.get_profile_info(uuid)
            if not fresh_info:
                continue
            
            new_country = fresh_info.get("country", "")
            if not new_country:
                continue
            
            # Check if country changed
            if old_country != new_country:
                logging.info(f"[AUTO_GEO_REFRESH] {uuid[:8]} country changed: {old_country} -> {new_country}")
                self.log(f"[Auto] 🌍 {uuid[:8]}... geo updated: {old_country} → {new_country}")
                
                # Update in scheduler (this will also re-evaluate awake/sleep status)
                self.auto_scheduler.update_profile_country(uuid, new_country)
                
                # Update in config/profile_info for persistence and UI
                cfg = self.get_mode_config(mode)
                profile_info = cfg.setdefault("profile_info", {})
                if uuid not in profile_info:
                    profile_info[uuid] = {}
                profile_info[uuid]["country"] = new_country
                self.set_mode_config(mode, cfg)
                
                geo_updated = True
        
        # If any geo changed, reload profile lists to update UI flags
        if geo_updated:
            self.load_profiles_list("cookie")
            self.load_profiles_list("google")

    def _auto_scheduler_tick(self):
        """Called periodically to check and start profiles."""
        if not self.auto_state.is_auto_running():
            return
        
        if self.auto_state.is_auto_paused():
            return
        
        # Check for day change - reset profiles if new day
        self._check_day_change_and_reset()
        
        # NOTE: Session timeout watchdog runs separately via _async_check_session_timeouts
        
        # NOTE: Geo refresh removed - it was blocking UI and didn't work anyway
        # (Octo API doesn't return actual proxy country until profile starts)
        # Real country detection happens in _on_auto_country_detected() after profile starts
        
        # Update UI
        self._update_auto_stats_display()
        self._update_auto_next_action()
        
        # Get profiles to start
        to_start = self.auto_scheduler.get_profiles_to_start()
        logging.info(f"[AUTO_DEBUG] _auto_scheduler_tick: to_start has {len(to_start)} profiles")
        
        # Get stagger delay settings from config
        stagger_min = self.config.get("auto_mode", {}).get("stagger_delay_min", 15)
        stagger_max = self.config.get("auto_mode", {}).get("stagger_delay_max", 30)
        
        # Staggered start: add profiles to queue with delay between each
        for i, profile in enumerate(to_start):
            # Calculate delay based on settings
            if i == 0:
                delay_ms = 0  # First profile starts immediately
            else:
                delay_ms = random.randint(stagger_min * 1000, stagger_max * 1000)
            
            # Use QTimer for delayed start
            if delay_ms == 0:
                logging.info(f"[AUTO_DEBUG] Starting profile immediately: {profile.uuid[:8]}, mode={profile.mode}")
                self._start_auto_profile(profile.uuid, profile.mode)
            else:
                logging.info(f"[AUTO_DEBUG] Scheduling profile start in {delay_ms/1000:.1f}s: {profile.uuid[:8]}, mode={profile.mode}")
                QTimer.singleShot(delay_ms, lambda u=profile.uuid, m=profile.mode: self._start_auto_profile(u, m))
    
    def _async_check_session_timeouts(self):
        """Async wrapper for session timeout check - runs in background thread."""
        if not self.auto_state.is_auto_running():
            return
        
        # Don't start if already checking
        if hasattr(self, '_watchdog_running') and self._watchdog_running:
            return
        
        self._watchdog_running = True
        
        import threading
        thread = threading.Thread(target=self._check_session_timeouts_thread, daemon=True)
        thread.start()
    
    def _check_session_timeouts_thread(self):
        """Background thread for session timeout checks."""
        import time
        
        try:
            if not hasattr(self, '_auto_worker_start_times'):
                return
            
            # Max session duration in seconds (from config, default 10 minutes)
            max_session_duration = self.config.get("auto_mode", {}).get("max_session_duration", 600)
            
            current_time = time.time()
            timed_out_profiles = []
            
            for uuid, start_time in list(self._auto_worker_start_times.items()):
                elapsed = current_time - start_time
                
                if elapsed > max_session_duration:
                    timed_out_profiles.append((uuid, int(elapsed)))
            
            # Schedule UI updates on main thread
            if timed_out_profiles:
                from PyQt5.QtCore import QMetaObject, Qt, Q_ARG
                for uuid, elapsed in timed_out_profiles:
                    QMetaObject.invokeMethod(
                        self,
                        "_handle_session_timeout",
                        Qt.QueuedConnection,
                        Q_ARG(str, uuid),
                        Q_ARG(int, elapsed)
                    )
        except Exception as e:
            logging.error(f"[WATCHDOG] Error in timeout check: {e}")
        finally:
            self._watchdog_running = False
    
    @pyqtSlot(str, int)
    def _handle_session_timeout(self, uuid: str, elapsed: int):
        """Handle session timeout on main thread."""
        max_duration = self.config.get("auto_mode", {}).get("max_session_duration", 600)
        self.log(f"[Auto] ⏱️ {uuid[:8]}... session timeout ({elapsed}s > {max_duration}s)")
        self._force_stop_hung_session(uuid)
    
    def _check_session_timeouts(self):
        """Check for sessions that exceeded max duration and kill them."""
        import time
        
        if not hasattr(self, '_auto_worker_start_times'):
            return
        
        # Max session duration in seconds (default 10 minutes)
        max_session_duration = self.config.get("auto_mode", {}).get("max_session_duration", 600)
        
        current_time = time.time()
        timed_out_profiles = []
        
        for uuid, start_time in list(self._auto_worker_start_times.items()):
            elapsed = current_time - start_time
            
            if elapsed > max_session_duration:
                timed_out_profiles.append(uuid)
                self.log(f"[Auto] ⏱️ {uuid[:8]}... session timeout ({int(elapsed)}s > {max_session_duration}s)")
        
        # Kill timed out sessions
        for uuid in timed_out_profiles:
            self._force_stop_hung_session(uuid)
    
    def _force_stop_hung_session(self, uuid: str):
        """Force stop a hung/timed-out session."""
        self.log(f"[Auto] 🔪 Force stopping hung session {uuid[:8]}...")
        
        # Stop worker thread
        if uuid in self.auto_workers:
            worker = self.auto_workers[uuid]
            worker.stop()
        
        # Force stop browser profile
        if self.api_manager:
            self.api_manager.stop_profile_async(uuid, force=True)
        elif self.octo_api:
            self.octo_api.force_stop_profile(uuid)
        
        # Clean up tracking
        if uuid in self.auto_workers:
            del self.auto_workers[uuid]
        
        if hasattr(self, '_auto_worker_start_times') and uuid in self._auto_worker_start_times:
            del self._auto_worker_start_times[uuid]
        
        # Mark as failed in scheduler
        self.auto_scheduler.mark_profile_completed(uuid, False)
        self.auto_state.increment_profile_error(uuid)
        
        self.log(f"[Auto] ⏹️ {uuid[:8]}... stopped due to session timeout")
    
    def _check_day_change_and_reset(self):
        """Check if day changed and reset scheduler profiles for new day."""
        from datetime import datetime, timezone
        
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        
        # Get stored date from auto_state
        state_date = self.auto_state._state.get("date", "")
        
        if state_date and state_date != today:
            # Day changed! Reset scheduler profiles
            self.log(f"🌅 New day detected ({today}), resetting profiles...")
            
            # auto_state._check_day_reset() will reset session counters
            # We need to reload profiles into scheduler with fresh data
            self._reload_auto_profiles_for_new_day()
    
    def _reload_auto_profiles_for_new_day(self):
        """Reload all profiles into scheduler with reset counters for new day."""
        # Get current profiles from scheduler
        old_profiles = self.auto_scheduler.get_all_profiles()
        
        # Clear scheduler
        self.auto_scheduler.clear_profiles()
        
        # Re-add all profiles with reset counters
        for p in old_profiles:
            # auto_state will return 0 for sessions_today (new day)
            sessions = self.auto_state.get_profile_sessions_today(p.uuid)
            errors = self.auto_state.get_profile_errors_today(p.uuid)
            target = self.auto_state.get_profile_target_sessions(p.uuid)  # Will be 0 for new day
            last_session = self.auto_state.get_last_session_time(p.uuid)
            
            self.auto_scheduler.add_profile(
                uuid=p.uuid,
                mode=p.mode,
                country=p.country,
                sessions_today=sessions,
                target_sessions=target,
                errors_today=errors,
                last_session_end=last_session
            )
            
            self.log(f"[Auto]   {p.uuid[:8]}... country={p.country}, target={target}")
        
        self.log(f"🔄 Profiles reloaded for new day")
    
    def _update_auto_next_action(self):
        """Update the next action label."""
        next_time, description = self.auto_scheduler.get_next_action_time()
        
        if next_time:
            from datetime import datetime, timezone
            now = datetime.now(timezone.utc)
            diff = next_time - now
            
            if diff.total_seconds() < 60:
                time_str = tr("now")
            elif diff.total_seconds() < 3600:
                time_str = f"{int(diff.total_seconds() // 60)} " + tr("min")
            else:
                time_str = f"{int(diff.total_seconds() // 3600)}h {int((diff.total_seconds() % 3600) // 60)}m"
            
            self.auto_next_action_label.setText(f"{tr('Next action')}: {time_str} - {description}")
        else:
            self.auto_next_action_label.setText(f"{tr('Next action')}: -")
    
    def _start_auto_profile(self, uuid: str, mode: str):
        """Start a profile in auto mode."""
        logging.info(f"[AUTO_DEBUG] _start_auto_profile called: uuid={uuid[:8]}, mode={mode}")
        
        # Check if already running (in auto or manual)
        if uuid in self.auto_workers:
            logging.info(f"[AUTO_DEBUG] {uuid[:8]} already in auto_workers, skipping")
            return
        if uuid in self.workers:
            # Running manually - mark as manual in scheduler
            self.auto_scheduler.mark_profile_manual(uuid, True)
            logging.info(f"[AUTO_DEBUG] {uuid[:8]} in manual workers, marking as manual")
            return
        
        # NOTE: Geo-data refresh now happens in _refresh_all_auto_profiles_geo() 
        # BEFORE get_profiles_to_start(), so we use already-fresh data here.
        
        # Final safety check: verify profile is still awake (in case of race condition)
        profile = self.auto_scheduler.get_profile(uuid)
        logging.info(f"[AUTO_DEBUG] get_profile({uuid[:8]}) returned: {profile}")
        
        if profile:
            logging.info(f"[AUTO_DEBUG] profile.country = '{profile.country}'")
            is_awake = self.auto_scheduler.is_profile_awake(profile.country)
            local_time = self.auto_scheduler.get_local_time(profile.country)
            logging.info(f"[AUTO_DEBUG] {uuid[:8]}: country={profile.country}, local_time={local_time}, is_awake={is_awake}")
            self.log(f"[Auto] 🕐 {uuid[:8]}... country={profile.country}, local={local_time.strftime('%H:%M')}, awake={is_awake}")
            if not is_awake:
                logging.info(f"[AUTO_DEBUG] {uuid[:8]} is NOT awake, SKIPPING!")
                self.log(f"[Auto] 😴 {uuid[:8]}... ({profile.country}) went to sleep, skipping")
                self.auto_scheduler._update_profile_status(profile)
                return
        else:
            logging.info(f"[AUTO_DEBUG] {uuid[:8]} NOT FOUND in scheduler!")
            self.log(f"[Auto] ⚠️ {uuid[:8]}... not found in scheduler!")
        
        # Get mode config and settings
        cfg = self.get_mode_config(mode)
        settings = cfg.get("settings", {}).copy()
        
        # Get profile country for geo-targeting
        profile_info = cfg.get("profile_info", {})
        profile_country = profile_info.get(uuid, {}).get("country", "")
        
        # Add global settings
        settings["base_delay_min"] = self.config.get("base_delay_min", 1)
        settings["base_delay_max"] = self.config.get("base_delay_max", 3)
        settings["start_minimized"] = self.config.get("start_minimized", True)
        settings["geo_visiting_enabled"] = self.config.get("geo_visiting_enabled", False)
        settings["geo_visiting_percent"] = self.config.get("geo_visiting_percent", 70)
        settings["profile_country"] = profile_country  # For geo-targeting
        
        # Get sites for this mode
        if mode == "cookie":
            sites = cfg.get("sites", [])
            youtube_enabled = cfg.get("youtube_enabled", False)
            settings["youtube_enabled"] = youtube_enabled
        else:  # google
            sites = cfg.get("browse_sites", []) + cfg.get("onetap_sites", [])
            # Add separate lists for proper handling in automation
            settings["browse_sites"] = cfg.get("browse_sites", [])
            settings["onetap_sites"] = cfg.get("onetap_sites", [])
            settings["services"] = cfg.get("services", {})
            settings["youtube_enabled"] = cfg.get("youtube_enabled", True)
            # Add YouTube queries from global settings
            settings["youtube_queries"] = self.config.get("youtube_queries", "")
        
        # Check if there are sites to visit
        # For google mode: also check if services are enabled (they count as sites)
        has_sites = bool(sites)
        if mode == "google" and not has_sites:
            # Check if any Google services are enabled
            services = cfg.get("services", {})
            has_services = any(services.values())
            has_sites = has_services
        
        if not has_sites:
            self.log(f"[Auto] ⚠️ No sites for {uuid[:8]}... ({mode})")
            return
        
        # Create and start worker
        start_minimized = self.config.get("start_minimized", True)
        worker = WorkerThread(uuid, sites, settings, self.octo_api, mode, start_minimized)
        worker.log_signal.connect(self.log)
        worker.finished_signal.connect(lambda u: self._on_auto_worker_finished(u, True))
        worker.error_signal.connect(lambda u, e: self._on_auto_worker_error(u, e))
        # CRITICAL: Connect country_detected to check timezone after REAL country is known
        # Use default argument to capture mode value at connection time
        worker.country_detected.connect(lambda u, c, m=mode: self._on_auto_country_detected(u, c, m))
        
        self.auto_workers[uuid] = worker
        self.auto_scheduler.mark_profile_started(uuid)
        
        # Update working state (UI + DB)
        self._set_profile_working(uuid, True, mode)
        
        # Track start time for session timeout watchdog
        import time
        if not hasattr(self, '_auto_worker_start_times'):
            self._auto_worker_start_times = {}
        self._auto_worker_start_times[uuid] = time.time()
        
        worker.start()
        self.log(f"[Auto] ▶ Started {uuid[:8]}... ({mode})")
    
    def _on_auto_worker_error(self, uuid: str, error: str):
        """Handle auto mode worker error."""
        self.log(f"[Auto] ❌ Error {uuid[:8]}...: {error}")
        self._on_auto_worker_finished(uuid, False)

    def _on_auto_country_detected(self, uuid: str, real_country: str, mode: str):
        """
        Handle country detection in Auto mode.
        This is called when the profile ACTUALLY starts and we get the REAL country from proxy.
        If the real country shows the profile should be sleeping, STOP it immediately.
        """
        logging.info(f"[AUTO_COUNTRY_DETECTED] {uuid[:8]}: REAL country = {real_country}")
        
        # Get old country from scheduler
        profile = self.auto_scheduler.get_profile(uuid)
        old_country = profile.country if profile else ""
        
        # Always update config (even if country same - for first_run initialization)
        cfg = self.get_mode_config(mode)
        profile_info = cfg.setdefault("profile_info", {})
        if uuid not in profile_info:
            profile_info[uuid] = {}
        
        # Update country
        profile_info[uuid]["country"] = real_country
        
        # Set first_run only if not already set (preserve original date)
        if not profile_info[uuid].get("first_run"):
            profile_info[uuid]["first_run"] = datetime.now().isoformat()
            self.log(f"[Auto] 📅 {uuid[:8]}... first run recorded")
        
        self.set_mode_config(mode, cfg)
        
        # Log country change if different
        if old_country != real_country:
            self.log(f"[Auto] 🌍 {uuid[:8]}... REAL country: {old_country} → {real_country}")
            logging.info(f"[AUTO_COUNTRY_DETECTED] {uuid[:8]}: country changed {old_country} -> {real_country}")
            
            # Update scheduler with real country
            self.auto_scheduler.update_profile_country(uuid, real_country)
        
        # Refresh UI to show new country flag and age
        self.log(f"[Auto] 🔄 Refreshing {mode} profiles list...")
        self.load_profiles_list(mode)
        
        # CRITICAL: Check if profile should be sleeping based on REAL country
        is_awake = self.auto_scheduler.is_profile_awake(real_country)
        local_time = self.auto_scheduler.get_local_time(real_country)
        
        logging.info(f"[AUTO_COUNTRY_DETECTED] {uuid[:8]}: local_time={local_time}, is_awake={is_awake}")
        self.log(f"[Auto] 🕐 {uuid[:8]}... ({real_country}) local={local_time.strftime('%H:%M')}, awake={is_awake}")
        
        if not is_awake:
            # Profile should be sleeping! Stop it immediately
            self.log(f"[Auto] 😴 {uuid[:8]}... STOPPING - {real_country} is sleeping at {local_time.strftime('%H:%M')}")
            logging.info(f"[AUTO_COUNTRY_DETECTED] {uuid[:8]}: STOPPING - profile should be sleeping!")
            
            # Stop the worker
            if uuid in self.auto_workers:
                worker = self.auto_workers[uuid]
                worker.stop()
                
                # Force stop the browser profile (async if manager available)
                if self.api_manager:
                    self.api_manager.stop_profile_async(uuid, force=True)
                elif self.octo_api:
                    self.octo_api.force_stop_profile(uuid)
                
                # Remove from auto_workers
                del self.auto_workers[uuid]
                
                # Update scheduler - mark as not running, set to sleeping status
                self.auto_scheduler.mark_profile_completed(uuid, False)  # Mark as not successful
                
                self.log(f"[Auto] ⏹️ {uuid[:8]}... stopped due to timezone")
                self._update_auto_stats_display()

    
    def _on_auto_worker_finished(self, uuid: str, success: bool):
        """Handle auto mode worker completion."""
        if uuid in self.auto_workers:
            del self.auto_workers[uuid]
        
        # Clean up start time tracking
        if hasattr(self, '_auto_worker_start_times') and uuid in self._auto_worker_start_times:
            del self._auto_worker_start_times[uuid]
        
        # Update working state (UI + DB)
        self._set_profile_working(uuid, False)
        
        # Update scheduler and state
        self.auto_scheduler.mark_profile_completed(uuid, success)
        
        if success:
            profile = self.auto_scheduler.get_profile(uuid)
            if profile:
                self.auto_state.increment_profile_session(uuid, profile.mode)
                self.auto_state.reset_profile_errors(uuid)
        else:
            self.auto_state.increment_profile_error(uuid)
            
            # Check if max errors reached
            errors = self.auto_state.get_profile_errors_today(uuid)
            max_errors = self.config.get("auto_mode", {}).get("max_errors", 3)
            
            if errors >= max_errors:
                error_action = self.config.get("auto_mode", {}).get("error_action", "skip_today")
                
                if error_action == "skip_today":
                    self.auto_state.mark_profile_skipped(uuid, "today")
                    action_str = tr("skipped for today")
                elif error_action == "skip_hour":
                    from datetime import datetime, timezone, timedelta
                    skip_until = datetime.now(timezone.utc) + timedelta(hours=1)
                    self.auto_state.mark_profile_skipped(uuid, skip_until.isoformat())
                    action_str = tr("skipped for 1 hour")
                else:
                    action_str = tr("continuing (notify only)")
                
                if self.config.get("auto_mode", {}).get("notify_profile_errors", True):
                    self.notifications.notify_profile_errors(uuid, errors, action_str)
                
                self.log(f"[Auto] ⚠️ {uuid[:8]}... reached {errors} errors - {action_str}")
        
        # Update display
        self._update_auto_stats_display()
        
        # Check if all done for today
        summary = self.auto_scheduler.get_summary()
        if (summary.get("by_status", {}).get("waiting", 0) == 0 and 
            summary.get("by_status", {}).get("cooldown", 0) == 0 and
            summary.get("by_status", {}).get("sleeping", 0) == 0 and
            len(self.auto_workers) == 0):
            
            # Daily cycle complete
            if self.config.get("auto_mode", {}).get("notify_cycle_complete", True):
                self.notifications.notify_daily_cycle_complete(self.auto_state.get_today_summary())
            self.log("🤖 Auto mode: Daily cycle complete!")
    
    def stop_auto_mode(self):
        """Stop auto mode completely."""
        # Stop scheduler timer first
        if self.auto_scheduler_timer:
            self.auto_scheduler_timer.stop()
            self.auto_scheduler_timer = None
        
        # Stop watchdog timer
        if hasattr(self, 'auto_watchdog_timer') and self.auto_watchdog_timer:
            self.auto_watchdog_timer.stop()
            self.auto_watchdog_timer = None
        
        # Stop all worker threads (tell them to stop)
        for uuid, worker in list(self.auto_workers.items()):
            worker.stop()
        
        # Get list of profiles to close
        uuids_to_stop = list(self.auto_workers.keys())
        
        if uuids_to_stop and self.api_manager:
            # Use async manager with progress dialog
            self._stop_auto_mode_async(uuids_to_stop)
        else:
            # No profiles to stop or no manager - finish immediately
            self._finish_stop_auto_mode()
    
    def _stop_auto_mode_async(self, uuids: list):
        """Stop profiles asynchronously with progress dialog."""
        # Create progress dialog
        self._async_progress_dialog = QProgressDialog(
            tr("Stopping profiles..."),
            tr("Cancel"),
            0, len(uuids),
            self
        )
        self._async_progress_dialog.setWindowModality(Qt.WindowModal)
        self._async_progress_dialog.setAutoClose(False)
        self._async_progress_dialog.setAutoReset(False)
        self._async_progress_dialog.canceled.connect(self._on_stop_auto_cancelled)
        self._async_progress_dialog.show()
        
        # Start async batch stop
        self._current_async_task = self.api_manager.stop_profiles_batch_async(
            uuids,
            force=False,
            callback=self._on_stop_auto_complete
        )
    
    def _on_stop_auto_cancelled(self):
        """Handle cancellation of stop operation."""
        if self.api_manager:
            self.api_manager.cancel_current_operation()
        self.log("[Auto] ⚠️ Stop operation cancelled by user")
        self._finish_stop_auto_mode()
    
    def _on_stop_auto_complete(self, result: dict):
        """Handle completion of async stop operation."""
        try:
            if self._async_progress_dialog:
                self._async_progress_dialog.close()
        except (RuntimeError, AttributeError):
            pass
        finally:
            self._async_progress_dialog = None
            self._current_async_task = None
        
        # Log results
        results = result.get("results", [])
        success_count = sum(1 for r in results if r.get("success"))
        self.log(f"[Auto] Stopped {success_count}/{len(results)} profiles")
        
        self._finish_stop_auto_mode()
    
    def _finish_stop_auto_mode(self):
        """Finish stopping auto mode - update state and UI."""
        # Reset working state for all profiles that were running
        for uuid in list(self.auto_workers.keys()):
            self._set_profile_working(uuid, False)
        
        self.auto_workers.clear()
        
        self.auto_state.set_auto_running(False)
        self.auto_state.save_current_stats()  # Archive today's stats
        
        self.auto_start_btn.setEnabled(True)
        self.auto_stop_btn.setEnabled(False)
        self.auto_status_label.setText(tr("Status: Stopped"))
        self.auto_status_label.setStyleSheet(f"font-weight: bold; font-size: {FONT_SIZE_LARGE}px; padding: 12px; color: {CATPPUCCIN['red']};")
        
        # Re-enable Play buttons
        self._set_play_buttons_enabled(True)
        
        self.log("🤖 Auto mode STOPPED")
    
    # === NOTIFICATIONS SYSTEM ===
    
    def _update_notification_badge(self):
        """Update notification button badge."""
        count = self.notifications.get_unread_count()
        if count > 0:
            self.notifications_btn.setText(f"🔔 {count}")
            self.notifications_btn.setStyleSheet("""
                QPushButton {
                    font-size: 14px;
                    background-color: #f38ba8;
                    color: white;
                    font-weight: bold;
                    border-radius: 4px;
                    padding: 4px 8px;
                    text-align: center;
                    min-width: 50px;
                }
                QPushButton:hover { background-color: #e879a0; }
            """)
        else:
            self.notifications_btn.setText("🔔")
            self.notifications_btn.setStyleSheet("""
                QPushButton {
                    font-size: 22px;
                    padding: 0px;
                    border: none;
                    min-width: 50px;
                    text-align: center;
                }
            """)
    
    def show_notifications(self):
        """Show notifications popup dialog."""
        from PyQt5.QtWidgets import QDialog, QDialogButtonBox, QScrollArea
        
        dialog = QDialog(self)
        dialog.setWindowTitle(tr("Notifications"))
        dialog.setMinimumSize(400, 300)
        dialog_layout = QVBoxLayout(dialog)
        
        # Header with mark all read and clear buttons
        header = QHBoxLayout()
        
        count_label = QLabel(f"{self.notifications.get_unread_count()} " + tr("unread"))
        count_label.setStyleSheet("font-weight: bold;")
        header.addWidget(count_label)
        
        header.addStretch()
        
        mark_read_btn = QPushButton(tr("Mark All Read"))
        mark_read_btn.clicked.connect(lambda: self._mark_all_notifications_read(dialog, count_label))
        header.addWidget(mark_read_btn)
        
        clear_btn = QPushButton(tr("Clear All"))
        clear_btn.clicked.connect(lambda: self._clear_all_notifications(dialog))
        header.addWidget(clear_btn)
        
        dialog_layout.addLayout(header)
        
        # Scrollable notification list
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)
        scroll_layout.setSpacing(8)
        
        notifications = self.notifications.get_all()
        
        if not notifications:
            empty_label = QLabel(tr("No notifications"))
            empty_label.setAlignment(Qt.AlignCenter)
            empty_label.setStyleSheet(f"color: {CATPPUCCIN['subtext0']}; padding: 20px;")
            scroll_layout.addWidget(empty_label)
        else:
            for notif in notifications:
                notif_widget = self._create_notification_widget(notif)
                scroll_layout.addWidget(notif_widget)
        
        scroll_layout.addStretch()
        scroll.setWidget(scroll_widget)
        dialog_layout.addWidget(scroll)
        
        # Close button
        close_btn = QPushButton(tr("Close"))
        close_btn.clicked.connect(dialog.reject)
        dialog_layout.addWidget(close_btn)
        
        dialog.exec_()
    
    def _create_notification_widget(self, notif):
        """Create a widget for displaying a single notification."""
        frame = QFrame()
        frame.setFrameShape(QFrame.StyledPanel)
        
        # Different background for unread
        if not notif.read:
            frame.setStyleSheet("QFrame { background-color: rgba(166, 227, 161, 0.1); border-radius: 4px; padding: 8px; }")
        else:
            frame.setStyleSheet("QFrame { background-color: rgba(108, 112, 134, 0.1); border-radius: 4px; padding: 8px; }")
        
        layout = QVBoxLayout(frame)
        layout.setSpacing(4)
        layout.setContentsMargins(8, 8, 8, 8)
        
        # Header: icon + title + time
        header = QHBoxLayout()
        
        icon_label = QLabel(notif.get_icon())
        icon_label.setStyleSheet("font-size: 16px;")
        header.addWidget(icon_label)
        
        if notif.title:
            title_label = QLabel(notif.title)
            title_label.setStyleSheet("font-weight: bold;")
            header.addWidget(title_label)
        
        header.addStretch()
        
        time_label = QLabel(notif.get_time_ago())
        time_label.setStyleSheet(f"color: {CATPPUCCIN['subtext0']}; font-size: {FONT_SIZE_SMALL}px;")
        header.addWidget(time_label)
        
        layout.addLayout(header)
        
        # Message
        msg_label = QLabel(notif.message)
        msg_label.setWordWrap(True)
        layout.addWidget(msg_label)
        
        return frame
    
    def _mark_all_notifications_read(self, dialog, count_label):
        """Mark all notifications as read."""
        self.notifications.mark_all_read()
        count_label.setText("0 " + tr("unread"))
        # Refresh dialog content
        dialog.close()
        self.show_notifications()
    
    def _clear_all_notifications(self, dialog):
        """Clear all notifications."""
        self.notifications.clear_all()
        dialog.close()
        self.show_notifications()
    
    def show_global_settings(self):
        """Show global settings dialog"""
        from PyQt5.QtWidgets import QDialog, QDialogButtonBox
        
        c = CATPPUCCIN
        
        dialog = QDialog(self)
        dialog.setWindowTitle(tr("Global Settings"))
        dialog.setMinimumSize(650, 600)
        dialog_layout = QVBoxLayout(dialog)
        dialog_layout.setSpacing(SPACING)
        dialog_layout.setContentsMargins(MARGIN, MARGIN, MARGIN, MARGIN)
        
        # Scroll area for form
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll_widget = QWidget()
        form = QFormLayout(scroll_widget)
        form.setSpacing(12)
        form.setContentsMargins(4, 4, 4, 4)
        
        # === CONNECTION ===
        conn_label = QLabel(tr("🔌 Connection"))
        conn_label.setStyleSheet(f"font-weight: bold; font-size: 18px; color: {c['blue']}; padding-top: 8px;")
        form.addRow(conn_label)
        
        self.global_api_url = QLineEdit()
        self.global_api_url.setText(self.config.get("api_url", "http://localhost:58888"))
        form.addRow("Octo Browser API:", self.global_api_url)
        
        # Octo API Token for Remote API (proxy checking)
        self.global_api_token = QLineEdit()
        self.global_api_token.setText(self.config.get("octo_api_token", ""))
        self.global_api_token.setPlaceholderText(tr("Enter Octo API token for proxy check"))
        self.global_api_token.setEchoMode(QLineEdit.Password)
        form.addRow(tr("Octo API Token:"), self.global_api_token)
        
        # Show/hide token button
        self.show_token_btn = QPushButton("👁")
        self.show_token_btn.setFixedSize(44, 36)
        self.show_token_btn.setStyleSheet("font-size: 16px; padding: 2px;")
        self.show_token_btn.setCheckable(True)
        self.show_token_btn.clicked.connect(self._toggle_token_visibility)
        form.addRow("", self.show_token_btn)
        
        # === INTERFACE ===
        iface_label = QLabel(tr("🎨 Interface"))
        iface_label.setStyleSheet(f"font-weight: bold; font-size: 18px; color: {c['blue']}; padding-top: 12px;")
        form.addRow(iface_label)
        
        self.global_language = QComboBox()
        self.global_language.addItems(["English", "Русский"])
        self.global_language.setCurrentText(self.config.get("language", "English"))
        form.addRow(tr("Language:"), self.global_language)
        
        # === EXECUTION ===
        exec_label = QLabel(tr("⚡ Execution"))
        exec_label.setStyleSheet(f"font-weight: bold; font-size: 18px; color: {c['blue']}; padding-top: 12px;")
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
        add_label.setStyleSheet(f"font-weight: bold; font-size: 18px; color: {c['blue']}; padding-top: 12px;")
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
        geo_label.setStyleSheet(f"font-weight: bold; font-size: 18px; color: {c['blue']}; padding-top: 12px;")
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
        geo_hint.setStyleSheet(f"color: {c['subtext0']}; font-size: {FONT_SIZE_SMALL}px;")
        form.addRow(geo_hint)
        
        # === YOUTUBE ===
        yt_label = QLabel(tr("📺 YouTube"))
        yt_label.setStyleSheet(f"font-weight: bold; font-size: 18px; color: {c['blue']}; padding-top: 12px;")
        form.addRow(yt_label)
        
        yt_queries_btn = QPushButton(tr("Edit YouTube Queries"))
        yt_queries_btn.clicked.connect(self._show_youtube_queries_editor)
        form.addRow(yt_queries_btn)
        
        # === UPDATES ===
        updates_label = QLabel(tr("🔄 Updates"))
        updates_label.setStyleSheet(f"font-weight: bold; font-size: 18px; color: {c['blue']}; padding-top: 12px;")
        form.addRow(updates_label)
        
        # Current version display
        from version import VERSION
        version_label = QLabel(f"v{VERSION}")
        version_label.setStyleSheet(f"font-weight: bold; color: {c['green']};")
        form.addRow(tr("Current version:"), version_label)
        
        # Check for updates button
        self.check_updates_btn = QPushButton(tr("Check for updates"))
        self.check_updates_btn.setStyleSheet(f"""
            QPushButton {{
                background: {c['blue']};
                color: white;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background: {c['sapphire']};
            }}
        """)
        self.check_updates_btn.clicked.connect(self._check_for_updates)
        form.addRow(self.check_updates_btn)
        
        # Update status label
        self.update_status_label = QLabel("")
        self.update_status_label.setStyleSheet(f"color: {c['subtext0']}; font-size: {FONT_SIZE_SMALL}px;")
        form.addRow(self.update_status_label)
        
        # Add scroll widget
        scroll.setWidget(scroll_widget)
        dialog_layout.addWidget(scroll, 1)
        
        # Buttons (outside scroll)
        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(lambda: self._save_global_settings(dialog))
        buttons.rejected.connect(dialog.reject)
        dialog_layout.addWidget(buttons)
        
        dialog.exec_()
    
    def _save_global_settings(self, dialog):
        """Save global settings"""
        self.config["api_url"] = self.global_api_url.text()
        self.config["octo_api_token"] = self.global_api_token.text()
        self.config["language"] = self.global_language.currentText()
        self.config["theme"] = "Light"  # Always use Light theme
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
        
        # Update API token in manager if connected
        if self.api_manager:
            self.api_manager.set_api_token(self.config["octo_api_token"])
        
        # Apply Light theme
        self.current_theme = "Light"
        self.apply_theme("Light")
        
        # Save config
        self.current_language = self.config["language"]
        self.save_config()
        self.log("[global] Settings saved")
        
        # Show message that restart is needed for language change
        QMessageBox.information(self, "OK", tr("Settings saved!") + "\n" + tr("Restart app for language change."))
        dialog.accept()
    
    def _toggle_token_visibility(self):
        """Toggle API token visibility."""
        if self.show_token_btn.isChecked():
            self.global_api_token.setEchoMode(QLineEdit.Normal)
            self.show_token_btn.setText("🔒")
        else:
            self.global_api_token.setEchoMode(QLineEdit.Password)
            self.show_token_btn.setText("👁")
    
    def _toggle_geo_percent(self, state):
        """Enable/disable geo percent spinner based on checkbox."""
        self.global_geo_percent.setEnabled(state == Qt.Checked)
    
    def _check_for_updates(self):
        """Check for available updates from GitHub."""
        from PyQt5.QtWidgets import QMessageBox
        from core.updater import UpdateChecker
        
        c = CATPPUCCIN
        
        # Update button state
        self.check_updates_btn.setEnabled(False)
        self.check_updates_btn.setText(tr("Checking..."))
        self.update_status_label.setText(tr("Connecting to GitHub..."))
        QApplication.processEvents()
        
        try:
            checker = UpdateChecker()
            result = checker.check_sync()
            
            if result.get("error"):
                self.update_status_label.setText(f"❌ {result['error']}")
                self.update_status_label.setStyleSheet(f"color: {c['red']};")
                
            elif result.get("available"):
                new_version = result["version"]
                current = result.get("current_version", "?")
                
                self.update_status_label.setText(f"✅ {tr('Update available')}: v{new_version}")
                self.update_status_label.setStyleSheet(f"color: {c['green']}; font-weight: bold;")
                
                # Ask user if they want to update
                reply = QMessageBox.question(
                    self,
                    tr("Update Available"),
                    f"{tr('New version available')}: v{new_version}\n"
                    f"{tr('Current version')}: v{current}\n\n"
                    f"{tr('Do you want to download and install the update?')}",
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.Yes
                )
                
                if reply == QMessageBox.Yes:
                    self._start_download_update(result)
            else:
                self.update_status_label.setText(f"✅ {tr('You have the latest version')}")
                self.update_status_label.setStyleSheet(f"color: {c['green']};")
                
        except Exception as e:
            self.update_status_label.setText(f"❌ {str(e)}")
            self.update_status_label.setStyleSheet(f"color: {c['red']};")
        finally:
            self.check_updates_btn.setEnabled(True)
            self.check_updates_btn.setText(tr("Check for updates"))
    
    def _start_download_update(self, update_info: dict):
        """Start downloading update in background thread."""
        from PyQt5.QtWidgets import QProgressDialog, QMessageBox
        from PyQt5.QtCore import QThread, pyqtSignal, Qt
        
        download_url = update_info.get("download_url")
        version = update_info.get("version", "?")
        
        if not download_url:
            QMessageBox.warning(
                self,
                tr("Error"),
                tr("No download URL found for your platform")
            )
            return
        
        # Close settings dialog if open
        if hasattr(self, '_settings_dialog') and self._settings_dialog:
            self._settings_dialog.close()
        
        # Create progress dialog (modal, on top)
        self._update_progress = QProgressDialog(
            tr("Downloading update..."),
            tr("Cancel"),
            0, 100,
            self
        )
        self._update_progress.setWindowTitle(tr("Updating"))
        self._update_progress.setWindowModality(Qt.ApplicationModal)
        self._update_progress.setAutoClose(False)
        self._update_progress.setAutoReset(False)
        self._update_progress.setMinimumDuration(0)
        self._update_progress.setMinimumWidth(400)
        self._update_progress.setValue(0)
        self._update_progress.show()
        self._update_progress.raise_()
        self._update_progress.activateWindow()
        
        # Create and start download thread
        self._download_thread = DownloadThread(download_url, version)
        self._download_thread.progress.connect(self._on_download_progress)
        self._download_thread.finished_signal.connect(self._on_download_finished)
        self._download_thread.error.connect(self._on_download_error)
        
        self._update_progress.canceled.connect(self._download_thread.cancel)
        
        self._download_thread.start()
    
    def _on_download_progress(self, percent: int, status: str):
        """Handle download progress update."""
        if hasattr(self, '_update_progress') and self._update_progress:
            self._update_progress.setValue(percent)
            self._update_progress.setLabelText(status)
    
    def _on_download_finished(self, file_path: str, version: str):
        """Handle download completion."""
        from PyQt5.QtWidgets import QMessageBox
        import subprocess
        import sys
        import os
        
        if hasattr(self, '_update_progress') and self._update_progress:
            self._update_progress.close()
            self._update_progress = None
        
        self.log(f"[Update] Download complete: {file_path}")
        
        # Check file type
        is_installer = file_path.endswith(".exe") and "installer" in file_path.lower()
        is_zip = file_path.endswith(".zip")
        is_dmg = file_path.endswith(".dmg")
        
        if is_zip:
            # For ZIP (portable) - open folder and show message
            folder = os.path.dirname(file_path)
            
            QMessageBox.information(
                self,
                tr("Download Complete"),
                f"{tr('Update downloaded successfully')}!\n\n"
                f"{tr('File')}: {os.path.basename(file_path)}\n\n"
                f"{tr('Please extract the archive and replace the application files')}.\n"
                f"{tr('The download folder will open now')}."
            )
            
            # Open folder with the file
            if sys.platform == "win32":
                subprocess.Popen(f'explorer /select,"{file_path}"', shell=True)
            elif sys.platform == "darwin":
                subprocess.Popen(["open", "-R", file_path])
            else:
                subprocess.Popen(["xdg-open", folder])
                
        elif is_installer or file_path.endswith(".exe"):
            # For EXE installer - ask to run
            reply = QMessageBox.question(
                self,
                tr("Download Complete"),
                f"{tr('Update downloaded successfully')}.\n\n"
                f"{tr('The application will close to install the update')}.\n"
                f"{tr('Continue?')}",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.Yes
            )
            
            if reply == QMessageBox.Yes:
                try:
                    # Run installer and close app
                    subprocess.Popen([file_path], shell=True)
                    QApplication.quit()
                except Exception as e:
                    QMessageBox.warning(
                        self,
                        tr("Error"),
                        f"{tr('Failed to start installer')}: {str(e)}\n\n"
                        f"{tr('File')}: {file_path}"
                    )
                    
        elif is_dmg:
            # For DMG - mount and open
            reply = QMessageBox.question(
                self,
                tr("Download Complete"),
                f"{tr('Update downloaded successfully')}.\n\n"
                f"{tr('The DMG will open. Please drag the app to Applications folder')}.\n"
                f"{tr('Continue?')}",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.Yes
            )
            
            if reply == QMessageBox.Yes:
                try:
                    subprocess.Popen(["open", file_path])
                    QApplication.quit()
                except Exception as e:
                    QMessageBox.warning(
                        self,
                        tr("Error"),
                        f"{tr('Failed to open DMG')}: {str(e)}"
                    )
    
    def _on_download_error(self, error_msg: str):
        """Handle download error."""
        from PyQt5.QtWidgets import QMessageBox
        
        if hasattr(self, '_update_progress') and self._update_progress:
            self._update_progress.close()
            self._update_progress = None
        
        QMessageBox.critical(
            self,
            tr("Download Error"),
            f"{tr('Failed to download update')}:\n{error_msg}"
        )
    
    def _show_youtube_queries_editor(self):
        """Show dialog to edit YouTube search queries."""
        from PyQt5.QtWidgets import QDialog, QDialogButtonBox, QTextEdit
        
        c = CATPPUCCIN
        
        dialog = QDialog(self)
        dialog.setWindowTitle(tr("YouTube Search Queries"))
        dialog.setMinimumSize(650, 500)
        layout = QVBoxLayout(dialog)
        layout.setSpacing(SPACING)
        layout.setContentsMargins(MARGIN, MARGIN, MARGIN, MARGIN)
        
        # Instructions
        info_label = QLabel(tr("Enter search queries separated by commas:"))
        info_label.setStyleSheet(f"font-size: {FONT_SIZE_BASE}px; color: {c['subtext1']};")
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
        self.yt_count_label.setStyleSheet(f"font-size: {FONT_SIZE_SMALL}px; color: {c['subtext0']};")
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
        self.auto_mode_btn.setChecked(mode == "auto")
        
        if mode == "cookie":
            self.mode_stack.setCurrentIndex(0)
            # Show START TEST / STOP TEST buttons for manual test
            self.start_btn.setText("▶ " + tr("START TEST"))
            self.stop_btn.setText("⏹ " + tr("STOP TEST"))
            self.start_btn.setVisible(True)
            self.stop_btn.setVisible(True)
        elif mode == "google":
            self.mode_stack.setCurrentIndex(1)
            # Show START TEST / STOP TEST buttons for manual test
            self.start_btn.setText("▶ " + tr("START TEST"))
            self.stop_btn.setText("⏹ " + tr("STOP TEST"))
            self.start_btn.setVisible(True)
            self.stop_btn.setVisible(True)
        else:  # auto
            self.mode_stack.setCurrentIndex(2)
            # Hide big START/STOP buttons in Auto mode - not needed
            self.start_btn.setVisible(False)
            self.stop_btn.setVisible(False)
        
        self.log(f"Mode: {mode.upper()}")
    
    def _reset_all_working_states(self):
        """Reset all working states to False on startup (cleanup after crash/close)."""
        for mode in ["cookie", "google"]:
            cfg = self.get_mode_config(mode)
            profile_info = cfg.get("profile_info", {})
            changed = False
            for uuid, info in profile_info.items():
                if info.get("working", False):
                    info["working"] = False
                    changed = True
            if changed:
                self.set_mode_config(mode, cfg)
    
    def get_mode_config(self, mode):
        key = "cookie_mode" if mode == "cookie" else "google_mode"
        return self.config.get(key, {"profiles": [], "sites": [], "settings": {}})
    
    def set_mode_config(self, mode, data):
        key = "cookie_mode" if mode == "cookie" else "google_mode"
        self.config[key] = data
        self.save_config()
    
    def apply_theme(self, theme="Light"):
        """Apply theme stylesheet from styles module."""
        self.setStyleSheet(get_theme_stylesheet(theme))
    
    def load_config(self):
        """Load configuration from MongoDB Atlas."""
        try:
            self.db = get_database()
            if not self.db.connect():
                print("[Config] ❌ Failed to connect to MongoDB, using defaults")
                return self.get_default_config()
            
            print("[Config] ✅ Connected to MongoDB Atlas")
            
            # Load global settings
            settings = self.db.get_settings()
            print(f"[Config] ✅ Loaded global settings from DB")
            
            # Load mode settings
            cookie_settings = self.db.get_mode_settings("cookie")
            google_settings = self.db.get_mode_settings("google")
            print(f"[Config] ✅ Loaded mode settings from DB")
            
            # Load profiles with full info (country, first_run, etc.)
            cookie_profiles_full = self.db.get_profiles("cookie")
            google_profiles_full = self.db.get_profiles("google")
            
            # Extract UUIDs and profile_info separately for compatibility
            cookie_profiles = [p.get("uuid", p.get("_id", "")) for p in cookie_profiles_full]
            google_profiles = [p.get("uuid", p.get("_id", "")) for p in google_profiles_full]
            
            # Build profile_info dicts
            cookie_profile_info = {}
            for p in cookie_profiles_full:
                uuid = p.get("uuid", p.get("_id", ""))
                if uuid:
                    info = {k: v for k, v in p.items() if k not in ("uuid", "_id", "mode", "updated_at")}
                    if info:
                        cookie_profile_info[uuid] = info
            
            google_profile_info = {}
            for p in google_profiles_full:
                uuid = p.get("uuid", p.get("_id", ""))
                if uuid:
                    info = {k: v for k, v in p.items() if k not in ("uuid", "_id", "mode", "updated_at")}
                    if info:
                        google_profile_info[uuid] = info
            
            print(f"[Config] ✅ Loaded profiles: {len(cookie_profiles)} cookie, {len(google_profiles)} google")
            if cookie_profile_info:
                print(f"[Config] ✅ Loaded profile info for {len(cookie_profile_info)} cookie profiles")
            if google_profile_info:
                print(f"[Config] ✅ Loaded profile info for {len(google_profile_info)} google profiles")
            
            # Load sites
            cookie_sites = self.db.get_sites("cookie_sites")
            google_sites = self.db.get_sites("google_sites")
            browse_sites = self.db.get_sites("browse_sites")
            onetap_sites = self.db.get_sites("onetap_sites")
            print(f"[Config] ✅ Loaded sites from DB")
            
            # Load YouTube queries
            youtube_queries = self.db.get_youtube_queries()
            print(f"[Config] ✅ Loaded {len(youtube_queries)} YouTube queries")
            
            # Build config dict (for compatibility with existing code)
            config = {
                # Global settings
                "api_url": settings.get("api_url", "http://localhost:58888"),
                "octo_api_token": settings.get("octo_api_token", ""),
                "language": settings.get("language", "English"),
                "theme": settings.get("theme", "Dark"),
                "max_parallel_profiles": settings.get("max_parallel_profiles", 5),
                "base_delay_min": settings.get("base_delay_min", 1),
                "base_delay_max": settings.get("base_delay_max", 3),
                "autosave_logs": settings.get("autosave_logs", False),
                "sound_on_finish": settings.get("sound_on_finish", False),
                "start_minimized": settings.get("start_minimized", False),
                "geo_visiting_enabled": settings.get("geo_visiting_enabled", False),
                "geo_visiting_percent": settings.get("geo_visiting_percent", 70),
                "max_session_duration": settings.get("max_session_duration", 900),
                
                # Auto mode settings (map DB names to UI names)
                "auto_mode": {
                    "sessions_per_profile_min": settings.get("sessions_per_profile_min", 3),
                    "sessions_per_profile_max": settings.get("sessions_per_profile_max", 4),
                    "cooldown_min": settings.get("session_break_min", 60),  # DB uses session_break
                    "cooldown_max": settings.get("session_break_max", 150),  # DB uses session_break
                    "work_start_weekday": settings.get("work_hours_weekday_start", 7),
                    "work_end_weekday": settings.get("work_hours_weekday_end", 23),
                    "work_start_weekend": settings.get("work_hours_weekend_start", 9),
                    "work_end_weekend": settings.get("work_hours_weekend_end", 23),
                    "max_session_duration": settings.get("max_session_duration", 900),
                    # New settings that were missing
                    "start_randomization": settings.get("start_randomization", 30),
                    "stagger_delay_min": settings.get("stagger_delay_min", 15),
                    "stagger_delay_max": settings.get("stagger_delay_max", 30),
                    "max_errors": settings.get("max_errors", 3),
                    "error_action": settings.get("error_action", "skip_today"),
                    "notify_cycle_complete": settings.get("notify_cycle_complete", True),
                    "notify_profile_errors": settings.get("notify_profile_errors", True),
                    "notify_time_shortage": settings.get("notify_time_shortage", True),
                },
                
                # YouTube queries (as comma-separated string for UI compatibility)
                "youtube_queries": ", ".join(youtube_queries) if youtube_queries else "",
                
                # Cookie mode
                "cookie_mode": {
                    "profiles": cookie_profiles,
                    "profile_info": cookie_profile_info,
                    "sites": cookie_sites,
                    "settings": cookie_settings
                },
                
                # Google mode
                "google_mode": {
                    "profiles": google_profiles,
                    "profile_info": google_profile_info,
                    "sites": google_sites,
                    "browse_sites": browse_sites,
                    "onetap_sites": onetap_sites,
                    "settings": google_settings,
                    "youtube_enabled": google_settings.get("youtube_enabled", True),
                    "services": google_settings.get("services", {})
                }
            }
            
            return config
            
        except Exception as e:
            print(f"[Config] ❌ Error loading config from DB: {e}")
            import traceback
            traceback.print_exc()
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
        """
        Schedule configuration save to MongoDB Atlas.
        Uses debouncing to prevent excessive writes - actual save happens 500ms after last call.
        """
        if not self._save_pending:
            self._save_pending = True
        
        # Reset timer - actual save will happen 500ms after last call
        self._save_timer.stop()
        self._save_timer.start(500)  # 500ms debounce
    
    def _do_save_config(self):
        """Actually save configuration to MongoDB Atlas (called by debounce timer)."""
        self._save_pending = False
        
        try:
            if not hasattr(self, 'db') or not self.db or not self.db.is_connected():
                print("[Config] ❌ DB not connected, cannot save")
                return
            
            # 1. Save global settings
            settings = {
                "api_url": self.config.get("api_url", "http://localhost:58888"),
                "octo_api_token": self.config.get("octo_api_token", ""),
                "language": self.config.get("language", "English"),
                "theme": self.config.get("theme", "Dark"),
                "max_parallel_profiles": self.config.get("max_parallel_profiles", 5),
                "base_delay_min": self.config.get("base_delay_min", 1),
                "base_delay_max": self.config.get("base_delay_max", 3),
                "autosave_logs": self.config.get("autosave_logs", False),
                "sound_on_finish": self.config.get("sound_on_finish", False),
                "start_minimized": self.config.get("start_minimized", False),
                "geo_visiting_enabled": self.config.get("geo_visiting_enabled", False),
                "geo_visiting_percent": self.config.get("geo_visiting_percent", 70),
                "max_session_duration": self.config.get("max_session_duration", 900),
            }
            
            # Add auto mode settings
            auto_mode = self.config.get("auto_mode", {})
            settings.update({
                "sessions_per_profile_min": auto_mode.get("sessions_per_profile_min", 3),
                "sessions_per_profile_max": auto_mode.get("sessions_per_profile_max", 4),
                "session_break_min": auto_mode.get("cooldown_min", 60),  # UI uses cooldown_min
                "session_break_max": auto_mode.get("cooldown_max", 150),  # UI uses cooldown_max
                "work_hours_weekday_start": auto_mode.get("work_start_weekday", 7),
                "work_hours_weekday_end": auto_mode.get("work_end_weekday", 23),
                "work_hours_weekend_start": auto_mode.get("work_start_weekend", 9),
                "work_hours_weekend_end": auto_mode.get("work_end_weekend", 23),
                "max_session_duration": auto_mode.get("max_session_duration", 900),
                # New settings
                "start_randomization": auto_mode.get("start_randomization", 30),
                "stagger_delay_min": auto_mode.get("stagger_delay_min", 15),
                "stagger_delay_max": auto_mode.get("stagger_delay_max", 30),
                "max_errors": auto_mode.get("max_errors", 3),
                "error_action": auto_mode.get("error_action", "skip_today"),
                "notify_cycle_complete": auto_mode.get("notify_cycle_complete", True),
                "notify_profile_errors": auto_mode.get("notify_profile_errors", True),
                "notify_time_shortage": auto_mode.get("notify_time_shortage", True),
            })
            
            if self.db.save_settings(settings):
                print("[Config] ✅ Saved global settings to DB")
            else:
                print("[Config] ❌ Failed to save global settings")
            
            # 2. Save mode settings
            cookie_mode = self.config.get("cookie_mode", {})
            google_mode = self.config.get("google_mode", {})
            
            if self.db.save_mode_settings("cookie", cookie_mode.get("settings", {})):
                print("[Config] ✅ Saved cookie mode settings to DB")
            else:
                print("[Config] ❌ Failed to save cookie mode settings")
            
            # Google mode settings include services and youtube_enabled
            google_settings = google_mode.get("settings", {}).copy()
            google_settings["youtube_enabled"] = google_mode.get("youtube_enabled", True)
            google_settings["services"] = google_mode.get("services", {})
            
            if self.db.save_mode_settings("google", google_settings):
                print("[Config] ✅ Saved google mode settings to DB")
            else:
                print("[Config] ❌ Failed to save google mode settings")
            
            # 3. Save profiles with their info (country, first_run, etc.)
            cookie_profiles_raw = cookie_mode.get("profiles", [])
            google_profiles_raw = google_mode.get("profiles", [])
            cookie_info = cookie_mode.get("profile_info", {})
            google_info = google_mode.get("profile_info", {})
            
            # Build full profile objects with info
            cookie_profiles_full = []
            for uuid in cookie_profiles_raw:
                profile_data = {"uuid": uuid}
                if uuid in cookie_info:
                    profile_data.update(cookie_info[uuid])
                cookie_profiles_full.append(profile_data)
            
            google_profiles_full = []
            for uuid in google_profiles_raw:
                profile_data = {"uuid": uuid}
                if uuid in google_info:
                    profile_data.update(google_info[uuid])
                google_profiles_full.append(profile_data)
            
            if self.db.save_profiles(cookie_profiles_full, "cookie"):
                print(f"[Config] ✅ Saved {len(cookie_profiles_full)} cookie profiles to DB")
            else:
                print("[Config] ❌ Failed to save cookie profiles")
            
            if self.db.save_profiles(google_profiles_full, "google"):
                print(f"[Config] ✅ Saved {len(google_profiles_full)} google profiles to DB")
            else:
                print("[Config] ❌ Failed to save google profiles")
            
            # 4. Save sites
            if self.db.save_sites("cookie_sites", cookie_mode.get("sites", [])):
                print(f"[Config] ✅ Saved cookie sites to DB")
            
            if self.db.save_sites("google_sites", google_mode.get("sites", [])):
                print(f"[Config] ✅ Saved google sites to DB")
            
            if self.db.save_sites("browse_sites", google_mode.get("browse_sites", [])):
                print(f"[Config] ✅ Saved browse sites to DB")
            
            if self.db.save_sites("onetap_sites", google_mode.get("onetap_sites", [])):
                print(f"[Config] ✅ Saved onetap sites to DB")
            
            # 5. Save YouTube queries
            youtube_queries = self.config.get("youtube_queries", "")
            if youtube_queries:
                keywords = [q.strip() for q in youtube_queries.split(",") if q.strip()]
                if self.db.save_youtube_queries(keywords):
                    print(f"[Config] ✅ Saved {len(keywords)} YouTube queries to DB")
            
        except Exception as e:
            print(f"[Config] ❌ Error saving config to DB: {e}")
            import traceback
            traceback.print_exc()
    
    def log(self, msg):
        """Log message to UI with throttling to prevent UI freeze."""
        timestamp = datetime.now().strftime('%H:%M:%S')
        log_line = f"[{timestamp}] {msg}"
        
        # Use buffered logging to prevent UI freeze
        if not hasattr(self, '_log_buffer'):
            self._log_buffer = []
            self._log_timer = None
        
        self._log_buffer.append(log_line)
        
        # Batch logs - update UI max once per 100ms
        if self._log_timer is None:
            from PyQt5.QtCore import QTimer
            self._log_timer = QTimer()
            self._log_timer.setSingleShot(True)
            self._log_timer.timeout.connect(self._flush_log_buffer)
            self._log_timer.start(100)  # 100ms delay
        
        # Auto-save logs to file if enabled (write immediately)
        if self.config.get("autosave_logs", False):
            self._save_log_to_file(log_line)
    
    def _flush_log_buffer(self):
        """Flush buffered log messages to UI."""
        if not hasattr(self, '_log_buffer') or not self._log_buffer:
            self._log_timer = None
            return
        
        # Join all buffered messages and append at once
        batch = '\n'.join(self._log_buffer)
        self._log_buffer.clear()
        self._log_timer = None
        
        # Single UI update instead of multiple
        self.log_area.append(batch)
    
    def connect_to_octo(self):
        url = self.api_url_input.text()
        self.config["api_url"] = url
        self.save_config()
        
        port = int(url.split(":")[-1]) if ":" in url else 58888
        self.octo_api = OctoAPI(local_port=port)
        
        if self.octo_api.test_connection():
            self.connection_status.setText("●")
            self.connection_status.setStyleSheet(f"color: {CATPPUCCIN['green']}; font-size: {FONT_SIZE_LARGE}px;")
            self.start_btn.setEnabled(True)
            self.log("Connected to Octo Browser")
            
            # Initialize async API manager
            self._init_api_manager()
            
            # Auto-check all proxies after connection
            QTimer.singleShot(500, self._auto_check_all_proxies)
        else:
            self.connection_status.setStyleSheet(f"color: {CATPPUCCIN['red']}; font-size: {FONT_SIZE_LARGE}px;")
            self.log("Connection failed")
    
    def _init_api_manager(self):
        """Initialize the async API manager."""
        if self.api_manager:
            self.api_manager.shutdown()
        
        self.api_manager = OctoApiManager(self.octo_api)
        
        # Set API token for remote API access
        api_token = self.config.get("octo_api_token", "")
        if api_token:
            self.api_manager.set_api_token(api_token)
        
        # Connect signals for progress tracking
        self.api_manager.operation_progress.connect(self._on_api_progress)
        self.api_manager.operation_finished.connect(self._on_api_finished)
        self.api_manager.operation_error.connect(self._on_api_error)
        self.api_manager.operation_cancelled.connect(self._on_api_cancelled)
        self.api_manager.profile_stopped.connect(self._on_profile_stopped_async)
        
        logging.info("[MainWindow] Async API manager initialized")
    
    def _on_api_progress(self, task_id: str, current: int, total: int, message: str):
        """Handle async API progress update."""
        try:
            if self._async_progress_dialog and self._current_async_task == task_id:
                self._async_progress_dialog.setValue(current)
                self._async_progress_dialog.setLabelText(f"{message}")
        except (RuntimeError, AttributeError):
            # Dialog was closed/destroyed
            pass
    
    def _on_api_finished(self, task_id: str, result: object):
        """Handle async API task completion."""
        try:
            if self._async_progress_dialog and self._current_async_task == task_id:
                self._async_progress_dialog.close()
        except (RuntimeError, AttributeError):
            pass
        finally:
            self._async_progress_dialog = None
            self._current_async_task = None
    
    def _on_api_error(self, task_id: str, error: str):
        """Handle async API error."""
        try:
            if self._async_progress_dialog:
                self._async_progress_dialog.close()
        except (RuntimeError, AttributeError):
            pass
        finally:
            self._async_progress_dialog = None
            self._current_async_task = None
            self.log(f"API Error: {error}")
    
    def _on_api_cancelled(self, task_id: str):
        """Handle async API cancellation."""
        try:
            if self._async_progress_dialog:
                self._async_progress_dialog.close()
        except (RuntimeError, AttributeError):
            pass
        finally:
            self._async_progress_dialog = None
            self._current_async_task = None
            self.log("Operation cancelled")
    
    def _on_profile_stopped_async(self, uuid: str, success: bool):
        """Handle individual profile stopped in batch operation."""
        if success:
            self.log(f"[Auto] ⏹ Stopped {uuid[:8]}...")
        else:
            self.log(f"[Auto] ⚠️ Failed to stop {uuid[:8]}...")
    
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
            # Paused and proxy status (persisted across UI refreshes)
            paused = info.get("paused", False)
            proxy_status = info.get("proxy_status", None)  # True/False/None
            working = info.get("working", False)  # Working state from DB
            
            item = QListWidgetItem()
            item.setData(Qt.UserRole, uuid)  # Store UUID in item data
            
            # Create custom widget with mode and states
            widget = ProfileItemWidget(
                uuid, country, first_run, mode, 
                google_authorized, ads_registered, payment_linked, campaign_launched,
                profile_ready, ads_timestamp, payment_timestamp, campaign_timestamp, ready_timestamp,
                paused, proxy_status, working
            )
            widget.copy_clicked.connect(lambda u: self.log(f"Copied: {u}"))
            widget.play_clicked.connect(self._on_play_profile)
            widget.proxy_check_clicked.connect(self._on_proxy_check)
            widget.paused_changed.connect(self._on_profile_paused_changed)
            widget.proxy_status_changed.connect(self._on_proxy_status_changed)
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
            
            # Disable Play button if Auto mode is running
            if self.auto_state.is_auto_running():
                widget.play_btn.setEnabled(False)
                widget.play_btn.setStyleSheet("""
                    QPushButton {
                        font-weight: bold;
                        color: #666;
                        border: 1px solid #444;
                        border-radius: 4px;
                        background: transparent;
                    }
                """)
    
    def add_profile(self, mode):
        inp = self.get_profile_input(mode)
        uuid = inp.text().strip()
        if uuid:
            # Check if UUID already exists in the OTHER mode
            other_mode = "google" if mode == "cookie" else "cookie"
            other_cfg = self.get_mode_config(other_mode)
            other_profiles = other_cfg.get("profiles", [])
            
            if uuid in other_profiles:
                if mode == "cookie":
                    # Trying to add to Cookie, but exists in Google
                    QMessageBox.warning(
                        self, 
                        tr("Cannot Add Profile"),
                        tr("This profile is already in Google mode!\n\nProfiles cannot exist in both modes simultaneously.")
                    )
                else:
                    # Trying to add to Google, but exists in Cookie
                    QMessageBox.warning(
                        self, 
                        tr("Cannot Add Profile"),
                        tr("This profile exists in Cookie mode.\n\nUse the migration button (→) in Cookie mode to move it to Google mode.")
                    )
                inp.clear()
                return
            
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
                
                widget = ProfileItemWidget(uuid, country, "", mode, False, False, False, False, False, "", "", "", "", False, None, False)
                widget.copy_clicked.connect(lambda u: self.log(f"Copied: {u}"))
                widget.play_clicked.connect(self._on_play_profile)
                widget.proxy_check_clicked.connect(self._on_proxy_check)
                widget.paused_changed.connect(self._on_profile_paused_changed)
                widget.proxy_status_changed.connect(self._on_proxy_status_changed)
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
                
                # Disable Play button if Auto mode is running
                if self.auto_state.is_auto_running():
                    widget.play_btn.setEnabled(False)
                    widget.play_btn.setStyleSheet("""
                        QPushButton {
                            font-weight: bold;
                            color: #666;
                            border: 1px solid #444;
                            border-radius: 4px;
                            background: transparent;
                        }
                    """)
                
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
    
    def _on_play_profile(self, uuid: str):
        """
        Toggle profile manual run state.
        If not running - starts the browser profile for manual operator interaction.
        If running - stops the profile.
        """
        if not self.octo_api:
            QMessageBox.warning(
                self,
                tr("Error"),
                tr("Not connected to Octo Browser!")
            )
            return
        
        # Find the widget for this profile to check/update its state
        widget = self._find_profile_widget(uuid)
        
        # Check if profile is running in automation mode
        if uuid in self.workers or uuid in self.auto_workers:
            QMessageBox.information(
                self,
                tr("Profile Running"),
                tr("This profile is running in automation mode. Stop automation first.")
            )
            return
        
        # Check if manually running - if so, stop it
        if uuid in self._manually_running_profiles:
            self._stop_manual_profile(uuid, widget)
            return
        
        # Start profile without minimized mode (normal window)
        self.log(f"[{uuid[:8]}] Opening profile manually...")
        
        try:
            result = self.octo_api.start_profile(uuid, minimized=False)
            
            if result and "error" not in result:
                self.log(f"[{uuid[:8]}] Profile opened successfully")
                # Track as manually running with start time for grace period
                import time
                self._manually_running_profiles.add(uuid)
                self._manual_profile_start_times[uuid] = time.time()
                # Update widget appearance
                if widget:
                    widget.set_manually_running(True)
            else:
                error_msg = result.get("error", "Unknown error") if result else "Failed to start"
                self.log(f"[{uuid[:8]}] Failed to open: {error_msg}")
                QMessageBox.warning(
                    self,
                    tr("Error"),
                    tr("Failed to open profile:") + f"\n{error_msg}"
                )
        except Exception as e:
            self.log(f"[{uuid[:8]}] Error opening profile: {e}")
            QMessageBox.warning(
                self,
                tr("Error"),
                tr("Error opening profile:") + f"\n{str(e)}"
            )
    
    def _stop_manual_profile(self, uuid: str, widget=None):
        """Stop a manually running profile."""
        self.log(f"[{uuid[:8]}] Stopping manual profile...")
        
        try:
            result = self.octo_api.stop_profile(uuid)
            
            if result and "error" not in result:
                self.log(f"[{uuid[:8]}] Profile stopped")
            else:
                # Even if API returns error, profile might already be closed
                self.log(f"[{uuid[:8]}] Profile stop result: {result}")
        except Exception as e:
            self.log(f"[{uuid[:8]}] Error stopping profile: {e}")
        
        # Remove from tracking regardless of API result
        self._manually_running_profiles.discard(uuid)
        self._manual_profile_start_times.pop(uuid, None)  # Clean up start time
        
        # Update widget appearance
        if widget:
            widget.set_manually_running(False)
    
    def _find_profile_widget(self, uuid: str):
        """Find ProfileItemWidget by UUID in both lists."""
        for lst in [self.cookie_profiles_list, self.google_profiles_list]:
            for i in range(lst.count()):
                item = lst.item(i)
                if item and item.data(Qt.UserRole) == uuid:
                    return lst.itemWidget(item)
        return None
    
    def _set_profile_working(self, uuid: str, working: bool, mode: str = None):
        """
        Set profile working state (UI + DB).
        Called when profile starts/stops in Auto mode.
        """
        # Update UI
        widget = self._find_profile_widget(uuid)
        if widget:
            widget.set_working(working)
        
        # Find mode if not provided
        if mode is None:
            for m in ["cookie", "google"]:
                cfg = self.get_mode_config(m)
                if uuid in cfg.get("profiles", []):
                    mode = m
                    break
        
        if not mode:
            return
        
        # Save to DB
        cfg = self.get_mode_config(mode)
        profile_info = cfg.setdefault("profile_info", {})
        if uuid not in profile_info:
            profile_info[uuid] = {}
        profile_info[uuid]["working"] = working
        self.set_mode_config(mode, cfg)
    
    def _on_proxy_check(self, uuid: str):
        """Handle manual proxy check for a single profile."""
        if not self.api_manager:
            self.log(f"[{uuid[:8]}] Cannot check proxy - not connected")
            return
        
        if not self.config.get("octo_api_token"):
            self.log(f"[{uuid[:8]}] Cannot check proxy - API token not set (add in Settings)")
            widget = self._find_profile_widget(uuid)
            if widget:
                widget.set_proxy_status(False, "No API token")
            return
        
        widget = self._find_profile_widget(uuid)
        if widget:
            widget.set_proxy_checking(True)
        
        self.log(f"[{uuid[:8]}] Checking proxy...")
        
        # Use async check
        self.api_manager.check_proxy_async(
            uuid,
            callback=lambda result: self._on_proxy_check_result(uuid, result),
            error_callback=lambda msg: self._on_proxy_check_error(uuid, msg)
        )
    
    def _on_proxy_check_result(self, uuid: str, result: dict):
        """Handle proxy check result for a single profile."""
        actual_result = result.get("result", {})
        success = actual_result.get("success", False)
        message = actual_result.get("message", "")
        ip = actual_result.get("ip", "")
        country = actual_result.get("country", "")
        
        widget = self._find_profile_widget(uuid)
        if widget:
            if success and ip:
                widget.set_proxy_status(True, f"IP: {ip}")
            else:
                widget.set_proxy_status(success, message)
            
            # Update geo if widget has no country and we got country from proxy check
            if success and not widget.country_code:
                if country:
                    # Use country from proxy check result
                    self._update_profile_geo_direct(uuid, widget, country)
                else:
                    # Fallback to API lookup
                    self._update_profile_geo_from_api(uuid, widget)
        
        status = "✓ OK" if success else f"✗ {message}"
        self.log(f"[{uuid[:8]}] Proxy: {status}")
    
    def _on_proxy_check_error(self, uuid: str, error: str):
        """Handle proxy check error."""
        widget = self._find_profile_widget(uuid)
        if widget:
            widget.set_proxy_status(False, error)
        
        self.log(f"[{uuid[:8]}] Proxy check error: {error}")
    
    def _auto_check_all_proxies(self):
        """Auto-check all proxies after Octo connection."""
        if not self.api_manager:
            return
        
        # Check if API token is set
        if not self.config.get("octo_api_token"):
            self.log("Proxy check skipped - no API token (add in Settings)")
            return
        
        # Collect all profile UUIDs
        all_uuids = []
        
        cookie_cfg = self.get_mode_config("cookie")
        google_cfg = self.get_mode_config("google")
        
        all_uuids.extend(cookie_cfg.get("profiles", []))
        all_uuids.extend(google_cfg.get("profiles", []))
        
        if not all_uuids:
            return
        
        self.log(f"Auto-checking proxies for {len(all_uuids)} profiles...")
        
        # Set all widgets to checking state
        for uuid in all_uuids:
            widget = self._find_profile_widget(uuid)
            if widget:
                widget.set_proxy_checking(True)
        
        # Store task ID for batch operation
        self._proxy_check_task_id = self.api_manager.check_proxies_batch_async(
            all_uuids,
            callback=self._on_batch_proxy_check_done
        )
    
    def _on_batch_proxy_check_done(self, result: dict):
        """Handle batch proxy check completion (auto-check on connect)."""
        results = result.get("results", {})
        
        ok_count = 0
        fail_count = 0
        geo_updated = 0
        
        for uuid, check_result in results.items():
            success = check_result.get("success", False)
            message = check_result.get("message", "")
            ip = check_result.get("ip", "")
            country = check_result.get("country", "")
            
            widget = self._find_profile_widget(uuid)
            if widget:
                if success and ip:
                    widget.set_proxy_status(True, f"IP: {ip}")
                else:
                    widget.set_proxy_status(success, message)
                
                # Update geo if widget has no country and we got country from check
                if success and not widget.country_code and country:
                    if self._update_profile_geo_direct(uuid, widget, country):
                        geo_updated += 1
            
            if success:
                ok_count += 1
            else:
                fail_count += 1
        
        msg = f"Proxy check complete: {ok_count} OK, {fail_count} failed"
        if geo_updated > 0:
            msg += f", {geo_updated} geo updated"
        self.log(msg)
    
    def _refresh_all_proxies_and_geo(self):
        """
        Refresh all proxies and update geo for profiles without country.
        Called by the refresh button (🔄) near API URL.
        """
        if not self.api_manager:
            QMessageBox.warning(self, "Error", tr("Not connected to Octo Browser"))
            return
        
        if not self.config.get("octo_api_token"):
            QMessageBox.warning(self, "Error", tr("API token not set (add in Settings)"))
            return
        
        # Collect all profile UUIDs from both modes
        all_uuids = []
        cookie_cfg = self.get_mode_config("cookie")
        google_cfg = self.get_mode_config("google")
        
        all_uuids.extend(cookie_cfg.get("profiles", []))
        all_uuids.extend(google_cfg.get("profiles", []))
        
        if not all_uuids:
            self.log("No profiles to check")
            return
        
        self.log(f"🔄 Refreshing proxies & geo for {len(all_uuids)} profiles...")
        
        # Set all widgets to checking state
        for uuid in all_uuids:
            widget = self._find_profile_widget(uuid)
            if widget:
                widget.set_proxy_checking(True)
        
        # Run batch proxy check with geo update
        self.api_manager.check_proxies_batch_async(
            all_uuids,
            callback=self._on_refresh_proxies_and_geo_done
        )
    
    def _on_refresh_proxies_and_geo_done(self, result: dict):
        """Handle batch proxy check + geo update completion."""
        results = result.get("results", {})
        
        ok_count = 0
        fail_count = 0
        geo_updated = 0
        
        for uuid, check_result in results.items():
            success = check_result.get("success", False)
            message = check_result.get("message", "")
            ip = check_result.get("ip", "")
            country = check_result.get("country", "")
            
            widget = self._find_profile_widget(uuid)
            if widget:
                if success and ip:
                    widget.set_proxy_status(True, f"IP: {ip}")
                else:
                    widget.set_proxy_status(success, message)
            
            if success:
                ok_count += 1
                # Try to update geo if widget has no country
                if widget and not widget.country_code:
                    if country:
                        # Use country from proxy check result (ip-api.com geolocation)
                        if self._update_profile_geo_direct(uuid, widget, country):
                            geo_updated += 1
                    else:
                        # Fallback to API lookup
                        if self._update_profile_geo_from_api(uuid, widget):
                            geo_updated += 1
            else:
                fail_count += 1
        
        msg = f"🔄 Proxy check complete: {ok_count} OK, {fail_count} failed"
        if geo_updated > 0:
            msg += f", {geo_updated} geo updated"
        self.log(msg)
    
    def _update_profile_geo_direct(self, uuid: str, widget, country_code: str) -> bool:
        """
        Update profile geo directly with provided country code.
        Returns True if geo was updated.
        """
        try:
            new_code = country_code.upper() if country_code else ""
            if not new_code or len(new_code) != 2:
                return False
            
            # Find which mode this profile belongs to
            mode = None
            for m in ["cookie", "google"]:
                cfg = self.get_mode_config(m)
                if uuid in cfg.get("profiles", []):
                    mode = m
                    break
            
            if not mode:
                return False
            
            # Update config
            cfg = self.get_mode_config(mode)
            profile_info = cfg.setdefault("profile_info", {})
            if uuid not in profile_info:
                profile_info[uuid] = {}
            profile_info[uuid]["country"] = new_code
            self.set_mode_config(mode, cfg)
            
            # Update widget
            widget.country_code = new_code
            
            # Update flag label
            app_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            flag_path = os.path.join(app_dir, "assets", "flags", f"{new_code.lower()}.png")
            if os.path.exists(flag_path):
                pixmap = QPixmap(flag_path)
                if not pixmap.isNull():
                    widget.flag_label.setPixmap(pixmap.scaled(24, 16, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            else:
                flag_emoji = COUNTRY_FLAGS.get(new_code, "🌐")
                widget.flag_label.setText(flag_emoji)
            
            # Update country code label and show it
            widget.code_label.setText(f"({new_code})")
            widget.code_label.show()
            
            self.log(f"[{uuid[:8]}] 🌍 Geo: {new_code}")
            return True
            
        except Exception as e:
            print(f"[Geo] Error updating geo for {uuid[:8]}: {e}")
            return False
    
    def _update_profile_geo_from_api(self, uuid: str, widget) -> bool:
        """
        Fetch profile geo from Octo API and update widget + config.
        Tries Remote API first (works even if profile never started), then Local API.
        Returns True if geo was updated.
        """
        if not self.octo_api:
            return False
        
        try:
            new_country = ""
            
            # Try Remote API first (works even if profile never started)
            if self.octo_api.api_token:
                new_country = self.octo_api.get_profile_country_from_remote_api(uuid)
            
            # Fallback to Local API
            if not new_country:
                info = self.octo_api.get_profile_info(uuid)
                if info:
                    new_country = info.get("country", "")
            
            if not new_country:
                print(f"[Geo] No country found for {uuid[:8]}")
                return False
            
            # Normalize country code
            new_code = normalize_country(new_country)
            if not new_code:
                # If not in mapping, try using as-is if it's 2 chars
                if len(new_country) == 2 and new_country.isalpha():
                    new_code = new_country.upper()
                else:
                    print(f"[Geo] Cannot normalize country '{new_country}' for {uuid[:8]}")
                    return False
            
            # Find which mode this profile belongs to
            mode = None
            for m in ["cookie", "google"]:
                cfg = self.get_mode_config(m)
                if uuid in cfg.get("profiles", []):
                    mode = m
                    break
            
            if not mode:
                return False
            
            # Update config
            cfg = self.get_mode_config(mode)
            profile_info = cfg.setdefault("profile_info", {})
            if uuid not in profile_info:
                profile_info[uuid] = {}
            profile_info[uuid]["country"] = new_code
            self.set_mode_config(mode, cfg)
            
            # Update widget
            widget.country_code = new_code
            
            # Update flag label
            app_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            flag_path = os.path.join(app_dir, "assets", "flags", f"{new_code.lower()}.png")
            if os.path.exists(flag_path):
                pixmap = QPixmap(flag_path)
                if not pixmap.isNull():
                    widget.flag_label.setPixmap(pixmap.scaled(24, 16, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            else:
                flag_emoji = COUNTRY_FLAGS.get(new_code, "🌐")
                widget.flag_label.setText(flag_emoji)
            
            # Update country code label and show it
            widget.code_label.setText(f"({new_code})")
            widget.code_label.show()
            
            self.log(f"[{uuid[:8]}] 🌍 Geo: {new_code}")
            return True
            
        except Exception as e:
            print(f"[Geo] Error updating geo for {uuid[:8]}: {e}")
            return False
    
    def _check_proxies_before_start(self, mode: str, profile_uuids: list):
        """
        Check proxies before starting work (auto mode or test mode).
        This runs asynchronously and updates UI with results.
        
        Args:
            mode: "auto", "cookie", or "google"
            profile_uuids: List of profile UUIDs to check
        """
        if not self.api_manager:
            self.log(f"[Proxy] Cannot check - API manager not initialized")
            return
        
        if not self.config.get("octo_api_token"):
            self.log(f"[Proxy] Cannot check - API token not set (add in Settings)")
            return
        
        if not profile_uuids:
            return
        
        self.log(f"[Proxy] Checking {len(profile_uuids)} profiles ({mode} mode)...")
        
        # Set all widgets to checking state
        for uuid in profile_uuids:
            widget = self._find_profile_widget(uuid)
            if widget:
                widget.set_proxy_checking(True)
        
        # Run async check
        self.api_manager.check_proxies_batch_async(
            profile_uuids,
            callback=lambda result: self._on_proxies_checked(mode, result)
        )
    
    def _on_proxies_checked(self, mode: str, result: dict):
        """Handle proxy check results for batch operation."""
        results = result.get("results", {})
        
        ok_count = 0
        fail_count = 0
        failed_profiles = []
        
        for uuid, check_result in results.items():
            success = check_result.get("success", False)
            message = check_result.get("message", "")
            ip = check_result.get("ip", "")
            
            widget = self._find_profile_widget(uuid)
            if widget:
                if success and ip:
                    widget.set_proxy_status(True, f"IP: {ip}")
                else:
                    widget.set_proxy_status(success, message)
            
            if success:
                ok_count += 1
            else:
                fail_count += 1
                failed_profiles.append(uuid[:8])
        
        self.log(f"[Proxy] Check complete ({mode}): {ok_count} OK, {fail_count} failed")
        
        if fail_count > 0:
            self.log(f"[Proxy] Failed: {', '.join(failed_profiles)}")
    
    def _check_manual_profiles_status(self):
        """
        Periodically check if manually opened profiles are still running.
        Updates Play button state when profile is closed externally.
        Uses background thread to avoid UI freeze.
        
        Only runs when:
        - Auto mode is NOT running
        - At least one profile was manually opened via Play button
        """
        # Skip if auto mode is running
        if self.auto_state.is_auto_running():
            return
        
        # Skip if no manually running profiles
        if not self._manually_running_profiles:
            return
        
        # Skip if no API connection
        if not self.octo_api:
            return
        
        # Don't start another check if one is already running
        if hasattr(self, '_profile_check_running') and self._profile_check_running:
            return
        
        self._profile_check_running = True
        
        # Run in background thread
        import threading
        thread = threading.Thread(target=self._check_manual_profiles_thread, daemon=True)
        thread.start()
    
    def _check_manual_profiles_thread(self):
        """Background thread for checking profile status."""
        import time
        GRACE_PERIOD_SECONDS = 10  # Don't check profiles for first 10 seconds after start
        
        try:
            current_time = time.time()
            closed_profiles = set()
            
            # Copy to avoid modification during iteration
            profiles_to_check = list(self._manually_running_profiles)
            
            for uuid in profiles_to_check:
                # Skip if within grace period
                start_time = self._manual_profile_start_times.get(uuid, 0)
                if current_time - start_time < GRACE_PERIOD_SECONDS:
                    continue  # Too soon to check this profile
                
                # Check if profile is still running using reliable method
                if not self.octo_api.is_profile_running(uuid):
                    closed_profiles.add(uuid)
            
            if closed_profiles:
                # Schedule UI update on main thread
                from PyQt5.QtCore import QMetaObject, Qt, Q_ARG
                for uuid in closed_profiles:
                    # Use invokeMethod to safely call from background thread
                    QMetaObject.invokeMethod(
                        self, 
                        "_update_manual_profile_closed",
                        Qt.QueuedConnection,
                        Q_ARG(str, uuid)
                    )
        except Exception as e:
            pass  # Silent fail
        finally:
            self._profile_check_running = False
    
    @pyqtSlot(str)
    def _update_manual_profile_closed(self, uuid: str):
        """Update UI when manually opened profile is closed. Called from main thread."""
        widget = self._find_profile_widget(uuid)
        if widget:
            widget.set_manually_running(False)
        self._manually_running_profiles.discard(uuid)
        self._manual_profile_start_times.pop(uuid, None)  # Clean up start time
    
    def _set_play_buttons_enabled(self, enabled: bool):
        """Enable or disable Play buttons on all profile widgets."""
        for lst in [self.cookie_profiles_list, self.google_profiles_list]:
            for i in range(lst.count()):
                item = lst.item(i)
                if item:
                    widget = lst.itemWidget(item)
                    if widget and hasattr(widget, 'play_btn'):
                        widget.play_btn.setEnabled(enabled)
                        if not enabled:
                            # Gray out style when disabled
                            widget.play_btn.setStyleSheet("""
                                QPushButton {
                                    font-weight: bold;
                                    color: #666;
                                    border: 1px solid #444;
                                    border-radius: 4px;
                                    background: transparent;
                                }
                            """)
                        else:
                            # Restore normal style based on running state
                            if hasattr(widget, '_is_manually_running') and widget._is_manually_running:
                                widget.set_manually_running(True)
                            else:
                                widget.set_manually_running(False)
    
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
    
    def _on_profile_paused_changed(self, uuid: str, paused: bool):
        """Save profile paused state and update scheduler in real-time."""
        # Find which mode this profile belongs to
        mode = None
        for m in ["cookie", "google"]:
            cfg = self.get_mode_config(m)
            if uuid in cfg.get("profiles", []):
                mode = m
                break
        
        if not mode:
            return
        
        cfg = self.get_mode_config(mode)
        profile_info = cfg.setdefault("profile_info", {})
        
        if uuid not in profile_info:
            profile_info[uuid] = {}
        
        profile_info[uuid]["paused"] = paused
        self.set_mode_config(mode, cfg)
        
        # Update scheduler in real-time if auto mode is running
        if self.auto_state.is_auto_running():
            if paused:
                # Remove from scheduler so it won't be picked up
                self.auto_scheduler.remove_profile(uuid)
                self.log(f"[{uuid[:8]}] ⏸ PAUSED - removed from auto scheduler")
            else:
                # Add back to scheduler with current state
                country = profile_info.get(uuid, {}).get("country", "UNKNOWN")
                sessions = self.auto_state.get_profile_sessions_today(uuid)
                errors = self.auto_state.get_profile_errors_today(uuid)
                last_session = self.auto_state.get_last_session_time(uuid)
                target_sessions = self.auto_state.get_profile_target_sessions(uuid)
                
                self.auto_scheduler.add_profile(
                    uuid=uuid,
                    mode=mode,
                    country=country,
                    sessions_today=sessions,
                    errors_today=errors,
                    target_sessions=target_sessions,
                    last_session_end=last_session
                )
                self.log(f"[{uuid[:8]}] ▶ RESUMED - added back to auto scheduler")
        else:
            status = "⏸ PAUSED" if paused else "▶ RESUMED"
            self.log(f"[{uuid[:8]}] {status}")
    
    def _on_proxy_status_changed(self, uuid: str, status: object):
        """Save proxy status to database for persistence across UI refreshes."""
        # Find which mode this profile belongs to
        mode = None
        for m in ["cookie", "google"]:
            cfg = self.get_mode_config(m)
            if uuid in cfg.get("profiles", []):
                mode = m
                break
        
        if not mode:
            return
        
        cfg = self.get_mode_config(mode)
        profile_info = cfg.setdefault("profile_info", {})
        
        if uuid not in profile_info:
            profile_info[uuid] = {}
        
        # Save proxy status (True/False/None)
        profile_info[uuid]["proxy_status"] = status
        self.set_mode_config(mode, cfg)
    
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
        
        if not profiles:
            self.log(f"[{mode}] No profiles to refresh")
            return
        
        if self.api_manager:
            # Async refresh with progress
            self._refresh_mode = mode
            self._async_progress_dialog = QProgressDialog(
                tr("Refreshing profile info..."),
                tr("Cancel"),
                0, len(profiles),
                self
            )
            self._async_progress_dialog.setWindowModality(Qt.WindowModal)
            self._async_progress_dialog.setAutoClose(True)
            self._async_progress_dialog.show()
            
            self._current_async_task = self.api_manager.get_profiles_info_batch_async(
                profiles,
                callback=self._on_refresh_profiles_complete
            )
        else:
            # Sync fallback
            self._refresh_profiles_sync(mode)
    
    def _refresh_profiles_sync(self, mode):
        """Synchronous profile refresh (fallback)."""
        cfg = self.get_mode_config(mode)
        profiles = cfg.get("profiles", [])
        profile_info = cfg.setdefault("profile_info", {})
        
        updated = 0
        for uuid in profiles:
            info = self.octo_api.get_profile_info(uuid)
            if info:
                country = info.get("country", "")
                if uuid not in profile_info:
                    profile_info[uuid] = {}
                old_country = profile_info[uuid].get("country", "")
                profile_info[uuid]["country"] = country
                
                if old_country and old_country != country:
                    self.log(f"[{mode}] {uuid[:8]}... geo changed: {old_country} → {country}")
                
                updated += 1
        
        cfg["profile_info"] = profile_info
        self.set_mode_config(mode, cfg)
        self.load_profiles_list(mode)
        
        if hasattr(self, 'auto_scheduler') and self.auto_scheduler:
            self._load_profiles_to_scheduler()
        
        self.log(f"[{mode}] Refreshed {updated}/{len(profiles)} profiles")
    
    def _on_refresh_profiles_complete(self, result: dict):
        """Handle completion of async profile refresh."""
        mode = getattr(self, '_refresh_mode', 'cookie')
        results = result.get("results", {})
        
        cfg = self.get_mode_config(mode)
        profile_info = cfg.setdefault("profile_info", {})
        
        updated = 0
        for uuid, info in results.items():
            if info:
                country = info.get("country", "")
                if uuid not in profile_info:
                    profile_info[uuid] = {}
                old_country = profile_info[uuid].get("country", "")
                profile_info[uuid]["country"] = country
                
                if old_country and old_country != country:
                    self.log(f"[{mode}] {uuid[:8]}... geo changed: {old_country} → {country}")
                
                updated += 1
        
        cfg["profile_info"] = profile_info
        self.set_mode_config(mode, cfg)
        self.load_profiles_list(mode)
        
        if hasattr(self, 'auto_scheduler') and self.auto_scheduler:
            self._load_profiles_to_scheduler()
        
        self.log(f"[{mode}] Refreshed {updated}/{len(results)} profiles")

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
        
        c = CATPPUCCIN
        
        dialog = QDialog(self)
        dialog.setWindowTitle(tr("Bulk Add Sites"))
        dialog.setMinimumSize(650, 500)
        layout = QVBoxLayout(dialog)
        layout.setSpacing(SPACING)
        layout.setContentsMargins(MARGIN, MARGIN, MARGIN, MARGIN)
        
        # Instructions
        info_label = QLabel(tr("Enter sites, one per line:"))
        info_label.setStyleSheet(f"font-size: {FONT_SIZE_BASE}px; color: {c['subtext1']};")
        layout.addWidget(info_label)
        
        # Text editor for sites
        text_edit = QTextEdit()
        text_edit.setPlaceholderText("https://example1.com\nhttps://example2.com\nexample3.com")
        layout.addWidget(text_edit)
        
        # Count label
        count_label = QLabel(tr("Sites to add:") + " 0")
        count_label.setStyleSheet(f"font-size: {FONT_SIZE_SMALL}px; color: {c['subtext0']};")
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
        hint_label.setStyleSheet(f"color: {CATPPUCCIN['subtext0']}; font-size: {FONT_SIZE_SMALL}px;")
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
                # One Tap Sites
                "onetap_visit_enabled": self.onetap_visit_enabled.isChecked(),
                "onetap_sites_min": self.onetap_sites_min.value(),
                "onetap_sites_max": self.onetap_sites_max.value(),
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
        
        # Check proxies before starting test
        self._check_proxies_before_start(mode, selected)
        
        # Check if any selected profile is running in Auto mode
        for uuid in selected:
            if uuid in self.auto_workers:
                # Stop it in auto mode and mark as manual
                self.auto_workers[uuid].stop()
                del self.auto_workers[uuid]
                self.auto_scheduler.mark_profile_manual(uuid, True)
                self.log(f"[Auto] ⏹ Stopped {uuid[:8]}... for manual control")
        
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
        # Add start minimized setting
        settings["start_minimized"] = self.config.get("start_minimized", True)
        # Get max parallel profiles from config
        max_parallel = self.config.get("max_parallel_profiles", 5)
        
        # Clear any old pending queue
        self.pending_queue = []
        
        # Get profile info for geo data
        profile_info = cfg.get("profile_info", {})
        
        # Check if timezone filtering is enabled
        timezone_filter_enabled = self.config.get("auto_mode", {}).get("timezone_filter_batch", False)
        
        # Add all selected profiles to queue with their settings
        skipped_sleeping = []
        for uuid in selected:
            # Get profile's country for geo-based visiting
            info = profile_info.get(uuid, {})
            profile_country = info.get("country", "")
            # Normalize country to 2-letter code (country may be full name like "Slovenia")
            if profile_country and len(profile_country) > 2:
                profile_country = normalize_country(profile_country)
            
            # Check if profile is sleeping (timezone-based)
            if timezone_filter_enabled and hasattr(self, 'auto_scheduler') and profile_country:
                if not self.auto_scheduler.is_profile_awake(profile_country):
                    local_time = self.auto_scheduler.get_local_time(profile_country)
                    skipped_sleeping.append(f"{uuid[:8]}... ({profile_country}, {local_time.strftime('%H:%M')})")
                    continue
            
            # Create a copy of settings with profile-specific country
            profile_settings = settings.copy()
            profile_settings["profile_country"] = profile_country
            
            self.pending_queue.append({
                "uuid": uuid,
                "sites": cfg.get("sites", []),
                "settings": profile_settings,
                "mode": mode
            })
        
        # Log skipped profiles
        if skipped_sleeping:
            self.log(f"😴 Skipped {len(skipped_sleeping)} sleeping profiles:")
            for p in skipped_sleeping:
                self.log(f"   {p}")
        
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
    
    def stop_automation(self, sync: bool = False):
        """Stop all running automation.
        
        Args:
            sync: If True, stop synchronously (for closeEvent). 
                  If False, stop asynchronously with progress dialog.
        """
        # Clear pending queue
        self.pending_queue = []
        
        # Stop worker threads
        for uuid, w in self.workers.items():
            w.stop()
        
        uuids_to_stop = list(self.workers.keys())
        
        if not uuids_to_stop:
            self.log("Nothing to stop")
            return
        
        if sync or not self.api_manager:
            # Synchronous stop (for closeEvent or when no manager)
            for uuid in uuids_to_stop:
                if self.octo_api:
                    self.octo_api.force_stop_profile(uuid)
            self.log("Stopped all profiles")
        else:
            # Async stop with progress
            self._stop_automation_async(uuids_to_stop)
    
    def _stop_automation_async(self, uuids: list):
        """Stop profiles asynchronously."""
        self._async_progress_dialog = QProgressDialog(
            tr("Stopping profiles..."),
            tr("Cancel"),
            0, len(uuids),
            self
        )
        self._async_progress_dialog.setWindowModality(Qt.WindowModal)
        self._async_progress_dialog.setAutoClose(True)
        self._async_progress_dialog.show()
        
        def on_manual_stop_complete(result):
            try:
                if self._async_progress_dialog:
                    self._async_progress_dialog.close()
            except (RuntimeError, AttributeError):
                pass
            finally:
                self._async_progress_dialog = None
                self._current_async_task = None
            self.log(f"Stopped {len(result.get('results', []))} profiles")
        
        self._current_async_task = self.api_manager.stop_profiles_batch_async(
            uuids,
            force=True,
            callback=on_manual_stop_complete
        )
        self.log("Stopping...")
    
    def on_finished(self, uuid):
        if uuid in self.workers:
            del self.workers[uuid]
            self.running_count = max(0, self.running_count - 1)
            self.log(f"[{uuid[:8]}] Done (running: {self.running_count}, pending: {len(self.pending_queue)})")
        
        # Return profile to Auto mode if it was taken from there
        if self.auto_state.is_auto_running():
            self.auto_scheduler.mark_profile_manual(uuid, False)
            self.log(f"[{uuid[:8]}] Returned to Auto queue")
        
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
        # Flush any remaining log messages
        if hasattr(self, '_log_buffer') and self._log_buffer:
            self._flush_log_buffer()
        
        # Use synchronous stop on close
        self.stop_automation(sync=True)
        
        # Shutdown async API manager
        if self.api_manager:
            self.api_manager.shutdown()
        
        self.save_config()
        e.accept()
