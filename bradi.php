<?php
/* =====================================================================
   HOTEL.PHP - Hôtel la Candide : gestion d'hôtel (PHP + PostgreSQL)
   Base : "hotel" - 9 tables : client, employe, type_chambre, chambre,
   service, reservation, concerner, consommer, paiement.
   Lancer : php -S localhost:8000 puis http://localhost:8000/Hotel.php
   Plan du fichier :
     1. Configuration            4. API (routeur JSON)
     2. Dictionnaire des colonnes 5. Page HTML
     3. Fonctions utilitaires     6. Styles CSS   7. JavaScript
   ===================================================================== */

/* ---------- 1. CONFIGURATION DE LA CONNEXION POSTGRESQL ---------- */
const DB = [                                   // tableau de connexion
  'host' => 'localhost',                       // serveur PostgreSQL
  'port' => '5432',                            // port par défaut
  'name' => 'hotel',                           // nom de la base
  'user' => 'postgres',                        // utilisateur
  'pass' => '12345',                           // mot de passe
];
session_start();                               // ouvre la session (connexion des employés)
$LOG = [];                                     // liste des requêtes SQL (mode démo)
$ROLES = ['Gerant' => 'G', 'Receptionniste' => 'R', 'Caissier' => 'C', 'Gouvernante' => 'H']; // poste -> rôle

/* ---------- 2. DICTIONNAIRE DES COLONNES (à modifier ici seulement) ---------- */
$ID_CLI  = 'id_client';                        // clé de la table client
$ID_EMP  = 'id_employe';                       // clé de la table employe
$ID_TYPE = 'id_type';                          // clé de la table type_chambre (et clé étrangère de chambre)
$ID_SRV  = 'id_service';                       // clé de la table service
$ID_RES  = 'id_reservation';                   // clé de reservation (et dans concerner, consommer, paiement)
$CLE_PAY = 'reference';                        // clé de la table paiement

/* ---------- 3. FONCTIONS UTILITAIRES ---------- */
function db() {                                // retourne la connexion PDO unique
  static $p;                                   // conserve la connexion entre les appels
  if (!$p) $p = new PDO(                       // crée la connexion au premier appel
    'pgsql:host='.DB['host'].';port='.DB['port'].';dbname='.DB['name'], // DSN PostgreSQL
    DB['user'], DB['pass'],                    // identifiants
    [PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION, PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC] // erreurs en exceptions, lignes en tableaux
  );
  return $p;                                   // renvoie la connexion
}
function q($sql, $args = []) {                 // exécute une requête préparée
  global $LOG;                                 // accès au journal SQL
  $LOG[] = preg_replace('/\s+/', ' ', trim($sql)); // enregistre la requête (mode démo)
  $st = db()->prepare($sql);                   // prépare (protège contre l'injection SQL)
  $st->execute($args);                         // exécute avec les paramètres
  return $st;                                  // retourne le résultat
}
function out($data) {                          // réponse JSON de succès
  global $LOG;                                 // journal SQL à renvoyer
  header('Content-Type: application/json');    // type de réponse
  echo json_encode(['d' => $data, 'sql' => $LOG]); // données + requêtes exécutées
  exit;                                        // fin du script
}
function fail($msg, $code = 400) {             // réponse JSON d'erreur
  http_response_code($code);                   // code HTTP d'erreur
  header('Content-Type: application/json');    // type de réponse
  echo json_encode(['e' => $msg]);             // message lisible
  exit;                                        // fin du script
}
function need($roles) {                        // vérifie le droit de l'utilisateur
  if (!in_array($_SESSION['u']['role'], $roles)) fail('Action non autorisée pour votre rôle.', 403); // refus
}

/* Sous-requête de calcul des soldes (remplace la vue v_solde_reservation) :
   facture = nuits x prix des chambres + services ; payé = somme des paiements */
$SOLDE = "SELECT r.{$ID_RES} AS id_reservation,
  COALESCE((SELECT SUM(c.prix_nuit) FROM concerner c WHERE c.{$ID_RES}=r.{$ID_RES}),0)*(r.date_depart-r.date_arrivee)
  + COALESCE((SELECT SUM(s.quantite*s.prix_unitaire) FROM consommer s WHERE s.{$ID_RES}=r.{$ID_RES}),0) AS total_facture,
  COALESCE((SELECT SUM(p.montant) FROM paiement p WHERE p.{$ID_RES}=r.{$ID_RES}),0) AS total_paye
  FROM reservation r";

