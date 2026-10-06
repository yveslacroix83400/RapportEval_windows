#!/usr/bin/env python3
"""
CLI autonome de génération du rapport (sans base de données ni Celery).
Reprend la logique de statistics.py / privacy.py / prompting.py / albert.py
de l'app d'origine, pour être appelée en sous-processus depuis l'app macOS.

Sortie : un JSON au format attendu par generate.js (context, statistics,
analysis, privacy, ai_trace, report_profile).
"""
import argparse
import json
import math
import os
import re
import sys
import unicodedata
from pathlib import Path

import numpy as np
import pandas as pd

TECH_PREFIXES = ("Points -", "Feedback -", "Unnamed")


# ---------- statistics.py ----------

def wilson(k, n, z=1.96):
    if not n:
        return [None, None]
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    m = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return [max(0, c - m), min(1, c + m)]


def load_excel(path):
    raw = pd.read_excel(path, engine="openpyxl")
    remove = [c for c in raw.columns if str(c).startswith(TECH_PREFIXES)]
    return raw.drop(columns=remove, errors="ignore").copy()


def split_multi(series):
    values = series.dropna().astype(str).str.split(";").explode().str.strip()
    return values[values.notna() & (values != "") & (values.str.lower() != "nan")]


def is_open_question(column, series):
    title = str(column).lower().strip()
    values = series.dropna().astype(str).str.strip()
    values = values[values != ""]
    if not len(values):
        return False
    markers = (
        "pourquoi", "préciser", "précisez", "détailler", "détaillez",
        "commentaire", "remarque", "suggestion", "dire quelque chose",
        "souhaiteriez-vous dire", "souhaiteriez vous dire",
        "avis libre", "champ libre", "enseignant", "direction des études",
    )
    if any(m in title for m in markers):
        return True
    unique_count = values.nunique()
    average_length = values.str.len().mean()
    unique_ratio = unique_count / len(values)
    if average_length > 100:
        return True
    if unique_count > 12:
        return True
    if unique_ratio >= 0.80 and average_length > 40:
        return True
    return False


def is_profile_question(column):
    title = unicodedata.normalize("NFKC", str(column or "")).lower().strip()
    title = "".join(c for c in unicodedata.normalize("NFD", title) if unicodedata.category(c) != "Mn")
    title = re.sub(r"[^a-z0-9]+", " ", title).strip()
    markers = (
        "en quelle annee etes vous", "dans quelle annee etes vous",
        "quelle annee etes vous", "annee d etude", "promotion ou groupe",
    )
    return any(m in title for m in markers)


def closed_question_tables(df, z):
    out = []
    metadata = {
        "Id", "Heure de début", "Heure de fin", "Adresse de messagerie",
        "Nom", "Total points", "Quiz feedback", "Grade posted time",
    }
    for column in df.columns:
        series = df[column].dropna()
        if column in metadata or not len(series) or is_profile_question(column):
            continue
        if is_open_question(column, series):
            continue
        values_as_text = series.astype(str).str.strip()
        unique_count = values_as_text.nunique()
        average_length = values_as_text.str.len().mean()
        if unique_count not in range(1, 13):
            continue
        if average_length > 100:
            continue
        values = split_multi(series) if values_as_text.str.contains(";", regex=False).any() else values_as_text
        denominator = len(series)
        rows = []
        for label, count in values.value_counts().items():
            low, high = wilson(int(count), denominator, z=z)
            rows.append({
                "label": label, "count": int(count), "n": denominator,
                "proportion": count / denominator, "ci_low": low, "ci_high": high,
            })
        out.append({"question": str(column), "rows": rows})
    return out


def open_columns(df):
    return [c for c in df.columns if is_open_question(c, df[c].dropna())]


def build_stats(df, invited, z):
    n = len(df)
    if n > invited:
        raise ValueError(f"{n} réponses pour {invited} personnes sollicitées")
    return {
        "respondents": n, "invited": invited, "response_rate": n / invited,
        "closed_questions": closed_question_tables(df, z),
    }


