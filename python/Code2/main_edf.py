"""Programme principal : lit un jeu de test, lance l'ordonnancement EDF et écrit les résultats.

Exemples :
    python main_edf.py                  (jeu de test Test1)
    python main_edf.py Test2
    python main_edf.py Test2 --energie-apres-profil cyclique
"""

import argparse
import sys
from pathlib import Path

from ecriture_fichiers import (
    ecrire_allocation_globale,
    ecrire_allocations_detaillees,
    ecrire_metriques,
)
from lecture_fichiers import (
    ErreurDonnees,
    exiger_cles,
    lire_algorithmes,
    lire_config,
    lire_energie,
    lire_processus,
    lire_ressources,
)
from metriques import calculer_metriques
from ordonnanceur_edf import MODES_APRES_PROFIL, ordonnancer_edf

RACINE = Path(__file__).resolve().parent  # dossier qui contient Inputs/ et Outputs/

LIBELLES_STATUT = {
    "non_termine": "non terminé",
    "termine": "terminé",
    "termine_en_retard": "terminé EN RETARD",
}


def trouver_fichier_ressources(dossier, config):
    """Fichier de ressources indiqué dans config.txt, sinon ressources.json par défaut."""
    nom = config.get("fichier_ressources", "ressources.json")
    chemin = dossier / nom
    if not chemin.is_file() and (dossier / "ressources.json").is_file():
        print(f"Avertissement : '{nom}' (config.txt) introuvable, utilisation de ressources.json.")
        chemin = dossier / "ressources.json"
    return chemin


def trouver_dossier_inputs(test, racine):
    """Cherche Inputs/<test> dans la racine, sinon considère 'test' comme un chemin de dossier."""
    candidat = racine / "Inputs" / test
    if candidat.is_dir():
        return candidat
    if Path(test).is_dir():
        return Path(test)
    raise ErreurDonnees(f"Dossier de test introuvable : {candidat}")


def afficher_resume(resultat, metriques):
    print(f"\n{'Processus':<10}{'Soumis':>7}{'Début':>7}{'Fin':>6}{'Butoir':>8}  {'CPU':<6}Statut")

    # D'abord les processus démarrés (dans l'ordre de démarrage), puis les autres
    demarres = [p for p in resultat.processus if p.debut is not None]
    non_demarres = [p for p in resultat.processus if p.debut is None]
    demarres.sort(key=lambda p: (p.debut, p.ordre))

    for p in demarres + non_demarres:
        debut = "-" if p.debut is None else str(p.debut)
        fin = "-" if p.fin is None else str(p.fin)
        cpu = p.processeur if p.processeur is not None else "-"
        print(f"{p.id:<10}{p.soumission:>7}{debut:>7}{fin:>6}{p.butoir:>8}  {cpu:<6}{LIBELLES_STATUT[p.statut()]}")

    print("\nMétriques EDF :")
    for cle, valeur in metriques.items():
        if cle != "algorithme":
            if valeur is None:
                valeur = "(non défini)"
            print(f"  {cle:<28}{valeur}")

    for avertissement in resultat.avertissements:
        print(f"Avertissement : {avertissement}")


def main(argv=None):
    parseur = argparse.ArgumentParser(description="Ordonnancement EDF non préemptif (RAM + énergie renouvelable).")
    parseur.add_argument("test", nargs="?", default="Test1", help="nom du sous-dossier de Inputs/ (défaut : Test1)")
    parseur.add_argument("--racine", type=Path, default=RACINE, help="dossier contenant Code/, Inputs/, Outputs/")
    parseur.add_argument(
        "--energie-apres-profil", choices=MODES_APRES_PROFIL, default="zero",
        help="énergie au-delà de energie.csv : 'zero' (défaut, rien n'est inventé) ou 'cyclique' (profil répété)",
    )
    args = parseur.parse_args(argv)

    try:
        dossier_in = trouver_dossier_inputs(args.test, args.racine)
        dossier_out = args.racine / "Outputs" / dossier_in.name

        config = lire_config(dossier_in / "config.txt")
        if "EDF" not in lire_algorithmes(config):
            print("EDF ne figure pas dans 'algorithmes' de config.txt : rien à exécuter.")
            return 0
        exiger_cles(config, ["fichier_processus", "fichier_global_EDF", "fichier_allocations_EDF", "fichier_metriques"])

        ressources = lire_ressources(trouver_fichier_ressources(dossier_in, config))
        liste_processus = lire_processus(dossier_in / config["fichier_processus"])
        profil = lire_energie(dossier_in / config.get("fichier_energie", "energie.csv"))

        resultat = ordonnancer_edf(liste_processus, ressources, profil, apres_profil=args.energie_apres_profil)
        metriques = calculer_metriques(resultat, ressources, "EDF")

        ecrire_allocation_globale(dossier_out / config["fichier_global_EDF"], resultat)
        ecrire_allocations_detaillees(dossier_out / config["fichier_allocations_EDF"], resultat)
        ecrire_metriques(dossier_out / config["fichier_metriques"], metriques)
    except ErreurDonnees as erreur:
        print(f"Erreur : {erreur}", file=sys.stderr)
        return 1

    afficher_resume(resultat, metriques)
    print(f"\nRésultats écrits dans {dossier_out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
