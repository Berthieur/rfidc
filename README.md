# RFID Door Platform

Plateforme web de gestion de contrôle d'accès RFID, construite avec **FastAPI**, **Jinja2**, **SQLAlchemy** et **MySQL**, avec intégration d'appareils **ESP32** pour la lecture des badges RFID.

## Objectif du projet

Cette application permet de :

- gérer les utilisateurs autorisés
- gérer les cartes RFID
- gérer les affectations carte ↔ utilisateur
- gérer les appareils ESP32
- enregistrer l'historique des accès
- superviser l'activité depuis un dashboard
- capturer automatiquement l'UID d'une carte RFID depuis un capteur ESP32 pendant l'inscription d'une nouvelle carte

---

## Fonctionnalités principales

### 1. Authentification back-office
- connexion par session
- rôles :
  - **admin**
  - **agent**
- middleware de redirection vers `/login` pour les routes web protégées
- redirection automatique vers `/dashboard` si un utilisateur connecté tente d'ouvrir `/login`

### 2. Gestion des utilisateurs autorisés
- création
- modification
- suppression logique
- filtres
- pagination
- validation :
  - email unique
  - téléphone unique
  - téléphone au format international (`+` suivi de chiffres)
  - genre obligatoire (`Homme` / `Femme`)
- dates par défaut :
  - `valid_from` = maintenant
  - `valid_until` = maintenant + 1 an

### 3. Gestion des cartes RFID
- création
- modification
- consultation
- filtres
- pagination
- UID unique
- capture UID depuis ESP32 pendant l'inscription

### 4. Gestion des affectations RFID
- création d'une affectation carte ↔ utilisateur
- consultation détaillée
- actions métier :
  - `active`
  - `expired`
  - `unassigned`
  - `revoked`
- logique métier historique :
  - une affectation n'est pas modifiée structurellement
  - on clôture l'ancienne puis on crée une nouvelle si nécessaire
- dates par défaut :
  - `assigned_at` = maintenant
  - `expired_at` = maintenant + 1 an

### 5. Gestion des appareils
- création
- modification
- consultation
- régénération du token API
- activation / désactivation

### 6. Historique d'accès
- enregistrement des scans RFID
- statuts d'accès :
  - `granted`
  - `denied`
  - `ignored`
- direction :
  - `entry`
  - `exit`
  - `unknown`
- filtres
- pagination
- consultation du détail

### 7. Dashboard métier
- KPI d'activité du jour
- KPI métier
- alertes
- derniers événements
- derniers refus
- navigation rapide vers les modules

### 8. Intégration ESP32
- endpoint accès normal
- endpoint dédié d'enrôlement RFID
- lecture UID pendant 15 secondes max lors de la création d'une carte
- remplissage automatique du champ UID dans le formulaire

---

## Stack technique

### Backend
- FastAPI
- SQLAlchemy
- Pydantic
- Jinja2
- Starlette SessionMiddleware
- PyMySQL
- Alembic

### Frontend
- Jinja2 Templates
- Bootstrap 5
- CSS personnalisé
- JavaScript vanilla

### Base de données
- MySQL

### Appareils
- ESP32
- lecteur RFID

---

## Architecture du projet

```text
app/
├── api/
│   ├── routes/
│   │   ├── auth.py
│   │   ├── dashboard.py
│   │   ├── authorized_users.py
│   │   ├── rfid_cards.py
│   │   ├── assignments.py
│   │   ├── devices.py
│   │   └── access_logs.py
│   └── esp32/
│       ├── access.py
│       └── enrollment.py
├── core/
│   ├── config.py
│   ├── database.py
│   ├── dependencies.py
│   └── security.py
├── crud/
├── middleware/
│   └── auth_redirect.py
├── models/
├── schemas/
├── seeders/
├── services/
├── static/
│   ├── css/
│   │   └── app.css
│   └── js/
│       └── app.js
└── templates/
```

---

## Types d'acteurs

### Staff users
Comptes qui accèdent au back-office :

- **admin**
- **agent**

### Authorized users
Personnes autorisées à utiliser une carte RFID pour franchir la porte.

### Devices
Appareils physiques ESP32 enregistrés dans la plateforme.

---

## Logique métier importante

### Différence entre `authorized_users` et `rfid_assignments`
Les dates de validité utilisateur et les dates d'affectation ne représentent pas la même chose :

- `authorized_users.valid_from / valid_until` : période d'autorisation de la personne
- `rfid_assignments.assigned_at / expired_at / unassigned_at` : vie de la liaison entre la carte et l'utilisateur

### Différence entre `unassigned`, `revoked`, `expired`
- **unassigned** : retrait normal de l'affectation
- **revoked** : retrait fort / décision administrative ou sécurité
- **expired** : affectation arrivée à échéance

### Réutilisation d'une carte
Une carte peut redevenir réutilisable si son ancienne affectation est :

- `expired`
- `unassigned`
- `revoked`

---

## Sécurité actuelle

