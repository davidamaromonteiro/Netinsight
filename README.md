# NetInsight — Plateforme d'analyse de sécurité réseau

![Version](https://img.shields.io/badge/version-0.3.0-blue)
![Licence](https://img.shields.io/badge/licence-MIT-green)
![Docker](https://img.shields.io/badge/docker-ready-brightgreen)

**NetInsight** est une plateforme de sécurité réseau conteneurisée permettant d'orchestrer des campagnes de scan, d'analyser les hôtes et services exposés, de détecter des vulnérabilités (CVE, SQL injection, failles web), et de produire des rapports de sécurité complets avec **MITRE ATT&CK** et **Cyber Kill Chain**.

---

## Objectif du projet

Fournir un environnement **isolé et reproductible** pour l'analyse de sécurité :
- Scan réseau automatisé (Nmap)
- Détection de services et banner grabbing
- Recherche de vulnérabilités (CVE/NVD, SQLmap, Nikto)
- Mapping des techniques adverses (MITRE ATT&CK)
- Analyse du cycle d'attaque (Cyber Kill Chain)
- Génération de rapports PDF détaillés
- Cible vulnérable intégrée pour tests (ACME Store)

---

## Prérequis

- **Docker** ≥ 24.0 et **Docker Compose** ≥ 2.20
- 4 Go RAM disponible
- Ports disponibles : `80`, `8000`, `8080`

---

## Installation (2 commandes)

```bash
git clone https://github.com/davidamaromonteiro/Netinsight.git
cd Netinsight && ./setup.sh
```

Le script `setup.sh` :
1. Vérifie Docker et Docker Compose
2. Crée le fichier `.env` avec une clé secrète aléatoire
3. Construit les images Docker
4. Lance tous les services
5. Seed la base de données avec des données de test
6. Affiche les URLs d'accès

---

## Services Docker

| Service | Image | Port | Rôle |
|---------|-------|------|------|
| `mongodb` | `mongo:7` | `27017` | Base de données NoSQL |
| `redis` | `redis:7-alpine` | `6379` | Broker Celery + cache |
| `backend` | `python:3.12-slim` | `8000` | API FastAPI |
| `celery-worker` | `python:3.12-slim` | — | Tâches async (Nmap, SQLmap, Nikto, PDF) |
| `frontend` | `nginx:alpine` | `80` | Interface Svelte 5 |
| `acme-mysql` | `mysql:8.0` | `3306` (interne) | Base cible vulnérable |
| `acme-store` | `php:8.2-apache` | `8080` | App web vulnérable (SQLi) |

### Commandes Docker utiles

```bash
docker compose up -d              # Démarrer
docker compose down               # Arrêter
docker compose logs -f backend    # Logs API
docker compose restart celery-worker  # Redémarrer les workers
docker compose ps                 # Statut des conteneurs
```

---

## Dépendances

### Backend (Python 3.12)
```
fastapi, uvicorn, pydantic, beanie, motor, celery, redis,
python-nmap, reportlab, slowapi, bcrypt, pyjwt, httpx
```

### Frontend (Node 22)
```
svelte 5, vite 6, tailwindcss 4, chart.js 4
```

### Outils système (intégrés dans l'image Docker)
```
nmap, nikto, sqlmap, perl (libwww, libjson, libxml-writer, libio-socket-ssl)
```

---

## Procédure de test

### 1. Vérifier que tout est lancé
```bash
docker compose ps
# Tous les services doivent être "healthy" ou "Up"
```

### 2. Accéder à l'interface
```
http://localhost
Login : admin@netinsight.io / Admin123!
```

### 3. Tester un scan Nmap
1. Onglet **Campagnes** → **+ Nouvelle campagne**
2. Remplir : Nom, Cible (ex: `scanme.nmap.org`)
3. Cliquer sur la campagne → **Démarrer le scan**
4. Voir les résultats dans **Hôtes** (ports, services, OS)

### 4. Tester SQLmap sur l'ACME Store
```bash
# Depuis le terminal
sqlmap -u "http://localhost:8080/product.php?id=1" --dbs --batch

# Ou via l'interface
# Onglet SQLMap → + Nouveau scan → URL: http://acme-store/product.php?id=1
```

### 5. Tester Nikto
```bash
# Onglet Nikto → + Nouveau scan → Host: acme-store, Port: 80
```

### 6. Générer un rapport PDF
1. Onglet **Campagnes** → cliquer sur une campagne complétée
2. Bouton **Générer le rapport**
3. Télécharger le PDF (MITRE ATT&CK + Cyber Kill Chain)

### 7. Tester l'ACME Store (cible vulnérable)
```
http://localhost:8080
```
Injection SQL sur :
- `product.php?id=1` (SQLi numérique)
- `index.php?category=Widgets` (SQLi string)
- `login.php` (POST, bypass auth)

---

## Résultats attendus

### Dashboard
- Statistiques agrégées : campagnes, hôtes, ports ouverts, vulnérabilités par sévérité
- Graphiques Chart.js (distribution sévérité, statut campagnes)
- Taux de succès des tests d'authentification

### Scan Nmap
- Hôtes découverts avec IP, hostname, OS, MAC
- Ports ouverts avec service, version, état
- Banner grabbing automatique sur les ports ouverts
- Enrichissement CVE via NVD + MITRE ATT&CK

### SQLmap
- Détection automatique des injections SQL (boolean, error, time, UNION)
- DBMS identifié automatiquement
- Dump des tables et données (utilisateurs, mots de passe, secrets)

### Nikto
- Scan de vulnérabilités web (OSVDB, CVE)
- En-têtes HTTP intéressants
- Fichiers et répertoires exposés

### Rapport PDF
- Résumé exécutif avec niveau de risque global
- Surface d'attaque (hôtes, ports, services, bannières)
- Vulnérabilités CVE détaillées (ID, CVSS, sévérité, description)
- **Mapping MITRE ATT&CK** : techniques automatiquement mappées depuis les services
- **Cyber Kill Chain** complète (7 phases) avec preuves concrètes
- Preuves d'exploitation (SQLmap, mots de passe faibles)
- Recommandations priorisées (Critical → Low)

---

## Architecture

```
┌──────────────┐     ┌──────────────┐     ┌───────────┐
│  Svelte 5    │────▶│  FastAPI      │────▶│ MongoDB 7 │
│  (Nginx:80)  │     │  (Uvicorn)    │     └───────────┘
└──────────────┘     │               │     ┌───────────┐
                     │  Celery       │────▶│  Redis 7  │
                     │  Workers      │     └───────────┘
                     └──────────────┘
                            │
          ┌─────────────────┼─────────────────┐
          ▼                 ▼                  ▼
     ┌─────────┐     ┌──────────┐      ┌───────────┐
     │  Nmap   │     │  SQLmap  │      │   Nikto   │
     │  Banner │     │  (ACME)  │      │  (Web)    │
     └─────────┘     └──────────┘      └───────────┘
          │                 │                  │
          ▼                 ▼                  ▼
     ┌─────────────────────────────────────────────┐
     │         ACME Store (cible test)             │
     │         PHP 8.2 + MySQL 8.0                 │
     │         http://localhost:8080               │
     └─────────────────────────────────────────────┘
```

---

## Stack technique

| Couche | Technologie |
|--------|-------------|
| Backend API | FastAPI (Python 3.12) |
| Base de données | MongoDB 7 (ODM Beanie) |
| Cache / Broker | Redis 7 (Celery) |
| Tâches async | Celery 5.4 |
| Scan réseau | python-nmap |
| Scan SQL | sqlmap |
| Scan web | Nikto 2.6 |
| Rapports PDF | ReportLab |
| Frontend | Svelte 5 + Vite 6 |
| CSS | Tailwind CSS 4 |
| Graphiques | Chart.js 4 |
| Reverse proxy | Nginx (Alpine) |
| Conteneurisation | Docker + Docker Compose |

---

## Licence

MIT — voir le fichier [LICENSE](LICENSE).
