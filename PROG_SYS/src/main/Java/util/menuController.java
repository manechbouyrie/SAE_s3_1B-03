package ihm.sokoban.util;

import java.net.URL;
import java.util.ResourceBundle;

import ihm.sokoban.SokobanApp;
import javafx.fxml.FXML;
import javafx.fxml.Initializable;
import javafx.scene.control.Button;

public class menuController implements Initializable{

    private AppOrdonnancement parent;

    @FXML
    private Button buttonTuto;
    @FXML
    private Button buttonSokoban;
    @FXML
    private Button buttonCharger;

    @FXML
    private void lauchSokoban(){
        parent.showSokoban("sokoban");
    }

    @FXML
    private void lauchTutoriel(){
        parent.showSokoban("tutoriel");
    }

    @FXML
    private void lauchCharger(){
        parent.showSokoban("charger");
    }

    public void setParent(AppOrdonnancement parent){
        this.parent = parent;
    }

    @Override
    public void initialize(URL location, ResourceBundle resources) {
    }
}