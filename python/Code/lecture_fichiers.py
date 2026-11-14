from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

COLONNES_PROCESSUS = [
    "id_processus",
    "date_soumission",
    "duree_execution",
    "ram_necessaire",
    "priorite",
    "date_butoir",
]
COLONNES_ENERGIE = ["instant", "energie_disponible"]


class ErreurDonnees(Exception):
    pass

@dataclass(frozen=True)
class Ressources:
    nb_processeurs: int
    ram_totale: int
    energie_par_proc: int
    ids_processeurs: list[str]


def lire_config(chemin: Path) -> dict[str, str]:
    chemin = Path(chemin)
    if not chemin.is_file():
        raise ErreurDonnees(f"Fichier de configuration introuvable : {chemin}")
    config: dict[str, str] = {}
    with open(chemin, encoding="utf-8-sig", errors="replace") as f:
        for numero, ligne in enumerate(f, start=1):
            ligne = ligne.strip()  # supprime aussi les fins de ligne CRLF
            if not ligne or ligne.startswith("#"):
                continue
            if "=" not in ligne:
                raise ErreurDonnees(
                    f"{chemin.name}, ligne {numero} : format 'clé = valeur' attendu ({ligne!r})"
                )
            cle, valeur = ligne.split("=", 1)
            config[cle.strip()] = valeur.strip()
    return config


def exiger_cles(config: dict[str, str], cles: list[str]) -> None:
    manquantes = [c for c in cles if not config.get(c)]
    if manquantes:
        raise ErreurDonnees(f"Clés manquantes dans config.txt : {', '.join(manquantes)}")


def lire_algorithmes(config: dict[str, str]) -> list[str]:
    exiger_cles(config, ["algorithmes"])
    return [a.strip().upper() for a in config["algorithmes"].split(",") if a.strip()]


def _entier_positif(valeur, nom: str) -> int:
    if isinstance(valeur, bool) or not isinstance(valeur, int) or valeur <= 0:
        raise ErreurDonnees(f"ressources.json : '{nom}' doit être un entier > 0 (reçu : {valeur!r})")
    return valeur


def lire_ressources(chemin: Path) -> Ressources:
    chemin = Path(chemin)
    if not chemin.is_file():
        raise ErreurDonnees(f"Fichier de ressources introuvable : {chemin}")
    try:
        with open(chemin, encoding="utf-8-sig") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        raise ErreurDonnees(f"{chemin.name} : JSON invalide ({e})") from e

    cles = ["nbProcesseurs", "ramTotale", "energieParProc", "processeur"]
    manquantes = [c for c in cles if c not in data]
    if manquantes:
        raise ErreurDonnees(f"{chemin.name} : clés manquantes : {', '.join(manquantes)}")

    nb = _entier_positif(data["nbProcesseurs"], "nbProcesseurs")
    ram = _entier_positif(data["ramTotale"], "ramTotale")
    energie = _entier_positif(data["energieParProc"], "energieParProc")
    ids = data["processeur"]
    if not isinstance(ids, list) or not all(isinstance(i, str) and i.strip() for i in ids):
        raise ErreurDonnees(f"{chemin.name} : 'processeur' doit être une liste d'identifiants texte")
    if len(set(ids)) != len(ids):
        raise ErreurDonnees(f"{chemin.name} : identifiants de processeurs en double : {ids}")
    if len(ids) != nb:
        raise ErreurDonnees(
            f"{chemin.name} : nbProcesseurs={nb} mais {len(ids)} identifiants listés ({ids})"
        )
    return Ressources(nb_processeurs=nb, ram_totale=ram, energie_par_proc=energie, ids_processeurs=list(ids))

def _lire_csv(chemin: Path, colonnes: list[str]) -> pd.DataFrame:
    chemin = Path(chemin)
    if not chemin.is_file():
        raise ErreurDonnees(f"Fichier introuvable : {chemin}")
    try:
        df = pd.read_csv(chemin, encoding="utf-8-sig")
    except (pd.errors.EmptyDataError, pd.errors.ParserError, UnicodeDecodeError) as e:
        raise ErreurDonnees(f"{chemin.name} : lecture impossible ({e})") from e

    df.columns = [str(c).strip() for c in df.columns]
    manquantes = [c for c in colonnes if c not in df.columns]
    if manquantes:
        raise ErreurDonnees(f"{chemin.name} : colonnes manquantes : {', '.join(manquantes)}")
    if df.empty:
        raise ErreurDonnees(f"{chemin.name} : le fichier ne contient aucune donnée")
    vides = df[colonnes].isna()
    if vides.any().any():
        lignes = sorted((vides.any(axis=1)[vides.any(axis=1)].index + 2).tolist())  # +2 : en-tête + base 1
        raise ErreurDonnees(f"{chemin.name} : valeurs manquantes aux lignes {lignes}")
    return df[colonnes].copy()


def _colonne_entiere(df: pd.DataFrame, colonne: str, nom_fichier: str, minimum: int) -> None:
    try:
        numerique = pd.to_numeric(df[colonne], errors="raise")
    except (ValueError, TypeError) as e:
        raise ErreurDonnees(f"{nom_fichier} : la colonne '{colonne}' doit être numérique ({e})") from e
    if not (numerique % 1 == 0).all():
        raise ErreurDonnees(f"{nom_fichier} : la colonne '{colonne}' doit contenir des entiers")
    df[colonne] = numerique.astype("int64")
    if (df[colonne] < minimum).any():
        raise ErreurDonnees(f"{nom_fichier} : '{colonne}' doit être >= {minimum}")


def lire_processus(chemin: Path) -> pd.DataFrame:
    df = _lire_csv(chemin, COLONNES_PROCESSUS)
    nom = Path(chemin).name
    df["id_processus"] = df["id_processus"].astype(str).str.strip()
    if df["id_processus"].duplicated().any():
        doublons = df.loc[df["id_processus"].duplicated(), "id_processus"].tolist()
        raise ErreurDonnees(f"{nom} : identifiants de processus en double : {doublons}")
    _colonne_entiere(df, "date_soumission", nom, 0)
    _colonne_entiere(df, "duree_execution", nom, 1)
    _colonne_entiere(df, "ram_necessaire", nom, 0)
    _colonne_entiere(df, "priorite", nom, -(10**9))  # une priorité peut être n'importe quel entier
    _colonne_entiere(df, "date_butoir", nom, 0)
    return df.reset_index(drop=True)


def lire_energie(chemin: Path) -> list[int]:

    df = _lire_csv(chemin, COLONNES_ENERGIE)
    nom = Path(chemin).name
    _colonne_entiere(df, "instant", nom, 0)
    _colonne_entiere(df, "energie_disponible", nom, 0)
    df = df.sort_values("instant").reset_index(drop=True)
    if df["instant"].tolist() != list(range(len(df))):
        raise ErreurDonnees(f"{nom} : les instants doivent être consécutifs à partir de 0 (sans trou ni doublon)")
    return df["energie_disponible"].tolist()