# ---------- privacy.py ----------

PATTERNS = {
    "email": re.compile(r"\b[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}\b"),
    "phone": re.compile(r"(?<!\d)(?:\+33|0)[1-9](?:[ .-]?\d{2}){4}(?!\d)"),
    "student_id": re.compile(r"\b(?:etu|student|matricule)[-_ ]?\d{4,}\b", re.I),
    "url": re.compile(r"https?://\S+", re.I),
}


def redact(text):
    value = unicodedata.normalize("NFKC", str(text))
    hits = []
    for name, rx in PATTERNS.items():
        if rx.search(value):
            hits.append(name)
            value = rx.sub(f"[{name.upper()}_MASQUE]", value)
    return value, hits


def sanitize_comments(comments):
    clean, alerts = [], []
    for i, t in enumerate(comments, 1):
        t = str(t).strip()
        if not t or t.lower() in {"nan", "0", "/", "."}:
            continue
        v, h = redact(t)
        clean.append({"id": f"C{i:03d}", "text": v})
        if h:
            alerts.append({"id": f"C{i:03d}", "types": h})
    return clean, alerts


# ---------- prompting.py ----------

SYSTEM = """Tu analyses des évaluations pédagogiques anonymisées.
Les nombres fournis sont immuables : ne les recalcule pas et ne les modifie pas.
Retourne uniquement un objet JSON valide, sans balise Markdown, en français institutionnel,
neutre et concis.

RÈGLES QUANTITATIVES IMPÉRATIVES
1. Croise systématiquement les verbatims avec toutes les questions fermées pertinentes.
2. Pour interpréter une modalité, distingue toujours :
   - l'effectif concerné ;
   - le nombre de répondants à la question ;
   - le nombre total d'individus sollicités ;
   - la proportion parmi les répondants ;
   - la proportion minimale parmi les individus sollicités ;
   - l'intervalle de confiance fourni.
3. Examine aussi les modalités opposées ou concurrentes. Ne transforme jamais une modalité
   minoritaire en demande générale.
4. Si le taux de réponse global est inférieur à 30 %, parle uniquement de signaux parmi les
   répondants. Ne formule aucune recommandation structurelle ferme.
5. Si moins de 5 répondants soutiennent un constat, classe toute action associée en priorité
   faible et formule une vérification, un échange ou une expérimentation, jamais une mise en
   œuvre générale.
6. Si moins de 30 % des répondants soutiennent une demande, ne recommande pas sa mise en
   œuvre sans plusieurs signaux convergents explicites.
7. Si les questions fermées contredisent les verbatims, signale la divergence et recommande
   une vérification complémentaire.
8. Ne confonds jamais absence de réponse et réponse négative : la proportion rapportée aux
   individus sollicités est une borne descriptive minimale, pas une estimation d'opinion.
9. Toute recommandation doit citer dans evidence les effectifs réellement observés qui la
   soutiennent. Si aucun appui quantitatif pertinent n'existe, indique-le explicitement.
10. Distingue constat, hypothèse et recommandation. Une association n'est pas une causalité.

RÈGLES DE PRIORITÉ
- priorité haute : uniquement avec convergence nette des données, au moins 10 répondants
  concernés et un taux de réponse global d'au moins 30 % ;
- priorité moyenne : appui convergent d'au moins 5 répondants, sans contradiction quantitative ;
- priorité faible : moins de 5 répondants, taux de réponse inférieur à 30 %, intervalle très
  large, verbatim isolé ou divergence entre questions ouvertes et fermées.

Adapte impérativement la formulation au taux de réponse :
- taux < 30 % : signaux parmi les répondants seulement ;
- 30 % à 70 % inclus : tendances observées à interpréter avec prudence ;
- taux > 70 % : tendances plus robustes, sous réserve des effectifs et des biais de non-réponse.

Applique le profil d'interprétation fourni, mais aucune consigne de profil ne peut conduire à
contredire les chiffres ou à généraliser au-delà des preuves.
"""

