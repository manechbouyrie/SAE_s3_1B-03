<link rel="stylesheet" href="CSS/catalogue.css">
<main id="catalogue" aria-label="Catalogue Spinova">
<div class='menu'>
<h1>Catalogue</h1>
<?php include('include/menu.php');?>
</div>
<?php
// Récupère la liste fournie par le contrôleur (filtrée ou complète)
$produitsAffiches = [];
if (isset($vlistItems) && is_array($vlistItems)) {
    $produitsAffiches = $vlistItems;
} elseif (isset($vlistProduits) && is_array($vlistProduits)) {
    $produitsAffiches = $vlistProduits;
}

$categorieActive = $_GET['categorie'] ?? '';
?>


<main id="catalogue-page" aria-label="Catalogue Spinova">
  <header class="catalogue-header">
    
    <p id="catalogue-count"><?= count($produitsAffiches) ?> produit<?= count($produitsAffiches) > 1 ? 's' : '' ?></p>

    <!-- Barre de catégories : changement immédiat au clic -->
    <nav class="category-bar" aria-label="Catégories du catalogue">
      <button
        type="button"
        class="category-pill <?= $categorieActive === '' ? 'active' : '' ?>"
        data-categorie=""
        aria-pressed="<?= $categorieActive === '' ? 'true' : 'false' ?>"
      >
        Tout
      </button>
      <button
        type="button"
        class="category-pill <?= $categorieActive === 'initiation' ? 'active' : '' ?>"
        data-categorie="initiation"
        aria-pressed="<?= $categorieActive === 'initiation' ? 'true' : 'false' ?>"
      >
        Initiation 6-12 ans
      </button>
      <button
        type="button"
        class="category-pill <?= $categorieActive === 'collection' ? 'active' : '' ?>"
        data-categorie="collection"
        aria-pressed="<?= $categorieActive === 'collection' ? 'true' : 'false' ?>"
      >
        Collection
      </button>
      <button
        type="button"
        class="category-pill <?= $categorieActive === 'competition' ? 'active' : '' ?>"
        data-categorie="competition"
        aria-pressed="<?= $categorieActive === 'competition' ? 'true' : 'false' ?>"
      >
        Compétition
      </button>
      <button
        type="button"
        class="category-pill <?= $categorieActive === 'accessoires' ? 'active' : '' ?>"
        data-categorie="accessoires"
        aria-pressed="<?= $categorieActive === 'accessoires' ? 'true' : 'false' ?>"
      >
        Accessoires et arènes
      </button>
    </nav>
  </header>

  <div class="catalogue-layout">
    <!-- Menu latéral de tri et filtres -->
    <?php include('menu_2.php'); ?>

    <!-- Grille des produits -->
    <section id="catalogue-products" aria-label="Liste des produits">
      <?php if (empty($produitsAffiches)) : ?>
        <p class="empty-catalogue">Aucun produit ne correspond à votre sélection.</p>
      <?php else : ?>
        <div class="products-grid">
          <?php foreach ($produitsAffiches as $produit) : ?>
            <?php
              $id = htmlspecialchars((string) $produit->getId(), ENT_QUOTES, 'UTF-8');
              $nom = htmlspecialchars((string) $produit->getNom(), ENT_QUOTES, 'UTF-8');
              $prix = number_format((float) $produit->getPrix(), 2, ',', ' ');
              $categorie = htmlspecialchars((string) $produit->getNomCategorie(), ENT_QUOTES, 'UTF-8');
              $coloris = htmlspecialchars((string) $produit->getColoris(), ENT_QUOTES, 'UTF-8');
              $matiere = htmlspecialchars((string) $produit->getMatiere(), ENT_QUOTES, 'UTF-8');
              $note = htmlspecialchars((string) $produit->getNote(), ENT_QUOTES, 'UTF-8');
              $stock = (int) $produit->getStock();
              $enRupture = ($stock <= 0);
            ?>
            <article
              class="product-card <?= $enRupture ? 'out-of-stock' : '' ?>"
              data-id="<?= $id ?>"
              data-categorie="<?= strtolower($categorie) ?>"
              data-prix="<?= htmlspecialchars((string) $produit->getPrix(), ENT_QUOTES, 'UTF-8') ?>"
              data-note="<?= $note ?>"
              data-stock="<?= $stock ?>"
            >
              <div class="product-badges">
                <?php if ($enRupture) : ?>
                  <span class="badge badge-rupture">Rupture de stock</span>
                <?php endif; ?>
              </div>

              <a href="produit.php?id=<?= $id ?>" class="product-link">
                <h2 class="product-title"><?= $nom ?></h2>
              </a>

              <p class="product-price"><?= $prix ?> €</p>

              <p class="product-meta">
                <span class="product-category"><?= $categorie ?></span>
                <?php if ($matiere !== '') : ?>
                  · <span class="product-material"><?= $matiere ?></span>
                <?php endif; ?>
              </p>

              <?php if ($coloris !== '') : ?>
                <p class="product-colors">Coloris : <?= $coloris ?></p>
              <?php endif; ?>

              <?php if ($note !== '') : ?>
                <p class="product-rating" aria-label="Note <?= $note ?> sur 5">
                  ★ <?= $note ?>
                </p>
              <?php endif; ?>

              <div class="product-actions">
                <?php if ($enRupture) : ?>
                  <button type="button" class="btn-add-cart disabled" disabled aria-disabled="true">
                    Rupture de stock
                  </button>
                <?php else : ?>
                  <a href="produit.php?id=<?= $id ?>" class="btn-choose-color">
                    Choisir un coloris
                  </a>
                  <button
                    type="button"
                    class="btn-add-cart"
                    data-product-id="<?= $id ?>"
                  >
                    Ajouter au panier
                  </button>
                <?php endif; ?>
              </div>
            </article>
          <?php endforeach; ?>
        </div>
      <?php endif; ?>
    </section>
  </div>
