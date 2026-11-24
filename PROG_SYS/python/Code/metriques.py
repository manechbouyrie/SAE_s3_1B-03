from __future__ import annotations

from statistics import fmean

from lecture_fichiers import Ressources
from ordonnanceur_edf import ResultatSimulation


def calculer_metriques(resultat: ResultatSimulation, ressources: Ressources, algorithme: str = "EDF") -> dict:
    procs = resultat.processus
    demarres = [p for p in procs if p.debut is not None]
    termines = [p for p in procs if p.fin is not None]

    temps_reponse = fmean(p.debut - p.soumission for p in demarres) if demarres else None
    temps_attente = fmean((p.fin - p.soumission) - p.duree for p in termines) if termines else None
    makespan = max(p.fin for p in termines) if procs and len(termines) == len(procs) else None

    pas_actifs = sum(a["date_fin"] - a["date_debut"] for a in resultat.allocations)
    energie_consommee = pas_actifs * ressources.energie_par_proc
    energie_disponible = resultat.energie_disponible_totale
    taux = energie_consommee / energie_disponible if energie_disponible > 0 else None
    deadlines_manquees = sum(1 for p in procs if p.fin is None or p.fin > p.butoir)

    return {
        "algorithme": algorithme,
        "temps_attente_moyen": None if temps_attente is None else round(temps_attente, 4),
        "temps_reponse_moyen": None if temps_reponse is None else round(temps_reponse, 4),
        "makespan": makespan,
        "energie_consommee_totale": energie_consommee,
        "energie_disponible_totale": energie_disponible,
        "taux_utilisation_energie": None if taux is None else round(taux, 4),
        "nb_processus_termines": len(termines),
        "nb_deadlines_manquees": deadlines_manquees,
    }
