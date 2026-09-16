from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QDragEnterEvent, QDropEvent
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QMainWindow,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class PdfDropArea(QLabel):
    paths_dropped = Signal(list)

    def __init__(self) -> None:
        super().__init__("Drop PDF files or folders here")
        self.setAcceptDrops(True)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setMinimumHeight(160)
        self.setStyleSheet(
            "QLabel { border: 2px dashed #777; border-radius: 8px; "
            "font-size: 18px; padding: 24px; }"
        )

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if self._contains_supported_path(event.mimeData().urls()):
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event: QDropEvent) -> None:
        paths = [url.toLocalFile() for url in event.mimeData().urls() if url.isLocalFile()]
        if paths:
            self.paths_dropped.emit(paths)
            event.acceptProposedAction()

    @staticmethod
    def _contains_supported_path(urls: list) -> bool:
        for url in urls:
            if not url.isLocalFile():
                continue
            path = Path(url.toLocalFile())
            if path.is_dir() or path.suffix.lower() == ".pdf":
                return True
        return False


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self._pdf_paths: list[Path] = []
        self.setWindowTitle("Filing Document Converter")
        self.resize(760, 560)

        self.drop_area = PdfDropArea()
        self.drop_area.paths_dropped.connect(self.add_paths)

        self.queue = QListWidget()
        self.queue.setAlternatingRowColors(True)

        add_files = QPushButton("Add PDFs")
        add_files.clicked.connect(self.choose_files)
        add_folder = QPushButton("Add Folder")
        add_folder.clicked.connect(self.choose_folder)
        remove_selected = QPushButton("Remove Selected")
        remove_selected.clicked.connect(self.remove_selected)
        clear_queue = QPushButton("Clear")
        clear_queue.clicked.connect(self.clear_queue)

        controls = QHBoxLayout()
        controls.addWidget(add_files)
        controls.addWidget(add_folder)
        controls.addStretch()
        controls.addWidget(remove_selected)
        controls.addWidget(clear_queue)

        layout = QVBoxLayout()
        layout.addWidget(self.drop_area)
        layout.addLayout(controls)
        layout.addWidget(self.queue)

        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)
        self.statusBar().showMessage("Add one or more PDF files")

    @property
    def pdf_paths(self) -> tuple[Path, ...]:
        return tuple(self._pdf_paths)

    def choose_files(self) -> None:
        paths, _ = QFileDialog.getOpenFileNames(
            self, "Choose PDF files", "", "PDF documents (*.pdf)"
        )
        self.add_paths(paths)

    def choose_folder(self) -> None:
        path = QFileDialog.getExistingDirectory(self, "Choose a folder")
        if path:
            self.add_paths([path])

    def add_paths(self, paths: list[str]) -> None:
        candidates: list[Path] = []
        for raw_path in paths:
            path = Path(raw_path)
            if path.is_dir():
                candidates.extend(sorted(path.rglob("*.pdf")))
                candidates.extend(sorted(path.rglob("*.PDF")))
            else:
                candidates.append(path)

        known = {path.resolve() for path in self._pdf_paths}
        for candidate in candidates:
            if not candidate.is_file() or candidate.suffix.lower() != ".pdf":
                continue
            resolved = candidate.resolve()
            if resolved in known:
                continue
            self._pdf_paths.append(resolved)
            self.queue.addItem(str(resolved))
            known.add(resolved)

        count = len(self._pdf_paths)
        self.statusBar().showMessage(f"{count} PDF file{'s' if count != 1 else ''} queued")

    def remove_selected(self) -> None:
        rows = sorted({index.row() for index in self.queue.selectedIndexes()}, reverse=True)
        for row in rows:
            self.queue.takeItem(row)
            self._pdf_paths.pop(row)
        self._update_status()

    def clear_queue(self) -> None:
        self.queue.clear()
        self._pdf_paths.clear()
        self._update_status()

    def _update_status(self) -> None:
        count = len(self._pdf_paths)
        message = "Add one or more PDF files" if count == 0 else f"{count} PDF files queued"
        self.statusBar().showMessage(message)
