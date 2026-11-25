<?php include_once('Modele/modeleCatalogue.php');
class ControleurCatalogue {
    private $modeleCatalogue;
public function __construct() {
    $this->modeleCatalogue = new modeleCatalogue();
}
public function read() {
    if (isset($_GET['categorie']) || isset($_GET['prix']) || isset($_GET['nouveaute']) || isset($_GET['recherche']) || isset($_GET['orderby'])){
        $vlistItems = $this->modeleCatalogue->getListProduitsTrier();
    }
    //else{
    //    $vlistProduits = $this->modeleCatalogue->getListProduits();
    //}
    include('include/header.php');
    include('Vue/VueCatalogue.php');
    include('include/footer.php');
}
}
?>