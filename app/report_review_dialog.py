import json
from pathlib import Path

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)


PRIORITIES = [
    "haute",
    "moyenne",
    "faible",
]


def value_as_int(value) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def value_as_float(value) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def format_percent(value) -> str:
    numeric_value = value_as_float(value)

    return (
        f"{numeric_value * 100:.1f} %"
        .replace(".", ",")
    )


class ClosedQuestionEditor(QGroupBox):
    def __init__(
        self,
        question: dict,
        index: int,
    ):
        super().__init__()

        self.question = question
        self.index = index

        question_id = question.get(
            "id",
            f"QF{index:03d}",
        )

        self.setTitle(
            question.get(
                "question",
                f"Question fermée {index}",
            )
        )

        self.include_input = QCheckBox(
            "Conserver cette question dans le rapport"
        )
        self.include_input.setChecked(
            bool(question.get("included", True))
        )

        identifier_label = QLabel(
            f"Identifiant : {question_id}"
        )
        identifier_label.setStyleSheet(
            "color: #66788A; font-size: 11px;"
        )

        rows = question.get("rows") or []

        details = []

        for row in rows:
            label = str(
                row.get("label", "")
            )

            count = value_as_int(
                row.get("count")
            )

            respondents = value_as_int(
                row.get("n")
                or row.get(
                    "respondents_to_question"
                )
            )

            proportion = value_as_float(
                row.get("proportion")
                or row.get(
                    "proportion_among_respondents"
                )
            )

            ci_low = value_as_float(
                row.get("ci_low")
            )

            ci_high = value_as_float(
                row.get("ci_high")
            )

            details.append(
                f"{label} : "
                f"{count}/{respondents} "
                f"({format_percent(proportion)}) · "
                f"IC [{format_percent(ci_low)} ; "
                f"{format_percent(ci_high)}]"
            )

        details_label = QLabel(
            "\n".join(details)
            if details
            else "Aucune modalité disponible."
        )
        details_label.setWordWrap(True)
        details_label.setStyleSheet(
            "color: #243447;"
        )

        layout = QVBoxLayout()
        layout.setSpacing(8)
        layout.addWidget(self.include_input)
        layout.addWidget(identifier_label)
        layout.addWidget(details_label)

        self.setLayout(layout)

    def is_included(self) -> bool:
        return self.include_input.isChecked()


class ThemeEditor(QGroupBox):
    def __init__(
        self,
        theme: dict,
        index: int,
    ):
        super().__init__(
            f"Synthèse {index}"
        )

        self.theme = theme
        self.index = index

        self.include_input = QCheckBox(
            "Conserver cette synthèse"
        )
        self.include_input.setChecked(
            bool(theme.get("included", True))
        )

        self.title_input = QTextEdit()
        self.title_input.setMaximumHeight(58)
        self.title_input.setPlainText(
            str(theme.get("title", ""))
        )

        self.summary_input = QTextEdit()
        self.summary_input.setMinimumHeight(110)
        self.summary_input.setPlainText(
            str(theme.get("summary", ""))
        )

        self.priority_input = QComboBox()
        self.priority_input.addItems(
            PRIORITIES
        )

        priority = str(
            theme.get("priority", "moyenne")
        ).lower()

        priority_index = (
            self.priority_input.findText(priority)
        )

        self.priority_input.setCurrentIndex(
            priority_index
            if priority_index >= 0
            else 1
        )

        form = QFormLayout()
        form.setSpacing(10)
        form.addRow("", self.include_input)
        form.addRow(
            "Importance",
            self.priority_input,
        )
        form.addRow(
            "Titre",
            self.title_input,
        )
        form.addRow(
            "Texte",
            self.summary_input,
        )

        self.setLayout(form)

    def edited_value(self) -> dict:
        edited = dict(self.theme)

        edited["id"] = edited.get(
            "id",
            f"TH{self.index:03d}",
        )
        edited["included"] = (
            self.include_input.isChecked()
        )
        edited["title"] = (
            self.title_input
            .toPlainText()
            .strip()
        )
        edited["summary"] = (
            self.summary_input
            .toPlainText()
            .strip()
        )
        edited["priority"] = (
            self.priority_input.currentText()
        )

        return edited


