"""Approval dialog — shown for Complex-tier tasks before AI execution."""

from __future__ import annotations

from PyQt6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QLabel,
    QPlainTextEdit,
    QVBoxLayout,
    QWidget,
)

from src.memory.audit import get_logger

_log = get_logger("ui.approval_dialog")


class ApprovalDialog(QDialog):
    """Shows the cleaned prompt in an editable field.

    User can edit the text before approving, or cancel to discard.
    """

    def __init__(self, request_id: str, prompt: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("JARVIS — Approve Task")
        self.setMinimumWidth(480)
        self._request_id = request_id

        label = QLabel("Review and edit the task before it runs:")

        self._editor = QPlainTextEdit(prompt)
        self._editor.setMinimumHeight(80)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._on_approve)
        buttons.rejected.connect(self._on_cancel)

        layout = QVBoxLayout()
        layout.addWidget(label)
        layout.addWidget(self._editor)
        layout.addWidget(buttons)
        self.setLayout(layout)

        self._approved = False
        self._edited_prompt = prompt

    def _on_approve(self) -> None:
        self._approved = True
        self._edited_prompt = self._editor.toPlainText().strip()
        _log.info("approval_dialog_approved", request_id=self._request_id,
                  edited=self._edited_prompt != self._editor.toPlainText())
        self.accept()

    def _on_cancel(self) -> None:
        self._approved = False
        _log.info("approval_dialog_cancelled", request_id=self._request_id)
        self.reject()

    @property
    def approved(self) -> bool:
        return self._approved

    @property
    def edited_prompt(self) -> str:
        return self._edited_prompt

    def prompt_text(self) -> str:
        return self._editor.toPlainText()
