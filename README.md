# 🔐 Projet CI/CD Sécurisé — Jenkins + Harbor + Docker

> **Sécurisation de la Supply Chain Logicielle**  
> Pipeline CI/CD DevSecOps complet avec Jenkins, Docker et Harbor

---

## 📋 Table des matières

- [Architecture](#architecture)
- [Prérequis](#prérequis)
- [Installation et Configuration](#installation-et-configuration)
- [Structure du projet](#structure-du-projet)
- [Pipeline Jenkins — 7 Stages](#pipeline-jenkins--7-stages)
- [Gestion des secrets Jenkins](#gestion-des-secrets-jenkins)
- [Harbor — Configuration sécurisée](#harbor--configuration-sécurisée)
- [Lancer les tests](#lancer-les-tests)
- [Déploiement local](#déploiement-local)
- [Documentation](#documentation)

---

## Architecture

```
Développeur (git push)
        │
        ▼
  Jenkins Pipeline
  ┌─────────────────────────────────────────────────────────┐
  │  Stage 1 │ SAST + Secrets Scan (Bandit/Semgrep/Gitleaks)│
  │  Stage 2 │ Build Docker Image (multi-stage, non-root)   │
  │  Stage 3 │ Scan Dépendances + Conteneur (OWASP / Trivy) │
  │  Stage 4 │ Signature Image (Cosign)                     │
  │  Stage 5 │ Push vers Harbor (registre privé)            │
  │  Stage 6 │ Vérification Politique Harbor (API)          │
  │  Stage 7 │ Déploiement Docker Compose (SSH)             │
  └─────────────────────────────────────────────────────────┘
        │
        ▼
  Harbor Registry ──► Serveur de déploiement
  (scan + RBAC)        (Docker Compose + Monitoring)
```

---

## Prérequis

| Composant | Version minimale | Installation |
|-----------|-----------------|--------------|
| Jenkins | LTS 2.460 | [jenkins.io](https://jenkins.io) |
| Docker | 25.0 | `apt install docker.io` |
| Docker Compose | v2.24 | Inclus avec Docker Desktop |
| Harbor | 2.10 | [goharbor.io](https://goharbor.io) |
| Python | 3.11 | `apt install python3.11` |

### Plugins Jenkins requis
```
- Pipeline
- Pipeline: Stage View
- Git
- Credentials Binding
- SSH Agent
- HTML Publisher
- AnsiColor (recommandé)
- Blue Ocean (recommandé pour l'UI)
```

---

## Installation et Configuration

### 1. Cloner le dépôt
```bash
git clone https://github.com/mon-org/devsecops-project.git
cd devsecops-project
```

### 2. Configurer les credentials Jenkins

Aller dans **Jenkins → Manage Jenkins → Credentials → System → Global credentials**
et créer les secrets suivants :

| ID Jenkins | Type | Description |
|------------|------|-------------|
| `HARBOR_URL` | Secret text | URL de Harbor (ex: `harbor.mondomaine.com`) |
| `HARBOR_CREDENTIALS` | Username/Password | Login Harbor |
| `COSIGN_PRIVATE_KEY` | Secret file | Clé privée Cosign (`cosign.key`) |
| `COSIGN_PASSWORD` | Secret text | Mot de passe de la clé Cosign |
| `NVD_API_KEY` | Secret text | Clé API NVD pour OWASP DC |
| `DEPLOY_SSH_KEY` | SSH private key | Clé SSH pour le serveur de déploiement |
| `DEPLOY_HOST` | Secret text | IP/hostname du serveur de déploiement |

### 3. Générer la paire de clés Cosign
```bash
# Installer Cosign
wget https://github.com/sigstore/cosign/releases/download/v2.2.3/cosign-linux-amd64
chmod +x cosign-linux-amd64 && sudo mv cosign-linux-amd64 /usr/local/bin/cosign

# Générer les clés
export COSIGN_PASSWORD="votre-mot-de-passe-fort"
cosign generate-key-pair

# cosign.key → à uploader dans Jenkins Credentials (ID: COSIGN_PRIVATE_KEY)
# cosign.pub → à copier sur le serveur de déploiement (/opt/devsecops/cosign.pub)
```

### 4. Configurer Harbor
```bash
# 1. Créer un projet privé "devsecops"
# 2. Activer le scan automatique à chaque push
# 3. Activer Content Trust (signature)
# 4. Configurer la politique : bloquer les images avec CVE Critical
# 5. Créer un robot account avec push/pull access
```

### 5. Créer le pipeline Jenkins
1. **New Item** → **Pipeline**
2. Nom : `devsecops-pipeline`
3. **Pipeline** → **Definition** : `Pipeline script from SCM`
4. **SCM** : Git → URL de votre dépôt
5. **Script Path** : `Jenkinsfile`
6. **Save** → **Build Now**

---

## Structure du projet

```
.
├── Jenkinsfile                     ← Pipeline CI/CD Jenkins (7 stages)
├── README.md
├── requirements.txt
├── docker-compose.yml              ← Déploiement production sécurisé
│
├── src/
│   ├── app.py                      ← Application FastAPI principale
│   └── utils.py                    ← Fonctions utilitaires + validation
│
├── tests/
│   └── test_app.py                 ← Tests unitaires et d'intégration
│
├── docker/
│   └── Dockerfile                  ← Image multi-stage sécurisée
│
├── scripts/
│   ├── scan.sh                     ← Scan Trivy
│   ├── sign.sh                     ← Signature Cosign
│   └── verify.sh                   ← Vérification signature (déploiement)
│
└── docs/
    ├── cahier_des_charges.md       ← Spécifications du projet
    ├── analyse_risques.md          ← Analyse STRIDE + conformité OWASP
    └── rapport_final.md            ← Rapport de fin de projet
```

---

## Pipeline Jenkins — 7 Stages

| Stage | Outils | Ce que ça fait | Bloquant si échec |
|-------|--------|----------------|:-----------------:|
| **1 - SAST & Secrets** | Bandit, Semgrep, Gitleaks | Analyse statique du code source et détection de secrets | ❌ |
| **2 - Build** | Docker | Construction de l'image multi-stage | ✅ |
| **3 - Scan** | OWASP DC, Trivy | Scan des dépendances et de l'image pour les CVE | ✅ (CRITICAL) |
| **4 - Signature** | Cosign | Signature cryptographique de l'image | ✅ |
| **5 - Push Harbor** | Docker, Harbor | Push de l'image signée dans le registre privé | ✅ |
| **6 - Politique Harbor** | Harbor API | Vérification que l'image respecte les politiques de sécurité | ✅ |
| **7 - Déploiement** | SSH, Docker Compose | Déploiement sur le serveur distant (branch `main` seulement) | ✅ |

---

## Gestion des secrets Jenkins

> ⚠️ **Aucun secret ne doit apparaître dans le code source.**

Les secrets sont injectés au moment du build via Jenkins Credentials :
```groovy
// Dans le Jenkinsfile
withCredentials([
    usernamePassword(credentialsId: 'HARBOR_CREDENTIALS', ...),
    file(credentialsId: 'COSIGN_PRIVATE_KEY', variable: 'COSIGN_KEY'),
    string(credentialsId: 'NVD_API_KEY', variable: 'NVD_API_KEY'),
])
```

---

## Harbor — Configuration sécurisée

```
Harbor → Projects → devsecops → Configuration
  ✅ Access Level        : Private
  ✅ Automatically scan  : ON (scan on push)
  ✅ Prevent vulnerable  : ON (block if CRITICAL)
  ✅ Content Trust       : ON (require signed images)
```

---

## Lancer les tests

```bash
# Installer les dépendances
pip install -r requirements.txt

# Lancer les tests avec couverture
pytest tests/ -v --cov=src --cov-report=term-missing --cov-report=xml

# Rapport HTML
pytest tests/ --html=reports/test-report.html
```

---

## Déploiement local

```bash
# Copier le fichier d'environnement
cp .env.example .env
# Éditer les variables dans .env

# Construire l'image
docker build -f docker/Dockerfile -t fastapi-app:local .

# Démarrer les services
docker compose up -d

# Vérifier
docker compose ps
curl http://localhost:8000/health
```

---

## Documentation

| Document | Description |
|----------|-------------|
| [Cahier des charges](docs/cahier_des_charges.md) | Objectifs, exigences, architecture |
| [Analyse des risques](docs/analyse_risques.md) | STRIDE + conformité OWASP CI/CD Top 10 |
| [Rapport final](docs/rapport_final.md) | Bilan du projet, résultats, métriques |

---

## Auteurs

Projet encadré par **M. Bonitah RAMBELOSON**  
Consultant DevOps | Cloud Engineer | MLOps Practitioner

---

> 💡 **Note** : Ce projet utilise **Jenkins** à la place de GitLab CI/CD, conformément aux besoins spécifiques de l'équipe. L'équivalence des stages est documentée dans le Jenkinsfile.
