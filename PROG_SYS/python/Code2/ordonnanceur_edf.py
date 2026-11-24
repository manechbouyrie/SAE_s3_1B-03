"""Ordonnancement EDF non préemptif, avec contraintes de RAM et d'énergie renouvelable.

Principe (la simulation avance d'une unité de temps à chaque tour de boucle) :
  - un processus démarré garde son processeur et sa RAM jusqu'à sa fin (non préemptif) ;
  - à chaque instant, l'énergie disponible limite le nombre de processeurs alimentés ;
  - les processus les plus urgents (date butoir la plus proche) sont alimentés en premier ;
  - s'il reste de l'énergie, on démarre de nouveaux processus (le plus urgent d'abord)
    à condition qu'il y ait un processeur libre et assez de RAM.
"""

MODES_APRES_PROFIL = ("zero", "cyclique")


class Processus:
    def __init__(self, id, soumission, duree, ram, priorite, butoir, ordre):
        self.id = id
        self.soumission = soumission
        self.duree = duree
        self.ram = ram
        self.priorite = priorite
        self.butoir = butoir
        self.ordre = ordre            # position dans processus.csv (sert à départager)
        self.restant = duree          # temps d'exécution qu'il reste à faire
        self.debut = None             # date de début (None tant qu'il n'a pas démarré)
        self.fin = None               # date de fin (None tant qu'il n'est pas terminé)
        self.processeur = None        # identifiant du processeur utilisé
        self.realisable = True        # False si sa RAM dépasse la RAM totale
        self.segment = None           # dernier segment d'exécution (pour fusionner les pas consécutifs)

    def cle_edf(self):
        """Clé de tri : butoir croissant, puis priorité décroissante, puis soumission, puis ordre."""
        return (self.butoir, -self.priorite, self.soumission, self.ordre)

    def statut(self):
        if self.fin is None:
            return "non_termine"
        if self.fin <= self.butoir:
            return "termine"
        return "termine_en_retard"


class ResultatSimulation:
    def __init__(self, processus, allocations, duree_simulation,
                 energie_disponible_totale, apres_profil, avertissements):
        self.processus = processus
        self.allocations = allocations  # liste de dictionnaires {id_processus, date_debut, date_fin, id_processeur}
        self.duree_simulation = duree_simulation
        self.energie_disponible_totale = energie_disponible_totale
        self.apres_profil = apres_profil
        self.avertissements = avertissements


def energie_au_pas(t, profil, apres_profil):
    """Énergie disponible à l'instant t. Au-delà du profil : 0, ou le profil qui se répète."""
    if t < len(profil):
        return profil[t]
    if apres_profil == "cyclique":
        return profil[t % len(profil)]
    return 0


def _creer_processus(liste_processus, ressources, avertissements):
    """Transforme les dictionnaires lus dans processus.csv en objets Processus."""
    procs = []
    for i in range(len(liste_processus)):
        d = liste_processus[i]
        p = Processus(d["id_processus"], d["date_soumission"], d["duree_execution"],
                      d["ram_necessaire"], d["priorite"], d["date_butoir"], i)
        if p.ram > ressources.ram_totale:
            p.realisable = False
            avertissements.append(
                f"{p.id} demande {p.ram} de RAM > RAM totale ({ressources.ram_totale}) : il ne pourra jamais démarrer."
            )
        procs.append(p)
    return procs


def ordonnancer_edf(liste_processus, ressources, profil_energie, apres_profil="zero"):
    if apres_profil not in MODES_APRES_PROFIL:
        raise ValueError(f"apres_profil doit valoir l'un de {MODES_APRES_PROFIL}")

    avertissements = []
    e_proc = ressources.energie_par_proc
    nb_proc = ressources.nb_processeurs

    # Mode cyclique inutile si le profil ne permet jamais d'alimenter un processeur
    if apres_profil == "cyclique" and max(profil_energie) < e_proc:
        avertissements.append(
            "Aucun pas du profil ne permet d'alimenter un processeur : mode 'cyclique' ramené à 'zero'."
        )
        apres_profil = "zero"

    procs = _creer_processus(liste_processus, ressources, avertissements)
    nb_a_terminer = 0
    for p in procs:
        if p.realisable:
            nb_a_terminer += 1

    # Durée maximale de la simulation
    if apres_profil == "zero":
        t_max = len(profil_energie)
    else:
        # borne large : le profil répété autant de fois qu'il faudrait pour tout exécuter
        derniere_soumission = max(p.soumission for p in procs)
        duree_totale = sum(p.duree for p in procs)
        t_max = derniere_soumission + len(profil_energie) * (duree_totale + 1)

    file_attente = []                           # processus soumis, pas encore démarrés
    residents = []                              # processus démarrés, pas encore terminés
    cpu_libres = list(ressources.ids_processeurs)
    ram_libre = ressources.ram_totale
    allocations = []
    nb_termines = 0
    t = 0

    while t < t_max and nb_termines < nb_a_terminer:
        # 1. Les processus soumis à l'instant t entrent dans la file d'attente
        for p in procs:
            if p.soumission == t and p.realisable:
                file_attente.append(p)
        file_attente.sort(key=lambda p: p.cle_edf())

        # 2. Combien de processeurs peut-on alimenter à cet instant ?
        energie_t = energie_au_pas(t, profil_energie, apres_profil)
        alimentables = min(nb_proc, energie_t // e_proc)

        # 3. Les processus déjà démarrés sont alimentés en premier, du plus urgent au moins urgent
        residents.sort(key=lambda p: p.cle_edf())
        actifs = residents[:alimentables]

        # 4. S'il reste de l'énergie : on démarre de nouveaux processus
        places = min(len(cpu_libres), alimentables - len(actifs))
        for p in list(file_attente):
            if places == 0:
                break
            if p.ram <= ram_libre:
                p.processeur = cpu_libres.pop(0)
                p.debut = t
                ram_libre -= p.ram
                file_attente.remove(p)
                residents.append(p)
                actifs.append(p)
                places -= 1

        # 5. Les processus actifs exécutent une unité de temps
        for p in actifs:
            p.restant -= 1
            if p.segment is not None and p.segment["date_fin"] == t:
                p.segment["date_fin"] = t + 1  # il s'exécutait déjà au pas précédent : on prolonge
            else:
                p.segment = {"id_processus": p.id, "date_debut": t, "date_fin": t + 1,
                             "id_processeur": p.processeur}
                allocations.append(p.segment)

        # 6. Ceux qui n'ont plus rien à faire se terminent et libèrent leurs ressources
        for p in actifs:
            if p.restant == 0:
                p.fin = t + 1
                residents.remove(p)
                cpu_libres.append(p.processeur)
                cpu_libres.sort(key=ressources.ids_processeurs.index)  # on garde l'ordre du fichier
                ram_libre += p.ram
                nb_termines += 1

        t += 1

    duree_simulation = max(len(profil_energie), t)
    energie_dispo_totale = 0
    for k in range(duree_simulation):
        energie_dispo_totale += energie_au_pas(k, profil_energie, apres_profil)

    non_termines = []
    for p in procs:
        if p.fin is None:
            non_termines.append(p.id)
    if len(non_termines) > 0:
        avertissements.append(f"Processus non terminés à la fin de la simulation : {', '.join(non_termines)}.")

    return ResultatSimulation(procs, allocations, duree_simulation,
                              energie_dispo_totale, apres_profil, avertissements)
