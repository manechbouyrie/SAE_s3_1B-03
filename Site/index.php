<?php
if (session_status() === PHP_SESSION_NONE) {
    session_start();
}

require 'Controleur/Routeur.php';
$routeur = new Routeur();
$routeur->RouterRequete();
?>