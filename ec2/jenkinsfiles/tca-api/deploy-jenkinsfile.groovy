pipeline {
    agent { label 'ecs' }
    parameters { 
        string(name: 'IMAGE_TAG', defaultValue: '', description: 'This is the OCU TCA API tag in the repo') 
        // choice(name: 'IMAGE_TAG', choices: getImages(artifact:'acapi'), description: 'This is the ACAPI tag in the repo')
        choice(name: 'ENV', choices: ['dev', 'qa', 'prod'], description: 'Environment to deploy to.')
    }
    environment { 
        GIT_REPO = 'ssh://git@bitbucket.pearson.com/cite-ocu/oculus-devops.git'
        ECR_ACCOUNT = '346147488134'
        ECR_REPO = 'oculus-tca-api'
        ECS_CLUSTER = 'ocu-dev-ecs'
        AWS_REGION = 'us-east-1'
        SERVICE = "ocu-${params.ENV}-tca-api"
        TASK_DEF = "ocu-${params.ENV}-tca-api"
        FAMILY = "ocu-${params.ENV}-tca-api"
    }
    stages {
        stage('Check ECR For Image'){
            steps{
                echo "Now checking for ECR Image..."
                script{
                    def result = imageExists()
                    echo "$result"
                    if ("${result}" == 'true'){
                        currentBuild.result = 'FAILURE'
                        echo 'Image Not Found'
                        sh 'exit 1'
                    }
                }
            }
        }
        stage('Checkout') {
            steps{
                checkout scm: [$class: 'GitSCM', userRemoteConfigs:
                                    [[url: "${env.GIT_REPO}",
                                    credentialsId: 'bitbucket']], 
                            branches: [[name: "master"]]], poll: false
            }
        }
        stage('Update App Task') {
            steps {
                echo 'Updating Task..'
                sh """sed -i "s/<<IMAGEID>>/${params.IMAGE_TAG}/g" task-defs/tca-api/taskdef-${params.ENV}.json"""
                script{
                    REVISION= sh(returnStdout: true, script: """aws ecs register-task-definition --region \$AWS_REGION --family \$FAMILY --cli-input-json file://task-defs/api/taskdef-${params.ENV}.json| jq .taskDefinition.revision""")
                }
                echo "Revision: $REVISION"
                script{
                    NEWTASK = sh(returnStdout: true, script: """aws ecs update-service --cluster \$ECS_CLUSTER --region \$AWS_REGION --service \$SERVICE --task-definition \$TASK_DEF:$REVISION""")
                    }
                echo "Our new task definition is: $NEWTASK"
            }
        }
        // stage('Poll Task'){
        //     steps{
        //         echo "The newtask is: $NEWTASK"
        //         polltask(NEWTASK)
        //     }
        // }
    }
    post {
        always {
            script{
                    manager.addShortText("${params.IMAGE_TAG}")
                    manager.addShortText("${params.ENV}")
                }
        }
    }
}

import groovy.json.JsonSlurperClassic

def imageExists() {
   sh """#!/bin/bash -e
                source /usr/local/bin/assume_role.sh
                assume_role arn:aws:iam::829809672214:role/common/common/common-common-jenkinsEcrPushRole
                eval \$(aws ecr get-login --no-include-email --registry-ids=\$ECR_ACCOUNT --region=\$AWS_REGION)"""
  
    echo "in the method"
    cmd="aws ecr batch-get-image --registry-id=\$ECR_ACCOUNT --region=\$AWS_REGION --repository-name=\$ECR_REPO --image-ids imageTag=${params.IMAGE_TAG}"
    echo "created the cmd"
    echo "${cmd}"
    def resultJson = sh(returnStdout: true, script: "${cmd}")
    echo "*****"
    echo "$resultJson"
    //return "${resultJson}"
    def resultParsed = new groovy.json.JsonSlurperClassic().parseText(resultJson)
    echo "resultParsed"
    def result = resultParsed.failures.collect { it.keySet().contains('failureReason')}[0]
    echo "RESULT DEBUGS TO: $result"
    def failure = resultParsed.failures[0]
    echo "for DEBUG: $failure"
    return "$result"
}

def getImages(def args) {
    artifact = args.artifact
    regex = args.get('regex', '')
    cmd="aws ecr list-images --registry-id=\$ECR_ACCOUNT --region=\$AWS_REGION --filter tagStatus=TAGGED"
    def process = "${cmd} --repository-name ${artifact}".execute()
    def hash = new groovy.json.JsonSlurperClassic().parseText(process.text)
    tags = hash['imageIds'].collect {it.imageTag}
    return tags.sort()
}

def polltask(newTask){
    echo "The newTask sent to function is: $newTask"
    sh """#!/bin/bash -e
                source /usr/local/bin/assume_role.sh
                assume_role arn:aws:iam::829809672214:role/common/common/common-common-jenkinsEcrPushRole
                eval \$(aws ecr get-login --no-include-email --registry-ids=\$ECR_ACCOUNT --region=\$AWS_REGION)"""

    currentTask= sh(returnStdout: true, script: "aws ecs list-tasks --cluster=\$ECS_CLUSTER --service=\$SERVICE --desired-status Running --region=\$AWS_REGION")
    def newTaskParsed = new groovy.json.JsonSlurperClassic().parseText(newTask)
    def currentTask = jsonParse(currentTask_raw)
    echo "Current task before starting: ${currentTask}"
    echo "Our new task we are starting: ${newTask}"
    checkRunningTasks(newTask)
}


def checkRunningTasks(newTaskARN){
    for (int i = 0; i < 3; i++){
        def runningTasks = sh(returnStdout: true, script: "aws ecs list-tasks --cluster=\$ECS_CLUSTER --service=\$SERVICE --desired-status Running --region=\$AWS_REGION")
        def runningTasksParsed = jsonParse(runningTasks)
        def runningTasksARN = runningTasksParsed['taskArns']

        echo "Current running tasks: $runningTasksARN"
        echo "New task being deployed: $newTaskARN"
        if (runningTasksParsed["taskArns"].size()==1 && newTaskARN != runningTasksARN ){
            echo "We are on interation:  $i"
            echo "Current running task $runningTasksARN"
            echo "Waiting until new service becomes active, please wait..."
            sh "sleep 5m"
        } else if (runningTasksParsed["taskArns"].size()==1 && newTaskARN == runningTasksARN){
            echo "We now have only 1 new task running and should be our new one: $runningTasksParsed" 
            currentBuild.result = 'SUCCESS'
            sh "exit 0"
        } 
        else {
            echo "We now have 2 tasks running..."
            echo "$runningTasksParsed"
            if (runningTasksParsed["taskArns"].size()==1){
                echo "Old task has now drained successfully"
                echo "$runningTasksParsed"
                currentBuild.result = 'SUCCESS'
            } else{
                echo "Still have 2 tasks, waiting another 5 minutes..."
                sh "sleep 5m"
            }
        }
        if (i == 3){
            currentBuild.result = 'FAILURE'
            echo "Took full 15 minutes and did not register new task: $runningTasksParsed"
        }
    }
}

@NonCPS
def jsonParse(def json) {
    new groovy.json.JsonSlurperClassic().parseText(json)
}