### Déjà en place
- protection des routes web via session
- gestion des rôles admin / agent
- contraintes d'unicité en base
- validation Pydantic
- ORM SQLAlchemy pour limiter les risques d'injection SQL
- tokens API hashés pour les appareils

### À renforcer plus tard
- protection CSRF sur tous les formulaires web
- sécurisation production des cookies de session
- audit sécurité global
- journalisation sécurité plus avancée

---

## Responsive design

L'interface a été améliorée pour être utilisable sur :

- desktop
- tablette
- mobile

Éléments améliorés :
- sidebar desktop
- menu mobile offcanvas
- dashboard responsive
- formulaires
- pages détail
- tableaux scrollables
- page login harmonisée avec le reste de l'application

---

## Installation

### 1. Cloner le projet
```bash
git clone <repo_url>
cd rfid-door-platform
```

### 2. Créer l'environnement virtuel
```bash
python -m venv .venv
source .venv/bin/activate
```

### 3. Installer les dépendances
```bash
pip install -r requirements.txt
```

### 4. Configurer les variables d'environnement
Créer un fichier `.env` avec au minimum :

```env
APP_NAME=RFID Door Platform
APP_DEBUG=true
SECRET_KEY=change-this-secret-key

DB_HOST=127.0.0.1
DB_PORT=3306
DB_NAME=rfid_door_platform
DB_USER=root
DB_PASSWORD=your_password
```

### 5. Appliquer les migrations
```bash
alembic upgrade head
```

### 6. Lancer l'application
```bash
uvicorn app.main:app --reload
```

### 7. Ouvrir dans le navigateur
```text
http://127.0.0.1:8000
```

---

## Seeders

Des seeders existent pour alimenter le projet avec des données variées.

### Lancer tous les seeders
```bash
python -m app.seeders.run_all
```

### Données générées
- rôles
- admin
- agent
- utilisateurs autorisés
- cartes RFID
- appareils
- affectations
- logs d'accès

### Comptes de test
- **Admin**
  - email : `admin@rfid.local`
  - mot de passe : `admin1234`

- **Agent**
  - email : `agent@rfid.local`
  - mot de passe : `agent1234`

---

## Endpoints importants

### Web
- `/login`
- `/logout`
- `/dashboard`
- `/authorized-users`
- `/rfid-cards`
- `/assignments`
- `/devices`
- `/access-logs`

### ESP32 accès normal
Exemple :
```bash
curl -X POST "http://127.0.0.1:8000/api/esp32/access" \
  -H "Content-Type: application/json" \
  -H "X-API-Token: token_main_door_123" \
  -d '{
    "device_code": "ESP32_MAIN_DOOR",
    "uid": "A1B2C3D4",
    "direction": "entry"
  }'
```

### ESP32 enrôlement UID
Exemple :
```bash
curl -X POST "http://127.0.0.1:8000/api/esp32/enrollment/scan" \
  -H "Content-Type: application/json" \
  -H "X-API-Token: token_main_door_123" \
  -d '{
    "device_code": "ESP32_MAIN_DOOR",
    "uid": "A1B2C3D4"
  }'
```

---

## Flux d'inscription UID via capteur

1. L'admin ouvre **Créer une carte RFID**
2. L'admin clique sur **Lire depuis le capteur**
3. L'application démarre une fenêtre d'attente de **15 secondes**
4. L'ESP32 lit le badge et envoie l'UID à l'endpoint dédié
5. Le champ UID est rempli automatiquement
6. En cas de succès :
   - le champ devient vert
   - le champ est désactivé
   - après 4 secondes, l'interface revient à l'état initial pour un nouveau scan possible
7. En cas d'échec :
   - message d'échec affiché
   - nouveau scan possible

---

## UX / règles d'interface mises en place

- liens dynamiques via `url_for`
- suppression des `id` techniques sur le front
- filtres et pagination harmonisés
- messages d'erreur mieux remontés
- login partagé avec le même layout de base
- footer commun
- page login sans navbar

---

## Ce qui a été stabilisé

- authentification par session
- redirections login/logout
- middleware de protection web
- gestion des rôles
- CRUD utilisateurs autorisés
- CRUD cartes RFID
- affectations métier
- CRUD devices
- access logs
- dashboard KPI
- seeders de volume
- responsive global
- lecture UID par capteur
- validations métiers principales

---

## Améliorations futures recommandées

- protection CSRF complète
- messages flash uniformisés
- traduction plus complète des statuts en français côté interface
- module de gestion des `staff_users`
- amélioration des confirmations d'actions sensibles
- amélioration finale UI / navigation
- tests fonctionnels complets automatisés
- persistance distribuée de la capture UID (Redis/DB) si multi-instances
- système d'audit plus poussé

---

## Philosophie du projet

Le projet a été construit avec une logique claire :

- préserver l'historique
- séparer les responsabilités métier
- privilégier une interface exploitable par un administrateur
- sécuriser progressivement
- rendre l'application maintenable et extensible

---

## Auteur / contexte

Projet développé dans le cadre d'une plateforme de contrôle d'accès RFID avec :

- interface web FastAPI
- appareils ESP32
- lecture RFID
- gestion métier des accès

---
