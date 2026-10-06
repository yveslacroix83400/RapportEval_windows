import json
from copy import deepcopy
from pathlib import Path
from uuid import uuid4

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)


APP_NAME = "RapportEval"

SETTINGS_DIRECTORY = (
    Path.home()
    / "AppData"
    / "Roaming"
    / APP_NAME
)

PROFILES_FILE = SETTINGS_DIRECTORY / "profiles.json"

DEFAULT_PROFILE_ID = (
    "5EA7EC00-0000-4000-8000-000000000001"
)


BUILT_IN_PROFILES = [
    {
        "id": DEFAULT_PROFILE_ID,
        "name": "Institutionnel prudent",
        "details": (
            "Synthèse institutionnelle concise, neutre et prudente, "
            "adaptée à une diffusion pédagogique."
        ),
        "tone": "Institutionnel et neutre",
        "audience": "Équipe pédagogique",
        "summary_length": "Moyenne",
        "maximum_themes": 5,
        "maximum_recommendations": 5,
        "instructions": (
            "Employer une formulation institutionnelle, neutre et concise. "
            "Distinguer les constats, les hypothèses et les recommandations. "
            "Ne jamais généraliser à la promotion lorsque le taux de réponse "
            "est faible. Croiser les verbatims avec les questions fermées et "
            "citer les effectifs pertinents."
        ),
        "is_built_in": True,
    },
    {
        "id": "5EA7EC00-0000-4000-8000-000000000002",
        "name": "Synthèse express",
        "details": (
            "Résumé court mettant en avant les principaux résultats, "
            "les points forts et les sujets à vérifier."
        ),
        "tone": "Direct et synthétique",
        "audience": "Responsable de formation",
        "summary_length": "Courte",
        "maximum_themes": 3,
        "maximum_recommendations": 3,
        "instructions": (
            "Produire une synthèse très courte. Conserver uniquement les "
            "résultats les plus significatifs et les recommandations soutenues "
            "par plusieurs éléments convergents. Signaler clairement les "
            "limites liées au nombre de répondants."
        ),
        "is_built_in": True,
    },
    {
        "id": "5EA7EC00-0000-4000-8000-000000000003",
        "name": "Retour pédagogique détaillé",
        "details": (
            "Analyse plus développée destinée à préparer un échange "
            "approfondi au sein de l’équipe pédagogique."
        ),
        "tone": "Pédagogique et analytique",
        "audience": "Enseignants et responsables pédagogiques",
        "summary_length": "Longue",
        "maximum_themes": 8,
        "maximum_recommendations": 8,
        "instructions": (
            "Développer les thèmes récurrents en distinguant les points forts, "
            "les difficultés, les demandes minoritaires et les contradictions. "
            "Relier chaque recommandation aux réponses fermées, aux effectifs "
            "et aux verbatims pertinents."
        ),
        "is_built_in": True,
    },
    {
        "id": "5EA7EC00-0000-4000-8000-000000000004",
        "name": "Orienté plan d’action",
        "details": (
            "Analyse centrée sur les actions possibles, leur priorité "
            "et les éléments probants qui les justifient."
        ),
        "tone": "Opérationnel et prudent",
        "audience": "Direction et responsables de programme",
        "summary_length": "Moyenne",
        "maximum_themes": 5,
        "maximum_recommendations": 8,
        "instructions": (
            "Formuler des actions précises, réalistes et proportionnées aux "
            "preuves. Classer en priorité faible toute proposition soutenue "
            "par moins de cinq répondants ou issue d’un taux de réponse "
            "inférieur à 30 %. Privilégier une vérification ou une "
            "expérimentation avant toute modification structurelle."
        ),
        "is_built_in": True,
    },
]


