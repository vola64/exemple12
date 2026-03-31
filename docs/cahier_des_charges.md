# Cahier des Charges — Pipeline CI/CD Sécurisé
## Projet : Sécurisation de la Supply Chain Logicielle

---

## 1. Contexte et Problématique

Les attaques sur la supply chain logicielle (SolarWinds 2020, Log4Shell 2021, Docker Hub Poisoning) ont démontré que la sécurité d'un logiciel ne se limite pas à son code source. Chaque étape — du commit au déploiement — peut être compromise.

Ce projet met en œuvre une chaîne CI/CD **end-to-end sécurisée** en s'appuyant sur :
- **Jenkins** pour l'orchestration du pipeline (remplaçant GitLab CI)
- **Harbor** comme registre privé sécurisé
- **Docker / Docker Compose** pour la conteneurisation
- **Cosign** pour la signature et la vérification d'images

---

## 2. Périmètre et Objectifs

### 2.1 Objectifs principaux
| # | Objectif | Priorité |
|---|----------|----------|
| O1 | Pipeline Jenkins automatisé couvrant build → test → scan → sign → deploy | Critique |
| O2 | Détection de secrets et vulnérabilités avant tout push d'image | Critique |
| O3 | Signature cryptographique des images (Cosign) | Haute |
| O4 | Vérification d'intégrité avant tout déploiement | Haute |
| O5 | Monitoring sécurité (Prometheus + Grafana) | Moyenne |
| O6 | Conformité OWASP Top 10 | Haute |

### 2.2 Hors périmètre
- Authentification SSO/LDAP (Jenkins / Harbor)
- Multi-cluster Kubernetes (hors Docker Compose)
- Gestion des licences logicielles

---

## 3. Architecture Fonctionnelle

```
Développeur
    │  git push
    ▼
Jenkins Pipeline
    ├── Stage 1 : SAST + Secrets Scan (Bandit / Semgrep / Gitleaks)
    ├── Stage 2 : Build Docker Image (multi-stage, non-root)
    ├── Stage 3 : Scan Dépendances + Conteneur (OWASP / Trivy)
    ├── Stage 4 : Signature Image (Cosign)
    ├── Stage 5 : Push Harbor (registre privé)
    ├── Stage 6 : Vérification Politique Harbor (API scan)
    └── Stage 7 : Déploiement Docker Compose (serveur distant, SSH)

Harbor ←─ registre privé + scan Trivy/Clair + RBAC + Content Trust
Serveur ←─ Docker Compose + Prometheus + Grafana
```

---

## 4. Exigences de Sécurité

### 4.1 Gestion des secrets
- **Aucun secret** ne doit être présent dans le code source (Gitleaks)
- Tous les secrets Jenkins sont stockés dans **Jenkins Credentials Store**
- Les variables d'environnement sensibles sont injectées uniquement au runtime
- Le fichier `.env` n'est **jamais** commité (listé dans `.gitignore`)

### 4.2 Image Docker
- Base : `python:3.11-slim` (surface d'attaque minimale)
- Build multi-stage (dépendances séparées du runtime)
- Utilisateur non-root (`appuser:appgroup`, UID 1001)
- Filesystem `read_only: true` en production
- Capabilities Linux réduites (`cap_drop: ALL`)
- Health check intégré

### 4.3 Pipeline Jenkins
- Timeout global : 60 minutes
- Builds concurrents désactivés
- Archivage de tous les rapports de sécurité
- Blocage du pipeline si vulnérabilité CRITICAL détectée

### 4.4 Harbor
- Authentification obligatoire (RBAC)
- Scan automatique à chaque push
- Content Trust activé (vérification de signature)
- Politique de rétention des images ancienne (> 30 tags)
- Vulnérabilités CRITICAL → refus de pull

---

## 5. Outils et Versions

| Outil | Rôle | Version cible |
|-------|------|---------------|
| Jenkins | Orchestration CI/CD | LTS 2.460+ |
| Harbor | Registre privé | 2.10+ |
| Docker | Conteneurisation | 25+ |
| Docker Compose | Déploiement | v2.24+ |
| Trivy | Scan image/dépendances | 0.50+ |
| Cosign | Signature d'images | 2.2+ |
| Bandit | SAST Python | 1.7+ |
| Semgrep | SAST multi-langage | 1.70+ |
| Gitleaks | Détection secrets | 8.18+ |
| OWASP DC | Scan CVE dépendances | 9.0+ |
| Python | Langage applicatif | 3.11 |
| FastAPI | Framework web | 0.111+ |
| Prometheus | Métriques | 2.51+ |
| Grafana | Dashboards | 10.4+ |

---

## 6. Critères d'Acceptation

| Critère | Condition de validation |
|---------|------------------------|
| Pipeline complet | Toutes les 7 stages s'exécutent sans erreur |
| Aucun secret exposé | Gitleaks ne retourne aucune détection sur `main` |
| Zéro CVE CRITICAL | Trivy et Harbor ne bloquent pas le build |
| Image signée | `cosign verify` retourne 0 sur l'image déployée |
| Déploiement automatisé | `docker compose ps` montre tous les services `Up` |
| Rapports générés | Tous les fichiers `reports/*.json` sont archivés |
