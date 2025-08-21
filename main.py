# =============================================================================
# STEP 1: Import Libraries - Menyiapkan semua tools yang dibutuhkan
# =============================================================================
import sys
import json
import os
import time
import threading
import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from collections import defaultdict
from PyQt6.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, 
                             QPushButton, QLabel, QListWidget, QWidget, QFileDialog,
                             QProgressBar, QSpinBox, QCheckBox, QGroupBox)
from PyQt6.QtCore import QTimer, pyqtSignal, QObject, Qt, QCoreApplication
from PyQt6.QtGui import QFont, QPalette, QColor, QIcon
import pydirectinput

# =============================================================================
# STEP 2: Setup Logging System - Sistem untuk mencatat aktivitas aplikasi
# =============================================================================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),  # Output ke terminal
        logging.FileHandler('sky_music_player.log', encoding='utf-8')  # Output ke file
    ]
)
logger = logging.getLogger(__name__)

# =============================================================================
# STEP 3: Data Classes - Struktur data untuk menyimpan informasi musik
# =============================================================================
@dataclass
class Note:
    """Data class untuk menyimpan informasi note musik"""
    key: str
    time: int

@dataclass
class SongData:
    """Data class untuk menyimpan informasi lagu lengkap"""
    name: str
    bpm: int
    notes: List[Note]
    file_path: str

