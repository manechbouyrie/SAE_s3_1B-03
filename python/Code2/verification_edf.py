"""Vérification indépendante des résultats EDF.

Ce script ne réutilise PAS l'ordonnanceur : il relit les fichiers d'entrée et les fichiers
de sortie, puis contrôle une à une les règles du problème (RAM, énergie, ordre EDF, métriques...).

Exemple :
    python verification_edf.py Test1
"""

import argparse
import csv
import math
import sys
from pathlib import Path

from lecture_fichiers import (
    ErreurDonnees,
    exiger_cles,
    lire_config,
    lire_energie,
    lire_processus,
    lire_ressources,
)
from main_edf import RACINE, trouver_dossier_inputs, trouver_fichier_ressources
from ordonnanceur_edf import MODES_APRES_PROFIL


# ----------------------------------------------------------------------
# Petites fonctions utiles
# ----------------------------------------------------------------------

def energie_au_pas(t, profil, mode):
    if t < len(profil):
        return profil[t]
    if mode == "cyclique":
        return profil[t % len(profil)]
    return 0


def lire_csv_sortie(chemin):
    """Lit un CSV produit par main_edf.py : liste de dictionnaires (valeurs sous forme de texte)."""
    with open(chemin, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def entier_ou_none(texte):
    """Cellule vide -> None, sinon entier."""
    if texte is None or texte == "":
        return None
    return int(texte)


def moyenne(valeurs):
    if len(valeurs) == 0:
        return None
    return sum(valeurs) / len(valeurs)


# ----------------------------------------------------------------------
# Chargement des données
# ----------------------------------------------------------------------

class Donnees:
    """Tout ce qu'il faut pour vérifier : les entrées, les sorties, et des dictionnaires {id_processus: valeur}."""

    def __init__(self, dossier_in, dossier_out, mode):
        config = lire_config(dossier_in / "config.txt")
        exiger_cles(config, ["fichier_processus", "fichier_global_EDF",
                             "fichier_allocations_EDF", "fichier_metriques"])
        self.mode = mode
        self.res = lire_ressources(trouver_fichier_ressources(dossier_in, config))
        self.profil = lire_energie(dossier_in / config.get("fichier_energie", "energie.csv"))
        self.e = self.res.energie_par_proc

        # Entrées : ce que contient processus.csv
        self.sou, self.duree, self.ram = {}, {}, {}
        self.prio, self.but, self.ordre = {}, {}, {}
        liste = lire_processus(dossier_in / config["fichier_processus"])
        for i in range(len(liste)):
            q = liste[i]["id_processus"]
            self.sou[q] = liste[i]["date_soumission"]
            self.duree[q] = liste[i]["duree_execution"]
            self.ram[q] = liste[i]["ram_necessaire"]
            self.prio[q] = liste[i]["priorite"]
            self.but[q] = liste[i]["date_butoir"]
            self.ordre[q] = i

        # Sorties : fichier global (un processus par ligne)
        self.lignes_globales = lire_csv_sortie(dossier_out / config["fichier_global_EDF"])
        self.ids = []
        self.deb, self.fin = {}, {}
        for ligne in self.lignes_globales:
            q = ligne["id_processus"]
            self.ids.append(q)
            self.deb[q] = entier_ou_none(ligne["date_debut_execution"])
            self.fin[q] = entier_ou_none(ligne["date_fin_execution"])

        # Sorties : fichier des allocations (un segment d'exécution par ligne)
        self.segs = {}  # {id_processus: liste triée de (debut, fin, processeur)}
        for q in self.ids:
            self.segs[q] = []
        self.allocations_inconnues = []
        for ligne in lire_csv_sortie(dossier_out / config["fichier_allocations_EDF"]):
            q = ligne["id_processus"]
            segment = (int(ligne["date_debut"]), int(ligne["date_fin"]), ligne["id_processeur"])
            if q in self.segs:
                self.segs[q].append(segment)
            else:
                self.allocations_inconnues.append(q)
        self.cpu = {}  # processeur utilisé par chaque processus (celui de son premier segment)
        for q in self.ids:
            self.segs[q].sort()
            if len(self.segs[q]) > 0:
                self.cpu[q] = self.segs[q][0][2]

        # Fichier des métriques : on prend la ligne de l'algorithme EDF
        self.metriques = None
        for ligne in lire_csv_sortie(dossier_out / config["fichier_metriques"]):
            if ligne["algorithme"] == "EDF":
                self.metriques = ligne
                break
        if self.metriques is None:
            raise ErreurDonnees("aucune ligne 'EDF' dans le fichier des métriques")

        # Nombre d'instants à examiner : le profil d'énergie, ou plus si un processus finit après
        self.T = len(self.profil)
        for q in self.ids:
            if self.fin[q] is not None and self.fin[q] > self.T:
                self.T = self.fin[q]

    def cle(self, q):
        """Même ordre de priorité que l'ordonnanceur : butoir, priorité décroissante, soumission, ordre."""
        return (self.but[q], -self.prio[q], self.sou[q], self.ordre[q])


def occupe_ressources(d, q, t):
    """Vrai si q a démarré (début <= t) et n'est pas fini (t < fin) : il garde sa RAM et son processeur."""
    if d.deb[q] is None or d.deb[q] > t:
        return False
    return d.fin[q] is None or t < d.fin[q]


def processus_actifs(d, t):
    """Processus qui s'exécutent réellement à l'instant t (un de leurs segments couvre t)."""
    actifs = []
    for q in d.ids:
        for debut, fin, cpu in d.segs[q]:
            if debut <= t < fin:
                actifs.append(q)
    return actifs


# ----------------------------------------------------------------------
# Les contrôles : chacun renvoie la liste des erreurs trouvées
# ----------------------------------------------------------------------

def verifier_coherence_entrees(d):
    erreurs = []
    if set(d.ids) != set(d.sou) or len(d.ids) != len(d.sou):
        erreurs.append("les processus du fichier global ne correspondent pas à processus.csv")
    for q in d.allocations_inconnues:
        erreurs.append(f"{q} : présent dans les allocations mais absent du fichier global")

    for ligne in d.lignes_globales:
        q = ligne["id_processus"]
        if q not in d.sou:
            continue
        lu = (int(ligne["date_soumission"]), int(ligne["ram_demandee"]), int(ligne["date_butoir"]))
        if lu != (d.sou[q], d.ram[q], d.but[q]):
            erreurs.append(f"{q} : soumission / RAM demandée / butoir différents de processus.csv")
        ram_attendue = 0
        if d.deb[q] is not None:
            ram_attendue = d.ram[q]
        if int(ligne["ram_utilisee"]) != ram_attendue:
            erreurs.append(f"{q} : RAM utilisée incohérente")
    return erreurs


def verifier_dates_et_segments(d):
    erreurs = []
    for q in d.ids:
        segs = d.segs[q]
        if len(segs) == 0:
            if d.deb[q] is not None or d.fin[q] is not None:
                erreurs.append(f"{q} : dates renseignées mais aucune allocation")
            continue

        # Chaque segment doit avoir debut < fin, et les segments ne doivent pas se chevaucher
        invalide = False
        for debut, fin, cpu in segs:
            if debut >= fin:
                invalide = True
        for i in range(len(segs) - 1):
            if segs[i][1] > segs[i + 1][0]:
                invalide = True
        if invalide:
            erreurs.append(f"{q} : segments invalides ou qui se chevauchent")

        # Non-préemption : un seul processeur du début à la fin
        liste_cpu = [cpu for debut, fin, cpu in segs]
        if len(set(liste_cpu)) != 1:
            erreurs.append(f"{q} : exécuté sur plusieurs processeurs ({liste_cpu})")
        if d.cpu[q] not in d.res.ids_processeurs:
            erreurs.append(f"{q} : processeur inconnu {d.cpu[q]}")

        # Dates
        execute = 0
        for debut, fin, cpu in segs:
            execute += fin - debut
        if d.deb[q] != segs[0][0]:
            erreurs.append(f"{q} : date de début globale != premier segment")
        if d.deb[q] is not None and d.deb[q] < d.sou[q]:
            erreurs.append(f"{q} : démarre avant sa soumission")
        if d.fin[q] is not None:
            if execute != d.duree[q] or d.fin[q] != segs[-1][1]:
                erreurs.append(f"{q} : durée exécutée {execute} != {d.duree[q]} ou fin != dernier segment")
        elif execute >= d.duree[q]:
            erreurs.append(f"{q} : exécution complète mais sans date de fin")
    return erreurs


def verifier_processeurs(d):
    """Un processeur ne peut pas être occupé par deux processus en même temps."""
    erreurs = []
    for cpu in d.res.ids_processeurs:
        occupations = []  # (début, fin, processus) : un processus occupe son processeur de début à fin
        for q in d.ids:
            if len(d.segs[q]) > 0 and d.cpu[q] == cpu and d.deb[q] is not None:
                fin = d.T if d.fin[q] is None else d.fin[q]
                occupations.append((d.deb[q], fin, q))
        occupations.sort()
        for i in range(len(occupations) - 1):
            d1, f1, q1 = occupations[i]
            d2, f2, q2 = occupations[i + 1]
            if d2 < f1:
                erreurs.append(f"{cpu} : {q1} [{d1},{f1}[ et {q2} [{d2},{f2}[ se chevauchent")
    return erreurs


def verifier_ram(d):
    erreurs = []
    for t in range(d.T):
        utilisee = 0
        for q in d.ids:
            if occupe_ressources(d, q, t):
                utilisee += d.ram[q]
        if utilisee > d.res.ram_totale:
            erreurs.append(f"t={t} : RAM {utilisee} > {d.res.ram_totale}")
    return erreurs


def verifier_energie(d):
    erreurs = []
    for t in range(d.T):
        consommation = len(processus_actifs(d, t)) * d.e
        disponible = energie_au_pas(t, d.profil, d.mode)
        if consommation > disponible:
            erreurs.append(f"t={t} : consommation {consommation} > énergie disponible {disponible}")
    return erreurs


def verifier_regle_edf(d):
    """À chaque instant t, on refait le raisonnement de l'ordonnanceur et on compare avec les fichiers."""
    erreurs = []
    for t in range(d.T):
        # Processus déjà démarrés avant t et pas encore finis
        residents = []
        for q in d.ids:
            if occupe_ressources(d, q, t) and d.deb[q] < t:
                residents.append(q)
        alimentables = min(d.res.nb_processeurs, energie_au_pas(t, d.profil, d.mode) // d.e)

        # (a) Parmi les résidents, seuls les plus urgents doivent être alimentés
        attendus = set(sorted(residents, key=d.cle)[:alimentables])
        alimentes = set(processus_actifs(d, t)) & set(residents)
        if alimentes != attendus:
            erreurs.append(
                f"t={t} : processus déjà démarrés alimentés = {sorted(alimentes)}, attendu {sorted(attendus)}"
            )

        # (b) Combien de nouveaux processus pouvaient démarrer ?
        cpu_occupes = [d.cpu.get(q) for q in residents]
        cpu_libres = [c for c in d.res.ids_processeurs if c not in cpu_occupes]
        ram_libre = d.res.ram_totale
        for q in residents:
            ram_libre -= d.ram[q]
        budget = min(len(cpu_libres), alimentables - len(attendus))

        demarrages = sorted([q for q in d.ids if d.deb[q] == t], key=d.cle)
        if len(demarrages) > budget:
            erreurs.append(f"t={t} : {len(demarrages)} démarrage(s) pour un budget de {budget}")

        # Processus soumis et pas encore démarrés avant t
        en_attente = [q for q in d.ids if d.sou[q] <= t and (d.deb[q] is None or d.deb[q] >= t)]

        # (c) Les démarrages se font dans l'ordre EDF, sur le premier processeur libre,
        #     et personne de plus urgent (et qui tenait en RAM) ne doit avoir été oublié
        deja_demarres = []
        for i in range(min(len(demarrages), len(cpu_libres))):
            p = demarrages[i]
            if d.cpu.get(p) != cpu_libres[i]:
                erreurs.append(f"t={t} : {p} sur {d.cpu.get(p)} au lieu du premier processeur libre {cpu_libres[i]}")
            for q in en_attente:
                if q != p and q not in deja_demarres and d.cle(q) < d.cle(p) and d.ram[q] <= ram_libre:
                    erreurs.append(f"t={t} : {q} (butoir {d.but[q]}) aurait dû démarrer avant {p} (butoir {d.but[p]})")
            ram_libre -= d.ram[p]
            deja_demarres.append(p)

        # (d) Si de la capacité restait libre, aucun processus admissible ne doit être resté en attente
        if len(demarrages) < budget:
            for q in en_attente:
                if q not in deja_demarres and d.ram[q] <= ram_libre:
                    erreurs.append(
                        f"t={t} : {q} admissible (RAM {d.ram[q]} <= {ram_libre}) alors qu'une capacité d'alimentation était libre"
                    )
    return erreurs


def verifier_statuts(d):
    """Contrôle la colonne 'statut' ; renvoie aussi les lignes d'information à afficher."""
    erreurs = []
    infos = []
    for ligne in d.lignes_globales:
        q = ligne["id_processus"]
        if q not in d.but:
            continue
        if d.fin[q] is None:
            attendu = "non_termine"
            fin_txt = "non terminé"
        else:
            fin_txt = f"fin={d.fin[q]}"
            if d.fin[q] <= d.but[q]:
                attendu = "termine"
            else:
                attendu = "termine_en_retard"
        if ligne["statut"] != attendu:
            erreurs.append(f"{q} : statut '{ligne['statut']}' != '{attendu}'")
        infos.append(f"  {q:<5} {fin_txt:<12} butoir={d.but[q]:<4} -> {attendu}")
    return erreurs, infos


def verifier_metriques(d):
    """Recalcule chaque métrique à partir des fichiers et la compare à celle du fichier de métriques."""
    erreurs = []
    demarres = [q for q in d.ids if d.deb[q] is not None]
    termines = [q for q in d.ids if d.fin[q] is not None]

    makespan = None
    if len(termines) == len(d.ids):
        makespan = max(d.fin[q] for q in termines)

    pas_actifs = 0
    for q in d.ids:
        for debut, fin, cpu in d.segs[q]:
            pas_actifs += fin - debut
    energie_consommee = pas_actifs * d.e

    energie_disponible = 0
    for t in range(d.T):
        energie_disponible += energie_au_pas(t, d.profil, d.mode)

    taux = None
    if energie_disponible > 0:
        taux = energie_consommee / energie_disponible

    attendues = {
        "temps_reponse_moyen": moyenne([d.deb[q] - d.sou[q] for q in demarres]),
        "temps_attente_moyen": moyenne([d.fin[q] - d.sou[q] - d.duree[q] for q in termines]),
        "makespan": makespan,
        "energie_consommee_totale": energie_consommee,
        "energie_disponible_totale": energie_disponible,
        "taux_utilisation_energie": taux,
    }

    for nom, attendue in attendues.items():
        texte = d.metriques.get(nom, "")
        lue = None
        if texte != "":
            lue = float(texte)
        if attendue is None and lue is None:
            continue  # les deux sont "non défini" : OK
        if attendue is None or lue is None or not math.isclose(attendue, lue, abs_tol=1e-4):
            erreurs.append(f"{nom} : fichier = {texte or '(vide)'}, recalculé = {attendue}")
    return erreurs


# ----------------------------------------------------------------------
# Programme principal
# ----------------------------------------------------------------------

def verifier(dossier_in, dossier_out, mode="zero"):
    """Lance tous les contrôles. Renvoie (erreurs par contrôle, lignes d'information sur les deadlines)."""
    d = Donnees(dossier_in, dossier_out, mode)
    erreurs = {}

    erreurs["Cohérence avec processus.csv"] = verifier_coherence_entrees(d)
    if set(d.ids) != set(d.sou):
        return erreurs, []  # impossible de continuer si les processus ne sont pas les mêmes

    erreurs["Cohérence des dates / segments"] = verifier_dates_et_segments(d)
    erreurs["Processeurs (exclusivité, non-préemption)"] = verifier_processeurs(d)
    erreurs["RAM <= capacité totale à chaque instant"] = verifier_ram(d)
    erreurs["Énergie consommée <= énergie disponible à chaque instant"] = verifier_energie(d)
    erreurs["Règle EDF non préemptive (ordre, RAM, processeurs libres)"] = verifier_regle_edf(d)
    erreurs["Statuts de deadline cohérents"], infos = verifier_statuts(d)
    erreurs["Métriques recalculées"] = verifier_metriques(d)
    return erreurs, infos


def main(argv=None):
    parseur = argparse.ArgumentParser(description="Vérifie indépendamment les résultats EDF d'un test.")
    parseur.add_argument("test", nargs="?", default="Test1")
    parseur.add_argument("--racine", type=Path, default=RACINE)
    parseur.add_argument("--energie-apres-profil", choices=MODES_APRES_PROFIL, default="zero")
    args = parseur.parse_args(argv)

    try:
        dossier_in = trouver_dossier_inputs(args.test, args.racine)
        dossier_out = args.racine / "Outputs" / dossier_in.name
        erreurs, infos = verifier(dossier_in, dossier_out, args.energie_apres_profil)
    except (ErreurDonnees, FileNotFoundError) as exc:
        print(f"Erreur : {exc}", file=sys.stderr)
        return 1

    total_erreurs = 0
    for nom, liste in erreurs.items():
        if len(liste) == 0:
            print(f"[OK] {nom}")
        else:
            print(f"[ERREUR] {nom}")
            for ligne in liste:
                print(f"      - {ligne}")
        total_erreurs += len(liste)

    print("Deadlines :")
    for ligne in infos:
        print(ligne)

    if total_erreurs == 0:
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