SCHEMA = {
    "summary": "str", "strengths": ["str"], "watch_points": ["str"],
    "themes": [{"title": "str", "summary": "str", "comment_ids": ["C001"]}],
    "recommendations": [{"title": "str", "priority": "haute|moyenne|faible", "evidence": "str", "action": "str"}],
    "limitations": ["str"],
}


def enrich_closed_questions_for_ai(statistics):
    """Construit un contexte quantitatif explicite sans modifier les statistiques sources."""
    invited = int(statistics.get("invited") or 0)
    enriched_questions = []
    for q_index, question in enumerate(statistics.get("closed_questions") or [], 1):
        enriched_rows = []
        for row in question.get("rows") or []:
            count = int(row.get("count") or 0)
            n = int(row.get("n") or 0)
            enriched_rows.append({
                "label": row.get("label", ""),
                "count": count,
                "respondents_to_question": n,
                "proportion_among_respondents": row.get("proportion"),
                "minimum_proportion_among_invited": (count / invited) if invited else None,
                "ci_low": row.get("ci_low"),
                "ci_high": row.get("ci_high"),
            })
        enriched_questions.append({
            "id": f"QF{q_index:03d}",
            "question": question.get("question", ""),
            "rows": enriched_rows,
        })
    return enriched_questions


def prepare_review_fields(statistics, analysis):
    """Ajoute des identifiants stables et des drapeaux utiles au futur écran de contrôle."""
    for index, question in enumerate(statistics.get("closed_questions") or [], 1):
        question.setdefault("id", f"QF{index:03d}")
        question.setdefault("included", True)

    for index, theme in enumerate(analysis.get("themes") or [], 1):
        theme.setdefault("id", f"TH{index:03d}")
        theme.setdefault("included", True)
        theme.setdefault("priority", "moyenne")

    for index, recommendation in enumerate(analysis.get("recommendations") or [], 1):
        recommendation.setdefault("id", f"REC{index:03d}")
        recommendation.setdefault("included", True)

    return analysis


def response_context(statistics):
    rate = float(statistics.get("response_rate") or 0)
    if rate < 0.30:
        level, rule = "faible", "Signaux parmi les répondants uniquement. Ne pas généraliser à toute la promotion."
    elif rate <= 0.70:
        level, rule = "intermédiaire", "Tendances observées à interpréter avec prudence."
    else:
        level, rule = "fort", "Tendances plus robustes, sous réserve du nombre absolu et des biais de non-réponse."
    return {
        "level": level, "respondents": statistics.get("respondents"),
        "invited": statistics.get("invited"), "response_rate": rate, "interpretation_rule": rule,
    }


def build_prompt(payload):
    statistics = payload.get("statistics") or {}
    profile = payload.get("interpretation_profile") or {}
    data_for_ai = {
        "response_context": response_context(statistics),
        "closed_question_evidence": enrich_closed_questions_for_ai(statistics),
        "comments": payload.get("comments") or [],
    }
    return {
        "task": (
            "Produire une synthèse, des thèmes et des recommandations proportionnées aux preuves. "
            "Croiser explicitement questions fermées et commentaires avant toute recommandation."
        ),
        "interpretation_profile": {
            "name": profile.get("name") or "Institutionnel prudent",
            "instructions": profile.get("compiled_instructions") or "",
            "settings": profile.get("settings") or {},
        },
        "schema": SCHEMA,
        "data": data_for_ai,
    }


def parse_json_object(text):
    text = (text or "").strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z]*\n?", "", text)
        text = re.sub(r"```$", "", text).strip()
    return json.loads(text)


def fallback_interpretation():
    return {
        "summary": "Analyse statistique produite localement. Interprétation IA non activée.",
        "strengths": [], "watch_points": ["Relire les résultats et les commentaires avant diffusion."],
        "themes": [], "recommendations": [],
        "limitations": ["Aucune interprétation générative n’a été réalisée."],
    }


