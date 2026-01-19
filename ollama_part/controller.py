from PySide6.QtCore import QObject, QThread, Signal

from ui import MainWindow


class _Worker(QObject):
    finished = Signal(object)
    error = Signal(str)

    def __init__(self, fn, *args, **kwargs):
        super().__init__()
        self._fn = fn
        self._args = args
        self._kwargs = kwargs

    def run(self):
        try:
            result = self._fn(*self._args, **self._kwargs)
            self.finished.emit(result)
        except Exception as exc:
            self.error.emit(str(exc))

class MainController:
    def __init__(self, view: MainWindow , analysis_service):
        self.view = view
        self.service = analysis_service
        self._threads = []
        self._workers = []
        self.view.get_models_signal.connect(self.on_get_models)
        self.view.say_hello_signal.connect(self.on_say_hello)

    def _run_in_thread(self, fn, on_success):
        worker = _Worker(fn)
        thread = QThread()
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.finished.connect(on_success)
        worker.error.connect(self.view.show_error)
        worker.error.connect(thread.quit)
        worker.error.connect(worker.deleteLater)
        worker.finished.connect(thread.quit)
        worker.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(lambda: self._cleanup_thread(thread, worker))
        self._threads.append(thread)
        self._workers.append(worker)
        thread.start()

    def _cleanup_thread(self, thread, worker):
        if thread in self._threads:
            self._threads.remove(thread)
        if worker in self._workers:
            self._workers.remove(worker)

    def on_get_models(self):
        self._run_in_thread(self.service.get_models, self.view.show_result)

    def on_say_hello(self):
        selected_model = self.view.get_selected_value()
        self._run_in_thread(
            lambda: self.service.say_hello(selected_model),
            self.view.show_response,
        )
