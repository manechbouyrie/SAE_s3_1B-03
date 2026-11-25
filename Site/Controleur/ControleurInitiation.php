<?php
class ControleurInitiation {
public function __construct() {
}
public function read() {
    include 'Include/head.php';
    include 'Include/header.php';
    include 'Vue/VueInitiation.php';
    include 'Include/footer.php';
}
}
?>