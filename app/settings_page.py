import json
import shutil
import subprocess
import sys
from pathlib import Path

import keyring
from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)


APP_NAME = "RapportEval"
KEYRING_SERVICE = "RapportEval"
KEYRING_ACCOUNT = "AlbertAPI"

if getattr(sys, "frozen", False):
    PROJECT_ROOT = Path(sys.executable).resolve().parent
else:
    PROJECT_ROOT = Path(__file__).resolve().parent.parent

DEFAULT_ENGINE_PATH = PROJECT_ROOT / "Engine"

SETTINGS_DIRECTORY = Path.home() / "AppData" / "Roaming" / APP_NAME
SETTINGS_FILE = SETTINGS_DIRECTORY / "settings.json"


class SettingsPage(QWidget):
    settings_changed = Signal()

    def __init__(self):
        super().__init__()

        self.setObjectName("settingsPage")
        self.build_interface()
        self.load_settings()

    def build_interface(self):
        title = QLabel("Albert et moteur")
        title.setObjectName("pageTitle")

        description = QLabel(
            "Configurez la connexion à Albert et vérifiez les composants "
            "nécessaires à la génération des rapports."
        )
        description.setObjectName("pageDescription")
        description.setWordWrap(True)

        connection_group = self.build_connection_group()
        engine_group = self.build_engine_group()

        self.diagnostic_output = QTextEdit()
        self.diagnostic_output.setReadOnly(True)
        self.diagnostic_output.setMinimumHeight(150)
        self.diagnostic_output.setPlaceholderText(
            "Les résultats des tests apparaîtront ici."
        )

        save_button = QPushButton("Enregistrer les paramètres")
        save_button.setObjectName("primaryButton")
        save_button.setMinimumHeight(40)
        save_button.clicked.connect(self.save_settings)

        test_button = QPushButton("Vérifier le moteur")
        test_button.setObjectName("secondaryButton")
        test_button.setMinimumHeight(40)
        test_button.clicked.connect(self.run_diagnostics)

        actions = QHBoxLayout()
        actions.addWidget(save_button)
        actions.addWidget(test_button)
        actions.addStretch()

        layout = QVBoxLayout()
        layout.setContentsMargins(40, 36, 40, 40)
        layout.setSpacing(18)

        layout.addWidget(title)
        layout.addWidget(description)
        layout.addWidget(connection_group)
        layout.addWidget(engine_group)
        layout.addWidget(QLabel("Diagnostic"))
        layout.addWidget(self.diagnostic_output)
        layout.addLayout(actions)
        layout.addStretch()

        self.setLayout(layout)

    def build_connection_group(self):
        group = QGroupBox("Connexion à Albert")

        self.base_url_input = QLineEdit()
        self.base_url_input.setPlaceholderText(
            "https://albert.api.etalab.gouv.fr/v1"
        )

        self.api_key_input = QLineEdit()
        self.api_key_input.setEchoMode(
            QLineEdit.EchoMode.Password
        )
        self.api_key_input.setPlaceholderText(
            "Laisser vide pour conserver la clé enregistrée"
        )

        self.model_input = QLineEdit()
        self.model_input.setPlaceholderText(
            "Nom du modèle Albert"
        )

        show_key_button = QPushButton("Afficher")
        show_key_button.setCheckable(True)
        show_key_button.toggled.connect(
            self.toggle_api_key_visibility
        )

        clear_key_button = QPushButton("Effacer la clé")
        clear_key_button.clicked.connect(
            self.delete_api_key
        )

        key_layout = QHBoxLayout()
        key_layout.addWidget(self.api_key_input)
        key_layout.addWidget(show_key_button)
        key_layout.addWidget(clear_key_button)

        form = QFormLayout()
        form.setSpacing(12)
        form.addRow("URL de l’API", self.base_url_input)
        form.addRow("Clé API", key_layout)
        form.addRow("Modèle", self.model_input)

        group.setLayout(form)
        return group

    def build_engine_group(self):
        group = QGroupBox("Moteur local")

        self.python_path_input = QLineEdit()
        self.node_path_input = QLineEdit()
        self.engine_path_input = QLineEdit()

        detect_button = QPushButton(
            "Détecter automatiquement"
        )
        detect_button.clicked.connect(
            self.detect_paths
        )

        choose_engine_button = QPushButton(
            "Choisir le dossier Engine…"
        )
        choose_engine_button.clicked.connect(
            self.choose_engine_directory
        )

        engine_path_layout = QHBoxLayout()
        engine_path_layout.addWidget(
            self.engine_path_input
        )
        engine_path_layout.addWidget(
            choose_engine_button
        )

        form = QFormLayout()
        form.setSpacing(12)
        form.addRow(
            "Python",
            self.python_path_input,
        )
        form.addRow(
            "Node.js",
            self.node_path_input,
        )
        form.addRow(
            "Dossier Engine",
            engine_path_layout,
        )
        form.addRow("", detect_button)

        group.setLayout(form)
        return group

    def toggle_api_key_visibility(self, checked):
        if checked:
            self.api_key_input.setEchoMode(
                QLineEdit.EchoMode.Normal
            )
        else:
            self.api_key_input.setEchoMode(
                QLineEdit.EchoMode.Password
            )

    def detect_paths(self):
        python_path = self.find_python()
        node_path = self.find_node()

        self.python_path_input.setText(
            python_path or ""
        )
        self.node_path_input.setText(
            node_path or ""
        )

        if DEFAULT_ENGINE_PATH.exists():
            self.engine_path_input.setText(
                str(DEFAULT_ENGINE_PATH)
            )

        self.diagnostic_output.setPlainText(
            "Détection automatique terminée."
        )

    @staticmethod
    def find_python():
        candidates = [
            PROJECT_ROOT / "Runtime" / "python" / "python.exe",
            PROJECT_ROOT / ".venv" / "Scripts" / "python.exe",
        ]

        if not getattr(sys, "frozen", False):
            candidates.insert(0, Path(sys.executable))

        for candidate in candidates:
            if candidate.is_file():
                return str(candidate)

        return (
            shutil.which("python.exe")
            or shutil.which("python")
            or shutil.which("py")
            or ""
        )

    @staticmethod
    def find_node():
        embedded_node = (
            PROJECT_ROOT
            / "Runtime"
            / "node"
            / "node.exe"
        )

        if embedded_node.is_file():
            return str(embedded_node)

        return (
            shutil.which("node.exe")
            or shutil.which("node")
            or ""
        )

    def choose_engine_directory(self):
        selected = QFileDialog.getExistingDirectory(
            self,
            "Choisissez le dossier Engine",
            self.engine_path_input.text()
            or str(PROJECT_ROOT),
        )

        if selected:
            self.engine_path_input.setText(selected)

    def load_settings(self):
        self.base_url_input.setText(
            "https://albert.api.etalab.gouv.fr/v1"
        )
        self.engine_path_input.setText(
            str(DEFAULT_ENGINE_PATH)
        )

        if SETTINGS_FILE.exists():
            try:
                data = json.loads(
                    SETTINGS_FILE.read_text(
                        encoding="utf-8"
                    )
                )

                self.base_url_input.setText(
                    data.get(
                        "base_url",
                        self.base_url_input.text(),
                    )
                )
                self.model_input.setText(
                    data.get("model", "")
                )
                self.python_path_input.setText(
                    data.get("python_path", "")
                )
                self.node_path_input.setText(
                    data.get("node_path", "")
                )
                self.engine_path_input.setText(
                    data.get(
                        "engine_path",
                        str(DEFAULT_ENGINE_PATH),
                    )
                )
            except (
                OSError,
                json.JSONDecodeError,
            ) as error:
                self.diagnostic_output.setPlainText(
                    f"Impossible de charger les paramètres : "
                    f"{error}"
                )

        if not self.python_path_input.text():
            self.python_path_input.setText(
                self.find_python() or ""
            )

        if not self.node_path_input.text():
            self.node_path_input.setText(
                self.find_node() or ""
            )

        try:
            saved_key = keyring.get_password(
                KEYRING_SERVICE,
                KEYRING_ACCOUNT,
            )

            if saved_key:
                self.api_key_input.setPlaceholderText(
                    "Clé enregistrée dans le gestionnaire "
                    "d’identifiants Windows"
                )
        except Exception as error:
            self.diagnostic_output.setPlainText(
                "Le gestionnaire d’identifiants Windows "
                f"n’est pas accessible : {error}"
            )

    def save_settings(self):
        SETTINGS_DIRECTORY.mkdir(
            parents=True,
            exist_ok=True,
        )

        settings = {
            "base_url": self.base_url_input.text().strip(),
            "model": self.model_input.text().strip(),
            "python_path": (
                self.python_path_input.text().strip()
            ),
            "node_path": (
                self.node_path_input.text().strip()
            ),
            "engine_path": (
                self.engine_path_input.text().strip()
            ),
        }

        try:
            SETTINGS_FILE.write_text(
                json.dumps(
                    settings,
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )

            new_key = self.api_key_input.text().strip()

            if new_key:
                keyring.set_password(
                    KEYRING_SERVICE,
                    KEYRING_ACCOUNT,
                    new_key,
                )
                self.api_key_input.clear()
                self.api_key_input.setPlaceholderText(
                    "Clé enregistrée dans le gestionnaire "
                    "d’identifiants Windows"
                )

            self.diagnostic_output.setPlainText(
                "Paramètres enregistrés avec succès."
            )
            self.settings_changed.emit()

        except Exception as error:
            self.diagnostic_output.setPlainText(
                f"Erreur pendant l’enregistrement : {error}"
            )

    def delete_api_key(self):
        try:
            existing_key = keyring.get_password(
                KEYRING_SERVICE,
                KEYRING_ACCOUNT,
            )

            if existing_key:
                keyring.delete_password(
                    KEYRING_SERVICE,
                    KEYRING_ACCOUNT,
                )

            self.api_key_input.clear()
            self.api_key_input.setPlaceholderText(
                "Aucune clé enregistrée"
            )

            self.diagnostic_output.setPlainText(
                "La clé Albert a été supprimée."
            )

        except Exception as error:
            self.diagnostic_output.setPlainText(
                f"Impossible de supprimer la clé : {error}"
            )

    def run_diagnostics(self):
        lines = []

        python_path = Path(
            self.python_path_input.text().strip()
        )
        node_path_text = (
            self.node_path_input.text().strip()
        )
        engine_path = Path(
            self.engine_path_input.text().strip()
        )

        if python_path.is_file():
            result = self.run_version_command(
                [str(python_path), "--version"]
            )
            lines.append(
                f"✓ Python : {result}"
            )
        else:
            lines.append(
                "✗ Python introuvable."
            )

        if node_path_text:
            result = self.run_version_command(
                [node_path_text, "--version"]
            )

            if result.startswith("Erreur"):
                lines.append(
                    f"✗ Node.js : {result}"
                )
            else:
                lines.append(
                    f"✓ Node.js : {result}"
                )
        else:
            lines.append(
                "✗ Node.js introuvable."
            )

        required_engine_files = [
            "cli_generate.py",
            "generate.js",
            "logo_seatech.png",
            "package.json",
        ]

        if engine_path.is_dir():
            lines.append(
                f"✓ Dossier Engine : {engine_path}"
            )

            for filename in required_engine_files:
                file_path = engine_path / filename

                if file_path.is_file():
                    lines.append(
                        f"  ✓ {filename}"
                    )
                else:
                    lines.append(
                        f"  ✗ {filename} manquant"
                    )

            pptxgen_path = (
                engine_path
                / "node_modules"
                / "pptxgenjs"
            )

            if pptxgen_path.exists():
                lines.append(
                    "  ✓ module pptxgenjs"
                )
            else:
                lines.append(
                    "  ✗ module pptxgenjs manquant"
                )
        else:
            lines.append(
                "✗ Dossier Engine introuvable."
            )

        try:
            saved_key = keyring.get_password(
                KEYRING_SERVICE,
                KEYRING_ACCOUNT,
            )

            if saved_key:
                lines.append(
                    "✓ Clé Albert enregistrée."
                )
            else:
                lines.append(
                    "⚠ Aucune clé Albert enregistrée."
                )
        except Exception as error:
            lines.append(
                "✗ Gestionnaire d’identifiants : "
                f"{error}"
            )

        self.diagnostic_output.setPlainText(
            "\n".join(lines)
        )

    @staticmethod
    def run_version_command(command):
        try:
            completed = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=15,
                check=False,
            )

            output = (
                completed.stdout.strip()
                or completed.stderr.strip()
            )

            if completed.returncode == 0:
                return output or "version détectée"

            return (
                f"Erreur {completed.returncode} : "
                f"{output}"
            )

        except Exception as error:
            return f"Erreur : {error}"

    def get_api_key(self):
        return keyring.get_password(
            KEYRING_SERVICE,
            KEYRING_ACCOUNT,
        ) or ""

    def get_settings(self):
        return {
            "base_url": self.base_url_input.text().strip(),
            "model": self.model_input.text().strip(),
            "python_path": (
                self.python_path_input.text().strip()
            ),
            "node_path": (
                self.node_path_input.text().strip()
            ),
            "engine_path": (
                self.engine_path_input.text().strip()
            ),
        }