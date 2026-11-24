from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd
from lecture_fichiers import Ressources

MODES_APRES_PROFIL = ("zero", "cyclique")


@dataclass
class Processus:
    id: str
    soumission: int
    duree: int
    ram: int
    priorite: int
    butoir: int
    ordre: int 
    restant: int = 0 
    debut: int | None = None 
    fin: int | None = None 
    processeur: str | None = None 
    realisable: bool = True 

    def cle_edf(self) -> tuple:
        """Clé de tri de la file : butoir croissant, puis priorité décroissante, soumission, ordre."""
        return (self.butoir, -self.priorite, self.soumission, self.ordre)


@dataclass
class ResultatSimulation:
    processus: list[Processus]
    allocations: list[dict] 
    duree_simulation: int 
    energie_disponible_totale: int
    apres_profil: str
    avertissements: list[str] = field(default_factory=list)


def energie_au_pas(t: int, profil: list[int], apres_profil: str) -> int:
    if t < len(profil):
        return profil[t]
    return profil[t % len(profil)] if apres_profil == "cyclique" else 0


def ordonnancer_edf(
    df_processus: pd.DataFrame,
    ressources: Ressources,
    profil_energie: list[int],
    apres_profil: str = "zero",
) -> ResultatSimulation:
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

    if apres_profil == "zero":
        t_max = len(profil_energie)
    else: 
        t_max = max(p.soumission for p in procs) + len(profil_energie) * (sum(p.duree for p in procs) + 1)

    file_attente: list[Processus] = [] 
    residents: list[Processus] = [] 
    cpu_libres = list(ressources.ids_processeurs)
    ram_libre = ressources.ram_totale
    dernier_segment: dict[str, dict] = {}
    allocations: list[dict] = []
    i_soumission = 0
    nb_termines = 0
    t = 0

    while t < t_max and nb_termines < nb_a_terminer:
        while i_soumission < len(a_soumettre) and a_soumettre[i_soumission].soumission <= t:
            if a_soumettre[i_soumission].realisable:
                file_attente.append(a_soumettre[i_soumission])
            i_soumission += 1

        file_attente.sort(key=Processus.cle_edf)

        energie_t = energie_au_pas(t, profil_energie, apres_profil)
        alimentables = min(nb_proc, energie_t // e_proc)

        residents.sort(key=Processus.cle_edf)
        actifs = residents[:alimentables]
        budget = min(len(cpu_libres), alimentables - len(actifs))
        for p in list(file_attente):
            if budget == 0:
                break
            if p.ram <= ram_libre:
                p.processeur = cpu_libres.pop(0)
                p.debut = t
                ram_libre -= p.ram
                file_attente.remove(p)
                residents.append(p)
                actifs.append(p)
                budget -= 1

        for p in actifs:
            p.restant -= 1
            seg = dernier_segment.get(p.id)
            if seg is not None and seg["date_fin"] == t: 
                seg["date_fin"] = t + 1
            else: 
                seg = {"id_processus": p.id, "date_debut": t, "date_fin": t + 1, "id_processeur": p.processeur}
                allocations.append(seg)
                dernier_segment[p.id] = seg

        for p in actifs:
            if p.restant == 0:
                p.fin = t + 1
                residents.remove(p)
                cpu_libres.append(p.processeur)
                cpu_libres.sort(key=rang_cpu.__getitem__)
                ram_libre += p.ram
                nb_termines += 1
        t += 1

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
