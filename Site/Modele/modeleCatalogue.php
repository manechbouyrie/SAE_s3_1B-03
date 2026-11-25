<?php
include_once("Objet/Items.php");
include_once("connect.inc.php");

class modeleCatalogue {
    public function getListItems(){
        $req = 'SELECT * FROM Produit;';
        $res = $conn->prepare($req);
        $res->execute();
        foreach($res as $item){
            $ListProduits[] = new Produit($item['IdProduit'],$item['nom'],$item['prix'],$item['NomCategorie'],$item['Coloris'],$item['Commentaire'],$item['DteAjout'],
            $item['Matiere'],$item['NbrAchat'],$item['Note'],$item['Stock']);
        }
        return $ListProduits;
    }
    
}