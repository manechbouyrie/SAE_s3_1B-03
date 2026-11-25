<?php

$user = 'root';
    $pass = 'root';

    try {
        $conn = new PDO(
            'mysql:host=localhost;dbname=dbGarage',
            $user,
            $pass,
            [PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION]
        );
    } catch (PDOException $e) {
        echo "Erreur : " . $e->getMessage() . "<br>";
        die();
    }

?>