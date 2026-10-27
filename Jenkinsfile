pipeline {
    agent any

    triggers {
        pollSCM('H/2 * * * *')
    }

    options {
        timestamps()
        disableConcurrentBuilds()
        buildDiscarder(logRotator(numToKeepStr: '20'))
    }

    environment {
        IMAGE = 'citizen-appeals-agent'
        VENV = "${WORKSPACE}/.venv"
        PATH = "${WORKSPACE}/.venv/bin:${env.PATH}"
    }

    stages {
        stage('Setup') {
            steps {
                script {
                    env.TAG = sh(script: 'git rev-parse --short HEAD', returnStdout: true).trim()
                }
                sh 'python3 -m venv "$VENV"'
                sh 'pip install --quiet -e ".[dev]"'
            }
        }

        stage('Lint') {
            steps {
                sh 'ruff check .'
                sh 'ruff format --check .'
                sh 'mypy'
            }
        }

        stage('Unit tests') {
            steps {
                sh 'pytest --junitxml=junit.xml --cov --cov-report=xml --cov-fail-under=90'
            }
            post {
                always {
                    junit 'junit.xml'
                }
            }
        }

        stage('Model quality gate') {
            steps {
                sh 'appeal-agent generate --n 2000 --seed 42'
                sh 'appeal-agent train --seed 42 --min-accuracy 0.90'
            }
            post {
                success {
                    archiveArtifacts artifacts: 'reports/**', fingerprint: true
                }
            }
        }

        stage('Docker build') {
            steps {
                sh 'docker build -t "$IMAGE:$TAG" -t "$IMAGE:latest" .'
            }
        }

        stage('Smoke test') {
            steps {
                sh '''
                    docker rm -f "smoke-$TAG" 2>/dev/null || true
                    docker run -d --name "smoke-$TAG" "$IMAGE:$TAG"
                    for i in $(seq 1 15); do
                        if docker exec "smoke-$TAG" python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/summary')"; then
                            echo "API is up"
                            exit 0
                        fi
                        sleep 2
                    done
                    docker logs "smoke-$TAG"
                    exit 1
                '''
            }
            post {
                always {
                    sh 'docker rm -f "smoke-$TAG" || true'
                }
            }
        }
    }

    post {
        success {
            echo "Image $IMAGE:$TAG is ready"
        }
    }
}
