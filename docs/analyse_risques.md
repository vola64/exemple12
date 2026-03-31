# Analyse des Risques — Modèle STRIDE
## Pipeline CI/CD Sécurisé : Jenkins + Harbor + Docker

---

## 1. Introduction

L'analyse STRIDE (Spoofing, Tampering, Repudiation, Information Disclosure, Denial of Service, Elevation of Privilege) est appliquée à chaque composant du pipeline pour identifier et mitiguer les menaces.

---

## 2. Tableau STRIDE — Composants du Pipeline

### 2.1 Jenkins (Orchestrateur CI/CD)

| Menace | Description | Sévérité | Mitigation mise en place |
|--------|-------------|----------|--------------------------|
| **S** Spoofing | Un attaquant usurpe l'identité d'un développeur pour déclencher un build malveillant | Haute | Authentification Jenkins obligatoire + MFA recommandé |
| **T** Tampering | Modification du `Jenkinsfile` dans la branche pour injecter des commandes | Haute | Protections de branche (`main` protégée), revue de code obligatoire |
| **R** Repudiation | Impossible de tracer qui a déclenché un build | Moyenne | Audit logs Jenkins activés, `BUILD_USER` enregistré |
| **I** Info Disclosure | Les secrets Jenkins apparaissent dans les logs de build | Critique | Jenkins masque automatiquement les credentials, `set +x` dans les scripts |
| **D** DoS | Flood de builds bloquant les agents Jenkins | Moyenne | `disableConcurrentBuilds()`, timeout global 60 min |
| **E** Elevation | Un plugin Jenkins compromis obtient un accès root sur l'agent | Haute | Agents Jenkins sans root, Docker socket limité, plugins auditésrégulièrement |

### 2.2 Dépôt Source (Git)

| Menace | Description | Sévérité | Mitigation |
|--------|-------------|----------|------------|
| **S** Spoofing | Push de commits avec une identité falsifiée | Haute | Signature GPG des commits recommandée |
| **T** Tampering | Injection de code malveillant dans `src/` ou `Dockerfile` | Critique | SAST (Bandit, Semgrep) à chaque commit + revue obligatoire |
| **I** Info Disclosure | Secrets commités par erreur (tokens, mots de passe) | Critique | Gitleaks en pre-commit hook ET dans le pipeline |
| **T** Tampering | Modification de `requirements.txt` pour introduire une dépendance malveillante | Haute | OWASP Dependency Check + pinning des versions |

### 2.3 Image Docker (Build & Distribution)

| Menace | Description | Sévérité | Mitigation |
|--------|-------------|----------|------------|
| **T** Tampering | Image modifiée après le build (man-in-the-middle) | Critique | Signature Cosign + vérification avant déploiement |
| **S** Spoofing | Image malveillante avec le même nom poussée sur Harbor | Critique | Harbor Content Trust activé, RBAC strict |
| **I** Info Disclosure | Image contient des données sensibles (fichiers .env dans les layers) | Haute | Build multi-stage, `.dockerignore` complet |
| **E** Elevation | Container s'exécute en root → compromission host | Haute | Utilisateur non-root (UID 1001), `cap_drop: ALL`, `no-new-privileges` |
| **T** Tampering | Dépendances avec CVE connues dans l'image de base | Haute | `apt-get upgrade -y` dans Dockerfile + Trivy scan |

### 2.4 Harbor (Registre)

| Menace | Description | Sévérité | Mitigation |
|--------|-------------|----------|------------|
| **S** Spoofing | Accès non authentifié au registre | Haute | Harbor public access désactivé, RBAC par projet |
| **I** Info Disclosure | Images propriétaires accessibles publiquement | Haute | Projet Harbor privé, rotation des tokens d'accès |
| **D** DoS | Saturation du stockage Harbor | Moyenne | Politique de rétention (max 30 tags), alertes disque |
| **T** Tampering | Remplacement d'une image signée par une non-signée | Critique | Content Trust = refus de pull si non signé |

### 2.5 Déploiement (Docker Compose / SSH)

| Menace | Description | Sévérité | Mitigation |
|--------|-------------|----------|------------|
| **S** Spoofing | Accès SSH non autorisé au serveur de déploiement | Critique | Clé SSH dédiée Jenkins (sans passphrase, scope limité), `authorized_keys` strict |
| **T** Tampering | `docker-compose.yml` modifié sur le serveur | Haute | Déploiement via pipeline uniquement + vérification hash |
| **E** Elevation | Container avec accès au socket Docker → escape | Critique | Pas de socket Docker monté dans les containers applicatifs |
| **I** Info Disclosure | Variables d'environnement exposées dans `docker inspect` | Moyenne | Secrets via Docker Secrets ou fichiers montés en tmpfs |

---

## 3. Conformité OWASP Top 10 CI/CD Risks

| OWASP Risk | Description | Statut |
|------------|-------------|--------|
| CICD-SEC-1 | Insufficient Flow Control Mechanisms | ✅ Protections de branche + approvals |
| CICD-SEC-2 | Inadequate Identity and Access Management | ✅ RBAC Jenkins + Harbor |
| CICD-SEC-3 | Dependency Chain Abuse | ✅ OWASP DC + Trivy |
| CICD-SEC-4 | Poisoned Pipeline Execution (PPE) | ✅ Jenkinsfile protégé, builds isolés |
| CICD-SEC-5 | Insufficient PBAC (Pipeline-Based Access Control) | ✅ Credentials Jenkins scoped |
| CICD-SEC-6 | Insufficient Credential Hygiene | ✅ Gitleaks + Jenkins Credentials Store |
| CICD-SEC-7 | Insecure System Configuration | ✅ Dockerfile hardened, Docker Compose sécurisé |
| CICD-SEC-8 | Ungoverned Usage of 3rd Party Services | ⚠️ Audit manuel des images de base recommandé |
| CICD-SEC-9 | Improper Artifact Integrity Validation | ✅ Cosign sign + verify |
| CICD-SEC-10 | Insufficient Logging and Visibility | ✅ Rapports archivés, Prometheus + Grafana |

---

## 4. Matrice de Risques Résiduelle

```
Probabilité
    ^
  H | [CICD-SEC-8]
  M | [Épuisement quotas Harbor]   [SSH brute-force]
  L |                               [PPE via fork]
    +────────────────────────────────────────────→
             Faible        Moyen         Élevé
                              Impact
```

**Risques résiduels acceptés :**
- Usage de services tiers (images de base DockerHub) → atténué par Trivy + MAJ régulières
- Clé SSH Jenkins → rotation tous les 90 jours recommandée

---

## 5. Plan de Remédiation

| Priorité | Action | Responsable | Délai |
|----------|--------|-------------|-------|
| P1 | Activer Cosign Content Trust sur Harbor | DevSecOps | Semaine 7 |
| P1 | Configurer Gitleaks pre-commit hook local | Développeurs | Semaine 1 |
| P2 | Intégrer HashiCorp Vault pour les secrets dynamiques | DevSecOps | Phase 4 |
| P2 | Générer SBOM avec Syft à chaque build | DevSecOps | Semaine 9 |
| P3 | Mise en place OPA/Conftest pour Policy-as-Code | DevSecOps | Phase 4 |
| P3 | Dashboard Grafana vulnérabilités dans le temps | DevOps | Semaine 11 |
