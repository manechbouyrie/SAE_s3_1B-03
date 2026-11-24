"""Calcul des métriques de performance d'une simulation."""


def _moyenne(valeurs):
    """Moyenne d'une liste de nombres, ou None si la liste est vide."""
    if len(valeurs) == 0:
        return None
    return sum(valeurs) / len(valeurs)


def _arrondi(valeur):
    """Arrondit à 4 décimales (en laissant passer None)."""
    if valeur is None:
        return None
    return round(valeur, 4)


def calculer_metriques(resultat, ressources, algorithme="EDF"):
    procs = resultat.processus
    demarres = [p for p in procs if p.debut is not None]
    termines = [p for p in procs if p.fin is not None]

    # Temps de réponse : attente avant le premier démarrage
    temps_reponse = _moyenne([p.debut - p.soumission for p in demarres])

    # Temps d'attente : temps passé dans le système sans s'exécuter
    temps_attente = _moyenne([p.fin - p.soumission - p.duree for p in termines])

    # Makespan : fin du dernier processus (défini seulement si tous sont terminés)
    makespan = None
    if len(termines) == len(procs):
        makespan = max(p.fin for p in termines)

    # Énergie : un processeur actif consomme energie_par_proc à chaque pas de temps
    pas_actifs = 0
    for allocation in resultat.allocations:
        pas_actifs += allocation["date_fin"] - allocation["date_debut"]
    energie_consommee = pas_actifs * ressources.energie_par_proc
    energie_disponible = resultat.energie_disponible_totale

    taux = None
    if energie_disponible > 0:
        taux = energie_consommee / energie_disponible

    # Une deadline est manquée si le processus n'est pas terminé ou terminé après son butoir
    deadlines_manquees = 0
    for p in procs:
        if p.fin is None or p.fin > p.butoir:
            deadlines_manquees += 1

    return {
        "algorithme": algorithme,
        "temps_attente_moyen": _arrondi(temps_attente),
        "temps_reponse_moyen": _arrondi(temps_reponse),
        "makespan": makespan,
        "energie_consommee_totale": energie_consommee,
        "energie_disponible_totale": energie_disponible,
        "taux_utilisation_energie": _arrondi(taux),
        "nb_processus_termines": len(termines),
        "nb_deadlines_manquees": deadlines_manquees,
    }
