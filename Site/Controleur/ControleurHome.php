<?php
class ControleurHome {
public function __construct() {
}
public function read() {
    include 'Include/head.php';
    include 'Include/header.php';
    include 'Vue/VueHome.php';
    include 'Include/footer.php';
}
}
?>