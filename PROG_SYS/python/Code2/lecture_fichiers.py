"""Lecture et vérification des fichiers d'entrée (config, ressources, processus, énergie)."""

import csv
import json
from pathlib import Path

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
    """Levée quand un fichier d'entrée est absent ou invalide."""


class Ressources:
    """Les ressources de la machine, lues dans ressources.json."""

    def __init__(self, nb_processeurs, ram_totale, energie_par_proc, ids_processeurs):
        self.nb_processeurs = nb_processeurs
        self.ram_totale = ram_totale
        self.energie_par_proc = energie_par_proc
        self.ids_processeurs = ids_processeurs


# ----------------------------------------------------------------------
# config.txt
# ----------------------------------------------------------------------

def lire_config(chemin):
    """Lit un fichier 'clé = valeur' (les lignes vides et les # sont ignorées)."""
    chemin = Path(chemin)
    if not chemin.is_file():
        raise ErreurDonnees(f"Fichier de configuration introuvable : {chemin}")

    config = {}
    numero = 0
    with open(chemin, encoding="utf-8-sig", errors="replace") as f:
        for ligne in f:
            numero += 1
            ligne = ligne.strip()
            if ligne == "" or ligne.startswith("#"):
                continue
            if "=" not in ligne:
                raise ErreurDonnees(
                    f"{chemin.name}, ligne {numero} : format 'clé = valeur' attendu ({ligne!r})"
                )
            cle, valeur = ligne.split("=", 1)
            config[cle.strip()] = valeur.strip()
    return config


def exiger_cles(config, cles):
    """Vérifie que toutes les clés demandées sont présentes et non vides."""
    manquantes = []
    for cle in cles:
        if not config.get(cle):
            manquantes.append(cle)
    if len(manquantes) > 0:
        raise ErreurDonnees("Clés manquantes dans config.txt : " + ", ".join(manquantes))


def lire_algorithmes(config):
    """Renvoie la liste des algorithmes demandés, en majuscules (ex : ['FIFO', 'EDF'])."""
    exiger_cles(config, ["algorithmes"])
    algorithmes = []
    for nom in config["algorithmes"].split(","):
        nom = nom.strip().upper()
        if nom != "":
            algorithmes.append(nom)
    return algorithmes


# ----------------------------------------------------------------------
# ressources.json
# ----------------------------------------------------------------------

def _entier_positif(valeur, nom):
    # type(valeur) is not int : refuse aussi les booléens et les nombres à virgule
    if type(valeur) is not int or valeur <= 0:
        raise ErreurDonnees(f"ressources.json : '{nom}' doit être un entier > 0 (reçu : {valeur!r})")
    return valeur


def lire_ressources(chemin):
    chemin = Path(chemin)
    if not chemin.is_file():
        raise ErreurDonnees(f"Fichier de ressources introuvable : {chemin}")

    try:
        with open(chemin, encoding="utf-8-sig") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        raise ErreurDonnees(f"{chemin.name} : JSON invalide ({e})")

    manquantes = []
    for cle in ["nbProcesseurs", "ramTotale", "energieParProc", "processeur"]:
        if cle not in data:
            manquantes.append(cle)
    if len(manquantes) > 0:
        raise ErreurDonnees(f"{chemin.name} : clés manquantes : {', '.join(manquantes)}")

    nb = _entier_positif(data["nbProcesseurs"], "nbProcesseurs")
    ram = _entier_positif(data["ramTotale"], "ramTotale")
    energie = _entier_positif(data["energieParProc"], "energieParProc")

    ids = data["processeur"]
    ids_valides = isinstance(ids, list)
    if ids_valides:
        for identifiant in ids:
            if not isinstance(identifiant, str) or identifiant.strip() == "":
                ids_valides = False
    if not ids_valides:
        raise ErreurDonnees(f"{chemin.name} : 'processeur' doit être une liste d'identifiants texte")
    if len(set(ids)) != len(ids):
        raise ErreurDonnees(f"{chemin.name} : identifiants de processeurs en double : {ids}")
    if len(ids) != nb:
        raise ErreurDonnees(
            f"{chemin.name} : nbProcesseurs={nb} mais {len(ids)} identifiants listés ({ids})"
        )
    return Ressources(nb, ram, energie, ids)


# ----------------------------------------------------------------------
# Fichiers CSV (processus.csv et energie.csv)
# ----------------------------------------------------------------------

