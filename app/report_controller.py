import json
import os
import tempfile
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import (
    QObject,
    QProcess,
    QProcessEnvironment,
    Signal,
)


class ReportController(QObject):
    """
    Lance le moteur Python dans un processus séparé.

    Le processus prépare le JSON contenant :
    - les statistiques ;
    - les questions fermées ;
    - les commentaires anonymisés ;
    - les synthèses Albert ;
    - les recommandations Albert.

    Le PowerPoint n'est pas encore généré à cette étape.
    Le JSON sera d'abord transmis à l'écran de contrôle.
    """

    log_received = Signal(str)
    preparation_started = Signal()
    preparation_finished = Signal(str)
    preparation_failed = Signal(str)

    generation_started = Signal()
    generation_finished = Signal(str)
    generation_failed = Signal(str)
    
    running_changed = Signal(bool)
    

    def __init__(
        self,
        settings_page,
        parent=None,
    ):
        super().__init__(parent)

        self.settings_page = settings_page
        self.process = None
        self.process_mode = None

        self.current_json_path = ""
        self.current_pptx_path = ""
        self.current_payload = None

    def prepare_report(
        self,
        payload: dict,
    ):
        """
        Prépare le rapport avec cli_generate.py.

        Le paramètre payload provient de GeneratorPage.collect_values().
        """

        if self.is_running():
            self.preparation_failed.emit(
                "Une analyse est déjà en cours."
            )
            return

        try:
            command = self.build_prepare_command(payload)
        except Exception as error:
            self.preparation_failed.emit(str(error))
            return

        self.current_payload = payload

        self.process_mode = "preparation"

        python_path = command["python_path"]
        arguments = command["arguments"]
        engine_path = command["engine_path"]
        api_key = command["api_key"]

        self.process = QProcess(self)
        self.process.setProgram(python_path)
        self.process.setArguments(arguments)
        self.process.setWorkingDirectory(engine_path)

        environment = QProcessEnvironment.systemEnvironment()

        if api_key:
            environment.insert(
                "ALBERT_API_KEY",
                api_key,
            )

        self.process.setProcessEnvironment(environment)

        self.process.setProcessChannelMode(
            QProcess.ProcessChannelMode.SeparateChannels
        )

        self.process.readyReadStandardOutput.connect(
            self.read_standard_output
        )
        self.process.readyReadStandardError.connect(
            self.read_standard_error
        )
        self.process.errorOccurred.connect(
            self.on_process_error
        )
        self.process.finished.connect(
            self.on_process_finished
        )

        self.preparation_started.emit()
        self.running_changed.emit(True)

        self.log_received.emit(
            "Démarrage de l’analyse statistique..."
        )

        if payload.get("use_ai"):
            self.log_received.emit(
                "L’interprétation Albert est activée."
            )
        else:
            self.log_received.emit(
                "L’interprétation Albert est désactivée."
            )

        self.log_received.emit(
            f"Fichier Excel : {payload['excel_path']}"
        )
        self.log_received.emit(
            f"JSON intermédiaire : {self.current_json_path}"
        )

        self.process.start()

    def build_prepare_command(
        self,
        payload: dict,
    ) -> dict:
        settings = self.settings_page.get_settings()

        python_path = Path(
            settings.get("python_path", "")
        )
        engine_path = Path(
            settings.get("engine_path", "")
        )
        cli_path = engine_path / "cli_generate.py"

        self.validate_payload(payload)

        if not python_path.is_file():
            raise RuntimeError(
                "L’exécutable Python est introuvable :\n"
                f"{python_path}"
            )

        if not engine_path.is_dir():
            raise RuntimeError(
                "Le dossier Engine est introuvable :\n"
                f"{engine_path}"
            )

        if not cli_path.is_file():
            raise RuntimeError(
                "Le fichier cli_generate.py est introuvable :\n"
                f"{cli_path}"
            )

        output_directory = (
            Path(tempfile.gettempdir())
            / "RapportEval"
        )
        output_directory.mkdir(
            parents=True,
            exist_ok=True,
        )

        timestamp = datetime.now().strftime(
            "%Y%m%d-%H%M%S"
        )

        json_path = (
            output_directory
            / f"rapport_prepare_{timestamp}.json"
        )

        self.current_json_path = str(json_path)

        profile = payload.get("profile") or {}

        profile_settings = {
            "tone": profile.get(
                "tone",
                "Institutionnel et neutre",
            ),
            "audience": profile.get(
                "audience",
                "Équipe pédagogique",
            ),
            "summary_length": profile.get(
                "summary_length",
                "Moyenne",
            ),
            "maximum_themes": profile.get(
                "maximum_themes",
                5,
            ),
            "maximum_recommendations": profile.get(
                "maximum_recommendations",
                5,
            ),
        }

        brand_json = json.dumps(
            payload.get("brand") or {},
            ensure_ascii=False,
            separators=(",", ":"),
        )

        charts_json = json.dumps(
            payload.get("charts") or {},
            ensure_ascii=False,
            separators=(",", ":"),
        )

        profile_settings_json = json.dumps(
            profile_settings,
            ensure_ascii=False,
            separators=(",", ":"),
        )

        arguments = [
            str(cli_path),
            "--excel",
            str(payload["excel_path"]),
            "--out-json",
            str(json_path),
            "--course",
            str(payload["course"]),
            "--invited",
            str(payload["invited"]),
            "--cohort",
            str(payload.get("cohort", "")),
            "--academic-year",
            str(payload.get("academic_year", "")),
            "--confidence",
            str(payload["confidence"]),
            "--profile-name",
            str(
                profile.get(
                    "name",
                    "Institutionnel prudent",
                )
            ),
            "--profile-settings-json",
            profile_settings_json,
            "--profile-instructions",
            str(
                payload.get(
                    "profile_instructions",
                    "",
                )
            ),
            "--brand-json",
            brand_json,
            "--charts-json",
            charts_json,
        ]

        api_key = ""

        if payload.get("use_ai"):
            api_key = self.settings_page.get_api_key()

            base_url = settings.get(
                "base_url",
                "",
            ).strip()

            model = settings.get(
                "model",
                "",
            ).strip()

            if not api_key:
                raise RuntimeError(
                    "Albert est activé, mais aucune clé API "
                    "n’est enregistrée.\n\n"
                    "Ouvrez l’onglet « Albert et moteur », "
                    "saisissez la clé, puis enregistrez les "
                    "paramètres."
                )

            if not base_url:
                raise RuntimeError(
                    "Albert est activé, mais l’URL de l’API "
                    "est vide."
                )

            if not model:
                raise RuntimeError(
                    "Albert est activé, mais aucun modèle "
                    "n’est renseigné."
                )

            arguments.extend(
                [
                    "--use-ai",
                    "--base-url",
                    base_url,
                    "--model",
                    model,
                ]
            )

        return {
            "python_path": str(python_path),
            "engine_path": str(engine_path),
            "arguments": arguments,
            "api_key": api_key,
        }

    @staticmethod
    def validate_payload(
        payload: dict,
    ):
        excel_path = Path(
            payload.get("excel_path", "")
        )

        if not excel_path.is_file():
            raise RuntimeError(
                "Le fichier Excel sélectionné est introuvable."
            )

        if excel_path.suffix.lower() != ".xlsx":
            raise RuntimeError(
                "Le fichier sélectionné doit être au format .xlsx."
            )

        course = str(
            payload.get("course", "")
        ).strip()

        if not course:
            raise RuntimeError(
                "L’intitulé du cours est obligatoire."
            )

        invited = int(
            payload.get("invited", 0)
        )

        if invited < 1:
            raise RuntimeError(
                "Le nombre d’individus sollicités doit "
                "être supérieur à zéro."
            )

        confidence = float(
            payload.get("confidence", 0)
        )

        if confidence not in {
            0.90,
            0.95,
            0.99,
        }:
            raise RuntimeError(
                "Le niveau de confiance doit être "
                "90 %, 95 % ou 99 %."
            )

    def generate_powerpoint(
        self,
        json_path: str,
    ):
        """
        Génère le PowerPoint à partir du JSON
        relu et corrigé dans l’écran de contrôle.
        """

        if self.is_running():
            self.generation_failed.emit(
                "Un traitement est déjà en cours."
            )
            return

        settings = self.settings_page.get_settings()

        node_path = Path(
            settings.get("node_path", "")
        )

        engine_path = Path(
            settings.get("engine_path", "")
        )

        generate_path = (
            engine_path
            / "generate.js"
        )

        logo_path = (
            engine_path
            / "logo_seatech.png"
        )

        reviewed_json_path = Path(json_path)

        if not node_path.is_file():
            self.generation_failed.emit(
                "L’exécutable Node.js est introuvable :\n"
                f"{node_path}"
            )
            return

        if not reviewed_json_path.is_file():
            self.generation_failed.emit(
                "Le JSON contrôlé est introuvable :\n"
                f"{reviewed_json_path}"
            )
            return

        if not generate_path.is_file():
            self.generation_failed.emit(
                "Le fichier generate.js est introuvable :\n"
                f"{generate_path}"
            )
            return

        if not logo_path.is_file():
            self.generation_failed.emit(
                "Le logo SeaTech est introuvable :\n"
                f"{logo_path}"
            )
            return

        output_directory = (
            Path.home()
            / "Documents"
            / "RapportEval"
        )

        output_directory.mkdir(
            parents=True,
            exist_ok=True,
        )

        course_name = self.report_course_name(
            reviewed_json_path
        )

        safe_course_name = self.safe_filename(
            course_name
        )

        timestamp = datetime.now().strftime(
            "%Y%m%d-%H%M%S"
        )

        output_path = (
            output_directory
            / (
                f"rapport_"
                f"{safe_course_name}_"
                f"{timestamp}.pptx"
            )
        )

        self.current_json_path = str(
            reviewed_json_path
        )

        self.current_pptx_path = str(
            output_path
        )

        self.process_mode = "generation"

        self.process = QProcess(self)
        self.process.setProgram(
            str(node_path)
        )

        self.process.setArguments(
            [
                str(generate_path),
                str(reviewed_json_path),
                str(logo_path),
                str(output_path),
            ]
        )

        self.process.setWorkingDirectory(
            str(engine_path)
        )

        environment = (
            QProcessEnvironment.systemEnvironment()
        )

        self.process.setProcessEnvironment(
            environment
        )

        self.process.setProcessChannelMode(
            QProcess.ProcessChannelMode.SeparateChannels
        )

        self.process.readyReadStandardOutput.connect(
            self.read_standard_output
        )

        self.process.readyReadStandardError.connect(
            self.read_standard_error
        )

        self.process.errorOccurred.connect(
            self.on_process_error
        )

        self.process.finished.connect(
            self.on_process_finished
        )

        self.generation_started.emit()
        self.running_changed.emit(True)

        self.log_received.emit(
            "Génération du PowerPoint contrôlé..."
        )

        self.log_received.emit(
            f"JSON contrôlé : {reviewed_json_path}"
        )

        self.log_received.emit(
            f"PowerPoint de sortie : {output_path}"
        )

        self.process.start()

    @staticmethod
    def safe_filename(
        value: str,
        ) -> str:
        """
        Produit un nom de fichier compatible Windows.
        """

        allowed_characters = []

        for character in value.strip():
            if character.isalnum():
                allowed_characters.append(character)
            elif character in {
                " ",
                "-",
                "_",
            }:
                allowed_characters.append("_")

        safe_value = "".join(
            allowed_characters
        )

        while "__" in safe_value:
            safe_value = safe_value.replace(
                "__",
                "_",
            )

        safe_value = safe_value.strip("_")

        return safe_value or "cours"


    @staticmethod
    def report_course_name(
        json_path: Path,
    ) -> str:
            """
            Retrouve l’intitulé du cours dans le JSON.
            """

            try:
                data = json.loads(
                    json_path.read_text(
                        encoding="utf-8"
                    )
                )

                context = data.get(
                    "context",
                    {},
                )

                course_name = str(
                    context.get(
                        "course",
                        "",
                    )
                ).strip()

                return course_name or "cours"

            except (
                OSError,
                json.JSONDecodeError,
                AttributeError,
            ):
                return "cours"

    def read_standard_output(self):
        if self.process is None:
            return

        raw_data = (
            self.process
            .readAllStandardOutput()
            .data()
        )

        text = raw_data.decode(
            "utf-8",
            errors="replace",
        )

        self.emit_log_lines(text)

    def read_standard_error(self):
        if self.process is None:
            return

        raw_data = (
            self.process
            .readAllStandardError()
            .data()
        )

        text = raw_data.decode(
            "utf-8",
            errors="replace",
        )

        self.emit_log_lines(
            text,
            prefix="Moteur : ",
        )

    def emit_log_lines(
        self,
        text: str,
        prefix: str = "",
    ):
        for line in text.splitlines():
            cleaned = line.strip()

            if cleaned:
                self.log_received.emit(
                    f"{prefix}{cleaned}"
                )

    def on_process_error(
        self,
        process_error,
    ):
        del process_error

        if self.process is None:
            return

        message = self.process.errorString()

        self.log_received.emit(
            f"Erreur de processus : {message}"
        )

    def on_process_finished(
        self,
        exit_code: int,
        exit_status,
        ):
        del exit_status

        self.read_standard_output()
        self.read_standard_error()

        self.running_changed.emit(False)

        process_mode = self.process_mode
        self.process = None
        self.process_mode = None

        if process_mode == "generation":
            self.finish_powerpoint_generation(
                exit_code
            )
            return

        self.finish_report_preparation(
            exit_code
        )

    def finish_report_preparation(
        self,
        exit_code: int,
    ):
        json_path = Path(
            self.current_json_path
        )

        if exit_code != 0:
            self.preparation_failed.emit(
                "Le moteur Python s’est arrêté avec "
                f"le code {exit_code}."
            )
            return

        if not json_path.is_file():
            self.preparation_failed.emit(
                "Le moteur s’est terminé sans créer "
                "le fichier JSON intermédiaire attendu."
            )
            return

        try:
            json.loads(
                json_path.read_text(
                    encoding="utf-8"
                )
            )
        except (
            OSError,
            json.JSONDecodeError,
        ) as error:
            self.preparation_failed.emit(
                "Le JSON produit par le moteur est "
                f"invalide : {error}"
            )
            return

        self.log_received.emit(
            "Analyse terminée. Le rapport est prêt "
            "pour l’écran de contrôle."
        )

        self.preparation_finished.emit(
            str(json_path)
        )

    def finish_powerpoint_generation(
        self,
        exit_code: int,
    ):
        output_path = Path(
            self.current_pptx_path
        )

        if exit_code != 0:
            self.generation_failed.emit(
                "Le moteur PowerPoint s’est arrêté "
                f"avec le code {exit_code}."
            )
            return

        if not output_path.is_file():
            self.generation_failed.emit(
                "Le moteur s’est terminé sans créer "
                "le fichier PowerPoint attendu."
            )
            return

        if output_path.stat().st_size == 0:
            self.generation_failed.emit(
                "Le fichier PowerPoint produit est vide."
            )
            return

        self.log_received.emit(
            "PowerPoint généré avec succès."
        )

        self.generation_finished.emit(
            str(output_path)
        )

    def is_running(self) -> bool:
        if self.process is None:
            return False

        return (
            self.process.state()
            != QProcess.ProcessState.NotRunning
        )

    def cancel(self):
        if not self.is_running():
            return

        self.log_received.emit(
            "Annulation demandée..."
        )

        self.process.terminate()

        if not self.process.waitForFinished(3000):
            self.process.kill()

    def remove_temporary_json(self):
        if not self.current_json_path:
            return

        path = Path(self.current_json_path)

        try:
            if path.exists():
                path.unlink()
        except OSError:
            pass

        self.current_json_path = ""