from datetime import date
from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QDragEnterEvent, QDropEvent
from PySide6.QtWidgets import (
    QCheckBox,
    QColorDialog,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)


SEATECH_COLORS = {
    "primary": "#071E33",
    "secondary": "#0057B8",
    "accent": "#00E89A",
}


def current_academic_year() -> str:
    today = date.today()
    start_year = (
        today.year
        if today.month >= 8
        else today.year - 1
    )
    return f"{start_year}-{start_year + 1}"


class ExcelDropArea(QLabel):
    file_selected = Signal(str)

    def __init__(self):
        super().__init__()

        self.setAcceptDrops(True)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setMinimumHeight(115)
        self.setWordWrap(True)

        self.setText(
            "Glissez-déposez un fichier Excel .xlsx ici\n"
            "ou utilisez le bouton « Choisir… »"
        )

        self.setStyleSheet(
            """
            QLabel {
                background-color: #FFFFFF;
                color: #66788A;
                border: 2px dashed #9FB3C8;
                border-radius: 8px;
                padding: 18px;
                font-size: 13px;
            }

            QLabel:hover {
                border-color: #0057B8;
                background-color: #F4FAFF;
            }
            """
        )

    def dragEnterEvent(
        self,
        event: QDragEnterEvent,
    ):
        if not event.mimeData().hasUrls():
            event.ignore()
            return

        urls = event.mimeData().urls()

        if any(
            url.isLocalFile()
            and url.toLocalFile().lower().endswith(
                ".xlsx"
            )
            for url in urls
        ):
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(
        self,
        event: QDropEvent,
    ):
        for url in event.mimeData().urls():
            if not url.isLocalFile():
                continue

            path = url.toLocalFile()

            if path.lower().endswith(".xlsx"):
                self.file_selected.emit(path)
                event.acceptProposedAction()
                return

        event.ignore()


class ColorSelector(QWidget):
    color_changed = Signal(str)

    def __init__(
        self,
        initial_color: str,
    ):
        super().__init__()

        self.color = initial_color.upper()

        self.preview = QLabel()
        self.preview.setFixedSize(28, 28)

        self.value_label = QLabel(self.color)
        self.value_label.setMinimumWidth(75)

        choose_button = QPushButton("Modifier…")
        choose_button.clicked.connect(
            self.choose_color
        )

        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        layout.addWidget(self.preview)
        layout.addWidget(self.value_label)
        layout.addWidget(choose_button)
        layout.addStretch()

        self.setLayout(layout)
        self.update_preview()

    def choose_color(self):
        selected = QColorDialog.getColor(
            initial=self.get_qcolor(),
            parent=self,
            title="Choisissez une couleur",
        )

        if not selected.isValid():
            return

        self.set_color(selected.name().upper())

    def get_qcolor(self):
        from PySide6.QtGui import QColor

        return QColor(self.color)

    def set_color(
        self,
        value: str,
    ):
        normalized = value.strip().upper()

        if not normalized.startswith("#"):
            normalized = f"#{normalized}"

        self.color = normalized
        self.value_label.setText(self.color)
        self.update_preview()
        self.color_changed.emit(self.color)

    def get_color(self) -> str:
        return self.color.lstrip("#").upper()

    def update_preview(self):
        self.preview.setStyleSheet(
            f"""
            QLabel {{
                background-color: {self.color};
                border: 1px solid #AAB7C4;
                border-radius: 14px;
            }}
            """
        )