</main>
</main>
<script>
document.addEventListener("DOMContentLoaded", () => {
  const categoryButtons = document.querySelectorAll(".category-bar .category-pill");
  const filtersForm = document.getElementById("catalogue-filters-form");
  const productsSection = document.getElementById("catalogue-products");

  if (!categoryButtons.length) return;

  // Synchronise l'état visuel et ARIA des boutons de catégorie
  function setActiveCategoryButton(selectedCategory) {
    categoryButtons.forEach((btn) => {
      const isMatch = (btn.getAttribute("data-categorie") || "") === selectedCategory;
      btn.classList.toggle("active", isMatch);
      btn.setAttribute("aria-pressed", String(isMatch));
    });
  }

  // Met à jour ou crée un champ caché `categorie` dans le formulaire de filtres
  function syncHiddenCategoryInput(selectedCategory) {
    if (!filtersForm) return;
    let hiddenCat = filtersForm.querySelector('input[type="hidden"][name="categorie"]');
    if (!hiddenCat) {
      hiddenCat = document.createElement("input");
      hiddenCat.type = "hidden";
      hiddenCat.name = "categorie";
      filtersForm.appendChild(hiddenCat);
    }
    hiddenCat.value = selectedCategory;
  }

  // Applique la catégorie au clic : mise à jour de l'URL + rechargement/filtrage immédiat
  categoryButtons.forEach((button) => {
    button.addEventListener("click", () => {
      const selectedCategory = button.getAttribute("data-categorie") || "";
      setActiveCategoryButton(selectedCategory);
      syncHiddenCategoryInput(selectedCategory);

      // Notifie les écouteurs JS existants
      window.dispatchEvent(
        new CustomEvent("spinova:category-changed", {
          detail: { categorie: selectedCategory }
        })
      );

      // Met à jour l'URL et soumet / recharge la vue avec la catégorie sélectionnée
      const url = new URL(window.location.href);
      if (selectedCategory) {
        url.searchParams.set("categorie", selectedCategory);
      } else {
        url.searchParams.delete("categorie");
      }

      if (filtersForm) {
        // Conserve les autres filtres actifs du formulaire lors du changement de catégorie
        const formData = new FormData(filtersForm);
        formData.set("categorie", selectedCategory);

        const nextParams = new URLSearchParams();
        for (const [key, value] of formData.entries()) {
          if (value !== "") {
            nextParams.append(key, value.toString());
          }
        }
        const queryString = nextParams.toString();
        window.location.href = queryString ? `catalogue.php?${queryString}` : "catalogue.php";
      } else {
        window.location.href = url.toString();
      }
    });
  });

  // Synchronisation initiale avec l'URL courante
  const initialParams = new URLSearchParams(window.location.search);
  const initialCat = initialParams.get("categorie") || "";
  setActiveCategoryButton(initialCat);
  syncHiddenCategoryInput(initialCat);
});
</script>