def _lire_csv(chemin, colonnes):
    """Lit un CSV et renvoie une liste de dictionnaires (un par ligne), après vérification."""
    chemin = Path(chemin)
    if not chemin.is_file():
        raise ErreurDonnees(f"Fichier introuvable : {chemin}")

    try:
        with open(chemin, encoding="utf-8-sig", newline="") as f:
            lecteur = csv.DictReader(f)
            if lecteur.fieldnames is None:
                raise ErreurDonnees(f"{chemin.name} : lecture impossible (fichier vide)")
            lecteur.fieldnames = [nom.strip() for nom in lecteur.fieldnames]
            lignes = list(lecteur)
    except (csv.Error, UnicodeDecodeError) as e:
        raise ErreurDonnees(f"{chemin.name} : lecture impossible ({e})")

    manquantes = []
    for colonne in colonnes:
        if colonne not in lecteur.fieldnames:
            manquantes.append(colonne)
    if len(manquantes) > 0:
        raise ErreurDonnees(f"{chemin.name} : colonnes manquantes : {', '.join(manquantes)}")

    if len(lignes) == 0:
        raise ErreurDonnees(f"{chemin.name} : le fichier ne contient aucune donnée")

    # Cellules vides ? (+2 : on compte l'en-tête et la numérotation commence à 1)
    lignes_incompletes = []
    for i in range(len(lignes)):
        for colonne in colonnes:
            valeur = lignes[i][colonne]
            if valeur is None or valeur.strip() == "":
                lignes_incompletes.append(i + 2)
                break
    if len(lignes_incompletes) > 0:
        raise ErreurDonnees(f"{chemin.name} : valeurs manquantes aux lignes {lignes_incompletes}")

    return lignes


def _entier(texte, colonne, nom_fichier, numero_ligne, minimum=None):
    """Convertit un texte en entier ('5' et '5.0' sont acceptés, pas '2.5') et vérifie valeur >= minimum."""
    try:
        nombre = float(texte)
        est_entier = nombre.is_integer()
    except ValueError:
        est_entier = False
    if not est_entier:
        raise ErreurDonnees(
            f"{nom_fichier}, ligne {numero_ligne} : '{colonne}' doit être un entier (reçu : {texte!r})"
        )
    valeur = int(nombre)
    if minimum is not None and valeur < minimum:
        raise ErreurDonnees(f"{nom_fichier}, ligne {numero_ligne} : '{colonne}' doit être >= {minimum}")
    return valeur


def lire_processus(chemin):
    """Renvoie la liste des processus : un dictionnaire par ligne de processus.csv."""
    nom = Path(chemin).name
    lignes = _lire_csv(chemin, COLONNES_PROCESSUS)

    # Identifiants en double ?
    ids_vus = set()
    doublons = []
    for ligne in lignes:
        identifiant = ligne["id_processus"].strip()
        if identifiant in ids_vus:
            doublons.append(identifiant)
        ids_vus.add(identifiant)
    if len(doublons) > 0:
        raise ErreurDonnees(f"{nom} : identifiants de processus en double : {doublons}")

    processus = []
    for i in range(len(lignes)):
        ligne = lignes[i]
        numero = i + 2
        processus.append({
            "id_processus": ligne["id_processus"].strip(),
            "date_soumission": _entier(ligne["date_soumission"], "date_soumission", nom, numero, 0),
            "duree_execution": _entier(ligne["duree_execution"], "duree_execution", nom, numero, 1),
            "ram_necessaire": _entier(ligne["ram_necessaire"], "ram_necessaire", nom, numero, 0),
            "priorite": _entier(ligne["priorite"], "priorite", nom, numero),  # n'importe quel entier
            "date_butoir": _entier(ligne["date_butoir"], "date_butoir", nom, numero, 0),
        })
    return processus


def lire_energie(chemin):
    """Renvoie le profil d'énergie : une liste où profil[t] = énergie disponible à l'instant t."""
    nom = Path(chemin).name
    lignes = _lire_csv(chemin, COLONNES_ENERGIE)

    mesures = []  # liste de couples (instant, énergie)
    for i in range(len(lignes)):
        numero = i + 2
        instant = _entier(lignes[i]["instant"], "instant", nom, numero, 0)
        energie = _entier(lignes[i]["energie_disponible"], "energie_disponible", nom, numero, 0)
        mesures.append((instant, energie))
    mesures.sort()

    profil = []
    for position in range(len(mesures)):
        instant, energie = mesures[position]
        if instant != position:
            raise ErreurDonnees(
                f"{nom} : les instants doivent être consécutifs à partir de 0 (sans trou ni doublon)"
            )
        profil.append(energie)
    return profil