class GeneratorPage(QWidget):
    analyze_requested = Signal(dict)

    def __init__(
        self,
        profiles_page=None,
        settings_page=None,
    ):
        super().__init__()

        self.profiles_page = profiles_page
        self.settings_page = settings_page
        self.excel_path = ""

        self.setAcceptDrops(True)
        self.build_interface()
        self.refresh_profiles()

    def build_interface(self):
        title = QLabel("Génération du rapport")
        title.setObjectName("pageTitle")

        description = QLabel(
            "Importez l’évaluation Excel, renseignez "
            "le contexte, choisissez les paramètres "
            "statistiques et préparez le contrôle du "
            "rapport avant sa génération."
        )
        description.setObjectName("pageDescription")
        description.setWordWrap(True)

        content = QWidget()
        content_layout = QVBoxLayout()
        content_layout.setSpacing(18)

        content_layout.addWidget(
            self.build_excel_group()
        )
        content_layout.addWidget(
            self.build_context_group()
        )
        content_layout.addWidget(
            self.build_statistics_group()
        )
        content_layout.addWidget(
            self.build_albert_group()
        )
        content_layout.addWidget(
            self.build_graphics_group()
        )
        content_layout.addWidget(
            self.build_action_group()
        )
        content_layout.addStretch()

        content.setLayout(content_layout)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(
            QScrollArea.Shape.NoFrame
        )
        scroll.setWidget(content)

        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(
            40,
            36,
            40,
            30,
        )
        main_layout.setSpacing(15)
        main_layout.addWidget(title)
        main_layout.addWidget(description)
        main_layout.addWidget(scroll)

        self.setLayout(main_layout)

    def build_excel_group(self):
        group = QGroupBox("Fichier Excel")

        self.drop_area = ExcelDropArea()
        self.drop_area.file_selected.connect(
            self.set_excel_file
        )

        self.excel_path_label = QLabel(
            "Aucun fichier choisi."
        )
        self.excel_path_label.setWordWrap(True)
        self.excel_path_label.setStyleSheet(
            "color: #66788A;"
        )

        choose_button = QPushButton(
            "Choisir…"
        )
        choose_button.setObjectName(
            "secondaryButton"
        )
        choose_button.clicked.connect(
            self.choose_excel_file
        )

        clear_button = QPushButton(
            "Retirer"
        )
        clear_button.clicked.connect(
            self.clear_excel_file
        )

        actions = QHBoxLayout()
        actions.addWidget(choose_button)
        actions.addWidget(clear_button)
        actions.addStretch()

        layout = QVBoxLayout()
        layout.addWidget(self.drop_area)
        layout.addWidget(self.excel_path_label)
        layout.addLayout(actions)

        group.setLayout(layout)
        return group

    def build_context_group(self):
        group = QGroupBox("Contexte du cours")

        self.course_input = QLineEdit()
        self.course_input.setPlaceholderText(
            "Ex. Ateliers statistiques et prédictions"
        )

        self.cohort_input = QLineEdit()
        self.cohort_input.setPlaceholderText(
            "Ex. SeaTech 2A"
        )

        self.academic_year_input = QLineEdit(
            current_academic_year()
        )

        self.invited_input = QSpinBox()
        self.invited_input.setRange(1, 5000)
        self.invited_input.setValue(44)

        form = QFormLayout()
        form.setSpacing(12)
        form.addRow(
            "Intitulé du cours",
            self.course_input,
        )
        form.addRow(
            "Promotion / cohorte",
            self.cohort_input,
        )
        form.addRow(
            "Année universitaire",
            self.academic_year_input,
        )
        form.addRow(
            "Individus sollicités",
            self.invited_input,
        )

        group.setLayout(form)
        return group

    def build_statistics_group(self):
        group = QGroupBox("Statistiques")

        self.confidence_input = QComboBox()
        self.confidence_input.addItem(
            "90 %",
            0.90,
        )
        self.confidence_input.addItem(
            "95 %",
            0.95,
        )
        self.confidence_input.addItem(
            "99 %",
            0.99,
        )
        self.confidence_input.setCurrentIndex(1)

        form = QFormLayout()
        form.addRow(
            "Niveau de confiance",
            self.confidence_input,
        )

        group.setLayout(form)
        return group

    def build_albert_group(self):
        group = QGroupBox(
            "Interprétation par Albert"
        )

        self.use_ai_input = QCheckBox(
            "Générer les synthèses et "
            "recommandations via Albert"
        )
        self.use_ai_input.setChecked(True)

        self.profile_input = QComboBox()

        refresh_button = QPushButton(
            "Actualiser les profils"
        )
        refresh_button.clicked.connect(
            self.refresh_profiles
        )

        profile_layout = QHBoxLayout()
        profile_layout.addWidget(
            self.profile_input,
            1,
        )
        profile_layout.addWidget(
            refresh_button,
        )

        self.profile_details_label = QLabel()
        self.profile_details_label.setWordWrap(True)
        self.profile_details_label.setStyleSheet(
            "color: #66788A; font-size: 12px;"
        )

        self.profile_input.currentIndexChanged.connect(
            self.update_profile_details
        )

        form = QFormLayout()
        form.setSpacing(12)
        form.addRow("", self.use_ai_input)
        form.addRow(
            "Profil d’interprétation",
            profile_layout,
        )
        form.addRow(
            "",
            self.profile_details_label,
        )

        group.setLayout(form)
        return group

    def build_graphics_group(self):
        group = QGroupBox(
            "Identité graphique et donuts"
        )

        self.color_profile_input = QComboBox()
        self.color_profile_input.addItem(
            "SeaTech",
            "seatech",
        )
        self.color_profile_input.addItem(
            "Personnalisé",
            "custom",
        )

        self.primary_color = ColorSelector(
            SEATECH_COLORS["primary"]
        )
        self.secondary_color = ColorSelector(
            SEATECH_COLORS["secondary"]
        )
        self.accent_color = ColorSelector(
            SEATECH_COLORS["accent"]
        )

        self.primary_color.color_changed.connect(
            self.switch_to_custom_colors
        )
        self.secondary_color.color_changed.connect(
            self.switch_to_custom_colors
        )
        self.accent_color.color_changed.connect(
            self.switch_to_custom_colors
        )

        self.color_profile_input.currentIndexChanged.connect(
            self.on_color_profile_changed
        )

        restore_button = QPushButton(
            "Restaurer SeaTech"
        )
        restore_button.clicked.connect(
            self.restore_seatech_colors
        )

        self.show_confidence_input = QCheckBox(
            "Afficher les arcs des intervalles "
            "de confiance"
        )
        self.show_confidence_input.setChecked(True)

        self.maximum_categories_input = QSpinBox()
        self.maximum_categories_input.setRange(
            3,
            10,
        )
        self.maximum_categories_input.setValue(8)

        self.ci_transparency_input = QSpinBox()
        self.ci_transparency_input.setRange(
            0,
            90,
        )
        self.ci_transparency_input.setValue(62)
        self.ci_transparency_input.setSuffix(" %")

        form = QFormLayout()
        form.setSpacing(12)
        form.addRow(
            "Profil couleur",
            self.color_profile_input,
        )
        form.addRow(
            "Couleur principale",
            self.primary_color,
        )
        form.addRow(
            "Couleur secondaire",
            self.secondary_color,
        )
        form.addRow(
            "Couleur d’accent",
            self.accent_color,
        )
        form.addRow("", restore_button)
        form.addRow(
            "",
            self.show_confidence_input,
        )
        form.addRow(
            "Catégories maximales",
            self.maximum_categories_input,
        )
        form.addRow(
            "Transparence des IC",
            self.ci_transparency_input,
        )

        group.setLayout(form)
        return group

    def build_action_group(self):
        group = QGroupBox()

        self.analyze_button = QPushButton(
            "Analyser et contrôler"
        )
        self.analyze_button.setObjectName(
            "primaryButton"
        )
        self.analyze_button.setMinimumHeight(44)
        self.analyze_button.clicked.connect(
            self.validate_and_emit
        )

        self.status_label = QLabel(
            "Choisissez un fichier Excel pour commencer."
        )
        self.status_label.setWordWrap(True)
        self.status_label.setStyleSheet(
            "color: #66788A;"
        )

        layout = QHBoxLayout()
        layout.addWidget(self.analyze_button)
        layout.addWidget(self.status_label, 1)

        group.setLayout(layout)
        return group

    def choose_excel_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Choisissez l’export Excel",
            str(Path.home()),
            "Fichiers Excel (*.xlsx)",
        )

        if path:
            self.set_excel_file(path)

    def set_excel_file(
        self,
        path: str,
    ):
        candidate = Path(path)

        if (
            not candidate.is_file()
            or candidate.suffix.lower() != ".xlsx"
        ):
            QMessageBox.warning(
                self,
                "Fichier incorrect",
                "Sélectionnez un fichier Excel .xlsx.",
            )
            return

        self.excel_path = str(candidate)
        self.excel_path_label.setText(
            self.excel_path
        )
        self.drop_area.setText(
            f"Fichier sélectionné :\n"
            f"{candidate.name}"
        )
        self.status_label.setText(
            "Fichier Excel prêt pour l’analyse."
        )

    def clear_excel_file(self):
        self.excel_path = ""
        self.excel_path_label.setText(
            "Aucun fichier choisi."
        )
        self.drop_area.setText(
            "Glissez-déposez un fichier Excel "
            ".xlsx ici\n"
            "ou utilisez le bouton « Choisir… »"
        )
        self.status_label.setText(
            "Choisissez un fichier Excel "
            "pour commencer."
        )

    def refresh_profiles(self):
        current_id = self.profile_input.currentData()

        self.profile_input.blockSignals(True)
        self.profile_input.clear()

        if self.profiles_page is None:
            self.profile_input.addItem(
                "Institutionnel prudent",
                "",
            )
        else:
            profiles = (
                self.profiles_page.all_profiles()
            )

            for profile in profiles:
                self.profile_input.addItem(
                    profile["name"],
                    profile["id"],
                )

        if current_id:
            index = self.profile_input.findData(
                current_id
            )

            if index >= 0:
                self.profile_input.setCurrentIndex(
                    index
                )

        self.profile_input.blockSignals(False)
        self.update_profile_details()

    def update_profile_details(self):
        if self.profiles_page is None:
            self.profile_details_label.setText(
                "Profil institutionnel prudent."
            )
            return

        profile_id = self.profile_input.currentData()

        if not profile_id:
            return

        profile = self.profiles_page.profile_by_id(
            profile_id
        )

        self.profile_details_label.setText(
            profile.get("details", "")
        )

    def on_color_profile_changed(self):
        if (
            self.color_profile_input.currentData()
            == "seatech"
        ):
            self.restore_seatech_colors()

    def switch_to_custom_colors(self):
        if (
            self.color_profile_input.currentData()
            == "seatech"
        ):
            index = self.color_profile_input.findData(
                "custom"
            )
            self.color_profile_input.blockSignals(True)
            self.color_profile_input.setCurrentIndex(
                index
            )
            self.color_profile_input.blockSignals(False)

    def restore_seatech_colors(self):
        self.primary_color.blockSignals(True)
        self.secondary_color.blockSignals(True)
        self.accent_color.blockSignals(True)

        self.primary_color.set_color(
            SEATECH_COLORS["primary"]
        )
        self.secondary_color.set_color(
            SEATECH_COLORS["secondary"]
        )
        self.accent_color.set_color(
            SEATECH_COLORS["accent"]
        )

        self.primary_color.blockSignals(False)
        self.secondary_color.blockSignals(False)
        self.accent_color.blockSignals(False)

        index = self.color_profile_input.findData(
            "seatech"
        )

        self.color_profile_input.blockSignals(True)
        self.color_profile_input.setCurrentIndex(index)
        self.color_profile_input.blockSignals(False)

    def validate_and_emit(self):
        errors = []

        if not self.excel_path:
            errors.append(
                "choisissez un fichier Excel"
            )

        if not self.course_input.text().strip():
            errors.append(
                "saisissez l’intitulé du cours"
            )

        if errors:
            QMessageBox.warning(
                self,
                "Informations manquantes",
                "Pour continuer :\n\n• "
                + "\n• ".join(errors),
            )
            return

        payload = self.collect_values()
        self.status_label.setText(
            "Analyse en cours..."
        )
        self.analyze_requested.emit(payload)


    def collect_values(self):
        profile_id = (
            self.profile_input.currentData()
        )

        profile = None
        compiled_instructions = ""

        if (
            self.profiles_page is not None
            and profile_id
        ):
            profile = (
                self.profiles_page.profile_by_id(
                    profile_id
                )
            )
            compiled_instructions = (
                self.profiles_page
                .compiled_instructions(profile_id)
            )

        return {
            "excel_path": self.excel_path,
            "course": self.course_input.text().strip(),
            "cohort": self.cohort_input.text().strip(),
            "academic_year": (
                self.academic_year_input.text().strip()
            ),
            "invited": self.invited_input.value(),
            "confidence": (
                self.confidence_input.currentData()
            ),
            "use_ai": self.use_ai_input.isChecked(),
            "profile_id": profile_id,
            "profile": profile,
            "profile_instructions": (
                compiled_instructions
            ),
            "brand": {
                "primary": (
                    self.primary_color.get_color()
                ),
                "secondary": (
                    self.secondary_color.get_color()
                ),
                "accent": (
                    self.accent_color.get_color()
                ),
                "font": "Calibri",
            },
            "charts": {
                "binary_gauge": True,
                "show_connectors": True,
                "show_confidence_intervals": (
                    self.show_confidence_input
                    .isChecked()
                ),
                "maximum_categories": (
                    self.maximum_categories_input
                    .value()
                ),
                "ci_transparency": (
                    self.ci_transparency_input.value()
                ),
            },
        }