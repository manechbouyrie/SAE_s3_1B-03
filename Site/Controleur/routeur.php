<?php
require_once 'Controleur/ControleurHome.php';
require_once 'Controleur/ControleurCatalogue.php';
require_once 'Controleur/ControleurInitiation.php';
//require_once 'Controleur/ControleurEtudiant.php';
//require_once 'Controleur/ControleurY.php';
Class Routeur {
public function RouterRequete() {
if (!empty($_GET['route'])) {
switch ($_GET['route']) {
case 'catalogue' : $ctrlCata = new ControleurCatalogue();$ctrlCata->read();
break;
case 'initiation' : $ctrlInit = new ControleurInitiation();$ctrlInit->read();
break;
case 'yRead' : $ctrlY = new ControleurY();
$ctrlY->read();
break;
default : $ctrlHome = new ControleurHome();
$ctrlHome->read();
break;
}
}
else {
$ctrlHome = new ControleurHome();
$ctrlHome->read();
}
}
}
?>