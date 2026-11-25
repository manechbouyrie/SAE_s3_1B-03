<link rel="stylesheet" href="CSS/header.css">
<body class="body">
    <header class="spinova-header">
        <div class="container">
            <div class="spinova-header-inner">
                <!-- Logo -->
                <a href="index.php?route=accueil" class="spinova-logo">
                    <img src="images/logo.png" alt="Logo Spinova" class="spinova-logo-img" width="auto" height="auto">
                </a>

                <!-- Navigation principale -->
                <nav class="spinova-nav" aria-label="Navigation principale">
                    <a href="index.php?route=accueil" class="active">Accueil</a>
                    <a href="index.php?route=catalogue">Catalogue</a>
                    <a href="index.php?route=initiation">Initiation</a>
                    <a href="index.php?route=competition">Compétition</a>
                    <a href="index.php?route=accessoire">Accessoire</a>
                </nav>

                

                <!-- Recherche + Panier + Avatar avec menu déroulant -->
                <div class="spinova-actions">

                <!-- Barre de recherche -->
                <form action="index.php" method="get" class="spinova-search" role="search">
                    <button type="submit" aria-label="Lancer la recherche" title="Rechercher">
                        <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
                            <circle cx="11" cy="11" r="8"></circle>
                            <line x1="21" y1="21" x2="16.65" y2="16.65"></line>
                        </svg>
                    </button>
                    <input type="hidden" name="route" value="recherche">
                    <input
                        type="search"
                        id="search-input"
                        name="q"
                        placeholder="Rechercher une toupie..."
                        aria-label="Rechercher"
                        required
                    >
                    
                </form>
                <?php   
                    if (!isset($_SESSION['acces']) || $_SESSION['acces'] !== 'yes') {
                                echo '<a class="spinova-cart-btn" href="index.php?route=connexion" title="Panier" aria-label="Panier">';
                            }
                            else {
                            
                                echo '<a href="index.php?route=panier" class="spinova-cart-btn" title="Panier" aria-label="Panier">';
                            }
                    ?>
                    
                        <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
                            <circle cx="9" cy="21" r="1"></circle>
                            <circle cx="20" cy="21" r="1"></circle>
                            <path d="M1 1h4l2.68 13.39a2 2 0 0 0 2 1.61h9.72a2 2 0 0 0 2-1.61L23 6H6"></path>
                        </svg>
                    </a>

                    <div class="spinova-avatar-wrapper" id="avatarMenuContainer">
                        <button
                            type="button"
                            id="avatarBtn"
                            class="spinova-avatar-btn"
                            aria-haspopup="true"
                            aria-expanded="false"
                            title="Menu du compte"
                            aria-label="Menu du compte"
                        >
                        <img src="images/avatar.jpg" alt="Compte utilisateur">
                        </button>

                        <div id="avatarDropdownMenu" class="spinova-dropdown-menu" role="menu">
                            <?php
                            if (!isset($_SESSION['acces']) || $_SESSION['acces'] !== 'yes') {
                                echo '<a class="spinova-dropdown-item" href="index.php?route=connexion" role="menuitem">Connexion</a>';
                                echo '<a class="spinova-dropdown-item" href="index.php?route=inscription" role="menuitem">Inscription</a>';
                            }
                            else {
                            
                                echo '<a class="spinova-dropdown-item" href="index.php?route=compte" role="menuitem">Mon compte</a>';
                                echo '<a class="spinova-dropdown-item" href="index.php?route=commandes" role="menuitem">Mes commandes</a>';
                                echo '<div class="spinova-dropdown-divider"></div>';
                                echo '<a class="spinova-dropdown-item danger" href="index.php?route=deconnexion" role="menuitem">Déconnexion</a>';
                            }
                            ?>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </header>

<script>
document.addEventListener('DOMContentLoaded', () => {
    const btn = document.getElementById('avatarBtn');
    const menu = document.getElementById('avatarDropdownMenu');
    const container = document.getElementById('avatarMenuContainer');

    if (!btn || !menu || !container) return;

    btn.addEventListener('click', (e) => {
        e.stopPropagation();
        const isOpen = menu.classList.toggle('is-open');
        btn.setAttribute('aria-expanded', String(isOpen));
    });

    document.addEventListener('click', (e) => {
        if (!container.contains(e.target)) {
            menu.classList.remove('is-open');
            btn.setAttribute('aria-expanded', 'false');
        }
    });

    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
            menu.classList.remove('is-open');
            btn.setAttribute('aria-expanded', 'false');
        }
    });
});
</script>