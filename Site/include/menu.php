<link rel="stylesheet" href="CSS/menu.css">
<aside id="catalogue-sidebar" aria-label="Tri et filtres du catalogue">
  <form id="catalogue-filters-form" action="catalogue.php" method="get">
    <!-- Trier par -->
    <div class="filter-group">
      <label for="sort-by">Trier par</label>
      <select id="sort-by" name="orderby">
        <option value="popularite">Popularité</option>
        <option value="prix_asc">Prix croissant</option>
        <option value="prix_desc">Prix décroissant</option>
        <option value="note_desc">Meilleures notes</option>
        <option value="nouveaute">Nouveautés</option>
      </select>
    </div>

    <!-- Recherche par mot-clé -->
    <div class="filter-group">
      <label for="filter-recherche">Recherche</label>
      <input
        type="search"
        id="filter-recherche"
        name="recherche"
        placeholder="Nom, gamme, couleur.."
      />
    </div>

    <fieldset class="filter-group">
  <legend>Prix</legend>
  <div class="dual-range" id="prix-dual-range" data-min="0" data-max="100" data-step="1">
    <div class="dual-range-track">
      <div class="dual-range-fill" id="prix-range-fill"></div>
    </div>
    <input
      type="range"
      id="prix-min"
      name="prix_min"
      min="0"
      max="100"
      step="1"
      value="0"
      aria-label="Prix minimum en euros"
    />
    <input
      type="range"
      id="prix-max"
      name="prix_max"
      min="0"
      max="100"
      step="1"
      value="60"
      aria-label="Prix maximum en euros"
    />
  </div>
  <div class="price-bounds">
    <span id="prix-min-valeur">0 €</span>
    <span id="prix-max-valeur">60 €</span>
  </div>
</fieldset>

    <!-- Sélections / Groupements -->
    <fieldset class="filter-group">
      <legend>Sélections</legend>
      <label>
        <input type="checkbox" name="groupement[]" value="nouveautes" />
        Nouveautés
      </label>
      <label>
        <input type="checkbox" name="groupement[]" value="soldes" />
        Soldes
      </label>
    </fieldset>

    <!-- Actions -->
    <div class="filter-actions">
      <button type="submit" id="apply-filters-btn">Appliquer les filtres</button>
      <button type="button" id="reset-filters-btn">Réinitialiser</button>
    </div>
  </form>
</aside>

<script>
document.addEventListener("DOMContentLoaded", () => {
  const form = document.getElementById("catalogue-filters-form");
  const prixMinInput = document.getElementById("prix-min");
  const prixMaxInput = document.getElementById("prix-max");
  const prixMinLabel = document.getElementById("prix-min-valeur");
  const prixMaxLabel = document.getElementById("prix-max-valeur");
  const rangeFill = document.getElementById("prix-range-fill");
  const resetBtn = document.getElementById("reset-filters-btn");

  if (!form) return;

  function syncPriceSlider(changedSource) {
    if (!prixMinInput || !prixMaxInput) return;

    const minBound = Number(prixMinInput.min);
    const maxBound = Number(prixMinInput.max);
    let minVal = Number(prixMinInput.value);
    let maxVal = Number(prixMaxInput.value);

    // Empêche les deux curseurs de se croiser
    if (minVal > maxVal) {
      if (changedSource === "min") {
        maxVal = minVal;
        prixMaxInput.value = String(maxVal);
      } else {
        minVal = maxVal;
        prixMinInput.value = String(minVal);
      }
    }

    if (prixMinLabel) prixMinLabel.textContent = `${minVal} €`;
    if (prixMaxLabel) prixMaxLabel.textContent = `${maxVal} €`;

    // Met à jour la portion cyan active entre les deux curseurs
    if (rangeFill && maxBound > minBound) {
      const leftPercent = ((minVal - minBound) / (maxBound - minBound)) * 100;
      const rightPercent = ((maxVal - minBound) / (maxBound - minBound)) * 100;
      rangeFill.style.left = `${leftPercent}%`;
      rangeFill.style.width = `${Math.max(0, rightPercent - leftPercent)}%`;
    }
  }

  prixMinInput?.addEventListener("input", () => {
    syncPriceSlider("min");
    emitFilterChange();
  });

  prixMaxInput?.addEventListener("input", () => {
    syncPriceSlider("max");
    emitFilterChange();
  });

  function getActiveFilters() {
    const formData = new FormData(form);
    return {
      orderby: formData.get("orderby") || "popularite",
      recherche: (formData.get("recherche") || "").toString().trim(),
      prixMin: Number(formData.get("prix_min") || 0),
      prixMax: Number(formData.get("prix_max") || 100),
      categorie: formData.get("categorie") || "",
      marques: formData.getAll("marque[]"),
      groupements: formData.getAll("groupement[]"),
      noteMin: formData.get("note_min") ? Number(formData.get("note_min")) : null,
      inclureRupture: formData.get("rupture") === "1"
    };
  }

  function emitFilterChange() {
    window.dispatchEvent(
      new CustomEvent("spinova:filters-changed", { detail: getActiveFilters() })
    );
  }

  form.addEventListener("change", (event) => {
    if (event.target !== prixMinInput && event.target !== prixMaxInput) {
      emitFilterChange();
    }
  });

  form.addEventListener("input", (event) => {
    if (event.target && event.target.id === "filter-recherche") {
      emitFilterChange();
    }
  });

  resetBtn?.addEventListener("click", () => {
    form.reset();
    if (prixMinInput) prixMinInput.value = "0";
    if (prixMaxInput) prixMaxInput.value = "60";
    syncPriceSlider("reset");
    emitFilterChange();
  });

  const params = new URLSearchParams(window.location.search);
  if (params.has("orderby")) {
    const select = document.getElementById("sort-by");
    if (select) select.value = params.get("orderby");
  }
  if (params.has("recherche")) {
    const searchInput = document.getElementById("filter-recherche");
    if (searchInput) searchInput.value = params.get("recherche");
  }
  if (params.has("prix_min") && prixMinInput) {
    prixMinInput.value = params.get("prix_min");
  }
  if (params.has("prix_max") && prixMaxInput) {
    prixMaxInput.value = params.get("prix_max");
  }
  if (params.has("categorie")) {
    const catValue = params.get("categorie");
    const radio = form.querySelector(`input[name="categorie"][value="${catValue}"]`);
    if (radio) radio.checked = true;
  }

  syncPriceSlider("init");
});
</script>