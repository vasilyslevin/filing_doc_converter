from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QDragEnterEvent, QDropEvent
from PySide6.QtWidgets import (
    QCheckBox,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QMainWindow,
    QMessageBox,
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
        self.setMinimumHeight(140)
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
        self._output_directory: Path | None = None
        self.setWindowTitle("Filing Document Converter")
        self.resize(760, 640)

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

        queue_controls = QHBoxLayout()
        queue_controls.addWidget(add_files)
        queue_controls.addWidget(add_folder)
        queue_controls.addStretch()
        queue_controls.addWidget(remove_selected)
        queue_controls.addWidget(clear_queue)

        output_group = QGroupBox("Output")
        output_layout = QVBoxLayout()

        output_folder_row = QHBoxLayout()
        self.output_path_edit = QLineEdit()
        self.output_path_edit.setReadOnly(True)
        self.output_path_edit.setPlaceholderText("Choose an output folder")
        choose_output = QPushButton("Choose Folder")
        choose_output.clicked.connect(self.choose_output_directory)
        output_folder_row.addWidget(self.output_path_edit)
        output_folder_row.addWidget(choose_output)

        output_types = QHBoxLayout()
        self.searchable_pdf_checkbox = QCheckBox("Searchable PDF")
        self.searchable_pdf_checkbox.setChecked(True)
        self.markdown_checkbox = QCheckBox("Markdown for AI")
        self.markdown_checkbox.setChecked(True)
        self.json_checkbox = QCheckBox("Structured JSON")
        output_types.addWidget(self.searchable_pdf_checkbox)
        output_types.addWidget(self.markdown_checkbox)
        output_types.addWidget(self.json_checkbox)
        output_types.addStretch()

        output_layout.addLayout(output_folder_row)
        output_layout.addLayout(output_types)
        output_group.setLayout(output_layout)

        self.process_button = QPushButton("Process Documents")
        self.process_button.setEnabled(False)
        self.process_button.clicked.connect(self.show_processing_placeholder)

        for checkbox in (
            self.searchable_pdf_checkbox,
            self.markdown_checkbox,
            self.json_checkbox,
        ):
            checkbox.checkStateChanged.connect(self.update_process_button)

        action_row = QHBoxLayout()
        action_row.addStretch()
        action_row.addWidget(self.process_button)

        layout = QVBoxLayout()
        layout.addWidget(self.drop_area)
        layout.addLayout(queue_controls)
        layout.addWidget(self.queue)
        layout.addWidget(output_group)
        layout.addLayout(action_row)

        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)
        self.statusBar().showMessage("Add one or more PDF files")

    @property
    def pdf_paths(self) -> tuple[Path, ...]:
        return tuple(self._pdf_paths)

    @property
    def output_directory(self) -> Path | None:
        return self._output_directory

    def choose_files(self) -> None:
        paths, _ = QFileDialog.getOpenFileNames(
            self, "Choose PDF files", "", "PDF documents (*.pdf)"
        )
        self.add_paths(paths)

    def choose_folder(self) -> None:
        path = QFileDialog.getExistingDirectory(self, "Choose a folder")
        if path:
            self.add_paths([path])

    def choose_output_directory(self) -> None:
        path = QFileDialog.getExistingDirectory(self, "Choose an output folder")
        if path:
            self.set_output_directory(Path(path))

    def set_output_directory(self, path: Path) -> None:
        self._output_directory = path.resolve()
        self.output_path_edit.setText(str(self._output_directory))
        self.update_process_button()

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

        if self._pdf_paths and self._output_directory is None:
            self.set_output_directory(self._pdf_paths[0].parent / "Converted")
        self._update_status()
        self.update_process_button()

    def remove_selected(self) -> None:
        rows = sorted({index.row() for index in self.queue.selectedIndexes()}, reverse=True)
        for row in rows:
            self.queue.takeItem(row)
            self._pdf_paths.pop(row)
        self._update_status()
        self.update_process_button()

    def clear_queue(self) -> None:
        self.queue.clear()
        self._pdf_paths.clear()
        self._update_status()
        self.update_process_button()

    def update_process_button(self) -> None:
        output_selected = any(
            checkbox.isChecked()
            for checkbox in (
                self.searchable_pdf_checkbox,
                self.markdown_checkbox,
                self.json_checkbox,
            )
        )
        ready = bool(self._pdf_paths and self._output_directory and output_selected)
        self.process_button.setEnabled(ready)

    def show_processing_placeholder(self) -> None:
        QMessageBox.information(
            self,
            "Processing not implemented",
            "The document queue is ready. Processing will be added in the next milestone.",
        )

    def _update_status(self) -> None:
        count = len(self._pdf_paths)
        if count == 0:
            message = "Add one or more PDF files"
        else:
            message = f"{count} PDF file{'s' if count != 1 else ''} queued"
        self.statusBar().showMessage(message)