class RecommendationEditor(QGroupBox):
    def __init__(
        self,
        recommendation: dict,
        index: int,
    ):
        super().__init__(
            f"Recommandation {index}"
        )

        self.recommendation = recommendation
        self.index = index

        self.include_input = QCheckBox(
            "Conserver cette recommandation"
        )
        self.include_input.setChecked(
            bool(
                recommendation.get(
                    "included",
                    True,
                )
            )
        )

        self.priority_input = QComboBox()
        self.priority_input.addItems(
            PRIORITIES
        )

        priority = str(
            recommendation.get(
                "priority",
                "moyenne",
            )
        ).lower()

        priority_index = (
            self.priority_input.findText(priority)
        )

        self.priority_input.setCurrentIndex(
            priority_index
            if priority_index >= 0
            else 1
        )

        self.title_input = QTextEdit()
        self.title_input.setMaximumHeight(58)
        self.title_input.setPlainText(
            str(
                recommendation.get(
                    "title",
                    "",
                )
            )
        )

        self.evidence_input = QTextEdit()
        self.evidence_input.setMinimumHeight(90)
        self.evidence_input.setPlainText(
            str(
                recommendation.get(
                    "evidence",
                    "",
                )
            )
        )

        self.action_input = QTextEdit()
        self.action_input.setMinimumHeight(90)
        self.action_input.setPlainText(
            str(
                recommendation.get(
                    "action",
                    "",
                )
            )
        )

        form = QFormLayout()
        form.setSpacing(10)
        form.addRow("", self.include_input)
        form.addRow(
            "Importance",
            self.priority_input,
        )
        form.addRow(
            "Titre",
            self.title_input,
        )
        form.addRow(
            "Éléments probants",
            self.evidence_input,
        )
        form.addRow(
            "Action recommandée",
            self.action_input,
        )

        self.setLayout(form)

    def edited_value(self) -> dict:
        edited = dict(self.recommendation)

        edited["id"] = edited.get(
            "id",
            f"REC{self.index:03d}",
        )
        edited["included"] = (
            self.include_input.isChecked()
        )
        edited["priority"] = (
            self.priority_input.currentText()
        )
        edited["title"] = (
            self.title_input
            .toPlainText()
            .strip()
        )
        edited["evidence"] = (
            self.evidence_input
            .toPlainText()
            .strip()
        )
        edited["action"] = (
            self.action_input
            .toPlainText()
            .strip()
        )

        return edited


