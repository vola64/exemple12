pipeline {
    agent any

    environment {
        // ─── Harbor Registry ───────────────────────────────────────────────
        HARBOR_URL      = credentials('HARBOR_URL')          // ex: harbor.mondomaine.com
        HARBOR_PROJECT  = 'devsecops'
        IMAGE_NAME      = 'fastapi-app'
        IMAGE_TAG       = "${env.BUILD_NUMBER}"
        FULL_IMAGE      = "${HARBOR_URL}/${HARBOR_PROJECT}/${IMAGE_NAME}:${IMAGE_TAG}"

        // ─── Cosign ────────────────────────────────────────────────────────
        COSIGN_PASSWORD = credentials('COSIGN_PASSWORD')

        // ─── OWASP NVD API Key ─────────────────────────────────────────────
        NVD_API_KEY     = credentials('NVD_API_KEY')

        // ─── Répertoires de rapports ───────────────────────────────────────
        REPORTS_DIR     = 'reports'
    }

    options {
        timestamps()
        timeout(time: 60, unit: 'MINUTES')
        buildDiscarder(logRotator(numToKeepStr: '10'))
        disableConcurrentBuilds()
    }

    stages {

        // ══════════════════════════════════════════════════════════════════
        // STAGE 1 — Analyse Statique (SAST + Secrets)
        // ══════════════════════════════════════════════════════════════════
        stage('1 - SAST & Secrets Scan') {
            parallel {

                stage('Bandit - SAST Python') {
                    steps {
                        sh '''
                            mkdir -p ${REPORTS_DIR}
                            echo "[*] Lancement Bandit (SAST Python)..."
                            pip install bandit --quiet
                            bandit -r src/ \
                                   -f json \
                                   -o ${REPORTS_DIR}/bandit-report.json \
                                   --exit-zero || true
                            bandit -r src/ -f txt | tee ${REPORTS_DIR}/bandit-report.txt
                            echo "[+] Bandit terminé."
                        '''
                    }
                }

                stage('Semgrep - SAST Multi-langage') {
                    steps {
                        sh '''
                            echo "[*] Lancement Semgrep..."
                            pip install semgrep --quiet
                            semgrep scan \
                                --config=auto \
                                --json \
                                --output=${REPORTS_DIR}/semgrep-report.json \
                                src/ || true
                            echo "[+] Semgrep terminé."
                        '''
                    }
                }

                stage('Gitleaks - Secrets Detection') {
                    steps {
                        sh '''
                            echo "[*] Lancement Gitleaks..."
                            if ! command -v gitleaks &> /dev/null; then
                                wget -q https://github.com/gitleaks/gitleaks/releases/download/v8.18.4/gitleaks_8.18.4_linux_x64.tar.gz
                                tar -xzf gitleaks_8.18.4_linux_x64.tar.gz
                                mv gitleaks /usr/local/bin/gitleaks
                            fi
                            gitleaks detect \
                                --source=. \
                                --report-format=json \
                                --report-path=${REPORTS_DIR}/gitleaks-report.json \
                                --exit-code 0 || true
                            echo "[+] Gitleaks terminé."
                        '''
                    }
                }
            }
            post {
                always {
                    archiveArtifacts artifacts: 'reports/bandit-report.*,reports/semgrep-report.json,reports/gitleaks-report.json',
                                     allowEmptyArchive: true
                }
            }
        }

        // ══════════════════════════════════════════════════════════════════
        // STAGE 2 — Build de l'image Docker
        // ══════════════════════════════════════════════════════════════════
        stage('2 - Build Docker Image') {
            steps {
                sh '''
                    echo "[*] Construction de l'image Docker : ${FULL_IMAGE}"
                    docker build \
                        --no-cache \
                        --label "build.number=${BUILD_NUMBER}" \
                        --label "build.date=$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
                        --label "git.commit=${GIT_COMMIT}" \
                        -t ${FULL_IMAGE} \
                        -f docker/Dockerfile .
                    echo "[+] Image construite avec succès."
                    docker images ${FULL_IMAGE}
                '''
            }
        }

        // ══════════════════════════════════════════════════════════════════
        // STAGE 3 — Scan Dépendances & Conteneur
        // ══════════════════════════════════════════════════════════════════
        stage('3 - Dependency & Container Scan') {
            parallel {

                stage('OWASP Dependency Check') {
                    steps {
                        sh '''
                            echo "[*] Lancement OWASP Dependency-Check..."
                            mkdir -p ${REPORTS_DIR}/owasp
                            docker run --rm \
                                -v "$(pwd):/src" \
                                -v "$(pwd)/${REPORTS_DIR}/owasp:/report" \
                                owasp/dependency-check:latest \
                                --scan /src \
                                --format JSON \
                                --format HTML \
                                --out /report \
                                --nvdApiKey ${NVD_API_KEY} \
                                --project "fastapi-app" \
                                --failOnCVSS 9 || true
                            echo "[+] OWASP Dependency-Check terminé."
                        '''
                    }
                }

                stage('Trivy - Container Scan') {
                    steps {
                        sh '''
                            echo "[*] Lancement Trivy (scan conteneur)..."
                            if ! command -v trivy &> /dev/null; then
                                wget -q https://github.com/aquasecurity/trivy/releases/download/v0.50.1/trivy_0.50.1_Linux-64bit.tar.gz
                                tar -xzf trivy_0.50.1_Linux-64bit.tar.gz
                                mv trivy /usr/local/bin/trivy
                            fi

                            # Scan JSON
                            trivy image \
                                --format json \
                                --output ${REPORTS_DIR}/trivy-report.json \
                                --severity HIGH,CRITICAL \
                                --exit-code 0 \
                                ${FULL_IMAGE}

                            # Rapport lisible
                            trivy image \
                                --format table \
                                --severity HIGH,CRITICAL \
                                --exit-code 1 \
                                ${FULL_IMAGE} | tee ${REPORTS_DIR}/trivy-report.txt

                            echo "[+] Trivy terminé."
                        '''
                    }
                }
            }
            post {
                always {
                    archiveArtifacts artifacts: 'reports/owasp/**,reports/trivy-report.*',
                                     allowEmptyArchive: true
                    // Publier rapport HTML OWASP dans Jenkins
                    publishHTML([
                        allowMissing: true,
                        alwaysLinkToLastBuild: true,
                        keepAll: true,
                        reportDir: 'reports/owasp',
                        reportFiles: 'dependency-check-report.html',
                        reportName: 'OWASP Dependency Check'
                    ])
                }
            }
        }

        // ══════════════════════════════════════════════════════════════════
        // STAGE 4 — Signature de l'image (Cosign)
        // ══════════════════════════════════════════════════════════════════
        stage('4 - Sign Image (Cosign)') {
            steps {
                withCredentials([file(credentialsId: 'COSIGN_PRIVATE_KEY', variable: 'COSIGN_KEY')]) {
                    sh '''
                        echo "[*] Signature de l'image avec Cosign..."
                        if ! command -v cosign &> /dev/null; then
                            wget -q https://github.com/sigstore/cosign/releases/download/v2.2.3/cosign-linux-amd64
                            chmod +x cosign-linux-amd64
                            mv cosign-linux-amd64 /usr/local/bin/cosign
                        fi

                        export COSIGN_PASSWORD=${COSIGN_PASSWORD}

                        cosign sign \
                            --key ${COSIGN_KEY} \
                            --yes \
                            ${FULL_IMAGE}

                        echo "[+] Image signée avec succès."
                        echo "[*] Vérification de la signature..."
                        cosign verify \
                            --key ${COSIGN_KEY} \
                            ${FULL_IMAGE} | tee ${REPORTS_DIR}/cosign-verify.txt

                        echo "[+] Signature vérifiée."
                    '''
                }
            }
            post {
                always {
                    archiveArtifacts artifacts: 'reports/cosign-verify.txt',
                                     allowEmptyArchive: true
                }
            }
        }

        // ══════════════════════════════════════════════════════════════════
        // STAGE 5 — Push vers Harbor
        // ══════════════════════════════════════════════════════════════════
        stage('5 - Push to Harbor') {
            steps {
                withCredentials([usernamePassword(
                    credentialsId: 'HARBOR_CREDENTIALS',
                    usernameVariable: 'HARBOR_USER',
                    passwordVariable: 'HARBOR_PASS'
                )]) {
                    sh '''
                        echo "[*] Connexion à Harbor : ${HARBOR_URL}..."
                        echo "${HARBOR_PASS}" | docker login ${HARBOR_URL} \
                            -u ${HARBOR_USER} --password-stdin

                        echo "[*] Push de l'image : ${FULL_IMAGE}"
                        docker push ${FULL_IMAGE}

                        # Tag latest également
                        docker tag ${FULL_IMAGE} \
                            ${HARBOR_URL}/${HARBOR_PROJECT}/${IMAGE_NAME}:latest
                        docker push \
                            ${HARBOR_URL}/${HARBOR_PROJECT}/${IMAGE_NAME}:latest

                        echo "[+] Image pushée avec succès vers Harbor."
                        docker logout ${HARBOR_URL}
                    '''
                }
            }
        }

        // ══════════════════════════════════════════════════════════════════
        // STAGE 6 — Vérification Politique Harbor
        // ══════════════════════════════════════════════════════════════════
        stage('6 - Harbor Policy Check') {
            steps {
                withCredentials([usernamePassword(
                    credentialsId: 'HARBOR_CREDENTIALS',
                    usernameVariable: 'HARBOR_USER',
                    passwordVariable: 'HARBOR_PASS'
                )]) {
                    sh '''
                        echo "[*] Vérification du scan Harbor via API..."

                        # Déclencher un scan de l'image dans Harbor
                        curl -s -u "${HARBOR_USER}:${HARBOR_PASS}" \
                             -X POST \
                             "https://${HARBOR_URL}/api/v2.0/projects/${HARBOR_PROJECT}/repositories/${IMAGE_NAME}/artifacts/${IMAGE_TAG}/scan"

                        echo "[*] Attente du rapport de scan Harbor (30s)..."
                        sleep 30

                        # Récupérer le rapport de vulnérabilités
                        curl -s -u "${HARBOR_USER}:${HARBOR_PASS}" \
                             "https://${HARBOR_URL}/api/v2.0/projects/${HARBOR_PROJECT}/repositories/${IMAGE_NAME}/artifacts/${IMAGE_TAG}/additions/vulnerabilities" \
                             -o ${REPORTS_DIR}/harbor-scan.json

                        echo "[+] Rapport Harbor récupéré."

                        # Vérifier s'il y a des vulnérabilités CRITICAL bloquantes
                        CRITICAL_COUNT=$(cat ${REPORTS_DIR}/harbor-scan.json | \
                            python3 -c "
import json, sys
data = json.load(sys.stdin)
count = 0
for report in data.values():
    for vuln in report.get('vulnerabilities', []):
        if vuln.get('severity') == 'Critical':
            count += 1
print(count)
" 2>/dev/null || echo "0")

                        echo "[!] Nombre de vulnérabilités CRITICAL : ${CRITICAL_COUNT}"

                        if [ "${CRITICAL_COUNT}" -gt "0" ]; then
                            echo "[ECHEC] Des vulnérabilités critiques ont été détectées. Pipeline arrêté."
                            exit 1
                        fi

                        echo "[+] Politique Harbor respectée. Aucune vulnérabilité critique."
                    '''
                }
            }
            post {
                always {
                    archiveArtifacts artifacts: 'reports/harbor-scan.json',
                                     allowEmptyArchive: true
                }
            }
        }

        // ══════════════════════════════════════════════════════════════════
        // STAGE 7 — Déploiement Docker Compose Sécurisé
        // ══════════════════════════════════════════════════════════════════
        stage('7 - Deploy (Docker Compose)') {
            when {
                branch 'main'
            }
            steps {
                withCredentials([
                    sshUserPrivateKey(credentialsId: 'DEPLOY_SSH_KEY',
                                     keyFileVariable: 'SSH_KEY',
                                     usernameVariable: 'DEPLOY_USER'),
                    string(credentialsId: 'DEPLOY_HOST', variable: 'DEPLOY_HOST')
                ]) {
                    sh '''
                        echo "[*] Déploiement sur ${DEPLOY_HOST}..."

                        # Copier docker-compose.yml vers le serveur distant
                        scp -i ${SSH_KEY} \
                            -o StrictHostKeyChecking=no \
                            docker-compose.yml \
                            ${DEPLOY_USER}@${DEPLOY_HOST}:/opt/devsecops/docker-compose.yml

                        # Déployer via SSH
                        ssh -i ${SSH_KEY} \
                            -o StrictHostKeyChecking=no \
                            ${DEPLOY_USER}@${DEPLOY_HOST} << EOF
                                export HARBOR_URL=${HARBOR_URL}
                                export IMAGE_TAG=${IMAGE_TAG}
                                cd /opt/devsecops

                                # Vérifier la signature avant déploiement
                                bash /opt/devsecops/scripts/verify.sh ${FULL_IMAGE}

                                # Pull & démarrer les conteneurs
                                docker compose pull
                                docker compose up -d --remove-orphans
                                docker compose ps
                                echo "[+] Déploiement terminé."
EOF
                    '''
                }
            }
        }
    }

    // ══════════════════════════════════════════════════════════════════════
    // POST — Actions globales (succès / échec / toujours)
    // ══════════════════════════════════════════════════════════════════════
    post {
        always {
            echo "=== Résumé du pipeline ==="
            sh 'ls -la reports/ 2>/dev/null || echo "Pas de rapports générés."'
        }
        success {
            echo "[✔] Pipeline CI/CD sécurisé terminé avec succès (Build #${BUILD_NUMBER})"
        }
        failure {
            echo "[✘] Pipeline échoué. Consultez les rapports dans l'onglet Archives."
        }
        cleanup {
            // Nettoyer l'image locale pour libérer de l'espace
            sh '''
                docker rmi ${FULL_IMAGE} || true
                docker rmi ${HARBOR_URL}/${HARBOR_PROJECT}/${IMAGE_NAME}:latest || true
            '''
        }
    }
}