# =============================================================================
# STEP 4: Music Player Engine - Inti sistem pemutaran musik
# =============================================================================
class MidiPlayer(QObject):
    """Class untuk mengelola pemutaran musik MIDI dengan dukungan simultaneous notes"""
    
    # Signals untuk komunikasi dengan UI
    progress_updated = pyqtSignal(int, int)  # current_time, total_time
    song_finished = pyqtSignal()
    status_changed = pyqtSignal(str)
    
    def __init__(self):
        super().__init__()
        logger.info("Initializing MidiPlayer")
        
        # Status pemutaran
        self.is_playing = False
        self.is_paused = False
        self.current_song: Optional[SongData] = None
        self.current_position = 0
        self.start_time = 0
        self.pause_time = 0
        
        # Key mapping untuk berbagai instrumen Sky Music
        self.key_mapping = {
            # Instrumen 1 - Mapping keyboard ke key game
            "1Key0": "y", "1Key1": "u", "1Key2": "i", "1Key3": "o", "1Key4": "p",
            "1Key5": "h", "1Key6": "j", "1Key7": "k", "1Key8": "l", "1Key9": ";",
            "1Key10": "n", "1Key11": "m", "1Key12": ",", "1Key13": ".", "1Key14": "/",
            
            # Instrumen 2 - Saat ini menggunakan mapping yang sama
            "2Key0": "y", "2Key1": "u", "2Key2": "i", "2Key3": "o", "2Key4": "p",
            "2Key5": "h", "2Key6": "j", "2Key7": "k", "2Key8": "l", "2Key9": ";",
            "2Key10": "n", "2Key11": "m", "2Key12": ",", "2Key13": ".", "2Key14": "/",
            
            # Instrumen 3 - Saat ini menggunakan mapping yang sama
            "3Key0": "y", "3Key1": "u", "3Key2": "i", "3Key3": "o", "3Key4": "p",
            "3Key5": "h", "3Key6": "j", "3Key7": "k", "3Key8": "l", "3Key9": ";",
            "3Key10": "n", "3Key11": "m", "3Key12": ",", "3Key13": ".", "3Key14": "/",
            
            # Instrumen 4 - Saat ini menggunakan mapping yang sama
            "4Key0": "y", "4Key1": "u", "4Key2": "i", "4Key3": "o", "4Key4": "p",
            "4Key5": "h", "4Key6": "j", "4Key7": "k", "4Key8": "l", "4Key9": ";",
            "4Key10": "n", "4Key11": "m", "4Key12": ",", "4Key13": ".", "4Key14": "/",
        }
        
        self.play_thread = None
        logger.info("MidiPlayer initialized successfully")
    
    # STEP 5: Song Loading Function - Fungsi untuk memuat file lagu
    def load_song(self, file_path: str) -> bool:
        """Load song dari file JSON"""
        logger.info(f"Loading song from: {file_path}")
        
        try:
            # Baca file JSON
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Handle berbagai format JSON
            if isinstance(data, list) and len(data) > 0:
                song_data = data[0]
                logger.debug("Song data is in list format, using first element")
            else:
                song_data = data
                logger.debug("Song data is in object format")
            
            # Parse notes dari songNotes
            notes = []
            if 'songNotes' in song_data:
                for note_data in song_data['songNotes']:
                    # Validasi data note
                    if 'key' in note_data and 'time' in note_data:
                        notes.append(Note(
                            key=note_data['key'],
                            time=note_data['time']
                        ))
                    else:
                        logger.warning(f"Invalid note data found: {note_data}")
                        
                logger.info(f"Parsed {len(notes)} notes from song")
            else:
                logger.warning("No 'songNotes' found in song data")
            
            # Buat objek SongData
            self.current_song = SongData(
                name=song_data.get('name', os.path.basename(file_path)),
                bpm=song_data.get('bpm', 120),
                notes=sorted(notes, key=lambda x: x.time),  # Sort berdasarkan waktu
                file_path=file_path
            )
            
            logger.info(f"Successfully loaded song: {self.current_song.name} "
                       f"(BPM: {self.current_song.bpm}, Notes: {len(self.current_song.notes)})")
            return True
            
        except FileNotFoundError:
            logger.error(f"File not found: {file_path}")
            return False
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON format in {file_path}: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error loading song from {file_path}: {e}")
            return False
    
    # STEP 6: Note Grouping Function - Fungsi untuk mengelompokkan note yang dimainkan bersamaan
    def group_notes_by_time(self, notes: List[Note]) -> List[Tuple[int, List[Note]]]:
        """Group notes yang harus dimainkan bersamaan (pada waktu yang sama)"""
        logger.debug(f"Grouping {len(notes)} notes by time")
        
        time_groups = defaultdict(list)
        
        # Group notes berdasarkan waktu
        for note in notes:
            time_groups[note.time].append(note)
        
        # Convert ke sorted list of (time, notes) tuples
        grouped_notes = []
        for time_ms in sorted(time_groups.keys()):
            grouped_notes.append((time_ms, time_groups[time_ms]))
        
        # Log informasi tentang chord (notes yang dimainkan bersamaan)
        chord_count = sum(1 for time_ms, group in grouped_notes if len(group) > 1)
        logger.info(f"Found {chord_count} chords in {len(grouped_notes)} time groups")
        
        return grouped_notes
    
    # STEP 7: Simultaneous Note Player - Fungsi untuk memainkan multiple note bersamaan
    def play_simultaneous_notes(self, notes: List[Note]):
        """Play multiple notes secara bersamaan menggunakan threading"""
        def press_key(key):
            """Helper function untuk menekan key dengan error handling"""
            if key in self.key_mapping:
                key_to_press = self.key_mapping[key]
                try:
                    pydirectinput.press(key_to_press)
                    logger.debug(f"Pressed key: {key} -> {key_to_press}")
                except Exception as e:
                    logger.error(f"Error pressing key {key_to_press}: {e}")
            else:
                logger.warning(f"Unknown key mapping for: {key}")
        
        # Buat threads untuk setiap key press
        threads = []
        for note in notes:
            thread = threading.Thread(target=press_key, args=(note.key,), daemon=True)
            threads.append(thread)
        
        # Start semua threads bersamaan untuk simultan input
        for thread in threads:
            thread.start()
        
        # Wait untuk semua threads selesai (dengan timeout untuk mencegah hang)
        for thread in threads:
            thread.join(timeout=0.1)
        
        # Log jika ada simultaneous notes
        if len(notes) > 1:
            keys_info = [f"{note.key}" for note in notes]
            logger.debug(f"Played simultaneous notes: {keys_info}")
    
    # STEP 8: Countdown Function - Fungsi countdown sebelum mulai memainkan lagu
    def start_countdown(self, callback):
        """Start countdown 3 detik sebelum mulai play"""
        logger.info("Starting 3-second countdown")
        
        def countdown():
            try:
                for i in range(3, 0, -1):
                    self.status_changed.emit(f"Starting in {i}...")
                    logger.info(f"Countdown: {i}")
                    time.sleep(1)
                    
                self.status_changed.emit("Playing...")
                logger.info("Countdown finished, starting playback")
                callback()
            except Exception as e:
                logger.error(f"Error during countdown: {e}")
        
        threading.Thread(target=countdown, daemon=True).start()
    
    # STEP 9: Play Control Functions - Fungsi kontrol pemutaran (play, pause, stop)
    def play(self):
        """Start playing current song dengan countdown"""
        if not self.current_song:
            logger.warning("No song loaded, cannot play")
            return
            
        if self.is_playing:
            logger.warning("Song is already playing")
            return
        
        logger.info(f"Starting to play: {self.current_song.name}")
        
        def start_play():
            """Internal function untuk memulai playback"""
            self.is_playing = True
            self.is_paused = False
            self.current_position = 0
            self.play_thread = threading.Thread(target=self._play_song, daemon=True)
            self.play_thread.start()
        
        self.start_countdown(start_play)
    
    def pause(self):
        """Pause/resume playing"""
        if not self.is_playing:
            logger.warning("No song is currently playing")
            return
        
        if self.is_paused:
            # Resume
            self.is_paused = False
            self.start_time += time.time() - self.pause_time
            self.status_changed.emit("Playing...")
            logger.info("Resumed playback")
        else:
            # Pause
            self.is_paused = True
            self.pause_time = time.time()
            self.status_changed.emit("Paused")
            logger.info("Paused playback")
    
    def stop(self):
        """Stop playing"""
        if self.is_playing or self.is_paused:
            logger.info("Stopping playback")
            
        self.is_playing = False
        self.is_paused = False
        self.current_position = 0
        self.status_changed.emit("Stopped")
    
    # STEP 10: Main Playback Engine - Engine utama untuk memainkan lagu
    def _play_song(self):
        """Internal method untuk memainkan lagu dengan dukungan simultaneous notes"""
        if not self.current_song:
            logger.error("No current song to play")
            return
        
        logger.info(f"Starting song playback: {self.current_song.name}")
        
        try:
            self.start_time = time.time()
            total_time = self.current_song.notes[-1].time if self.current_song.notes else 0
            
            # Group notes berdasarkan waktu untuk simultaneous playback
            grouped_notes = self.group_notes_by_time(self.current_song.notes)
            
            logger.info(f"Playing {len(grouped_notes)} note groups over {total_time}ms")
            
            for time_ms, notes_group in grouped_notes:
                # Check jika masih harus playing
                if not self.is_playing:
                    logger.info("Playback stopped by user")
                    break
                
                # Wait jika di-pause
                while self.is_paused and self.is_playing:
                    time.sleep(0.01)
                
                if not self.is_playing:
                    logger.info("Playback stopped during pause wait")
                    break
                
                # Hitung kapan harus play note group ini
                target_time = time_ms / 1000.0  # Convert ke seconds
                elapsed_time = time.time() - self.start_time
                
                # Wait sampai waktunya play group ini
                if target_time > elapsed_time:
                    sleep_time = target_time - elapsed_time
                    time.sleep(sleep_time)
                
                if not self.is_playing:
                    logger.info("Playback stopped during timing wait")
                    break
                
                # Play semua notes di group ini secara bersamaan
                self.play_simultaneous_notes(notes_group)
                
                # Update progress
                self.current_position = time_ms
                self.progress_updated.emit(self.current_position, total_time)
            
            # Song selesai
            if self.is_playing:  # Hanya emit jika tidak di-stop manual
                logger.info("Song finished naturally")
                self.is_playing = False
                self.song_finished.emit()
                self.status_changed.emit("Finished")
            
        except Exception as e:
            logger.error(f"Error during song playback: {e}")
            self.is_playing = False
            self.status_changed.emit("Error occurred during playback")

