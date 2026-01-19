# ui/main_window.py
from PySide6.QtWidgets import QWidget, QPushButton, QVBoxLayout, QListWidget, QTextEdit
from PySide6.QtCore import Signal

class MainWindow(QWidget):

    # Signal
    get_models_signal= Signal()
    say_hello_signal= Signal()

    def __init__(self):
        super().__init__()
        self.get_models_button = QPushButton("get models")
        self.say_hello_button = QPushButton("say hello")
        self.list_view = QListWidget()
        self.response_view = QTextEdit()
        self.response_view.setReadOnly(True)
        layout = QVBoxLayout(self)
        layout.addWidget(self.get_models_button)
        layout.addWidget(self.say_hello_button)
        layout.addWidget(self.list_view)
        layout.addWidget(self.response_view)

        self.get_models_button.clicked.connect(self._get_models_button_on_click)
        self.say_hello_button.clicked.connect(self._say_hello_button_on_click)

    def _get_models_button_on_click(self):
        self.get_models_signal.emit()

    def _say_hello_button_on_click(self):
        self.say_hello_signal.emit()
    

    def get_selected_value(self) -> str | None:
        item = self.list_view.currentItem()
        return item.text() if item else None

    def show_result(self, values):
        self.list_view.clear()
        if values is None:
            return
        for value in values:
            self.list_view.addItem(str(value))

    def show_response(self, text: str):
        self.response_view.setPlainText(text or "")

    def show_error(self, message: str):
        self.response_view.setPlainText(message or "Unknown error.")
