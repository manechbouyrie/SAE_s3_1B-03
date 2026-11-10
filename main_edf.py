"""Point d'entrée : ordonnancement EDF non préemptif (SAE S3.01, partie Python).

Utilisation (depuis la racine du projet) :
    python Code/main_edf.py                      # test par défaut : Inputs/Test1 -> Outputs/Test1
    python Code/main_edf.py Test2                # Inputs/Test2 -> Outputs/Test2
    python Code/main_edf.py Test1 --energie-apres-profil cyclique

Le programme lit Inputs/<test>/config.txt, puis ressources.json, processus.csv et energie.csv, simule EDF
et écrit dans Outputs/<test>/ les fichiers dont les noms sont donnés par config.txt :
    fichier_global_EDF, fichier_allocations_EDF, fichier_metriques.
"""

from __future__ import annotations

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

RACINE = Path(__file__).resolve().parent.parent  # dossier contenant Code/, Inputs/, Outputs/


def trouver_fichier_ressources(dossier: Path, config: dict[str, str]) -> Path:
    """Chemin du fichier de ressources. Le sujet impose ressources.json : si config.txt désigne un fichier
    absent (ex. 'ressources.csv'), on se rabat sur le .json de même nom, en le signalant."""
    nom = config.get("fichier_ressources", "ressources.json")
    chemin = dossier / nom
    if not chemin.is_file() and (dossier / "ressources.json").is_file():
        print(f"Avertissement : '{nom}' (config.txt) introuvable, utilisation de ressources.json.")
        chemin = dossier / "ressources.json"
    return chemin


def trouver_dossier_inputs(test: str, racine: Path) -> Path:
    candidat = racine / "Inputs" / test
    if candidat.is_dir():
        return candidat
    if Path(test).is_dir():
        return Path(test)
    raise ErreurDonnees(f"Dossier de test introuvable : {candidat}")


def _afficher_resume(resultat, metriques: dict, ressources) -> None:
    print(f"\n{'Processus':<10}{'Soumis':>7}{'Début':>7}{'Fin':>6}{'Butoir':>8}  {'CPU':<6}Statut")
    for p in sorted(resultat.processus, key=lambda p: (p.debut is None, p.debut, p.ordre)):
        deb = "-" if p.debut is None else p.debut
        fin = "-" if p.fin is None else p.fin
        statut = "non terminé" if p.fin is None else ("terminé" if p.fin <= p.butoir else "terminé EN RETARD")
        print(f"{p.id:<10}{p.soumission:>7}{deb!s:>7}{fin!s:>6}{p.butoir:>8}  {p.processeur or '-':<6}{statut}")
    print("\nMétriques EDF :")
    for cle, valeur in metriques.items():
        if cle != "algorithme":
            print(f"  {cle:<28}{'(non défini)' if valeur is None else valeur}")
    for avertissement in resultat.avertissements:
        print(f"Avertissement : {avertissement}")


def main(argv: list[str] | None = None) -> int:
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
        df_processus = lire_processus(dossier_in / config["fichier_processus"])
        profil = lire_energie(dossier_in / config.get("fichier_energie", "energie.csv"))

        resultat = ordonnancer_edf(df_processus, ressources, profil, apres_profil=args.energie_apres_profil)
        metriques = calculer_metriques(resultat, ressources, "EDF")

        ecrire_allocation_globale(dossier_out / config["fichier_global_EDF"], resultat)
        ecrire_allocations_detaillees(dossier_out / config["fichier_allocations_EDF"], resultat)
        ecrire_metriques(dossier_out / config["fichier_metriques"], metriques)
    except ErreurDonnees as erreur:
        print(f"Erreur : {erreur}", file=sys.stderr)
        return 1

    _afficher_resume(resultat, metriques, ressources)
    print(f"\nRésultats écrits dans {dossier_out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
