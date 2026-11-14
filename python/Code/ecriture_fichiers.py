"""Écriture des fichiers de résultats (CSV, séparateur virgule, UTF-8) lus ensuite par l'application Java.

Dates : pas de temps entiers ; la date de fin est EXCLUSIVE (un processus exécuté aux pas 13 à 17 a pour
date de début 13 et date de fin 18). Une cellule vide signifie "valeur non définie" (ex. processus non terminé).
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
from lecture_fichiers import ErreurDonnees
from ordonnanceur_edf import ResultatSimulation

COLONNES_GLOBAL = [
    "id_processus", "date_soumission", "date_debut_execution", "date_fin_execution",
    "ram_demandee", "ram_utilisee",
    "date_butoir", "statut",  # colonnes complémentaires utiles pour EDF (respect des deadlines)
]
COLONNES_ALLOCATIONS = ["id_processus", "date_debut", "date_fin", "id_processeur"]
COLONNES_ENTIERES_METRIQUES = [
    "makespan", "energie_consommee_totale", "energie_disponible_totale",
    "nb_processus_termines", "nb_deadlines_manquees",
]


def _ecrire(df: pd.DataFrame, chemin: Path) -> None:
    chemin = Path(chemin)
    try:
        chemin.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(chemin, index=False)
    except OSError as e:
        raise ErreurDonnees(f"Écriture impossible de {chemin} : {e}") from e


def _statut(p) -> str:
    if p.fin is None:
        return "non_termine"
    return "termine" if p.fin <= p.butoir else "termine_en_retard"


def ecrire_allocation_globale(chemin: Path, resultat: ResultatSimulation) -> None:
    """Un enregistrement par processus : soumission, premier démarrage, fin, RAM demandée / utilisée."""
    lignes = [
        {
            "id_processus": p.id,
            "date_soumission": p.soumission,
            "date_debut_execution": p.debut,
            "date_fin_execution": p.fin,
            "ram_demandee": p.ram,
            "ram_utilisee": p.ram if p.debut is not None else 0,  # RAM réservée seulement une fois démarré
            "date_butoir": p.butoir,
            "statut": _statut(p),
        }
        for p in resultat.processus
    ]
    df = pd.DataFrame(lignes, columns=COLONNES_GLOBAL)
    for col in ("date_debut_execution", "date_fin_execution"):
        df[col] = df[col].astype("Int64")  # entiers + cellules vides (évite "13.0")
    _ecrire(df, chemin)


def ecrire_allocations_detaillees(chemin: Path, resultat: ResultatSimulation) -> None:
    """Un enregistrement par période continue d'exécution d'un processus sur un processeur."""
    allocations = sorted(resultat.allocations, key=lambda a: (a["date_debut"], a["id_processeur"]))
    _ecrire(pd.DataFrame(allocations, columns=COLONNES_ALLOCATIONS), chemin)


def ecrire_metriques(chemin: Path, metriques: dict) -> None:
    """Écrit la ligne de métriques de l'algorithme dans le fichier commun.

    Le fichier de métriques est partagé entre algorithmes : si il existe déjà, les lignes des autres
    algorithmes sont conservées et seule la ligne de cet algorithme est remplacée.
    """
    chemin = Path(chemin)
    df = pd.DataFrame([metriques])
    if chemin.is_file():
        try:
            ancien = pd.read_csv(chemin)
        except (pd.errors.EmptyDataError, pd.errors.ParserError):
            ancien = pd.DataFrame()
        if not ancien.empty and "algorithme" in ancien.columns:
            ancien = ancien[ancien["algorithme"] != metriques["algorithme"]]
            df = pd.concat([ancien, df], ignore_index=True) if not ancien.empty else df
    for col in COLONNES_ENTIERES_METRIQUES:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col]).astype("Int64")
    _ecrire(df, chemin)