class ReportReviewDialog(QDialog):
    generate_requested = Signal(str)

    def __init__(
        self,
        json_path: str,
        parent=None,
    ):
        super().__init__(parent)

        self.json_path = Path(json_path)
        self.report_data = {}

        self.question_editors = []
        self.theme_editors = []
        self.recommendation_editors = []

        self.setWindowTitle(
            "Contrôle avant génération"
        )
        self.resize(1040, 760)
        self.setMinimumSize(860, 620)

        self.load_report()
        self.build_interface()

    def load_report(self):
        if not self.json_path.is_file():
            raise FileNotFoundError(
                "Le fichier JSON intermédiaire "
                "est introuvable :\n"
                f"{self.json_path}"
            )

        self.report_data = json.loads(
            self.json_path.read_text(
                encoding="utf-8"
            )
        )

        if not isinstance(
            self.report_data,
            dict,
        ):
            raise ValueError(
                "Le fichier intermédiaire ne "
                "contient pas un objet JSON valide."
            )

    def build_interface(self):
        title = QLabel(
            "Contrôle avant génération"
        )
        title.setStyleSheet(
            """
            QLabel {
                color: #071E33;
                font-size: 24px;
                font-weight: 700;
            }
            """
        )

        description = QLabel(
            "Vérifiez les questions fermées, "
            "les synthèses et les recommandations. "
            "Les éléments décochés seront exclus "
            "du PowerPoint."
        )
        description.setWordWrap(True)
        description.setStyleSheet(
            "color: #66788A;"
        )

        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)

        self.tabs.addTab(
            self.build_questions_tab(),
            "Questions fermées",
        )

        self.tabs.addTab(
            self.build_themes_tab(),
            "Synthèses",
        )

        self.tabs.addTab(
            self.build_recommendations_tab(),
            "Recommandations",
        )

        select_all_button = QPushButton(
            "Tout conserver"
        )
        select_all_button.clicked.connect(
            lambda: self.set_all_included(True)
        )

        exclude_all_button = QPushButton(
            "Tout exclure"
        )
        exclude_all_button.clicked.connect(
            lambda: self.set_all_included(False)
        )

        self.summary_label = QLabel()
        self.summary_label.setStyleSheet(
            "color: #66788A;"
        )

        self.update_summary()

        global_actions = QHBoxLayout()
        global_actions.addWidget(
            select_all_button
        )
        global_actions.addWidget(
            exclude_all_button
        )
        global_actions.addStretch()
        global_actions.addWidget(
            self.summary_label
        )

        self.button_box = QDialogButtonBox()

        self.cancel_button = (
            self.button_box.addButton(
                "Annuler",
                QDialogButtonBox.ButtonRole.RejectRole,
            )
        )

        self.generate_button = (
            self.button_box.addButton(
                "Générer le PowerPoint",
                QDialogButtonBox.ButtonRole.AcceptRole,
            )
        )

        self.generate_button.setStyleSheet(
            """
            QPushButton {
                background-color: #00E89A;
                color: #071E33;
                border: none;
                border-radius: 6px;
                padding: 9px 18px;
                font-weight: 700;
            }

            QPushButton:hover {
                background-color: #20F0AC;
            }
            """
        )

        self.cancel_button.clicked.connect(
            self.reject
        )

        self.generate_button.clicked.connect(
            self.save_and_request_generation
        )

        layout = QVBoxLayout()
        layout.setContentsMargins(
            26,
            24,
            26,
            22,
        )
        layout.setSpacing(14)

        layout.addWidget(title)
        layout.addWidget(description)
        layout.addLayout(global_actions)
        layout.addWidget(self.tabs)
        layout.addWidget(self.button_box)

        self.setLayout(layout)

    def build_questions_tab(self):
        questions = (
            self.report_data
            .get("statistics", {})
            .get("closed_questions", [])
        )

        content = QWidget()
        layout = QVBoxLayout()
        layout.setSpacing(12)

        if not questions:
            label = QLabel(
                "Aucune question fermée "
                "n’est disponible."
            )
            label.setStyleSheet(
                "color: #66788A;"
            )
            layout.addWidget(label)
        else:
            for index, question in enumerate(
                questions,
                start=1,
            ):
                editor = ClosedQuestionEditor(
                    question,
                    index,
                )

                editor.include_input.toggled.connect(
                    self.update_summary
                )

                self.question_editors.append(
                    editor
                )

                layout.addWidget(editor)

        layout.addStretch()
        content.setLayout(layout)

        return self.scrollable(content)

    def build_themes_tab(self):
        themes = (
            self.report_data
            .get("analysis", {})
            .get("themes", [])
        )

        content = QWidget()
        layout = QVBoxLayout()
        layout.setSpacing(12)

        if not themes:
            label = QLabel(
                "Aucune synthèse Albert "
                "n’est disponible."
            )
            label.setStyleSheet(
                "color: #66788A;"
            )
            layout.addWidget(label)
        else:
            for index, theme in enumerate(
                themes,
                start=1,
            ):
                editor = ThemeEditor(
                    theme,
                    index,
                )

                editor.include_input.toggled.connect(
                    self.update_summary
                )

                self.theme_editors.append(
                    editor
                )

                layout.addWidget(editor)

        layout.addStretch()
        content.setLayout(layout)

        return self.scrollable(content)

    def build_recommendations_tab(self):
        recommendations = (
            self.report_data
            .get("analysis", {})
            .get("recommendations", [])
        )

        content = QWidget()
        layout = QVBoxLayout()
        layout.setSpacing(12)

        if not recommendations:
            label = QLabel(
                "Aucune recommandation Albert "
                "n’est disponible."
            )
            label.setStyleSheet(
                "color: #66788A;"
            )
            layout.addWidget(label)
        else:
            for index, recommendation in enumerate(
                recommendations,
                start=1,
            ):
                editor = RecommendationEditor(
                    recommendation,
                    index,
                )

                editor.include_input.toggled.connect(
                    self.update_summary
                )

                self.recommendation_editors.append(
                    editor
                )

                layout.addWidget(editor)

        layout.addStretch()
        content.setLayout(layout)

        return self.scrollable(content)

    @staticmethod
    def scrollable(widget):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(
            QScrollArea.Shape.NoFrame
        )
        scroll.setWidget(widget)

        return scroll

    def set_all_included(
        self,
        included: bool,
    ):
        for editor in self.question_editors:
            editor.include_input.setChecked(
                included
            )

        for editor in self.theme_editors:
            editor.include_input.setChecked(
                included
            )

        for editor in self.recommendation_editors:
            editor.include_input.setChecked(
                included
            )

        self.update_summary()

    def update_summary(self):
        questions = sum(
            editor.is_included()
            for editor in self.question_editors
        )

        themes = sum(
            editor.include_input.isChecked()
            for editor in self.theme_editors
        )

        recommendations = sum(
            editor.include_input.isChecked()
            for editor
            in self.recommendation_editors
        )

        self.summary_label.setText(
            f"Sélection : "
            f"{questions} question(s), "
            f"{themes} synthèse(s), "
            f"{recommendations} recommandation(s)"
        )

    def apply_edits(self):
        statistics = self.report_data.setdefault(
            "statistics",
            {},
        )

        original_questions = (
            statistics.get(
                "closed_questions",
                [],
            )
        )

        retained_questions = []

        for index, question in enumerate(
            original_questions
        ):
            if index >= len(
                self.question_editors
            ):
                continue

            editor = self.question_editors[
                index
            ]

            if not editor.is_included():
                continue

            edited_question = dict(question)
            edited_question["included"] = True
            edited_question["id"] = (
                edited_question.get("id")
                or f"QF{index + 1:03d}"
            )

            retained_questions.append(
                edited_question
            )

        statistics["closed_questions"] = (
            retained_questions
        )

        analysis = self.report_data.setdefault(
            "analysis",
            {},
        )

        analysis["themes"] = [
            editor.edited_value()
            for editor in self.theme_editors
            if editor.include_input.isChecked()
        ]

        analysis["recommendations"] = [
            editor.edited_value()
            for editor
            in self.recommendation_editors
            if editor.include_input.isChecked()
        ]

    def save_reviewed_json(self):
        self.apply_edits()

        self.json_path.write_text(
            json.dumps(
                self.report_data,
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

    def save_and_request_generation(self):
        retained_count = (
            sum(
                editor.is_included()
                for editor
                in self.question_editors
            )
            + sum(
                editor.include_input.isChecked()
                for editor
                in self.theme_editors
            )
            + sum(
                editor.include_input.isChecked()
                for editor
                in self.recommendation_editors
            )
        )

        if retained_count == 0:
            answer = QMessageBox.question(
                self,
                "Rapport vide",
                (
                    "Aucun contenu n’est sélectionné.\n\n"
                    "Voulez-vous quand même poursuivre ?"
                ),
                (
                    QMessageBox.StandardButton.Yes
                    | QMessageBox.StandardButton.No
                ),
                QMessageBox.StandardButton.No,
            )

            if (
                answer
                != QMessageBox.StandardButton.Yes
            ):
                return

        try:
            self.save_reviewed_json()
        except Exception as error:
            QMessageBox.critical(
                self,
                "Erreur d’enregistrement",
                (
                    "Le JSON contrôlé n’a pas pu "
                    f"être enregistré :\n\n{error}"
                ),
            )
            return

        self.generate_requested.emit(
            str(self.json_path)
        )

        self.accept()