# =============================================================================
# STEP 11: Main Window Class - Class utama untuk tampilan aplikasi
# =============================================================================
class SkyMusicPlayer(QMainWindow):
    """Main window class untuk Sky Music Player"""
    
    def __init__(self):
        super().__init__()
        logger.info("Initializing Sky Music Player main window")
        
        self.player = MidiPlayer()
        self.song_list: List[SongData] = []  # List untuk menyimpan semua song data
        self.loaded_file_paths = set()  # Set untuk track file yang sudah di-load (mencegah duplikasi)
        
        self.setup_window_properties()
        self.setup_ui()
        self.setup_connections()
        self.apply_cyberpunk_style()
        
        logger.info("Sky Music Player initialized successfully")
    
    # STEP 12: Window Properties Setup - Pengaturan dasar tampilan window
    def setup_window_properties(self):
        """Setup window properties untuk transparan dan frameless"""
        logger.debug("Setting up window properties")
        
        # Hapus title bar dan borders, tapi tetap muncul di taskbar
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint | 
            Qt.WindowType.WindowStaysOnTopHint
        )
        
        # Set window transparency
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        
        # Tambahkan ini untuk memastikan window muncul di taskbar
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, False)
        
        # Set window size dan posisi
        self.setGeometry(100, 100, 800, 600)
        self.setWindowTitle("Sky Music - By Ayy")
        
        logger.debug("Window properties configured for transparent frameless display")
    
    # STEP 13: UI Layout Creation - Membuat layout dan elemen-elemen visual
    def setup_ui(self):
        """Setup user interface"""
        logger.debug("Setting up UI components")
        
        # Main container widget sebagai container utama
        main_container = QWidget()
        main_container.setObjectName("MainContainer")
        self.setCentralWidget(main_container)
        
        # Main layout dengan margins untuk visual border
        main_layout = QVBoxLayout(main_container)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)
        
        # STEP 13a: Title Bar - Membuat title bar dengan tombol close
        title_layout = QHBoxLayout()
        
        # Title label
        title_label = QLabel("Sky Music - By Ayy")
        title_label.setStyleSheet("""
            QLabel {
                color: #00ffff;
                font-size: 16px;
                font-weight: bold;
                padding: 10px;
            }
        """)
        
        # Close button
        self.close_btn = QPushButton("⌐")
        self.close_btn.clicked.connect(self.close_application)
        self.close_btn.setFixedSize(60, 35)
        self.close_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(200, 0, 0, 0);
                color: white;
                border: 2px solid #ff4444;
                border-radius: 8px;
                font-weight: bold;
            } 
            QPushButton:hover {
                background-color: rgba(255, 0, 0, 220);
            }
        """)
        
        title_layout.addWidget(title_label)
        title_layout.addStretch()
        title_layout.addWidget(self.close_btn)
        
        main_layout.addLayout(title_layout)
        
        # STEP 13b: File Management Section - Area untuk memilih dan mengelola file
        file_group = QGroupBox("File Management")
        file_layout = QHBoxLayout(file_group)
        
        self.select_folder_btn = QPushButton("Select Folder")
        self.select_files_btn = QPushButton("Select Files")
        self.clear_list_btn = QPushButton("Clear List")
        
        file_layout.addWidget(self.select_folder_btn)
        file_layout.addWidget(self.select_files_btn)
        file_layout.addWidget(self.clear_list_btn)
        
        main_layout.addWidget(file_group)
        
        # STEP 13c: Song List Widget - Daftar lagu yang bisa dipilih
        list_group = QGroupBox("Song List")
        list_layout = QVBoxLayout(list_group)
        
        self.song_list_widget = QListWidget()
        self.song_list_widget.setMinimumHeight(250)  # Tinggi minimum 250 pixel
        
        list_layout.addWidget(self.song_list_widget)
        
        main_layout.addWidget(list_group)
        
        # STEP 13d: Control Section - Tombol-tombol kontrol pemutaran
        control_group = QGroupBox("Controls")
        control_layout = QVBoxLayout(control_group)
        
        # Playback controls
        playback_layout = QHBoxLayout()
        
        self.play_btn = QPushButton("Play")
        self.pause_btn = QPushButton("Pause/Resume")
        self.stop_btn = QPushButton("Stop")
        
        playback_layout.addWidget(self.play_btn)
        playback_layout.addWidget(self.pause_btn)
        playback_layout.addWidget(self.stop_btn)
        
        control_layout.addLayout(playback_layout)
        
        # STEP 13e: Settings Controls - Pengaturan kecepatan dan loop
        settings_layout = QHBoxLayout()
        
        self.speed_label = QLabel("Speed:")
        self.speed_spin = QSpinBox()
        self.speed_spin.setRange(50, 200)
        self.speed_spin.setValue(100)
        self.speed_spin.setSuffix("%")
        
        self.loop_checkbox = QCheckBox("Loop")
        
        settings_layout.addWidget(self.speed_label)
        settings_layout.addWidget(self.speed_spin)
        settings_layout.addWidget(self.loop_checkbox)
        settings_layout.addStretch()
        
        control_layout.addLayout(settings_layout)
        
        main_layout.addWidget(control_group)
        
        # STEP 13f: Status Section - Area untuk menampilkan status dan progress
        status_group = QGroupBox("Status")
        status_layout = QVBoxLayout(status_group)
        
        self.status_label = QLabel("Ready - Now supports simultaneous notes!")
        self.progress_bar = QProgressBar()
        
        status_layout.addWidget(self.status_label)
        status_layout.addWidget(self.progress_bar)
        
        main_layout.addWidget(status_group)
        
        # Initially disable control buttons
        self.play_btn.setEnabled(False)
        self.pause_btn.setEnabled(False)
        self.stop_btn.setEnabled(False)
        
        logger.debug("UI setup completed")
    
    # STEP 14: Signal Connections - Menghubungkan tombol dengan fungsi-fungsinya
    def setup_connections(self):
        """Setup signal connections"""
        logger.debug("Setting up signal connections")
        
        # File management connections
        self.select_folder_btn.clicked.connect(self.select_folder)
        self.select_files_btn.clicked.connect(self.select_files)
        self.clear_list_btn.clicked.connect(self.clear_song_list)
        self.song_list_widget.currentRowChanged.connect(self.song_selected)
        
        # Playback control connections
        self.play_btn.clicked.connect(self.play_song)
        self.pause_btn.clicked.connect(self.pause_song)
        self.stop_btn.clicked.connect(self.stop_song)
        
        # Player signal connections
        self.player.progress_updated.connect(self.update_progress)
        self.player.song_finished.connect(self.song_finished)
        self.player.status_changed.connect(self.update_status)
        
        logger.debug("Signal connections completed")
    
    # STEP 15: Cyberpunk Styling - Menerapkan tema cyberpunk yang keren
    def apply_cyberpunk_style(self):
        """Apply cyberpunk theme styling dengan transparansi dan main container"""
        logger.debug("Applying cyberpunk theme with transparency and main container")
        
        self.setStyleSheet("""
            QMainWindow {
                background-color: transparent;
                color: #00ffff;
                font-family: 'Consolas', 'Monaco', monospace;
            }
            
            #MainContainer {
                background-color: rgba(50, 50, 70, 180);
                border: 2px solid #00ffff;
                border-radius: 15px;
            }
            
            QWidget {
                background-color: transparent;
            }
            
            QGroupBox {
                border: 2px solid rgba(0, 255, 255, 200);
                border-radius: 8px;
                margin: 20px;
                padding-top: 15px;
                font-weight: bold;
                color: #00ffff;
                background-color: rgba(26, 26, 58, 100);
            }
            
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 15px;
                padding: 0 10px 0 10px;
                background-color: rgba(10, 10, 26, 200);
                border-radius: 4px;
            }
            
            QPushButton {
                background-color: rgba(26, 26, 58, 150);
                border: 2px solid #00ffff;
                border-radius: 6px;
                padding: 8px 16px;
                color: #00ffff;
                font-weight: bold;
                min-height: 20px;
            }
            
            QPushButton:hover {
                background-color: rgba(42, 42, 74, 200);
                border-color: #44ffff;
            }
            
            QPushButton:pressed {
                background-color: rgba(0, 255, 255, 200);
                color: #0a0a1a;
            }
            
            QPushButton:disabled {
                background-color: rgba(26, 26, 42, 100);
                border-color: #666666;
                color: #666666;
            }
            
            QListWidget {
                background-color: rgba(26, 26, 42, 150);
                border: 2px solid #00ffff;
                border-radius: 6px;
                color: #00ffff;
                selection-background-color: rgba(0, 255, 255, 100);
                selection-color: #0a0a1a;
                padding: 5px;
            }
            
            QListWidget::item {
                padding: 8px;
                border-bottom: 1px solid rgba(51, 51, 102, 100);
                background-color: transparent;
            }
            
            QListWidget::item:hover {
                background-color: rgba(42, 42, 74, 100);
            }
            
            QListWidget::item:selected {
                background-color: rgba(0, 255, 255, 150);
                color: #0a0a1a;
            }
            
            QProgressBar {
                border: 2px solid #00ffff;
                border-radius: 6px;
                text-align: center;
                background-color: rgba(26, 26, 42, 150);
                color: #00ffff;
                font-weight: bold;
            }
            
            QProgressBar::chunk {
                background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 rgba(0, 255, 255, 200), stop:1 rgba(0, 136, 255, 200));
                border-radius: 4px;
            }
            
            QLabel {
                color: #00ffff;
                font-weight: bold;
                background-color: transparent;
            }
            
            QSpinBox {
                background-color: rgba(26, 26, 42, 150);
                border: 2px solid #00ffff;
                border-radius: 4px;
                padding: 4px;
                color: #00ffff;
                min-width: 60px;
            }
            
            QSpinBox::up-button, QSpinBox::down-button {
                background-color: rgba(26, 26, 58, 150);
                border: 1px solid #00ffff;
            }
            
            QSpinBox::up-arrow, QSpinBox::down-arrow {
                border: 2px solid #00ffff;
                width: 6px;
                height: 6px;
            }
            
            QCheckBox {
                color: #00ffff;
                font-weight: bold;
                background-color: transparent;
            }
            
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
                border: 2px solid #00ffff;
                border-radius: 4px;
                background-color: rgba(26, 26, 42, 150);
            }
            
            QCheckBox::indicator:checked {
                background-color: rgba(0, 255, 255, 200);
            }
        """)
    
    # STEP 16: Window Control Functions - Fungsi untuk mengontrol window
    def close_application(self):
        """Method untuk menutup aplikasi dengan benar"""
        logger.info("Close button clicked - shutting down application")
        
        # Stop player jika sedang bermain
        if self.player.is_playing:
            self.player.stop()
        
        # Stop semua threads yang masih berjalan
        if hasattr(self.player, 'play_thread') and self.player.play_thread:
            self.player.play_thread = None
        
        # Tutup window
        self.close()
        
        # Force quit aplikasi
        QCoreApplication.quit()
        
        logger.info("Application shutdown initiated")
    
    def closeEvent(self, event):
        """Override closeEvent untuk memastikan aplikasi benar-benar tertutup"""
        logger.info("Window close event triggered")
        
        # Stop player
        if self.player.is_playing:
            self.player.stop()
        
        # Accept close event
        event.accept()
        
        # Force quit aplikasi
        QCoreApplication.quit()
        
        logger.info("Application closed")
    
    # STEP 17: File Management Functions - Fungsi untuk mengelola file lagu
    def clear_song_list(self):
        """Clear semua song dari list dan reset state"""
        logger.info("Clearing song list")
        
        # Stop playback jika sedang bermain
        if self.player.is_playing:
            self.player.stop()
        
        # Clear semua data
        self.song_list.clear()
        self.loaded_file_paths.clear()
        self.song_list_widget.clear()
        
        # Reset player state
        self.player.current_song = None
        
        # Disable control buttons
        self.play_btn.setEnabled(False)
        self.pause_btn.setEnabled(False)
        self.stop_btn.setEnabled(False)
        
        # Reset progress bar
        self.progress_bar.setValue(0)
        
        self.update_status("Song list cleared")
        logger.info("Song list cleared successfully")
    
    def select_folder(self):
        """Select folder containing song files"""
        logger.info("Opening folder selection dialog")
        
        folder = QFileDialog.getExistingDirectory(self, "Select Folder with Song Files")
        if folder:
            logger.info(f"Selected folder: {folder}")
            self.load_songs_from_folder(folder)
        else:
            logger.info("Folder selection cancelled")
    
    def select_files(self):
        """Select individual song files"""
        logger.info("Opening file selection dialog")
        
        files, _ = QFileDialog.getOpenFileNames(
            self, "Select Song Files", "", "JSON Files (*.json);;All Files (*)"
        )
        if files:
            logger.info(f"Selected {len(files)} files")
            self.load_songs_from_files(files)
        else:
            logger.info("File selection cancelled")
    
    # STEP 18: Song Loading Functions - Fungsi untuk memuat lagu dari file
    def load_songs_from_folder(self, folder_path: str):
        """Load semua file JSON dari folder"""
        logger.info(f"Loading songs from folder: {folder_path}")
        
        try:
            json_files = []
            
            # Scan folder untuk file JSON
            for file in os.listdir(folder_path):
                if file.lower().endswith('.json'):
                    file_path = os.path.join(folder_path, file)
                    json_files.append(file_path)
            
            if json_files:
                logger.info(f"Found {len(json_files)} JSON files in folder")
                self.load_songs_from_files(json_files)
            else:
                message = "No JSON files found in selected folder"
                logger.warning(message)
                self.update_status(message)
                
        except Exception as e:
            error_msg = f"Error scanning folder {folder_path}: {e}"
            logger.error(error_msg)
            self.update_status(error_msg)
    
    def load_songs_from_files(self, file_paths: List[str]):
        """Load songs dari file paths dengan pencegahan duplikasi"""
        logger.info(f"Loading songs from {len(file_paths)} files")
        
        loaded_count = 0
        skipped_count = 0
        error_count = 0
        
        for file_path in file_paths:
            try:
                # Normalisasi path untuk mencegah duplikasi
                normalized_path = os.path.normpath(os.path.abspath(file_path))
                
                # Check jika file sudah di-load sebelumnya
                if normalized_path in self.loaded_file_paths:
                    logger.debug(f"Skipping duplicate file: {file_path}")
                    skipped_count += 1
                    continue
                
                # Coba load song
                if self.player.load_song(file_path):
                    song_data = self.player.current_song
                    
                    # Tambahkan ke list dan UI
                    self.song_list.append(song_data)
                    self.song_list_widget.addItem(f"{song_data.name} (BPM: {song_data.bpm})")
                    
                    # Track file yang sudah di-load
                    self.loaded_file_paths.add(normalized_path)
                    
                    loaded_count += 1
                    logger.debug(f"Successfully loaded: {song_data.name}")
                else:
                    error_count += 1
                    logger.error(f"Failed to load: {file_path}")
                    
            except Exception as e:
                error_count += 1
                logger.error(f"Error processing file {file_path}: {e}")
        
        # Update status dengan hasil loading
        status_parts = []
        if loaded_count > 0:
            status_parts.append(f"Loaded {loaded_count} songs")
        if skipped_count > 0:
            status_parts.append(f"Skipped {skipped_count} duplicates")
        if error_count > 0:
            status_parts.append(f"Failed {error_count} files")
        
        status_message = ", ".join(status_parts) if status_parts else "No files processed"
        self.update_status(status_message)
        
        logger.info(f"Loading completed: {loaded_count} loaded, {skipped_count} skipped, {error_count} errors")
        
        # Auto-select first song jika ada song yang di-load
        if self.song_list and loaded_count > 0:
            self.song_list_widget.setCurrentRow(0)
    
    # STEP 19: Song Selection Function - Fungsi untuk memilih lagu dari list
    def song_selected(self, index: int):
        """Handle song selection dari list"""
        if index == -1:  # No selection
            logger.debug("No song selected")
            return
            
        if 0 <= index < len(self.song_list):
            selected_song = self.song_list[index]
            self.player.current_song = selected_song
            
            logger.info(f"Selected song: {selected_song.name}")
            
            # Enable control buttons
            self.play_btn.setEnabled(True)
            self.pause_btn.setEnabled(False)
            self.stop_btn.setEnabled(False)
            
            # Analisis chord (simultaneous notes)
            grouped_notes = self.player.group_notes_by_time(selected_song.notes)
            chord_count = sum(1 for time_ms, notes in grouped_notes if len(notes) > 1)
            
            status_msg = f"Selected: {selected_song.name} ({chord_count} chords detected)"
            self.update_status(status_msg)
            self.progress_bar.setValue(0)
            
            logger.info(f"Song analysis: {len(selected_song.notes)} total notes, {chord_count} chords")
        else:
            logger.warning(f"Invalid song index selected: {index}")
    
    # STEP 20: Playback Control Functions - Fungsi kontrol pemutaran untuk UI
    def play_song(self):
        """Start playing selected song"""
        if self.player.current_song:
            logger.info(f"Starting playback: {self.player.current_song.name}")
            
            # Update button states
            self.play_btn.setEnabled(False)
            self.pause_btn.setEnabled(True)
            self.stop_btn.setEnabled(True)
            self.player.play()
        else:
            logger.warning("No song selected for playback")
            self.update_status("Please select a song first")
    
    def pause_song(self):
        """Pause/resume current song"""
        logger.info("Pause/resume button clicked")
        self.player.pause()
    
    def stop_song(self):
        """Stop current song"""
        logger.info("Stop button clicked")
        self.player.stop()
        
        # Update button states
        self.play_btn.setEnabled(True)
        self.pause_btn.setEnabled(False)
        self.stop_btn.setEnabled(False)
        self.progress_bar.setValue(0)
    
    # STEP 21: UI Update Functions - Fungsi untuk update tampilan UI
    def update_progress(self, current: int, total: int):
        """Update progress bar"""
        if total > 0:
            progress = int((current / total) * 100)
            self.progress_bar.setValue(progress)
            
            # Log progress setiap 10% untuk debugging
            if progress > 0 and progress % 10 == 0:
                logger.debug(f"Playback progress: {progress}% ({current}/{total}ms)")
    
    def song_finished(self):
        """Handle song finished event"""
        logger.info("Song playback finished")
        
        if self.loop_checkbox.isChecked():
            # Restart song jika loop enabled
            logger.info("Loop enabled, restarting song")
            self.player.play()
        else:
            # Reset button states
            self.play_btn.setEnabled(True)
            self.pause_btn.setEnabled(False)
            self.stop_btn.setEnabled(False)
            self.progress_bar.setValue(100)
            
            logger.info("Playback completed")
    
    def update_status(self, message: str):
        """Update status label dengan message"""
        self.status_label.setText(message)
        logger.debug(f"Status updated: {message}")

    # STEP 22: Window Movement Functions - Fungsi untuk menggerakkan window
    def mousePressEvent(self, event):
        """Allow window movement when clicking and dragging"""
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_pos = event.globalPosition().toPoint()
            event.accept()

    def mouseMoveEvent(self, event):
        """Handle window movement"""
        if hasattr(self, 'drag_pos'):
            self.move(self.pos() + event.globalPosition().toPoint() - self.drag_pos)
            self.drag_pos = event.globalPosition().toPoint()
            event.accept()

# =============================================================================
# STEP 23: Main Application Functions - Fungsi utama untuk menjalankan aplikasi
# =============================================================================
def main():
    """Main function untuk menjalankan aplikasi"""
    logger.info("Starting Sky Music Auto Player application")
    
    try:
        app = QApplication(sys.argv)
        
        # Set application properties
        app.setApplicationName("Sky Music - By Ayy")
        app.setApplicationVersion("1.2")
        
        # Handle application quit event
        app.aboutToQuit.connect(lambda: logger.info("Application about to quit"))
        
        logger.info("Creating main window")
        
        # Create dan show main window
        window = SkyMusicPlayer()
        window.show()
        
        logger.info("Application started successfully")
        
        # Run application event loop
        exit_code = app.exec()
        logger.info(f"Application exited with code: {exit_code}")
        sys.exit(exit_code)
        
    except Exception as e:
        logger.critical(f"Critical error starting application: {e}")
        sys.exit(1)

# =============================================================================
# STEP 24: Application Entry Point - Titik masuk aplikasi
# =============================================================================
if __name__ == "__main__":
    main()