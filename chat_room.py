import sys
import datetime
import ollama
import pyttsx3
import json
import threading
import speech_recognition as sr
import tempfile
import queue
import array
from mic_system import MicSystem
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QTextEdit, QPushButton, QDesktopWidget
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt5.QtGui import QFont, QPainter, QColor, QTextCursor, QTextBlockFormat, QTextCharFormat

print("Starting chat room")

# ----- DELTA AI CLASS -----
class DeltaAI:
    """Handles AI logic and predefined commands."""
    def __init__(self):
        self.engine = pyttsx3.init()

    def speak(self, text):
        self.engine.say(text)
        self.engine.runAndWait()

    def process_command(self, user_input):
        user_input = user_input.lower().strip()
        commands = {
            "hello": "Hello! How can I assist you today?",
            "how are you": "I'm just a virtual assistant, but I'm always ready to help!",
            "who are you": "I am Delta, your AI assistant.",
            "bye": "Goodbye! Have a great day!",
            "what time is it": f"The time is {datetime.datetime.now().strftime('%I:%M %p')}.",
            "what is today's date": f"Today's date is {datetime.datetime.now().strftime('%A, %B %d, %Y')}."
        }
        return commands.get(user_input, None)

    def chat_with_ai(self, user_input):
        model_name = "deepseek-v2"
        chat_history = [{"role": "user", "content": user_input}]
        try:
            response = ollama.chat(model=model_name, messages=chat_history)
            return response["message"]["content"]
        except Exception:
            return "I'm having trouble connecting to the AI."

    def get_response(self, user_input=None):
        return self.process_command(user_input) or self.chat_with_ai(user_input)

# ----- AI WORKER THREAD -----
class AIWorker(QThread):
    response_signal = pyqtSignal(str)
    def __init__(self, user_input, ai, gui):
        super().__init__()
        self.user_input = user_input
        self.ai = ai
        self.gui = gui
    def run(self):
        if self.user_input.lower() == "exit":
            self.gui.exit_sequence()
            return
        response = self.ai.get_response(self.user_input)
        self.response_signal.emit(response)

