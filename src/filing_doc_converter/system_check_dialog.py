from collections.abc import Callable
from pathlib import Path

from PySide6.QtCore import Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from filing_doc_converter.system_diagnostics import (
    SystemDiagnostics,
    collect_system_diagnostics,
    installation_guidance,
)


class SystemCheckDialog(QDialog):
    diagnostics_updated = Signal(object)

    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        diagnostics_provider: Callable[[], SystemDiagnostics] = collect_system_diagnostics,
    ) -> None:
        super().__init__(parent)
        self._diagnostics_provider = diagnostics_provider
        self._diagnostics: SystemDiagnostics | None = None

        self.setWindowTitle("System Check")
        self.resize(720, 440)

        self.system_label = QLabel()
        self.system_label.setWordWrap(True)

        self.component_table = QTableWidget(0, 4)
        self.component_table.setHorizontalHeaderLabels(
            ["Component", "Status", "Version", "Details"]
        )
        self.component_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.component_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        header = self.component_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)

        self.guidance_label = QLabel()
        self.guidance_label.setWordWrap(True)
        self.guidance_label.setTextInteractionFlags(
            self.guidance_label.textInteractionFlags()
        )

        self.refresh_button = QPushButton("Refresh")
        self.refresh_button.clicked.connect(self.refresh)
        self.save_button = QPushButton("Save Report")
        self.save_button.clicked.connect(self.choose_report_path)
        close_button = QPushButton("Close")
        close_button.clicked.connect(self.accept)

        buttons = QHBoxLayout()
        buttons.addWidget(self.refresh_button)
        buttons.addWidget(self.save_button)
        buttons.addStretch()
        buttons.addWidget(close_button)

        layout = QVBoxLayout()
        layout.addWidget(self.system_label)
        layout.addWidget(self.component_table)
        layout.addWidget(self.guidance_label)
        layout.addLayout(buttons)
        self.setLayout(layout)

        self.refresh()

    @property
    def diagnostics(self) -> SystemDiagnostics | None:
        return self._diagnostics

    def refresh(self) -> None:
        self.refresh_button.setEnabled(False)
        try:
            diagnostics = self._diagnostics_provider()
        except Exception as error:  # noqa: BLE001 - diagnostic boundary must keep UI usable
            QMessageBox.warning(self, "System Check", f"The system check could not finish: {error}")
            return
        finally:
            self.refresh_button.setEnabled(True)

        self._diagnostics = diagnostics
        self._populate(diagnostics)
        self.diagnostics_updated.emit(diagnostics)

    def _populate(self, diagnostics: SystemDiagnostics) -> None:
        self.system_label.setText(
            f"Filing Document Converter {diagnostics.application_version}<br>"
            f"{diagnostics.operating_system} {diagnostics.operating_system_version} "
            f"({diagnostics.architecture})<br>"
            f"Python {diagnostics.python_version}; PySide6 {diagnostics.pyside_version}"
        )

        self.component_table.setRowCount(len(diagnostics.components))
        guidance: list[str] = []
        for row, component in enumerate(diagnostics.components):
            status = "Available" if component.available else "Unavailable"
            status_item = QTableWidgetItem(status)
            status_item.setForeground(QColor("#18794e" if component.available else "#b42318"))
            details = "; ".join(component.details)
            if component.error:
                details = f"{details}; {component.error}" if details else component.error

            self.component_table.setItem(row, 0, QTableWidgetItem(component.label))
            self.component_table.setItem(row, 1, status_item)
            self.component_table.setItem(row, 2, QTableWidgetItem(component.version or ""))
            self.component_table.setItem(row, 3, QTableWidgetItem(details))

            if not component.available:
                guidance.append(
                    f"{component.label}: "
                    f"{installation_guidance(component.key, diagnostics.operating_system)}"
                )

        self.guidance_label.setText(
            "\n".join(guidance) if guidance else "All optional conversion components are available."
        )
        self.save_button.setEnabled(True)

    def choose_report_path(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Save diagnostic report",
            "filing-doc-converter-diagnostics.txt",
            "Text files (*.txt)",
        )
        if not path:
            return
        try:
            self.save_report(Path(path))
        except OSError as error:
            QMessageBox.warning(self, "Save Report", f"The report could not be saved: {error}")

    def save_report(self, path: Path) -> None:
        if self._diagnostics is None:
            raise RuntimeError("No diagnostic report is available")
        path.write_text(self._diagnostics.to_text(), encoding="utf-8", newline="\n")
