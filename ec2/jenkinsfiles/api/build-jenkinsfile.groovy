pipeline {
    agent { label 'ecs' }
    parameters { 
        string(name: 'IMAGE_TAG', defaultValue: '', description: 'This is the Oculus API tag in the repo') 
    }
    environment { 
        GIT_REPO = 'ssh://git@bitbucket.pearson.com/cite-ocu/oculus-api.git'
        ECR_ACCOUNT = '346147488134'
        ECR_REPO = 'oculus-api'
    }
    stages {
        stage('checkout') {
            steps{
                checkout scm: [$class  : 'GitSCM', userRemoteConfigs:
                        [[url          : "${env.GIT_REPO}",
                        credentialsId: 'bitbucket']],
                            branches: [[name: "refs/tags/${IMAGE_TAG}"]]], poll: false
            }
        }

        stage('Build Image') {
            steps{
                sh """
                    docker build -t ${env.ECR_ACCOUNT}.dkr.ecr.us-east-1.amazonaws.com/${ECR_REPO}:${params.IMAGE_TAG} .
                """
            }
        }
        stage('Push to ECR'){
            steps{
                sh """#!/bin/bash -e
                source /usr/local/bin/assume_role.sh
                assume_role arn:aws:iam::829809672214:role/common/common/common-common-jenkinsEcrPushRole
                eval \$(aws ecr get-login --no-include-email --registry-ids=346147488134 --region=us-east-1) 

                docker push ${ECR_ACCOUNT}.dkr.ecr.us-east-1.amazonaws.com/${ECR_REPO}:${params.IMAGE_TAG}

                # Remove docker image after push to ECR as not required on jenkins host after push
                docker rmi ${ECR_ACCOUNT}.dkr.ecr.us-east-1.amazonaws.com/${ECR_REPO}:${params.IMAGE_TAG}
                """
            }
        }
    }
    post {
        always {
            script{
                    manager.addShortText("${params.IMAGE_TAG}")
                }
        }
    }
}