class ProfilesPage(QWidget):
    profile_selected = Signal(str)

    def __init__(self):
        super().__init__()

        self.custom_profiles = []
        self.current_profile_id = DEFAULT_PROFILE_ID
        self.loading_editor = False

        self.build_interface()
        self.load_custom_profiles()
        self.refresh_profile_list(
            profile_id=DEFAULT_PROFILE_ID
        )

    def build_interface(self):
        title = QLabel("Profils d’interprétation")
        title.setObjectName("pageTitle")

        description = QLabel(
            "Les profils fournis avec l’application sont protégés. "
            "Vous pouvez les dupliquer pour créer une version "
            "personnalisée, modifiable et supprimable."
        )
        description.setObjectName("pageDescription")
        description.setWordWrap(True)

        content_layout = QHBoxLayout()
        content_layout.setSpacing(20)

        content_layout.addWidget(
            self.build_profile_list_panel(),
            1,
        )

        content_layout.addWidget(
            self.build_editor_panel(),
            2,
        )

        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(40, 36, 40, 40)
        main_layout.setSpacing(18)

        main_layout.addWidget(title)
        main_layout.addWidget(description)
        main_layout.addLayout(content_layout)

        self.setLayout(main_layout)

    def build_profile_list_panel(self):
        group = QGroupBox("Profils disponibles")

        self.profile_list = QListWidget()
        self.profile_list.setMinimumWidth(280)
        self.profile_list.currentItemChanged.connect(
            self.on_profile_selection_changed
        )

        new_button = QPushButton("Nouveau profil")
        new_button.setObjectName("secondaryButton")
        new_button.clicked.connect(
            self.create_profile
        )

        duplicate_button = QPushButton("Dupliquer")
        duplicate_button.setObjectName("secondaryButton")
        duplicate_button.clicked.connect(
            self.duplicate_current_profile
        )

        buttons_layout = QHBoxLayout()
        buttons_layout.addWidget(new_button)
        buttons_layout.addWidget(duplicate_button)

        layout = QVBoxLayout()
        layout.addWidget(self.profile_list)
        layout.addLayout(buttons_layout)

        group.setLayout(layout)
        return group

    def build_editor_panel(self):
        group = QGroupBox("Configuration du profil")

        self.profile_status_label = QLabel()
        self.profile_status_label.setWordWrap(True)

        self.name_input = QLineEdit()

        self.details_input = QTextEdit()
        self.details_input.setMinimumHeight(75)

        self.tone_input = QComboBox()
        self.tone_input.setEditable(True)
        self.tone_input.addItems(
            [
                "Institutionnel et neutre",
                "Direct et synthétique",
                "Pédagogique et analytique",
                "Opérationnel et prudent",
                "Personnalisé",
            ]
        )

        self.audience_input = QLineEdit()

        self.summary_length_input = QComboBox()
        self.summary_length_input.addItems(
            [
                "Courte",
                "Moyenne",
                "Longue",
            ]
        )

        self.maximum_themes_input = QSpinBox()
        self.maximum_themes_input.setRange(1, 20)

        self.maximum_recommendations_input = QSpinBox()
        self.maximum_recommendations_input.setRange(
            0,
            20,
        )

        self.instructions_input = QTextEdit()
        self.instructions_input.setMinimumHeight(180)

        form = QFormLayout()
        form.setSpacing(12)
        form.addRow("Nom", self.name_input)
        form.addRow(
            "Description",
            self.details_input,
        )
        form.addRow(
            "Ton",
            self.tone_input,
        )
        form.addRow(
            "Public visé",
            self.audience_input,
        )
        form.addRow(
            "Longueur de la synthèse",
            self.summary_length_input,
        )
        form.addRow(
            "Nombre maximal de thèmes",
            self.maximum_themes_input,
        )
        form.addRow(
            "Nombre maximal de recommandations",
            self.maximum_recommendations_input,
        )
        form.addRow(
            "Consignes complémentaires",
            self.instructions_input,
        )

        self.save_button = QPushButton(
            "Enregistrer le profil"
        )
        self.save_button.setObjectName("primaryButton")
        self.save_button.clicked.connect(
            self.save_current_profile
        )

        self.use_button = QPushButton(
            "Utiliser ce profil"
        )
        self.use_button.setObjectName("secondaryButton")
        self.use_button.clicked.connect(
            self.use_current_profile
        )

        self.delete_button = QPushButton(
            "Supprimer"
        )
        self.delete_button.setObjectName(
            "destructiveButton"
        )
        self.delete_button.clicked.connect(
            self.delete_current_profile
        )

        actions = QHBoxLayout()
        actions.addWidget(self.save_button)
        actions.addWidget(self.use_button)
        actions.addWidget(self.delete_button)
        actions.addStretch()

        layout = QVBoxLayout()
        layout.setSpacing(12)
        layout.addWidget(self.profile_status_label)
        layout.addLayout(form)
        layout.addLayout(actions)

        group.setLayout(layout)
        return group

    def all_profiles(self):
        return (
            deepcopy(BUILT_IN_PROFILES)
            + deepcopy(self.custom_profiles)
        )

    def profile_by_id(self, profile_id):
        for profile in self.all_profiles():
            if profile["id"] == profile_id:
                return profile

        return deepcopy(BUILT_IN_PROFILES[0])

    def load_custom_profiles(self):
        SETTINGS_DIRECTORY.mkdir(
            parents=True,
            exist_ok=True,
        )

        if not PROFILES_FILE.exists():
            self.custom_profiles = []
            return

        try:
            decoded = json.loads(
                PROFILES_FILE.read_text(
                    encoding="utf-8"
                )
            )

            if not isinstance(decoded, list):
                self.custom_profiles = []
                return

            built_in_ids = {
                profile["id"]
                for profile in BUILT_IN_PROFILES
            }

            sanitized_profiles = []

            for profile in decoded:
                if not isinstance(profile, dict):
                    continue

                profile_id = profile.get("id")

                if not profile_id:
                    continue

                if profile_id in built_in_ids:
                    continue

                sanitized = self.normalize_profile(
                    profile
                )
                sanitized["is_built_in"] = False

                sanitized_profiles.append(
                    sanitized
                )

            self.custom_profiles = sanitized_profiles

        except (
            OSError,
            json.JSONDecodeError,
        ) as error:
            self.custom_profiles = []

            QMessageBox.warning(
                self,
                "Profils",
                "Impossible de charger les profils "
                f"personnalisés : {error}",
            )

    def save_custom_profiles(self):
        SETTINGS_DIRECTORY.mkdir(
            parents=True,
            exist_ok=True,
        )

        profiles_to_save = []

        for profile in self.custom_profiles:
            sanitized = self.normalize_profile(
                profile
            )
            sanitized["is_built_in"] = False
            profiles_to_save.append(sanitized)

        PROFILES_FILE.write_text(
            json.dumps(
                profiles_to_save,
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

    @staticmethod
    def normalize_profile(profile):
        return {
            "id": str(
                profile.get("id")
                or uuid4()
            ),
            "name": str(
                profile.get("name")
                or "Profil personnalisé"
            ),
            "details": str(
                profile.get("details")
                or ""
            ),
            "tone": str(
                profile.get("tone")
                or "Institutionnel et neutre"
            ),
            "audience": str(
                profile.get("audience")
                or "Équipe pédagogique"
            ),
            "summary_length": str(
                profile.get("summary_length")
                or "Moyenne"
            ),
            "maximum_themes": int(
                profile.get("maximum_themes")
                or 5
            ),
            "maximum_recommendations": int(
                profile.get(
                    "maximum_recommendations"
                )
                or 5
            ),
            "instructions": str(
                profile.get("instructions")
                or ""
            ),
            "is_built_in": bool(
                profile.get("is_built_in", False)
            ),
        }

    def refresh_profile_list(
        self,
        profile_id=None,
    ):
        target_id = (
            profile_id
            or self.current_profile_id
            or DEFAULT_PROFILE_ID
        )

        self.profile_list.blockSignals(True)
        self.profile_list.clear()

        target_item = None

        for profile in self.all_profiles():
            item = QListWidgetItem()

            if profile["is_built_in"]:
                item.setText(
                    f"🔒 {profile['name']}"
                )
            else:
                item.setText(
                    f"✎ {profile['name']}"
                )

            item.setData(
                Qt.ItemDataRole.UserRole,
                profile["id"],
            )

            self.profile_list.addItem(item)

            if profile["id"] == target_id:
                target_item = item

        self.profile_list.blockSignals(False)

        if target_item is None:
            target_item = self.profile_list.item(0)

        self.profile_list.setCurrentItem(
            target_item
        )

        if target_item is not None:
            self.load_profile_into_editor(
                target_item.data(
                    Qt.ItemDataRole.UserRole
                )
            )

    def on_profile_selection_changed(
        self,
        current_item,
        previous_item,
    ):
        del previous_item

        if current_item is None:
            return

        profile_id = current_item.data(
            Qt.ItemDataRole.UserRole
        )

        self.load_profile_into_editor(
            profile_id
        )

    def load_profile_into_editor(
        self,
        profile_id,
    ):
        profile = self.profile_by_id(
            profile_id
        )

        self.current_profile_id = profile["id"]
        self.loading_editor = True

        self.name_input.setText(
            profile["name"]
        )
        self.details_input.setPlainText(
            profile["details"]
        )
        self.tone_input.setCurrentText(
            profile["tone"]
        )
        self.audience_input.setText(
            profile["audience"]
        )
        self.summary_length_input.setCurrentText(
            profile["summary_length"]
        )
        self.maximum_themes_input.setValue(
            profile["maximum_themes"]
        )
        self.maximum_recommendations_input.setValue(
            profile[
                "maximum_recommendations"
            ]
        )
        self.instructions_input.setPlainText(
            profile["instructions"]
        )

        built_in = profile["is_built_in"]
        self.set_editor_read_only(
            built_in
        )

        if built_in:
            self.profile_status_label.setText(
                "🔒 Profil fourni avec l’application. "
                "Le profil est en lecture seule et ne "
                "peut pas être supprimé. Utilisez "
                "« Dupliquer » pour créer une version "
                "personnalisée."
            )
        else:
            self.profile_status_label.setText(
                "✎ Profil personnalisé. Le profil peut "
                "être modifié ou supprimé."
            )

        self.loading_editor = False

    def set_editor_read_only(
        self,
        read_only,
    ):
        self.name_input.setReadOnly(
            read_only
        )
        self.details_input.setReadOnly(
            read_only
        )
        self.tone_input.setEnabled(
            not read_only
        )
        self.audience_input.setReadOnly(
            read_only
        )
        self.summary_length_input.setEnabled(
            not read_only
        )
        self.maximum_themes_input.setEnabled(
            not read_only
        )
        self.maximum_recommendations_input.setEnabled(
            not read_only
        )
        self.instructions_input.setReadOnly(
            read_only
        )

        self.save_button.setEnabled(
            not read_only
        )
        self.delete_button.setEnabled(
            not read_only
        )

    def editor_profile_data(self):
        return {
            "id": self.current_profile_id,
            "name": (
                self.name_input.text().strip()
                or "Profil personnalisé"
            ),
            "details": (
                self.details_input
                .toPlainText()
                .strip()
            ),
            "tone": (
                self.tone_input
                .currentText()
                .strip()
            ),
            "audience": (
                self.audience_input
                .text()
                .strip()
            ),
            "summary_length": (
                self.summary_length_input
                .currentText()
            ),
            "maximum_themes": (
                self.maximum_themes_input.value()
            ),
            "maximum_recommendations": (
                self.maximum_recommendations_input
                .value()
            ),
            "instructions": (
                self.instructions_input
                .toPlainText()
                .strip()
            ),
            "is_built_in": False,
        }

    def create_profile(self):
        new_profile = {
            "id": str(uuid4()),
            "name": "Mon profil",
            "details": (
                "Profil d’interprétation personnalisé."
            ),
            "tone": "Institutionnel et neutre",
            "audience": "Équipe pédagogique",
           "summary_length": "Moyenne",
            "maximum_themes": 5,
            "maximum_recommendations": 5,
            "instructions": "",
            "is_built_in": False,
        }

        self.custom_profiles.append(
            new_profile
        )
        self.save_custom_profiles()
        self.refresh_profile_list(
            new_profile["id"]
        )

    def duplicate_current_profile(self):
        source = self.profile_by_id(
            self.current_profile_id
        )

        duplicate = deepcopy(source)
        duplicate["id"] = str(uuid4())
        duplicate["name"] = (
            f"{source['name']} - Copie"
        )
        duplicate["is_built_in"] = False

        self.custom_profiles.append(
            duplicate
        )
        self.save_custom_profiles()
        self.refresh_profile_list(
            duplicate["id"]
        )

    def save_current_profile(self):
        selected = self.profile_by_id(
            self.current_profile_id
        )

        if selected["is_built_in"]:
            QMessageBox.information(
                self,
                "Profil protégé",
                "Les profils fournis avec "
                "l’application ne peuvent pas être "
                "modifiés. Dupliquez le profil pour "
                "créer une version personnalisée.",
            )
            return

        updated_profile = (
            self.editor_profile_data()
        )

        for index, profile in enumerate(
            self.custom_profiles
        ):
            if (
                profile["id"]
                == self.current_profile_id
            ):
                self.custom_profiles[index] = (
                    updated_profile
                )
                break

        self.save_custom_profiles()
        self.refresh_profile_list(
            updated_profile["id"]
        )

        QMessageBox.information(
            self,
            "Profil enregistré",
            "Le profil personnalisé a été "
            "enregistré.",
        )

    def delete_current_profile(self):
        profile = self.profile_by_id(
            self.current_profile_id
        )

        if profile["is_built_in"]:
            QMessageBox.warning(
                self,
                "Profil protégé",
                "Les profils fournis avec "
                "l’application ne peuvent pas être "
                "supprimés.",
            )
            return

        profile_name = (
            profile["name"]
            or "Sans nom"
        )

        answer = QMessageBox.question(
            self,
            "Supprimer le profil",
            (
                f"Supprimer définitivement le profil "
                f"« {profile_name} » ?\n\n"
                "Les rapports déjà générés ne seront "
                "pas modifiés."
            ),
            (
                QMessageBox.StandardButton.Yes
                | QMessageBox.StandardButton.No
            ),
            QMessageBox.StandardButton.No,
        )

        if answer != QMessageBox.StandardButton.Yes:
            return

        self.custom_profiles = [
            item
            for item in self.custom_profiles
            if item["id"] != profile["id"]
        ]

        self.save_custom_profiles()

        if (
            self.current_profile_id
            == profile["id"]
        ):
            self.current_profile_id = (
                DEFAULT_PROFILE_ID
            )

        self.refresh_profile_list(
            DEFAULT_PROFILE_ID
        )

    def use_current_profile(self):
        self.profile_selected.emit(
            self.current_profile_id
        )

        profile = self.profile_by_id(
            self.current_profile_id
        )

        QMessageBox.information(
            self,
            "Profil sélectionné",
            (
                f"Le profil « {profile['name']} » "
                "sera utilisé lors de la prochaine "
                "analyse."
            ),
        )

    def selected_profile_id(self):
        return self.current_profile_id

    def selected_profile(self):
        return self.profile_by_id(
            self.current_profile_id
        )

    def compiled_instructions(
        self,
        profile_id=None,
    ):
        profile = self.profile_by_id(
            profile_id
            or self.current_profile_id
        )

        return (
            f"Ton : {profile['tone']}\n"
            f"Public visé : {profile['audience']}\n"
            f"Longueur de la synthèse : "
            f"{profile['summary_length']}\n"
            f"Nombre maximal de thèmes : "
            f"{profile['maximum_themes']}\n"
            f"Nombre maximal de recommandations : "
            f"{profile['maximum_recommendations']}\n\n"
            f"Consignes complémentaires :\n"
            f"{profile['instructions']}"
        )