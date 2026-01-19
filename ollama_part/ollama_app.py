import sys

from PySide6.QtWidgets import QApplication

from ui import MainWindow
from controller import MainController
from services import ollama_services

def run():
    app = QApplication(sys.argv)
    view = MainWindow()
    service = ollama_services()
    controller = MainController(view, service)  # Pass the service instance here
    view.show()
    app.exec()




if __name__ == "__main__":
    run()