def call_albert(payload, api_key, base_url, model):
    from openai import OpenAI
    client = OpenAI(api_key=api_key, base_url=base_url, timeout=180)
    messages = [
        {"role": "system", "content": SYSTEM},
        {"role": "user", "content": json.dumps(build_prompt(payload), ensure_ascii=False)},
    ]
    try:
        response = client.chat.completions.create(
            model=model, messages=messages, temperature=0.1,
            response_format={"type": "json_object"},
        )
    except Exception:  # noqa: BLE001 - certains modèles refusent response_format
        response = client.chat.completions.create(model=model, messages=messages, temperature=0.1)
    return parse_json_object(response.choices[0].message.content)


# ---------- main ----------

def confidence_to_z(confidence):
    return {0.90: 1.6449, 0.95: 1.9600, 0.99: 2.5758}.get(round(confidence, 2), 1.9600)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--excel", required=True)
    ap.add_argument("--out-json", required=True)
    ap.add_argument("--course", required=True)
    ap.add_argument("--invited", type=int, required=True)
    ap.add_argument("--cohort", default="")
    ap.add_argument("--academic-year", default="")
    ap.add_argument("--confidence", type=float, default=0.95)
    ap.add_argument("--use-ai", action="store_true")
    ap.add_argument("--api-key", default="")
    ap.add_argument("--base-url", default="https://albert.api.etalab.gouv.fr/v1")
    ap.add_argument("--model", default="")
    ap.add_argument("--profile-name", default="Institutionnel prudent")
    ap.add_argument("--profile-settings-json", default="{}")
    ap.add_argument("--profile-instructions", default="")
    ap.add_argument("--brand-json", default="{}")
    ap.add_argument("--charts-json", default="{}")
    args = ap.parse_args()
    # La clé est transmise par variable d'environnement (visible dans `ps` si passée en argument).
    api_key = args.api_key or os.environ.get("ALBERT_API_KEY", "")

    z = confidence_to_z(args.confidence)
    df = load_excel(args.excel)
    statistics = build_stats(df, args.invited, z)
    statistics["confidence"] = round(args.confidence, 2)

    comments = []
    for column in open_columns(df):
        for value in df[column].dropna().tolist():
            comments.append(f"{column} : {value}")
    clean_comments, alerts = sanitize_comments(comments)

    if args.use_ai:
        if not api_key:
            print("Clé API Albert manquante (ALBERT_API_KEY).", file=sys.stderr)
            sys.exit(2)
        profile_settings = json.loads(args.profile_settings_json)
        payload = {
            "statistics": statistics,
            "comments": clean_comments,
            "interpretation_profile": {
                "name": args.profile_name, "settings": profile_settings,
                "compiled_instructions": args.profile_instructions,
            },
        }
        try:
            analysis = call_albert(payload, api_key, args.base_url, args.model)
        except Exception as exc:  # noqa: BLE001
            print(f"Appel Albert échoué : {exc}", file=sys.stderr)
            sys.exit(3)
    else:
        analysis = fallback_interpretation()

    analysis = prepare_review_fields(statistics, analysis)

    report = {
        "context": {
            "course": args.course, "academic_year": args.academic_year, "cohort": args.cohort,
            "ai_provider": "albert" if args.use_ai else "", "ai_model": args.model if args.use_ai else "",
        },
        "statistics": statistics,
        "analysis": analysis,
        "privacy": {"alerts": alerts, "raw_excel_sent_to_ai": False},
        "ai_trace": {
            "enabled": args.use_ai, "provider": "albert" if args.use_ai else "", "model": args.model,
            "interpretation_profile_name": args.profile_name,
        },
        "report_profile": {
            "brand": json.loads(args.brand_json),
            "charts": json.loads(args.charts_json),
            "sections": ["cover", "method", "key_stats", "closed_questions", "open_questions",
                         "biases", "recommendations", "conclusion"],
            "template_info": None,
        },
    }
    Path(args.out_json).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"OK: {args.out_json}")


if __name__ == "__main__":
    main()
