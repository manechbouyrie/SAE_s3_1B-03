"""Ordonnancement EDF (Earliest Deadline First) NON PRÉEMPTIF, sous contraintes de RAM et d'énergie.

Conventions de temps
--------------------
Le temps est discret. Le pas de temps t couvre l'intervalle [t, t+1[. Les dates de fin sont donc
exclusives : un processus qui s'exécute aux pas 13, 14 et 15 a pour date de début 13 et date de fin 16.
L'énergie `energie.csv[t]` est celle disponible pendant le pas t ; un processeur actif y consomme
`energieParProc`. Les ressources libérées à la fin du pas t sont réutilisables dès le pas t+1.

Définition EDF appliquée (sujet, §V.4)
--------------------------------------
  * une seule file d'attente, triée par date butoir croissante ;
  * le processeur est attribué au premier processus ADMISSIBLE de la file (RAM suffisante) ;
  * il reste attribué au processus jusqu'à la fin de son exécution ; le processus sort ensuite
    définitivement du système.
Départage en cas de dates butoirs égales : priorité décroissante (plus la valeur est élevée, plus le
processus est prioritaire, cf. sujet), puis date de soumission, puis ordre dans processus.csv.

Hypothèses retenues pour ce que le sujet ne précise pas
-------------------------------------------------------
H1 - Énergie insuffisante pour un processus DÉJÀ démarré.
     Le sujet impose à la fois la non-préemption et l'interdiction de consommer plus d'énergie que
     disponible. Règle retenue : un processus démarré GARDE son processeur et sa RAM jusqu'à sa fin
     (jamais retiré au profit d'un autre processus, donc l'algorithme reste non préemptif) ; mais si
     l'énergie du pas ne permet pas d'alimenter tous les processeurs occupés, les processeurs non
     alimentés sont simplement "en pause" : le processus n'avance pas et ne consomme rien. Il reprend,
     sur le même processeur, dès que l'énergie le permet. En cas de pénurie, les processus démarrés
     dont la date butoir est la plus proche sont alimentés en premier. Tant qu'un processus démarré
     n'est pas alimenté, aucun nouveau processus ne peut démarrer.
H2 - Un processus ne peut démarrer qu'au pas où son processeur est effectivement alimenté.
H3 - Nombre de processeurs alimentables au pas t = min(nbProcesseurs, énergie(t) // énergieParProc)
     (partie entière : on ne dépasse jamais l'énergie disponible).
H4 - La RAM d'un processus est réservée de son démarrage à sa fin, y compris pendant une pause.
H5 - Énergie après la dernière ligne de energie.csv ("apres_profil") :
       "zero"     (défaut) : aucune énergie n'est disponible au-delà du fichier (aucune valeur inventée) ;
                             la simulation s'arrête à la fin du profil, les processus inachevés sont
                             signalés comme non terminés.
       "cyclique"          : le profil se répète à l'identique (journée suivante) jusqu'à ce que tous
                             les processus soient terminés.
H6 - Un processeur libre est choisi dans l'ordre de la liste "processeur" de ressources.json.
H7 - Aucun abandon de processus en retard : un processus dont la date butoir est dépassée reste dans la
     file et sera exécuté normalement (le retard est seulement signalé dans les résultats).
"""

from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

from lecture_fichiers import Ressources

MODES_APRES_PROFIL = ("zero", "cyclique")


@dataclass
class Processus:
    """Un processus et son état pendant la simulation."""

    id: str
    soumission: int
    duree: int
    ram: int
    priorite: int
    butoir: int
    ordre: int  # position dans processus.csv (départage final)
    restant: int = 0  # unités d'exécution restantes
    debut: int | None = None  # première date d'obtention du processeur
    fin: int | None = None  # date de fin (exclusive) ; None tant que non terminé
    processeur: str | None = None  # processeur réservé (fixe pendant toute l'exécution)
    realisable: bool = True  # False si sa RAM dépasse la RAM totale (ne pourra jamais démarrer)

    def cle_edf(self) -> tuple:
        """Clé de tri de la file : butoir croissant, puis priorité décroissante, soumission, ordre."""
        return (self.butoir, -self.priorite, self.soumission, self.ordre)


@dataclass
class ResultatSimulation:
    processus: list[Processus]
    allocations: list[dict]  # un segment = une période continue d'exécution sur un processeur
    duree_simulation: int  # nombre de pas couverts (au moins la longueur du profil d'énergie)
    energie_disponible_totale: int  # somme de l'énergie disponible sur toute la durée de simulation
    apres_profil: str
    avertissements: list[str] = field(default_factory=list)


def energie_au_pas(t: int, profil: list[int], apres_profil: str) -> int:
    """Énergie renouvelable disponible au pas t (voir hypothèse H5 pour t au-delà du profil)."""
    if t < len(profil):
        return profil[t]
    return profil[t % len(profil)] if apres_profil == "cyclique" else 0


