<link rel="stylesheet" href="CSS/home.css">
<main id="contenu-principal">
  <section class="hero">
    <div class="hero-texte">
      <h1>La toupie qui ne touche plus le sol.</h1>
      
      <p>
        Nos toupies de combat flottent au-dessus de leur socle magnétique. 
        <strong>Lance-la, elle tourne en l'air jusqu'à 3 min 40.</strong> 
        Conçues et assemblées à Toulouse.
      </p>
      
      <div class="hero-actions">
        <button type="button" id="btn-catalogue">Voir le catalogue</button>
        <button type="button" id="btn-autan">Découvrir Autan</button>
      </div>
    </div>

    <div class="hero-visuel">
      <figure>
        <img 
          src="images/toupie-autan-levitation.png" 
          alt="Toupie de combat Spinova Autan en lévitation magnétique à 12 millimètres au-dessus de son socle"
        >
        <figcaption>
          <strong>12 mm</strong> de vide sous la pointe
        </figcaption>
      </figure>
    </div>
  </section>
</main>
<!-- Script JavaScript pour gérer les boutons -->
<script>
document.addEventListener('DOMContentLoaded', () => {
  const btnCatalogue = document.getElementById('btn-catalogue');
  const btnAutan = document.getElementById('btn-autan');

  // Redirection vers la page catalogue
  if (btnCatalogue) {
    btnCatalogue.addEventListener('click', () => {
      window.location.href = 'catalogue.php';
    });
  }

  // Redirection vers la fiche produit de la toupie Autan
  if (btnAutan) {
    btnAutan.addEventListener('click', () => {
      window.location.href = 'produit.php?modele=autan';
    });
  }
});
</script>