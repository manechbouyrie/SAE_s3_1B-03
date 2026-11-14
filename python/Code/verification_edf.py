from __future__ import annotations

import argparse
import itertools
import math
import sys
from pathlib import Path
from statistics import fmean

import pandas as pd
from lecture_fichiers import (
    ErreurDonnees,
    lire_config,
    lire_energie,
    lire_processus,
    lire_ressources,
)
from main_edf import RACINE, trouver_dossier_inputs, trouver_fichier_ressources
from ordonnanceur_edf import MODES_APRES_PROFIL


def _energie(t: int, profil: list[int], mode: str) -> int:
    n = len(profil)
    return profil[t] if t < n else (profil[t % n] if mode == "cyclique" else 0)


def _entier_ou_none(x):
    return None if pd.isna(x) else int(x)


def verifier(dossier_in: Path, dossier_out: Path, mode: str = "zero") -> tuple[dict[str, list[str]], list[str]]:
    config = lire_config(dossier_in / "config.txt")
    res = lire_ressources(trouver_fichier_ressources(dossier_in, config))
    entree = lire_processus(dossier_in / config["fichier_processus"]).set_index("id_processus")
    profil = lire_energie(dossier_in / config.get("fichier_energie", "energie.csv"))
    glob = pd.read_csv(dossier_out / config["fichier_global_EDF"])
    alloc = pd.read_csv(dossier_out / config["fichier_allocations_EDF"])
    met = pd.read_csv(dossier_out / config["fichier_metriques"])
    met = met[met["algorithme"] == "EDF"].iloc[0]

    ids = list(glob["id_processus"])
    sou = {q: int(entree.loc[q, "date_soumission"]) for q in entree.index}
    duree = {q: int(entree.loc[q, "duree_execution"]) for q in entree.index}
    ram = {q: int(entree.loc[q, "ram_necessaire"]) for q in entree.index}
    prio = {q: int(entree.loc[q, "priorite"]) for q in entree.index}
    but = {q: int(entree.loc[q, "date_butoir"]) for q in entree.index}
    ordre = {q: i for i, q in enumerate(entree.index)}
    deb = {r.id_processus: _entier_ou_none(r.date_debut_execution) for r in glob.itertuples()}
    fin = {r.id_processus: _entier_ou_none(r.date_fin_execution) for r in glob.itertuples()}
    segs: dict[str, list[tuple[int, int, str]]] = {q: [] for q in ids}
    for r in alloc.itertuples():
        segs[r.id_processus].append((int(r.date_debut), int(r.date_fin), r.id_processeur))
    for q in segs:  # noqa: PLC0206
        segs[q].sort()
    cpu = {q: segs[q][0][2] for q in ids if segs[q]}

    def cle(q):
        return (but[q], -prio[q], sou[q], ordre[q])

    T = max([len(profil)] + [f for f in fin.values() if f is not None])
    e = res.energie_par_proc
    erreurs: dict[str, list[str]] = {}
    infos: list[str] = []
    err = []
    if set(ids) != set(entree.index) or len(ids) != len(entree):
        err.append("les processus du fichier global ne correspondent pas à processus.csv")
    for r in glob.itertuples():
        q = r.id_processus
        if (r.date_soumission, r.ram_demandee, r.date_butoir) != (sou[q], ram[q], but[q]):
            err.append(f"{q} : soumission / RAM demandée / butoir différents de processus.csv")
        if r.ram_utilisee != (ram[q] if deb[q] is not None else 0):
            err.append(f"{q} : RAM utilisée incohérente")
    erreurs["Cohérence avec processus.csv"] = err
    err = []
    for q in ids:
        s = segs[q]
        if not s:
            if deb[q] is not None or fin[q] is not None:
                err.append(f"{q} : dates renseignées mais aucune allocation")
            continue
        if any(d >= f for d, f, _ in s) or any(s[i][1] > s[i + 1][0] for i in range(len(s) - 1)):
            err.append(f"{q} : segments invalides ou qui se chevauchent")
        if len({c for _, _, c in s}) != 1:
            err.append(f"{q} : exécuté sur plusieurs processeurs ({[c for _, _, c in s]})")
        if cpu[q] not in res.ids_processeurs:
            err.append(f"{q} : processeur inconnu {cpu[q]}")
        execute = sum(f - d for d, f, _ in s)
        if deb[q] != s[0][0]:
            err.append(f"{q} : date de début globale != premier segment")
        if deb[q] < sou[q]:
            err.append(f"{q} : démarre avant sa soumission")
        if fin[q] is not None:
            if execute != duree[q] or fin[q] != s[-1][1]:
                err.append(f"{q} : durée exécutée {execute} != {duree[q]} ou fin != dernier segment")
        elif execute >= duree[q]:
            err.append(f"{q} : exécution complète mais sans date de fin")
    erreurs["Cohérence des dates / segments"] = err
    err = []
    occupation: dict[str, list[tuple[int, int, str]]] = {c: [] for c in res.ids_processeurs}
    for q in ids:
        if q in cpu:
            occupation[cpu[q]].append((deb[q], fin[q] if fin[q] is not None else T, q))
    for c, lst in occupation.items():
        lst.sort()
        for (d1, f1, q1), (d2, f2, q2) in itertools.pairwise(lst):
            if d2 < f1:
                err.append(f"{c} : {q1} [{d1},{f1}[ et {q2} [{d2},{f2}[ se chevauchent")
    erreurs["Processeurs (exclusivité, non-préemption)"] = err
    err = []
    for t in range(T):
        utilisee = sum(ram[q] for q in ids if deb[q] is not None and deb[q] <= t and (fin[q] is None or t < fin[q]))
        if utilisee > res.ram_totale:
            err.append(f"t={t} : RAM {utilisee} > {res.ram_totale}")
    erreurs["RAM <= capacité totale à chaque instant"] = err
    err = []
    conso_totale = 0
    for t in range(T):
        actifs = sum(1 for q in ids for d, f, _ in segs[q] if d <= t < f)
        conso_totale += actifs * e
        if actifs * e > _energie(t, profil, mode):
            err.append(f"t={t} : consommation {actifs * e} > énergie disponible {_energie(t, profil, mode)}")
    erreurs["Énergie consommée <= énergie disponible à chaque instant"] = err
    err = []
    for t in range(T):
        residents = [q for q in ids if deb[q] is not None and deb[q] < t and (fin[q] is None or fin[q] > t)]
        actifs_t = {q for q in ids for d, f, _ in segs[q] if d <= t < f}
        alim = min(res.nb_processeurs, _energie(t, profil, mode) // e)
        attendus = set(sorted(residents, key=cle)[:alim])
        if actifs_t & set(residents) != attendus:
            err.append(f"t={t} : processus déjà démarrés alimentés = {sorted(actifs_t & set(residents))}, attendu {sorted(attendus)}")
        demarrages = sorted((q for q in ids if deb[q] == t), key=cle)
        ram_libre = res.ram_totale - sum(ram[q] for q in residents)
        cpu_libres = [c for c in res.ids_processeurs if c not in {cpu[q] for q in residents}]
        budget = min(len(cpu_libres), alim - len(attendus))
        if len(demarrages) > budget:
            err.append(f"t={t} : {len(demarrages)} démarrage(s) pour un budget de {budget}")
        en_attente = [q for q in ids if sou[q] <= t and (deb[q] is None or deb[q] >= t)]
        deja = set()
        for p, cpu_attendu in zip(demarrages, cpu_libres):
            if cpu[p] != cpu_attendu:
                err.append(f"t={t} : {p} sur {cpu[p]} au lieu du premier processeur libre {cpu_attendu}")
            for q in en_attente:
                if q != p and q not in deja and cle(q) < cle(p) and ram[q] <= ram_libre:
                    err.append(f"t={t} : {q} (butoir {but[q]}) aurait dû démarrer avant {p} (butoir {but[p]})")
            ram_libre -= ram[p]
            deja.add(p)
        if len(demarrages) < budget:
            for q in en_attente:
                if q not in deja and ram[q] <= ram_libre:
                    err.append(f"t={t} : {q} admissible (RAM {ram[q]} <= {ram_libre}) alors qu'une capacité d'alimentation était libre")
    erreurs["Règle EDF non préemptive (ordre, RAM, processeurs libres)"] = err
    err = []
    for r in glob.itertuples():
        q = r.id_processus
        attendu = "non_termine" if fin[q] is None else ("termine" if fin[q] <= but[q] else "termine_en_retard")
        if r.statut != attendu:
            err.append(f"{q} : statut '{r.statut}' != '{attendu}'")
        fin_txt = "non terminé" if fin[q] is None else f"fin={fin[q]}"
        infos.append(f"  {q:<5} {fin_txt:<12} butoir={but[q]:<4} -> {attendu}")
    erreurs["Statuts de deadline cohérents"] = err
    err = []
    dem = [q for q in ids if deb[q] is not None]
    ter = [q for q in ids if fin[q] is not None]
    attendues = {
        "temps_reponse_moyen": fmean(deb[q] - sou[q] for q in dem) if dem else math.nan,
        "temps_attente_moyen": fmean(fin[q] - sou[q] - duree[q] for q in ter) if ter else math.nan,
        "makespan": max(fin[q] for q in ter) if len(ter) == len(ids) else math.nan,
        "energie_consommee_totale": conso_totale,
        "energie_disponible_totale": sum(_energie(t, profil, mode) for t in range(T)),
    }
    attendues["taux_utilisation_energie"] = (
        attendues["energie_consommee_totale"] / attendues["energie_disponible_totale"]
        if attendues["energie_disponible_totale"] else math.nan
    )
    for nom, valeur in attendues.items():
        lu = met[nom]
        if pd.isna(valeur) != pd.isna(lu) or (not pd.isna(valeur) and not math.isclose(valeur, float(lu), abs_tol=1e-4)):
            err.append(f"{nom} : fichier = {lu}, recalculé = {valeur}")
    erreurs["Métriques recalculées"] = err
    return erreurs, infos


def main(argv: list[str] | None = None) -> int:
    parseur = argparse.ArgumentParser(description="Vérifie indépendamment les résultats EDF d'un test.")
    parseur.add_argument("test", nargs="?", default="Test1")
    parseur.add_argument("--racine", type=Path, default=RACINE)
    parseur.add_argument("--energie-apres-profil", choices=MODES_APRES_PROFIL, default="zero")
    args = parseur.parse_args(argv)
    try:
        dossier_in = trouver_dossier_inputs(args.test, args.racine)
        erreurs, infos = verifier(dossier_in, args.racine / "Outputs" / dossier_in.name, args.energie_apres_profil)
    except (ErreurDonnees, FileNotFoundError) as exc:
        print(f"Erreur : {exc}", file=sys.stderr)
        return 1
    for nom, liste in erreurs.items():
        print(f"[{'OK' if not liste else 'ERREUR'}] {nom}")
        for ligne in liste:
            print(f"      - {ligne}")
    print("Deadlines :")
    print("\n".join(infos))
    return 0 if not any(erreurs.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
