package util;

import java.io.BufferedReader;
import java.io.IOException;
import java.io.InputStreamReader;
import java.nio.charset.StandardCharsets;

public class LanceurPython {

    public static void execFichier(String argument) {
        ProcessBuilder processBuilder = new ProcessBuilder(
                "C:\\Python314\\python.exe", "PROG_SYS/python/Code/main_edf.py"
        );

        if (argument != null) {
            processBuilder.command().add(argument);
        }

        processBuilder.redirectErrorStream(true);

        try {
            Process process = processBuilder.start();

            try (BufferedReader reader = new BufferedReader(
                    new InputStreamReader(process.getInputStream(), StandardCharsets.UTF_8))) {
                String ligne;
                while ((ligne = reader.readLine()) != null) {
                    System.out.println(ligne);
                }
            }

            int codeRetour = process.waitFor();
            System.out.println("Le script Python s'est terminé avec le code : " + codeRetour);

        } catch (IOException e) {
            System.err.println("Erreur lors du lancement de Python : " + e.getMessage());
        } catch (InterruptedException e) {
            System.err.println("L'exécution a été interrompue : " + e.getMessage());
            Thread.currentThread().interrupt();
        }
    }
}