// =============================================================================
// DRAFT — scheduled data run for justifactu.
//
// Status: NOT wired into any Jenkins job yet. Prerequisites before first use:
//   - an agent labelled 'justifactu' that carries the onedrive binary
//     (see service/agent/dockerfile/Dockerfile) and the two persistent volumes
//   - persistent Docker volumes mounted at /onedrive/conf and /onedrive/data
//   - a one-time interactive OneDrive authorization seeded into /onedrive/conf
//
// Full design and rationale:
//   docs/ (submodule) -> docs/explanation/onedrive_sync_and_orchestration.md
//   Decision IDs referenced below (D3, D4, D10, D12, D13, D14, D15) are in that
//   document's Section 12, "Decision log".
// =============================================================================

pipeline {
    agent { label 'justifactu' }                 // D5 — one pinned agent: it alone has onedrive + the volumes

    options {
        disableConcurrentBuilds()                // D4 — replaces any lock file; there is no monitor to coordinate with
        buildDiscarder(logRotator(numToKeepStr: '30'))
        timestamps()
    }

    environment {
        OD_CONF = '/onedrive/conf'               // the persistent conf volume mount (config, refresh_token, items.sqlite3)
        OD_DATA = '/onedrive/data'
    }

    stages {

        stage('Run justifactu') {
            // Reads the warm local cache; performs every SharePoint mutation (rename / delete / upload) itself
            // through Microsoft Graph. D16 — there is no "upload results" sync stage.
            steps {
                sh '''
                    set -eu
                    make install
                    make run CMD="--onedrive-conf-folder ${OD_CONF} --onedrive-data-folder ${OD_DATA} --dry-run"  # TODO: remove when we enter into production
                '''
            }
        }
    }

    post {
        // D15 — notify once, here, rather than with try/catch around stages.
        failure {
            emailext(
                to: 'dromero@iciq.es',
                subject: "FAILED: ${env.JOB_NAME} #${env.BUILD_NUMBER}",
                body: "Build failed or was aborted.\n\nConsole: ${env.BUILD_URL}console",
                attachLog: true
            )
        }
        aborted {
            emailext(
                to: 'dromero@iciq.es',
                subject: "ABORTED: ${env.JOB_NAME} #${env.BUILD_NUMBER}",
                body: "Build aborted (most likely the 20h timeout during the initial sync).\n" +
                      "OneDrive saved its resume state; the next scheduled run continues.\n\n" +
                      "Console: ${env.BUILD_URL}console",
                attachLog: true
            )
        }
    }
}