/* ---------- 4. API : toutes les actions arrivent par ?a=nom_action ---------- */
if (isset($_GET['a'])) {                       // requête AJAX ?
  $a  = $_GET['a'];                            // nom de l'action
  $in = json_decode(file_get_contents('php://input'), true) ?: []; // données JSON reçues
  try {                                        // toute erreur SQL/trigger sera attrapée plus bas
    if ($a === 'install') {                    // préparation de la base (une seule fois)
      q("ALTER TABLE employe ADD COLUMN IF NOT EXISTS login text UNIQUE"); // colonne identifiant
      q("ALTER TABLE employe ADD COLUMN IF NOT EXISTS mot_de_passe text"); // colonne mot de passe haché
      q("INSERT INTO employe ({$ID_EMP},nom,prenom,poste,telephone) VALUES (4,'Ilunga','Esther','Caissier','0810000004'),(5,'Bakala','Marie','Gouvernante','0810000005') ON CONFLICT DO NOTHING"); // caissier + gouvernante
      q("UPDATE employe SET login=regexp_replace(lower(trim(prenom)),'\s+','','g'), mot_de_passe=?", [password_hash('hotel123', PASSWORD_DEFAULT)]); // (re)crée le compte de chaque employé : identifiant = prénom en minuscules
      $logins = q("SELECT string_agg(login, ', ' ORDER BY {$ID_EMP}) FROM employe")->fetchColumn(); // liste des identifiants réellement créés
      out('Installation terminée. Identifiants : '.$logins.' - mot de passe : hotel123'); // message avec les vrais identifiants
    }
    if ($a === 'login') {                      // connexion
      $u = strtolower(trim($in['u'] ?? '')); // identifiant nettoyé : majuscules et espaces ignorés
      $r = q("SELECT {$ID_EMP} AS id_employe,prenom,nom,poste,mot_de_passe FROM employe WHERE login=?", [$u])->fetch(); // cherche l'employé
      if (!$r) fail("Identifiant inconnu : « {$u} ». Cliquez sur Installer et utilisez un identifiant affiché dans le message vert."); // identifiant absent de la base
      if (!password_verify(trim($in['p'] ?? ''), $r['mot_de_passe'] ?? '')) fail('Mot de passe incorrect : tapez hotel123 (tout en minuscules).'); // mauvais mot de passe
      $_SESSION['u'] = ['id' => $r['id_employe'], 'nom' => $r['prenom'].' '.$r['nom'], 'role' => $ROLES[$r['poste']] ?? 'R', 'poste' => $r['poste']]; // mémorise l'utilisateur
      out($_SESSION['u']);                     // renvoie l'utilisateur connecté
    }
    if ($a === 'logout') { session_destroy(); out(1); } // déconnexion
    if ($a === 'me') out($_SESSION['u'] ?? null);       // utilisateur courant (ou null)
    if (empty($_SESSION['u'])) fail('Session expirée.', 401); // toutes les actions suivantes exigent une connexion
    $db = db();                                // connexion (pour les transactions)

    switch ($a) {                              // actions métier
      case 'state':                            // charge toutes les données de l'écran
        out([
          'chambres' => q("SELECT c.num_chambre,c.etage,c.statut,t.{$ID_TYPE} AS id_type,t.libelle,t.prix_nuit_cdf,t.capacite FROM chambre c JOIN type_chambre t ON t.{$ID_TYPE}=c.{$ID_TYPE} ORDER BY 1")->fetchAll(), // chambres + type
          'resa'     => q("SELECT r.{$ID_RES} AS id_reservation,cl.nom||' '||cl.prenom AS client,r.date_arrivee,r.date_depart,r.statut,s.total_facture,s.total_paye,s.total_facture-s.total_paye AS reste_a_payer FROM reservation r JOIN client cl ON cl.{$ID_CLI}=r.{$ID_CLI} JOIN ({$SOLDE}) s ON s.id_reservation=r.{$ID_RES} ORDER BY 1 DESC")->fetchAll(), // réservations + soldes
          'clients'  => q("SELECT {$ID_CLI} AS id_client,nom,prenom,ville,telephone,email FROM client ORDER BY 1")->fetchAll(), // clients
          'services' => q("SELECT {$ID_SRV} AS id_service,libelle,prix_cdf FROM service ORDER BY 1")->fetchAll(), // services
        ]);
      case 'resa':                             // nouvelle réservation (tables reservation + concerner)
        need(['G', 'R']);                      // gérant ou réceptionniste
        if (empty($in['chambres'])) fail('Choisissez au moins une chambre.'); // au moins une chambre
        $db->beginTransaction();               // tout ou rien
        $id = q("SELECT COALESCE(MAX({$ID_RES}),100)+1 FROM reservation")->fetchColumn(); // prochain numéro
        q("INSERT INTO reservation ({$ID_RES},{$ID_CLI},{$ID_EMP},date_reservation,date_arrivee,date_depart,statut) VALUES (?,?,?,CURRENT_DATE,?,?,'Confirmee')", [$id, $in['client'], $_SESSION['u']['id'], $in['arrivee'], $in['depart']]); // en-tête
        foreach ($in['chambres'] as $n)        // une ligne concerner par chambre (le trigger la passe à "occupee")
          q("INSERT INTO concerner ({$ID_RES},num_chambre,prix_nuit) SELECT ?,c.num_chambre,t.prix_nuit_cdf FROM chambre c JOIN type_chambre t ON t.{$ID_TYPE}=c.{$ID_TYPE} WHERE c.num_chambre=?", [$id, $n]);
        $db->commit(); out($id);               // valide et renvoie le numéro
      case 'pay':                              // encaissement (table paiement)
        need(['G', 'C']);                      // gérant ou caissier
        q("INSERT INTO paiement ({$CLE_PAY},{$ID_RES},date_paiement,montant,mode_paiement) VALUES (?,?,CURRENT_DATE,?,?)", ['P'.date('ymdHis').rand(10, 99), $in['id'], $in['montant'], $in['mode']]); // le trigger refuse un surpaiement
        out(1);                                // succès
      case 'conso':                            // service consommé (table consommer)
        need(['G', 'R', 'H']);                 // gérant, réception, gouvernante
        q("INSERT INTO consommer ({$ID_RES},{$ID_SRV},quantite,date_consommation,prix_unitaire) SELECT ?,{$ID_SRV},?,CURRENT_DATE,prix_cdf FROM service WHERE {$ID_SRV}=? ON CONFLICT ({$ID_RES},{$ID_SRV}) DO UPDATE SET quantite=consommer.quantite+EXCLUDED.quantite", [$in['id'], $in['qte'], $in['service']]); // cumule la quantité
        out(1);                                // succès
      case 'client':                           // nouveau client (table client)
        need(['G', 'R']);                      // gérant ou réceptionniste
        q("INSERT INTO client ({$ID_CLI},nom,prenom,ville,telephone,email) VALUES ((SELECT COALESCE(MAX({$ID_CLI}),0)+1 FROM client),?,?,?,?,NULLIF(?,''))", [$in['nom'], $in['prenom'], $in['ville'], $in['tel'], $in['email'] ?? '']); // numéro automatique
        out(1);                                // succès
      case 'statut':                           // maintenance / remise en service d'une chambre
        need(['G', 'H']);                      // gérant ou gouvernante
        if (!in_array($in['st'], ['libre', 'maintenance'])) fail('Statut invalide.'); // valeurs permises
        q("UPDATE chambre SET statut=? WHERE num_chambre=? AND statut<>'occupee'", [$in['st'], $in['num']]); // jamais une chambre occupée
        out(1);                                // succès
      case 'checkin':                          // arrivée du client
        need(['G', 'R']);                      // gérant ou réceptionniste
        q("UPDATE reservation SET statut='En cours' WHERE {$ID_RES}=? AND statut='Confirmee'", [$in['id']]); // passe en cours
        out(1);                                // succès
      case 'checkout':                         // départ du client
        need(['G', 'R']);                      // gérant ou réceptionniste
        if (q("SELECT total_facture-total_paye FROM ({$SOLDE}) s WHERE s.id_reservation=?", [$in['id']])->fetchColumn() > 0) fail('Réglez le solde avant le départ.'); // solde obligatoire
        $db->beginTransaction();               // tout ou rien
        q("UPDATE reservation SET statut='Terminee' WHERE {$ID_RES}=?", [$in['id']]); // séjour terminé
        q("UPDATE chambre SET statut='libre' WHERE num_chambre IN (SELECT num_chambre FROM concerner WHERE {$ID_RES}=?)", [$in['id']]); // libère les chambres
        $db->commit(); out(1);                 // valide
      case 'explore':                          // explorateur des 9 tables (gérant)
        need(['G']);                           // gérant seulement
        $T = ['client', 'employe', 'type_chambre', 'chambre', 'service', 'reservation', 'concerner', 'consommer', 'paiement']; // liste blanche
        if (!in_array($in['t'], $T)) fail('Table inconnue.'); // refuse tout autre nom
        $cols = $in['t'] === 'employe' ? "{$ID_EMP},nom,prenom,poste,telephone,login" : '*'; // masque le mot de passe
        out(['tables' => $T, 'rows' => q("SELECT {$cols} FROM {$in['t']} LIMIT 100")->fetchAll()]); // 100 lignes max
    }
    fail('Action inconnue.');                  // aucune action reconnue
  } catch (Throwable $e) {                     // erreur SQL, trigger ou PHP
    if (db()->inTransaction()) db()->rollBack(); // annule la transaction
    $m = $e->getMessage();                     // message brut
    if (preg_match('/ERROR:\s+(.*?)(\n|$)/', $m, $x)) $m = $x[1]; // garde le message du trigger
    if (strpos($m, 'duplicate key') !== false) $m = 'Cette ligne existe déjà.'; // doublon
    if (strpos($m, 'login') !== false && strpos($m, 'does not exist') !== false) $m = 'Base non préparée : cliquez sur « Installer ».'; // colonnes absentes
    fail($m);                                  // renvoie l'erreur claire
  }
  exit;                                        // fin de l'API
}
?><!DOCTYPE html>
<!-- ---------- 5. PAGE HTML ---------- -->
<html lang="fr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Hôtel la Candide</title>
<link href="https://fonts.googleapis.com/css2?family=Playfair+Display:wght@600;700&family=Plus+Jakarta+Sans:wght@400;500;700&display=swap" rel="stylesheet"><!-- polices (repli système si hors ligne) -->
<style>
/* ---------- 6. STYLES CSS ---------- */
/* Variables : palette (nuit, or, ivoire) et statuts */
:root{--nuit:#0B1F3A;--or:#C9A24B;--bg:#F7F3EA;--card:#fff;--tx:#14233b;--mut:#6b7788;--ok:#1FA97A;--bad:#E5584F;--warn:#F2A33A;--line:#e4dfd2;--r:14px}
[data-t=dark]{--bg:#08142a;--card:#102a4c;--tx:#f0ece0;--mut:#9fb0c8;--line:#1f3a60} /* thème sombre */
/* Base : police, fond, titres */
*{box-sizing:border-box;margin:0}
body{font:15px/1.5 'Plus Jakarta Sans',system-ui,sans-serif;background:var(--bg);color:var(--tx);transition:background .4s,color .4s}
h1,h2,h3{font-family:'Playfair Display',Georgia,serif}
button,input,select{font:inherit}
/* Écran de connexion : fond dégradé et carte vitrée animée */
#login{min-height:100vh;display:grid;place-items:center;background:radial-gradient(circle at 30% 20%,#17407a,var(--nuit) 60%)}
.lg{background:#ffffff14;backdrop-filter:blur(14px);border:1px solid #ffffff30;border-radius:22px;padding:38px;width:min(380px,92vw);color:#fff;text-align:center;animation:pop .8s cubic-bezier(.2,1.2,.3,1)}
.lg input{width:100%;margin:6px 0;padding:12px 14px;border-radius:10px;border:1px solid #ffffff40;background:#ffffff18;color:#fff}
.lg input::placeholder{color:#cfd8e6}
.logo{width:92px;height:92px;margin:0 auto 8px;display:block;animation:float 4s ease-in-out infinite} /* logo qui flotte */
/* Boutons : or, survol qui se soulève */
.btn{border:0;border-radius:10px;padding:10px 16px;background:linear-gradient(135deg,#d9b45c,var(--or));color:var(--nuit);font-weight:700;cursor:pointer;transition:transform .2s,box-shadow .2s}
.btn:hover{transform:translateY(-2px);box-shadow:0 8px 20px #c9a24b55}
.btn.s{padding:5px 10px;font-size:13px} /* petit bouton */
.btn.g{background:var(--card);color:var(--tx);border:1px solid var(--line)} /* bouton discret */
/* Mise en page : menu latéral, zone principale, barre du haut */
#app{display:none;min-height:100vh}
.side{position:fixed;inset:0 auto 0 0;width:230px;background:var(--nuit);color:#fff;padding:20px 14px;display:flex;flex-direction:column;gap:4px}
.side .brand{display:flex;gap:10px;align-items:center;font-family:'Playfair Display';font-size:19px;margin-bottom:18px}
.side .brand svg{width:40px}
.nav{padding:10px 12px;border-radius:10px;cursor:pointer;color:#c9d4e6;transition:all .25s;border-left:3px solid transparent}
.nav:hover{background:#ffffff14;color:#fff;padding-left:18px} /* survol : glisse */
.nav.on{background:#ffffff1c;color:#fff;border-left-color:var(--or)} /* page active */
main{margin-left:230px;padding:26px 30px 90px}
.top{display:flex;justify-content:space-between;align-items:center;margin-bottom:22px;gap:10px;flex-wrap:wrap}
.view{animation:vin .45s ease} /* transition entre pages */
/* Cartes, indicateurs, chambres */
.grid{display:grid;gap:16px;grid-template-columns:repeat(auto-fill,minmax(210px,1fr))}
.card{background:var(--card);border:1px solid var(--line);border-radius:var(--r);padding:18px;transition:transform .3s,box-shadow .3s}
.card:hover{transform:translateY(-4px);box-shadow:0 14px 30px #0b1f3a22}
.kpi b{display:block;font:700 26px 'Playfair Display';color:var(--or)}
.kpi span{color:var(--mut);font-size:13px}
.room{padding:0;overflow:hidden;position:relative}
.room svg{width:100%;display:block;transition:transform .6s} /* illustration de la chambre */
.room:hover svg{transform:scale(1.07)} /* zoom au survol */
.room .in{padding:12px 14px}
/* Pastilles de statut */
.badge{display:inline-block;padding:2px 10px;border-radius:99px;font-size:12px;font-weight:700;color:#fff}
.libre{background:var(--ok)}
.occupee{background:var(--bad);animation:pulse 2s infinite} /* occupée : pulse */
.maintenance{background:var(--warn)}
/* Tableaux */
table{width:100%;border-collapse:collapse;background:var(--card);border-radius:var(--r);overflow:hidden}
th,td{padding:10px 12px;text-align:left;border-bottom:1px solid var(--line);font-size:14px}
th{background:var(--nuit);color:#fff;font-weight:500}
tr:hover td{background:#c9a24b14}
/* Fenêtre modale (formulaires) */
.ov{position:fixed;inset:0;background:#0b1f3a99;display:none;place-items:center;z-index:9;backdrop-filter:blur(4px)}
.ov.on{display:grid}
.mod{background:var(--card);border-radius:18px;padding:26px;width:min(480px,94vw);max-height:90vh;overflow:auto;animation:pop .35s}
.mod label{display:block;margin:10px 0 3px;font-size:13px;color:var(--mut)}
.mod input,.mod select{width:100%;padding:10px;border-radius:9px;border:1px solid var(--line);background:var(--bg);color:var(--tx)}
.chk{display:flex;gap:8px;align-items:center;padding:6px 0}
.chk input{width:auto}
/* Notifications et panneau SQL (mode démo) */
#toast{position:fixed;right:20px;top:20px;z-index:99;display:flex;flex-direction:column;gap:8px}
.t{padding:12px 18px;border-radius:12px;color:#fff;background:var(--ok);animation:vin .3s;box-shadow:0 8px 24px #0004}
.t.e{background:var(--bad)} /* erreur */
#sqlp{position:fixed;left:230px;right:0;bottom:0;background:#050d1c;color:#9ef0c8;font:12px ui-monospace,monospace;padding:8px 16px;max-height:110px;overflow:auto;display:none;z-index:5}
#sqlp code{display:block;white-space:pre-wrap;margin:2px 0}
/* Graphique en barres animé */
.bars{display:flex;gap:10px;align-items:flex-end;height:150px}
.bars div{flex:1;background:linear-gradient(var(--or),#8a6d2a);border-radius:6px 6px 0 0;transform-origin:bottom;animation:grow .9s ease both;position:relative}
.bars i{position:absolute;bottom:-20px;left:0;right:0;text-align:center;font-size:11px;color:var(--mut)}
/* Animations */
@keyframes pop{from{opacity:0;transform:translateY(30px) scale(.94)}}
@keyframes float{50%{transform:translateY(-6px)}}
@keyframes vin{from{opacity:0;transform:translateX(18px)}}
@keyframes pulse{50%{box-shadow:0 0 0 6px #e5584f33}}
@keyframes grow{from{transform:scaleY(0)}}
/* Mobile et accessibilité (mouvement réduit) */
@media(max-width:800px){.side{position:static;width:auto;flex-direction:row;overflow:auto}.side .brand span{display:none}main{margin:0;padding:16px}#sqlp{left:0}}
@media(prefers-reduced-motion:reduce){*{animation:none!important;transition:none!important}}
</style></head><body>
<!-- Logo SVG réutilisable : écusson, toit, clé et vague du fleuve -->
<svg width="0" height="0" style="position:absolute"><defs><symbol id="lg" viewBox="0 0 100 100"><circle cx="50" cy="50" r="46" fill="#0B1F3A" stroke="#C9A24B" stroke-width="3"/><path d="M26 44 50 24 74 44" fill="none" stroke="#C9A24B" stroke-width="5" stroke-linejoin="round"/><circle cx="50" cy="40" r="6" fill="#C9A24B"/><rect x="47.5" y="46" width="5" height="26" fill="#C9A24B"/><path d="M52 62h8v4h-8M52 70h6v4h-6" fill="#C9A24B"/><path d="M22 80q7-7 14 0t14 0 14 0 14 0" fill="none" stroke="#C9A24B" stroke-width="3" stroke-linecap="round"/></symbol></defs></svg>
<!-- Écran de connexion -->
<div id="login"><div class="lg"><svg class="logo"><use href="#lg"/></svg><h1>Hôtel la Candide</h1><p style="opacity:.8;margin-bottom:14px">Gestion hôtelière intelligente</p>
<input id="u" placeholder="Identifiant (ex. joseph)"><input id="p" type="password" placeholder="Mot de passe"><button class="btn" style="width:100%;margin-top:10px" id="go">Se connecter</button>
<p style="margin-top:14px;font-size:13px"><a href="#" id="inst" style="color:#e8cf8f">Installer / préparer la base</a></p></div></div>
<!-- Application (visible après connexion) : menu, barre du haut, contenu -->
<div id="app"><aside class="side"><div class="brand"><svg><use href="#lg"/></svg><span>la Candide</span></div><div id="nav"></div></aside>
<main><div class="top"><div><h2 id="ttl"></h2><small id="who" style="color:var(--mut)"></small></div><div><button class="btn g s" data-a="sql">Mode démo SQL</button> <button class="btn g s" data-a="theme">Clair / sombre</button> <button class="btn g s" data-a="out">Déconnexion</button></div></div><div id="v" class="view"></div></main></div>
<div class="ov" id="ov"><div class="mod" id="mod"></div></div><!-- fenêtre modale -->
<div id="toast"></div><!-- notifications -->
<div id="sqlp"></div><!-- panneau des requêtes SQL -->
<script>
/* ---------- 7. JAVASCRIPT ---------- */
/* 7.1 Outils généraux */
const $ = s => document.querySelector(s);                                   // raccourci de sélection
const esc = s => String(s ?? '').replace(/[&<>"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c])); // protège l'affichage (anti-XSS)
const fm = n => new Intl.NumberFormat('fr-FR').format(Math.round(n || 0)) + ' CDF'; // format monétaire
let U, S = {}, V = 'dash';                                                  // U = utilisateur, S = données, V = page courante
/* Menu de chaque rôle : [identifiant de page, libellé] */
const NAV = {
  G: [['dash','Tableau de bord'],['rooms','Chambres'],['resa','Réservations'],['cli','Clients'],['svc','Services'],['exp','Base de données']], // gérant
  R: [['dash','Tableau de bord'],['rooms','Chambres'],['resa','Réservations'],['cli','Clients']],                                                 // réception
  C: [['dash','Tableau de bord'],['resa','Paiements']],                                                                                           // caisse
  H: [['dash','Tableau de bord'],['rooms','Chambres'],['svc','Services']]                                                                         // gouvernante
};
function toast(m, e) {                                                      // affiche une notification
  const d = document.createElement('div');                                  // crée la bulle
  d.className = 't' + (e ? ' e' : '');                                      // style erreur ou succès
  d.textContent = m;                                                        // texte du message
  $('#toast').append(d);                                                    // l'ajoute à l'écran
  setTimeout(() => d.remove(), 4200);                                       // la retire après 4 s
}
/* 7.2 Communication avec l'API PHP */
async function api(a, b) {                                                  // appelle ?a=action
  const r = await fetch('?a=' + a, {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(b || {})}); // envoie les données
  let j;                                                                    // réponse JSON
  try { j = await r.json(); } catch (x) { throw Error('Connexion PostgreSQL impossible : vérifiez DB en haut de Hotel.php.'); } // réponse illisible
  if (j.sql && j.sql.length) $('#sqlp').innerHTML = j.sql.map(x => '<code>▶ ' + esc(x) + '</code>').join(''); // alimente le mode démo SQL
  if (!r.ok) throw Error(j.e);                                              // erreur du serveur ou d'un trigger
  return j.d;                                                               // données utiles
}
const run = async (a, b, ok) => {                                           // action + message + rechargement
  try { await api(a, b); if (ok) toast(ok); await load(); } catch (e) { toast(e.message, 1); } // affiche l'erreur en rouge
};
/* 7.3 Illustration SVG des chambres selon id_type */
function art(t) {
  const bed = (x, w) => `<rect x="${x}" y="82" width="${w}" height="34" rx="5" fill="#f4efe2"/><rect x="${x}" y="70" width="${w}" height="18" rx="6" fill="#C9A24B"/>`; // un lit
  const c = {                                                               // décor par type : [couleur du mur, meubles]
    1: ['#1b3a66', bed(80, 90)],                                            // simple : un lit
    2: ['#143055', bed(60, 130) + '<rect x="196" y="60" width="6" height="40" fill="#C9A24B"/><circle cx="199" cy="56" r="9" fill="#ffe9a8"/>'], // double : grand lit + lampe
    3: ['#1f3f5e', bed(30, 70) + bed(115, 70) + '<rect x="200" y="96" width="22" height="20" fill="#e5584f"/>'], // familiale : deux lits + lit bébé
    4: ['#2a2a55', bed(60, 100) + '<rect x="175" y="90" width="55" height="26" rx="6" fill="#1FA97A"/><rect x="0" y="118" width="260" height="2" fill="#C9A24B"/><circle cx="236" cy="30" r="14" fill="#ffd36b"/>'] // suite : salon + soleil
  }[t] || ['#1b3a66', bed(80, 90)];                                         // décor par défaut
  return `<svg viewBox="0 0 260 130"><rect width="260" height="130" fill="${c[0]}"/><rect x="14" y="16" width="54" height="46" rx="4" fill="#9fd6ff55" stroke="#C9A24B"/><rect x="0" y="116" width="260" height="14" fill="#0006"/>${c[1]}</svg>`; // fenêtre + sol + meubles
}
/* 7.4 Composants : fenêtre modale, pastille de statut, compteur animé */
function modal(t, h, f) {                                                   // t = titre, h = champs HTML, f = action à la validation
  $('#mod').innerHTML = `<h2>${t}</h2><form>${h}<div style="margin-top:16px;display:flex;gap:8px"><button class="btn">Valider</button><button type="button" class="btn g" data-a="x">Annuler</button></div></form>`; // contenu
  $('#ov').classList.add('on');                                             // affiche la fenêtre
  $('#mod form').onsubmit = e => { e.preventDefault(); f(Object.fromEntries(new FormData(e.target))); $('#ov').classList.remove('on'); }; // envoie puis ferme
}
const st = s => `<span class="badge ${s == 'libre' ? 'libre' : s == 'occupee' ? 'occupee' : 'maintenance'}">${s}</span>`; // pastille colorée
function count(el) {                                                        // anime un nombre de 0 à data-n
  const n = +el.dataset.n, t0 = performance.now();                          // cible et heure de départ
  (function f(t) { const k = Math.min(1, (t - t0) / 900); el.textContent = fm(n * k); if (k < 1) requestAnimationFrame(f); })(t0); // 0,9 s
}
/* 7.5 Les pages (chaque fonction retourne du HTML) */
const V_ = {
  dash() {                                                                  // tableau de bord
    const ch = S.chambres, oc = ch.filter(c => c.statut == 'occupee').length, act = ch.filter(c => c.statut != 'maintenance').length || 1; // occupation
    const F = S.resa.reduce((a, r) => a + +r.total_facture, 0), P = S.resa.reduce((a, r) => a + +r.total_paye, 0), mx = Math.max(1, ...S.resa.map(r => +r.total_facture)); // totaux
    return `<div class="grid"><div class="card kpi"><span>Chiffre facturé</span><b data-n="${F}"></b></div><div class="card kpi"><span>Encaissé</span><b data-n="${P}"></b></div><div class="card kpi"><span>Reste à encaisser</span><b data-n="${F - P}"></b></div><div class="card kpi"><span>Occupation</span><b>${Math.round(oc / act * 100)} %</b><span>${oc} chambre(s) occupée(s) sur ${act}</span></div></div>
    <h3 style="margin:26px 0 14px">Facturation par réservation</h3><div class="card"><div class="bars" style="padding-bottom:22px">${S.resa.slice(0, 10).reverse().map(r => `<div style="height:${+r.total_facture / mx * 100}%" title="${fm(r.total_facture)}"><i>#${r.id_reservation}</i></div>`).join('')}</div></div>`; // barres
  },
  rooms() {                                                                 // plan des chambres
    const ed = ['G', 'H'].includes(U.role);                                 // droit de changer le statut
    return '<div class="grid">' + S.chambres.map(c => `<div class="card room">${art(c.id_type)}<div class="in"><b>Chambre ${c.num_chambre}</b> · étage ${c.etage}<br><small>${esc(c.libelle)} · ${c.capacite} pers. · ${fm(c.prix_nuit_cdf)}/nuit</small><br>${st(c.statut)} ${ed && c.statut != 'occupee' ? `<button class="btn s g" data-a="room" data-n="${c.num_chambre}" data-s="${c.statut == 'libre' ? 'maintenance' : 'libre'}">${c.statut == 'libre' ? 'Mettre en maintenance' : 'Remettre en service'}</button>` : ''}</div></div>`).join('') + '</div>'; // une carte par chambre
  },
  resa() {                                                                  // réservations et paiements
    const w = ['G', 'R'].includes(U.role), p = ['G', 'C'].includes(U.role); // w = réserver, p = encaisser
    return (w ? '<button class="btn" data-a="nr" style="margin-bottom:14px">Nouvelle réservation</button>' : '') + `<table><tr><th>N°</th><th>Client</th><th>Séjour</th><th>Statut</th><th>Facture</th><th>Reste</th><th>Actions</th></tr>${S.resa.map(r => `<tr><td>${r.id_reservation}</td><td>${esc(r.client)}</td><td>${r.date_arrivee} → ${r.date_depart}</td><td>${r.statut}</td><td>${fm(r.total_facture)}</td><td style="color:${+r.reste_a_payer > 0 ? 'var(--bad)' : 'var(--ok)'}">${fm(r.reste_a_payer)}</td><td>${p && +r.reste_a_payer > 0 ? `<button class="btn s" data-a="pay" data-i="${r.id_reservation}" data-r="${r.reste_a_payer}">Encaisser</button> ` : ''}${w ? `<button class="btn s g" data-a="cs" data-i="${r.id_reservation}">+ Service</button> ${r.statut == 'Confirmee' ? `<button class="btn s g" data-a="in" data-i="${r.id_reservation}">Arrivée</button>` : ''}${r.statut == 'En cours' ? `<button class="btn s g" data-a="chk" data-i="${r.id_reservation}">Départ</button>` : ''}` : ''}</td></tr>`).join('')}</table>`; // une ligne par réservation
  },
  cli() {                                                                   // clients
    return '<button class="btn" data-a="nc" style="margin-bottom:14px">Nouveau client</button><table><tr><th>N°</th><th>Nom</th><th>Ville</th><th>Téléphone</th><th>Email</th></tr>' + S.clients.map(c => `<tr><td>${c.id_client}</td><td>${esc(c.nom + ' ' + c.prenom)}</td><td>${esc(c.ville)}</td><td>${esc(c.telephone)}</td><td>${esc(c.email)}</td></tr>`).join('') + '</table>'; // liste
  },
  svc() {                                                                   // services
    return '<table><tr><th>N°</th><th>Service</th><th>Prix</th></tr>' + S.services.map(s => `<tr><td>${s.id_service}</td><td>${esc(s.libelle)}</td><td>${fm(s.prix_cdf)}</td></tr>`).join('') + '</table>'; // liste
  },
  exp() { return '<div id="ex">Chargement…</div>'; }                        // explorateur (rempli par expl)
};
/* 7.6 Affichage et chargement */
async function show(v) {                                                    // affiche une page
  V = v;                                                                    // mémorise la page
  $('#nav').innerHTML = NAV[U.role].map(n => `<div class="nav ${n[0] == v ? 'on' : ''}" data-a="go" data-v="${n[0]}">${n[1]}</div>`).join(''); // menu du rôle
  $('#ttl').textContent = NAV[U.role].find(n => n[0] == v)[1];              // titre
  const e = $('#v'); e.style.animation = 'none'; e.offsetHeight; e.style.animation = ''; // relance l'animation d'entrée
  e.innerHTML = V_[v]();                                                    // construit la page
  e.querySelectorAll('[data-n]').forEach(count);                            // lance les compteurs
  if (v == 'exp') expl('client');                                           // charge l'explorateur
}
async function expl(t) {                                                    // explorateur : affiche la table t
  try {
    const d = await api('explore', {t}), k = Object.keys(d.rows[0] || {});  // données et colonnes
    $('#ex').innerHTML = `<div style="margin-bottom:12px">${d.tables.map(x => `<button class="btn s ${x == t ? '' : 'g'}" data-a="ex" data-t="${x}">${x}</button>`).join(' ')}</div><table><tr>${k.map(c => `<th>${c}</th>`).join('')}</tr>${d.rows.map(r => '<tr>' + k.map(c => `<td>${esc(r[c])}</td>`).join('') + '</tr>').join('')}</table>`; // boutons + tableau
  } catch (e) { toast(e.message, 1); }                                      // erreur
}
async function load() { S = await api('state'); await show(V); }            // recharge les données puis la page
async function enter(u) {                                                   // entre dans l'application
  U = u;                                                                    // utilisateur connecté
  $('#login').style.display = 'none'; $('#app').style.display = 'block';    // change d'écran
  $('#who').textContent = u.nom + ' · ' + u.poste;                          // nom et poste
  V = 'dash';                                                               // page d'accueil
  try { await load(); } catch (e) { toast(e.message, 1); }                  // charge les données
}
/* 7.7 Actions des boutons (data-a="nom") */
const A = {
  go: d => show(d.v),                                                       // changer de page
  x: () => $('#ov').classList.remove('on'),                                 // fermer la fenêtre
  theme: () => { const h = document.documentElement; h.dataset.t = h.dataset.t == 'dark' ? '' : 'dark'; }, // clair / sombre
  sql: () => { const p = $('#sqlp'); p.style.display = p.style.display == 'block' ? 'none' : 'block'; },    // panneau SQL
  out: async () => { await api('logout'); location.reload(); },             // déconnexion
  ex: d => expl(d.t),                                                       // changer de table
  room: d => run('statut', {num: d.n, st: d.s}, 'Statut mis à jour'),       // maintenance / remise en service
  in: d => run('checkin', {id: d.i}, 'Arrivée enregistrée'),                // arrivée
  chk: d => run('checkout', {id: d.i}, 'Départ enregistré, chambres libérées'), // départ
  pay: d => modal('Encaisser (reste ' + fm(d.r) + ')', `<label>Montant (CDF)</label><input name="montant" type="number" value="${d.r}" min="1"><label>Mode</label><select name="mode"><option>Especes</option><option>Mobile money</option><option>Carte</option><option>Virement</option></select>`, f => run('pay', {id: d.i, ...f}, 'Paiement enregistré')), // encaisser
  cs: d => modal('Ajouter un service', `<label>Service</label><select name="service">${S.services.map(s => `<option value="${s.id_service}">${esc(s.libelle)} (${fm(s.prix_cdf)})</option>`).join('')}</select><label>Quantité</label><input name="qte" type="number" value="1" min="1">`, f => run('conso', {id: d.i, ...f}, 'Service ajouté')), // service consommé
  nc: () => modal('Nouveau client', '<label>Nom</label><input name="nom" required><label>Prénom</label><input name="prenom" required><label>Ville</label><input name="ville" required><label>Téléphone</label><input name="tel"><label>Email</label><input name="email" type="email">', f => run('client', f, 'Client ajouté')), // nouveau client
  nr: () => {                                                               // nouvelle réservation
    const td = new Date().toISOString().slice(0, 10), lib = S.chambres.filter(c => c.statut == 'libre'); // date du jour, chambres libres
    modal('Nouvelle réservation', `<label>Client</label><select name="client">${S.clients.map(c => `<option value="${c.id_client}">${esc(c.nom + ' ' + c.prenom)}</option>`).join('')}</select><label>Arrivée</label><input name="arrivee" type="date" value="${td}" required><label>Départ</label><input name="depart" type="date" required><label>Chambres libres</label>${lib.map(c => `<div class="chk"><input type="checkbox" name="ch${c.num_chambre}" value="${c.num_chambre}"> N°${c.num_chambre} · ${esc(c.libelle)} · ${fm(c.prix_nuit_cdf)}/nuit</div>`).join('') || '<p>Aucune chambre libre.</p>'}`, f => {
      const ch = Object.keys(f).filter(k => k.startsWith('ch')).map(k => +f[k]); // numéros cochés
      run('resa', {client: f.client, arrivee: f.arrivee, depart: f.depart, chambres: ch}, 'Réservation créée'); // enregistre
    });
  }
};
/* 7.8 Démarrage : clics, connexion, installation, session existante */
document.addEventListener('click', e => { const b = e.target.closest('[data-a]'); if (b && A[b.dataset.a]) A[b.dataset.a](b.dataset); }); // un seul écouteur pour tous les boutons
$('#go').onclick = async () => { try { enter(await api('login', {u: $('#u').value, p: $('#p').value})); } catch (e) { toast(e.message, 1); } }; // connexion
$('#p').onkeydown = e => { if (e.key == 'Enter') $('#go').click(); };       // Entrée valide
$('#inst').onclick = async e => { e.preventDefault(); try { toast(await api('install')); } catch (x) { toast(x.message, 1); } }; // installation
api('me').then(u => u && enter(u)).catch(() => {});                         // reconnexion automatique si la session existe
</script></body></html>
