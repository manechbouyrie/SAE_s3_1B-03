"""Calcul des métriques globales d'un ordonnancement.

Définitions (dates exclusives en fin, cf. ordonnanceur_edf.py) :
  - temps de réponse d'un processus = date de début - date de soumission
        (première obtention du processeur) ;
  - temps d'attente d'un processus  = (date de fin - date de soumission) - durée d'exécution
        = temps passé à attendre, avant le démarrage et pendant les éventuelles pauses d'énergie ;
  - makespan                        = date de fin du dernier processus ;
  - énergie consommée               = somme, sur tous les pas de temps, de l'énergie de chaque
        processeur actif = (nombre total de pas d'exécution) x énergieParProc ;
  - énergie disponible              = somme de l'énergie renouvelable sur la durée de simulation ;
  - taux d'utilisation énergétique  = énergie consommée / énergie disponible.

Chaque métrique est calculée sur les processus pour lesquels elle est définie : la réponse sur ceux qui
ont démarré, l'attente sur ceux qui ont terminé. Le makespan n'existe que si TOUS les processus ont
terminé ; sinon il est laissé vide (None) plutôt que de donner une valeur trompeuse.
"""

from __future__ import annotations

from statistics import fmean

from lecture_fichiers import Ressources
from ordonnanceur_edf import ResultatSimulation


def calculer_metriques(resultat: ResultatSimulation, ressources: Ressources, algorithme: str = "EDF") -> dict:
    """Renvoie un dictionnaire de métriques (une ligne du fichier de métriques)."""
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

    # Un processus non terminé ne respectera jamais sa date butoir (aucune énergie ne lui sera allouée
    # hors simulation) : il est compté comme manqué, au même titre qu'une fin après la date butoir.
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
