<?php

class Produit {
    private $Id;
    private $nom;
    private $prix;
    private $NomCategorie;
    private $Coloris;
    private $Commentaire;
    private $DteAjout;
    private $Matiere;
    private $NbrAchat;
    private $Note;
    private $Stock;

    // Constructeur
    public function __construct($Id, $nom, $prix, $NomCategorie, $Coloris, $Commentaire, $DteAjout, $Matiere, $NbrAchat, $Note, $Stock) {
        $this->Id = $Id;
        $this->nom = $nom;
        $this->prix = $prix;
        $this->NomCategorie = $NomCategorie;
        $this->Coloris = $Coloris;
        $this->Commentaire = $Commentaire;
        $this->DteAjout = $DteAjout;
        $this->Matiere = $Matiere;
        $this->NbrAchat = $NbrAchat;
        $this->Note = $Note;
        $this->Stock = $Stock;
    }

    // Getters
    public function getId() { return $this->Id; }
    public function getNom() { return $this->nom; }
    public function getPrix() { return $this->prix; }
    public function getNomCategorie() { return $this->NomCategorie; }
    public function getColoris() { return $this->Coloris; }
    public function getCommentaire() { return $this->Commentaire; }
    public function getDteAjout() { return $this->DteAjout; }
    public function getMatiere() { return $this->Matiere; }
    public function getNbrAchat() { return $this->NbrAchat; }
    public function getNote() { return $this->Note; }
    public function getStock() { return $this->Stock; }
}

?>