def ordonnancer_edf(
    df_processus: pd.DataFrame,
    ressources: Ressources,
    profil_energie: list[int],
    apres_profil: str = "zero",
) -> ResultatSimulation:
    """Simule EDF non préemptif pas à pas et renvoie les dates, allocations et énergie disponible."""
    if apres_profil not in MODES_APRES_PROFIL:
        raise ValueError(f"apres_profil doit valoir l'un de {MODES_APRES_PROFIL}")

    avertissements: list[str] = []
    e_proc = ressources.energie_par_proc
    nb_proc = ressources.nb_processeurs
    rang_cpu = {cpu: i for i, cpu in enumerate(ressources.ids_processeurs)}

    if apres_profil == "cyclique" and max(profil_energie) < e_proc:
        avertissements.append(
            "Aucun pas du profil ne permet d'alimenter un processeur : mode 'cyclique' ramené à 'zero'."
        )
        apres_profil = "zero"

    # --- Création des processus (valeurs lues telles quelles dans processus.csv) ---
    procs = [
        Processus(
            id=r.id_processus, soumission=int(r.date_soumission), duree=int(r.duree_execution),
            ram=int(r.ram_necessaire), priorite=int(r.priorite), butoir=int(r.date_butoir),
            ordre=i, restant=int(r.duree_execution),
        )
        for i, r in enumerate(df_processus.itertuples(index=False))
    ]
    for p in procs:
        if p.ram > ressources.ram_totale:
            p.realisable = False
            avertissements.append(
                f"{p.id} demande {p.ram} de RAM > RAM totale ({ressources.ram_totale}) : il ne pourra jamais démarrer."
            )
    a_soumettre = sorted(procs, key=lambda p: (p.soumission, p.ordre))
    nb_a_terminer = sum(p.realisable for p in procs)

    # --- Borne de la simulation ---
    if apres_profil == "zero":
        t_max = len(profil_energie)  # au-delà, plus aucune énergie : rien ne peut progresser
    else:  # au moins 1 unité de travail par cycle de profil une fois tout soumis -> borne sûre
        t_max = max(p.soumission for p in procs) + len(profil_energie) * (sum(p.duree for p in procs) + 1)

    # --- État de la simulation ---
    file_attente: list[Processus] = []  # soumis, pas encore démarrés
    residents: list[Processus] = []  # démarrés, non terminés (ils détiennent CPU + RAM)
    cpu_libres = list(ressources.ids_processeurs)
    ram_libre = ressources.ram_totale
    dernier_segment: dict[str, dict] = {}
    allocations: list[dict] = []
    i_soumission = 0
    nb_termines = 0
    t = 0

    while t < t_max and nb_termines < nb_a_terminer:
        # 1. Nouveaux processus soumis -> file d'attente (les irréalisables n'y entrent pas)
        while i_soumission < len(a_soumettre) and a_soumettre[i_soumission].soumission <= t:
            if a_soumettre[i_soumission].realisable:
                file_attente.append(a_soumettre[i_soumission])
            i_soumission += 1

        # 2-3. File triée par date butoir croissante
        file_attente.sort(key=Processus.cle_edf)

        # 4. Nombre de processeurs alimentables grâce à l'énergie du pas (jamais plus que l'énergie dispo)
        energie_t = energie_au_pas(t, profil_energie, apres_profil)
        alimentables = min(nb_proc, energie_t // e_proc)

        # 5a. Processus déjà démarrés : alimentés par date butoir croissante (H1), les autres sont en pause
        residents.sort(key=Processus.cle_edf)
        actifs = residents[:alimentables]

        # 5b-7. Nouveaux démarrages : file examinée dans l'ordre EDF, premier processus dont la RAM convient
        budget = min(len(cpu_libres), alimentables - len(actifs))
        for p in list(file_attente):
            if budget == 0:
                break
            if p.ram <= ram_libre:  # sinon on examine le processus suivant de la file
                p.processeur = cpu_libres.pop(0)
                p.debut = t
                ram_libre -= p.ram
                file_attente.remove(p)
                residents.append(p)
                actifs.append(p)
                budget -= 1

        # 8. Exécution d'une unité de temps pour chaque processus alimenté
        for p in actifs:
            p.restant -= 1
            seg = dernier_segment.get(p.id)
            if seg is not None and seg["date_fin"] == t:  # exécution continue -> on prolonge le segment
                seg["date_fin"] = t + 1
            else:  # début, ou reprise après une pause -> nouveau segment
                seg = {"id_processus": p.id, "date_debut": t, "date_fin": t + 1, "id_processeur": p.processeur}
                allocations.append(seg)
                dernier_segment[p.id] = seg

        # 9. Libération des ressources des processus terminés (réutilisables au pas suivant)
        for p in actifs:
            if p.restant == 0:
                p.fin = t + 1
                residents.remove(p)
                cpu_libres.append(p.processeur)
                cpu_libres.sort(key=rang_cpu.__getitem__)
                ram_libre += p.ram
                nb_termines += 1
        t += 1

    # --- Durée de simulation et énergie disponible associée ---
    duree_simulation = max(len(profil_energie), t)
    energie_dispo_totale = sum(energie_au_pas(k, profil_energie, apres_profil) for k in range(duree_simulation))

    non_termines = [p.id for p in procs if p.fin is None]
    if non_termines:
        avertissements.append(f"Processus non terminés à la fin de la simulation : {', '.join(non_termines)}.")

    return ResultatSimulation(
        processus=procs, allocations=allocations, duree_simulation=duree_simulation,
        energie_disponible_totale=energie_dispo_totale, apres_profil=apres_profil,
        avertissements=avertissements,
    )
