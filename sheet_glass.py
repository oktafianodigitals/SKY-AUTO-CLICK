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