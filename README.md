# Oculus Devops
This DevOps repo should be for all the applications. This is for Unified Jenkins - build, deploy and updating tasks. This repo is for Oculus-Fargate 

'jenkinsfiles' has build and deploy groovy's, these jobs are in declarative pipeline whereas 'task-defs' has all the task definitions that to be updated to the ECS for all the environments.

For Fargate jobs, there is a view 'Oculus Fargate' in Unified Jenkins - https://unified-jenkins-nonprod.pearsoncms.net/view/Oculus%20Fargate/


# CDK
It is OCULUS CDK fargate. It has the READme in it.
'Master' branch has the working DEV stack code.


# ec2 
'ec2' is for Oculus-EC2 stack - unified jenkins. Initially Oculus-ec2 has the jobs in Scripted pipeline and uses 'ecs-boss-config' repo. This 'ec2' has the jenkinsfiles with Declarative pipeline. 
It has similar jenkinsfiles and task-def's for all the three services - web, api and tca-api but for 'EC2' stack.

For Oculus EC2 (Declarative Pipeline) jobs, there is a view 'Ocu EC2' in Unified Jenkins - https://unified-jenkins-nonprod.pearsoncms.net/view/Ocu%20EC2/