# ----- Delta GUI -----
class DeltaGUI(QWidget):
    def __init__(self):
        super().__init__()
        self.ai = DeltaAI()
        self.processing = False
        self.pending_command = None
        self.audio_queue = queue.Queue()
        self.recognizer = sr.Recognizer()
        self._mic_system = None
        self.initUI()

    def initUI(self):
        self.setWindowTitle("Delta AI Assistant")
        self.resize(500, 600)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground, True)

        layout = QVBoxLayout()

        self.conversation_area = QTextEdit(self)
        self.conversation_area.setFont(QFont("Arial", 12))
        self.conversation_area.setReadOnly(True)
        self.conversation_area.setStyleSheet("""
            QTextEdit {
                background-color: rgba(0, 0, 0, 150);
                border-radius: 10px;
                padding: 10px;
                color: white;
            }
        """)
        layout.addWidget(self.conversation_area)

        self.user_input_area = QTextEdit(self)
        self.user_input_area.setFixedHeight(50)
        self.user_input_area.setStyleSheet("""
            QTextEdit {
                background-color: rgba(0, 0, 0, 150);
                border-radius: 10px;
                color: white;
                border: 2px solid #0078D7;
            }
        """)
        layout.addWidget(self.user_input_area)

        self.send_button = QPushButton("Ask Delta", self)
        self.send_button.setStyleSheet("""
            QPushButton {
                background-color: #0078D7;
                color: white;
                border-radius: 10px;
            }
            QPushButton:hover {
                background-color: #0a84ff;
            }
        """)
        self.send_button.clicked.connect(self.send_input)
        layout.addWidget(self.send_button)

        self.setLayout(layout)

    def _display_message_in_main_thread(self, message, system_message=False):
        cursor = self.conversation_area.textCursor()
        cursor.movePosition(QTextCursor.End)

        block_format = QTextBlockFormat()
        if system_message:
            block_format.setAlignment(Qt.AlignCenter)
        elif message.startswith("You:"):
            block_format.setAlignment(Qt.AlignRight)
        else:
            block_format.setAlignment(Qt.AlignLeft)
        cursor.insertBlock(block_format)

        char_format = QTextCharFormat()
        char_format.setFontWeight(QFont.Bold)
        if system_message:
            char_format.setForeground(QColor("red"))
        else:
            char_format.setForeground(QColor("white"))
        cursor.insertText(message, char_format)
        cursor.insertBlock()
        self.conversation_area.setTextCursor(cursor)

    def display_message(self, message, system_message=False):
        QTimer.singleShot(0, lambda: self._display_message_in_main_thread(message, system_message))

    def exit_sequence(self):
        QTimer.singleShot(0, self._exit_in_main_thread)

    def _exit_in_main_thread(self):
        self._display_message_in_main_thread("Shutting down chat room", True)
        QTimer.singleShot(2000, lambda: sys.exit())

    def send_input(self):
        user_text = self.user_input_area.toPlainText().strip()
        if user_text:
            if self.processing:
                self.display_message("Please wait, processing current command...", True)
                self.pending_command = user_text
                self.user_input_area.clear()
                return

            self.processing = True
            self.display_message(f"You: {user_text}")
            self.user_input_area.clear()
            self.worker = AIWorker(user_text, self.ai, self)
            self.worker.response_signal.connect(self.display_message)
            self.worker.response_signal.connect(lambda msg: setattr(self, 'processing', False))
            self.worker.response_signal.connect(lambda msg: self.process_pending_command())
            self.worker.start()

    def process_pending_command(self):
        if self.pending_command:
            command = self.pending_command
            self.pending_command = None
            self.processing = True
            self.display_message(f"You (Delayed): {command}")
            self.worker = AIWorker(command, self.ai, self)
            self.worker.response_signal.connect(self.display_message)
            self.worker.response_signal.connect(lambda msg: setattr(self, 'processing', False))
            self.worker.response_signal.connect(lambda msg: self.process_pending_command())
            self.worker.start()

    def start_voice_record(self):
        self.display_message("Listening...", True)
        self.voice_thread = threading.Thread(target=self._record_and_set_text)
        self.voice_thread.start()

    def stop_voice_record(self):
        # Let the thread finish naturally (records fixed duration)
        pass

    def _audio_callback(self, chunk):
        self.audio_queue.put(chunk)

    def recognize_from_mic(self, max_seconds=5):
        """
        Records a phrase using MicSystem and returns the recognized text.
        """
        self.audio_queue.queue.clear()
        self._mic_system = MicSystem(callback=self._audio_callback)
        self._mic_system.start_stream()
        self.display_message("Listening (MicSystem)... Speak now.", True)
        try:
            frames = []
            silence_chunks = 0
            max_chunks = int(max_seconds * self._mic_system.rate / self._mic_system.chunk)
            while len(frames) < max_chunks:
                try:
                    chunk = self.audio_queue.get(timeout=0.5)
                except queue.Empty:
                    silence_chunks += 1
                    if silence_chunks > 5:
                        break
                    continue
                frames.append(chunk)
            self._mic_system.stop_stream()
            audio_data = b''.join(frames)
            audio = sr.AudioData(audio_data, self._mic_system.rate, 2)
            try:
                return self.recognizer.recognize_google(audio)
            except sr.UnknownValueError:
                return ""
            except sr.RequestError:
                return "Speech recognition service unavailable."
        finally:
            if self._mic_system:
                self._mic_system.stop_stream()

    def _record_and_set_text(self):
        text = self.recognize_from_mic(max_seconds=5)
        QTimer.singleShot(0, lambda: self._set_voice_text(text))

    def _set_voice_text(self, text):
        if text:
            self.user_input_area.setText(text)
            self.display_message(f"You (voice): {text}")
            self.send_input()
        else:
            self.display_message("Sorry, I didn't catch that.", True)

    def test_microphone(self):
        import os
        import wave
        import tempfile
        tmpfile = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        tmpfile.close()
        try:
            MicSystem.record_to_file(tmpfile.name, duration=2)
            wf = wave.open(tmpfile.name, 'rb')
            if wf.getnframes() > 0:
                self.display_message("Microphone test successful!", True)
            else:
                self.display_message("Microphone test failed: No audio detected.", True)
            wf.close()
        except Exception as e:
            self.display_message(f"Microphone test failed: {e}", True)
        finally:
            os.remove(tmpfile.name)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        rect = self.rect()
        painter.setBrush(QColor(0, 0, 0, 150))
        painter.setPen(QColor(0, 120, 215, 255))
        painter.drawRoundedRect(rect, 15, 15)

if __name__ == "__main__":
    print("Delta activated")
    # Load default screen index from settings.json
    try:
        with open("settings.json", "r") as f:
            settings = json.load(f)
            screen_index = settings.get("default_screen_index", 0)
    except Exception:
        screen_index = 0

    app = QApplication(sys.argv)
    gui = DeltaGUI()

    # Move to the specified screen if available
    desktop = QDesktopWidget()
    if 0 <= screen_index < desktop.screenCount():
        screen_rect = desktop.screenGeometry(screen_index)
        gui.move(screen_rect.left(), screen_rect.top())
        gui.resize(screen_rect.width(), screen_rect.height())
    gui.showFullScreen()
    sys.exit(app.exec_())
