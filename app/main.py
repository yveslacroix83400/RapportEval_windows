import sys
import os

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from profiles_page import ProfilesPage
from settings_page import SettingsPage
from generator_page import GeneratorPage
from report_controller import ReportController
from report_review_dialog import ReportReviewDialog


COLORS = {
    "navy": "#071E33",
    "blue": "#0057B8",
    "green": "#00E89A",
    "background": "#F4F7FA",
    "white": "#FFFFFF",
    "text": "#243447",
    "muted": "#66788A",
    "border": "#D9E2EC",
}


class PlaceholderPage(QWidget):
    def __init__(
        self,
        title_text: str,
        description_text: str,
        button_text: str,
    ):
        super().__init__()

        title = QLabel(title_text)
        title.setObjectName("pageTitle")

        description = QLabel(description_text)
        description.setObjectName("pageDescription")
        description.setWordWrap(True)

        button = QPushButton(button_text)
        button.setObjectName("secondaryButton")
        button.setMinimumHeight(38)
        button.setMaximumWidth(260)

        status = QLabel("Écran prêt à être complété.")
        status.setObjectName("statusLabel")
        status.setWordWrap(True)

        button.clicked.connect(
            lambda: status.setText(
                f"Le bouton « {button_text} » fonctionne correctement."
            )
        )

        layout = QVBoxLayout()
        layout.setContentsMargins(40, 36, 40, 40)
        layout.setSpacing(18)

        layout.addWidget(title)
        layout.addWidget(description)
        layout.addSpacing(15)
        layout.addWidget(
            button,
            alignment=Qt.AlignmentFlag.AlignLeft,
        )
        layout.addWidget(status)
        layout.addStretch()

        self.setLayout(layout)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("RapportEval")
        self.resize(1120, 780)
        self.setMinimumSize(900, 650)

        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)

        self.profiles_page = ProfilesPage()

        self.settings_page = SettingsPage()

        self.generator_page = GeneratorPage(
                    profiles_page=self.profiles_page,
                    settings_page=self.settings_page,
        )

        self.report_controller = ReportController(
                    settings_page=self.settings_page,
                    parent=self,
                )
        self.generator_page.analyze_requested.connect(
                    self.report_controller.prepare_report
                )

        self.report_controller.log_received.connect(
                    self.on_report_log
                )

        self.report_controller.preparation_failed.connect(
                    self.on_report_error
                )

        self.report_controller.preparation_finished.connect(
                    self.on_report_prepared
                )

        self.report_controller.generation_finished.connect(
                    self.on_generation_finished
                )

        self.report_controller.generation_failed.connect(
                    self.on_generation_failed
                )

        self.tabs.addTab(
            self.generator_page,
            "Génération du rapport",
        )
        self.tabs.addTab(
            self.profiles_page,
            "Profils d’interprétation",
        )
        self.tabs.addTab(
            self.settings_page,
            "Albert et moteur",
        )

        self.setCentralWidget(self.tabs)
        self.statusBar().showMessage(
            "RapportEval est prêt."
        )

        self.apply_style()

    def on_report_log(self, message):
        self.statusBar().showMessage(message)

    def on_report_error(self, message):
        self.statusBar().showMessage(
                "Échec de la préparation du rapport."
        )

        QMessageBox.critical(
        self,
        "Erreur pendant l’analyse",
        message,
         )

    def on_report_prepared(self, json_path):
        self.statusBar().showMessage(
            "Analyse terminée. Ouverture du contrôle."
        )

        try:
            review_dialog = ReportReviewDialog(
                json_path=json_path,
                parent=self,
            )

            review_dialog.generate_requested.connect(
                self.on_review_approved
            )

            review_dialog.exec()

        except Exception as error:
            QMessageBox.critical(
                self,
                "Erreur d’ouverture du contrôle",
                (
                    "L’écran de contrôle n’a pas pu "
                    "être ouvert.\n\n"
                    f"{error}"
                ),
            )

    def on_review_approved(self, json_path):
        self.statusBar().showMessage(
            "Lancement de la génération du PowerPoint..."
        )

        self.report_controller.generate_powerpoint(
            json_path
        )

    def on_generation_finished(self, pptx_path):
        self.statusBar().showMessage(
            "PowerPoint généré avec succès."
        )

        message_box = QMessageBox(self)
        message_box.setWindowTitle("Rapport généré")
        message_box.setIcon(
            QMessageBox.Icon.Information
        )
        message_box.setText(
            "Le rapport PowerPoint a été généré "
            "avec succès."
        )
        message_box.setInformativeText(
            pptx_path
        )

        open_button = message_box.addButton(
            "Ouvrir le PowerPoint",
            QMessageBox.ButtonRole.AcceptRole,
        )

        explorer_button = message_box.addButton(
            "Afficher dans l’Explorateur",
            QMessageBox.ButtonRole.ActionRole,
        )

        close_button = message_box.addButton(
            "Fermer",
            QMessageBox.ButtonRole.RejectRole,
        )

        message_box.setDefaultButton(open_button)
        message_box.exec()

        clicked_button = message_box.clickedButton()

        if clicked_button == open_button:
            try:
                os.startfile(pptx_path)
            except OSError as error:
                QMessageBox.critical(
                    self,
                    "Ouverture impossible",
                    (
                        "Windows n’a pas pu ouvrir "
                        "le fichier PowerPoint.\n\n"
                        f"{error}"
                    ),
                )

        elif clicked_button == explorer_button:
            try:
                import subprocess

                subprocess.run(
                    [
                        "explorer.exe",
                        "/select,",
                        os.path.normpath(pptx_path),
                    ],
                    check=False,
                )
            except OSError as error:
                QMessageBox.critical(
                    self,
                    "Explorateur indisponible",
                    (
                        "Windows n’a pas pu afficher "
                        "le rapport dans l’Explorateur.\n\n"
                        f"{error}"
                    ),
                )


    def on_generation_failed(self, message):
        self.statusBar().showMessage(
            "Échec de la génération du PowerPoint."
        )

        QMessageBox.critical(
            self,
            "Erreur de génération",
            message,
        )

    def apply_style(self):
        self.setStyleSheet(
            f"""
            QMainWindow {{
                background-color: {COLORS["background"]};
            }}

            QTabWidget::pane {{
                border: 1px solid {COLORS["border"]};
                background-color: {COLORS["background"]};
            }}

            QTabBar::tab {{
                background-color: #E8EEF3;
                color: {COLORS["text"]};
                border: 1px solid {COLORS["border"]};
                border-bottom: none;
                padding: 11px 20px;
                margin-right: 2px;
                font-size: 13px;
                font-weight: 600;
            }}

            QTabBar::tab:selected {{
                background-color: {COLORS["white"]};
                color: {COLORS["navy"]};
                border-top: 3px solid {COLORS["green"]};
            }}

            QTabBar::tab:hover:!selected {{
                background-color: #DDE7EE;
            }}

            QLabel#pageTitle {{
                color: {COLORS["navy"]};
                font-size: 25px;
                font-weight: 700;
            }}

            QLabel#pageDescription {{
                color: {COLORS["muted"]};
                font-size: 14px;
                line-height: 1.4;
            }}

            QLabel#statusLabel {{
                color: {COLORS["muted"]};
                font-size: 13px;
                padding-top: 8px;
            }}

            QPushButton#secondaryButton {{
                background-color: {COLORS["white"]};
                color: {COLORS["navy"]};
                border: 1px solid {COLORS["blue"]};
                border-radius: 6px;
                padding: 8px 18px;
                font-size: 13px;
                font-weight: 600;
            }}

            QPushButton#secondaryButton:hover {{
                background-color: #E9F3FC;
            }}

            QPushButton#secondaryButton:pressed {{
                background-color: #D7EAF9;
            }}

            QStatusBar {{
                background-color: {COLORS["white"]};
                color: {COLORS["muted"]};
                border-top: 1px solid {COLORS["border"]};
                font-size: 12px;
            }}
            """
        )


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("RapportEval")
    app.setOrganizationName("SeaTech")

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()