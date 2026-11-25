"""Écriture des fichiers de résultats (CSV)."""

import csv
from pathlib import Path

from lecture_fichiers import ErreurDonnees

COLONNES_GLOBAL = [
    "id_processus", "date_soumission", "date_debut_execution", "date_fin_execution",
    "ram_demandee", "ram_utilisee", "date_butoir", "statut",
]
COLONNES_ALLOCATIONS = ["id_processus", "date_debut", "date_fin", "id_processeur"]


def _ecrire_csv(chemin, colonnes, lignes):
    """Écrit un CSV : 'lignes' est une liste de dictionnaires (None est écrit comme une cellule vide)."""
    chemin = Path(chemin)
    try:
        chemin.parent.mkdir(parents=True, exist_ok=True)
        with open(chemin, "w", encoding="utf-8", newline="") as f:
            ecrivain = csv.DictWriter(f, fieldnames=colonnes, extrasaction="ignore")
            ecrivain.writeheader()
            ecrivain.writerows(lignes)
    except OSError as e:
        raise ErreurDonnees(f"Écriture impossible de {chemin} : {e}")


def ecrire_allocation_globale(chemin, resultat):
    """Une ligne par processus : dates de début et de fin, RAM, statut."""
    lignes = []
    for p in resultat.processus:
        ram_utilisee = 0
        if p.debut is not None:
            ram_utilisee = p.ram  # la RAM n'est réservée qu'une fois le processus démarré
        lignes.append({
            "id_processus": p.id,
            "date_soumission": p.soumission,
            "date_debut_execution": p.debut,
            "date_fin_execution": p.fin,
            "ram_demandee": p.ram,
            "ram_utilisee": ram_utilisee,
            "date_butoir": p.butoir,
            "statut": p.statut(),
        })
    _ecrire_csv(chemin, COLONNES_GLOBAL, lignes)


def ecrire_allocations_detaillees(chemin, resultat):
    """Une ligne par segment d'exécution, triée par date de début puis par processeur."""
    allocations = sorted(resultat.allocations, key=lambda a: (a["date_debut"], a["id_processeur"]))
    _ecrire_csv(chemin, COLONNES_ALLOCATIONS, allocations)


def ecrire_metriques(chemin, metriques):
    """Ajoute la ligne de l'algorithme au fichier (en remplaçant son ancienne ligne si elle existe)."""
    chemin = Path(chemin)

    # On garde les lignes des autres algorithmes
    lignes = []
    if chemin.is_file():
        try:
            with open(chemin, encoding="utf-8", newline="") as f:
                for ligne in csv.DictReader(f):
                    if ligne.get("algorithme") != metriques["algorithme"]:
                        lignes.append(ligne)
        except csv.Error:
            lignes = []  # ancien fichier illisible : on repart de zéro
        except (OSError, UnicodeDecodeError) as e:
            raise ErreurDonnees(f"Lecture impossible de {chemin} : {e}")

    lignes.append(metriques)
    _ecrire_csv(chemin, list(metriques.keys()), lignes)
