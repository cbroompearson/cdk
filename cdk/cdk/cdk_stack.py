from aws_cdk import (
    aws_ec2 as ec2,
    aws_ecs as ecs,
    aws_ecr as ecr,
    aws_iam as iam,
    aws_logs as logs,
    aws_elasticloadbalancingv2 as elbv2,
    aws_route53 as route53,
    aws_route53_targets, 
    core,
)

class CdkStack(core.Stack):

    def __init__(self, scope: core.Construct, id: str, props, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        pearson_vpn_connection = ec2.Peer.ipv4(
            '159.182.0.0/16'
        )


        # Props Setup
        stage = scope.node.try_get_context('stage')
        my_service_name = scope.node.try_get_context('serviceName')
        api_health_path = props['apiHealthPath']
        tca_health_path = props['tcaHealthPath']

        # Setup IAM user for logs
        vpc_flow_role = iam.Role(
            self, 'FlowLog',
            assumed_by=iam.ServicePrincipal('vpc-flow-logs.amazonaws.com')
        )

        vpc_flow_role.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    'iam:PassRole',
                    'logs:CreateLogGroup',
                    'logs:DescribeLogGroups',
                    'logs:CreateLogStream',
                    'logs:PutLogEvents'
                ],
                resources=["*"]
            )
        )

        # Create Cloudwatch log group
        log_group = logs.LogGroup(
            self, 'LogGroup',
            log_group_name="{0}-{1}".format(my_service_name, stage),
            retention=logs.RetentionDays('ONE_YEAR'),
            removal_policy=core.RemovalPolicy('DESTROY')
            )

        # Setup VPC resource
        vpc = ec2.Vpc(
            self, '{0}-{1}-vpc'.format(my_service_name, stage),
            cidr=props['cidr'],
            max_azs=props['vpcAzCount']
        )
        
        # Setup VPC flow logs
        vpc_log = ec2.CfnFlowLog(
            self, 'FlowLogs',
            resource_id=vpc.vpc_id,
            resource_type='VPC',
            traffic_type='ALL',
            deliver_logs_permission_arn=vpc_flow_role.role_arn,
            log_destination_type='cloud-watch-logs',
            log_group_name="{0}-{1}".format(log_group.log_group_name, stage)
        )

        # Setup Security Group in VPC
        vpc_sg = ec2.SecurityGroup(
            self,
            'EcSSG',
            vpc=vpc,
            allow_all_outbound=None,
            description="Security Group for Oculus vpc",
            security_group_name="{0}-{1}-vpc-sg".format(my_service_name, stage)
        )

        # Add Rules to Security Group
        vpc_sg.add_ingress_rule(
            peer=pearson_vpn_connection,
            connection=ec2.Port.tcp(22)
        )

        # ALB Security Group
        alb_sg = ec2.SecurityGroup(
            self,
            'AlbSG',
            vpc=vpc,
            allow_all_outbound=None,
            description="Security group for oculus ALB",
            security_group_name="{0}-{1}-alb-sg".format(my_service_name,stage)
        )

        # Add HTTPS Rule to Security Group
        alb_sg.add_ingress_rule(
            peer=pearson_vpn_connection,
            connection=ec2.Port.tcp(443)
        )

        # Setup ALB
        alb = elbv2.ApplicationLoadBalancer(
            self,'ALB',
            vpc=vpc,
            internet_facing=True,
            security_group=alb_sg
        )

        # Setup API Target Group
        api_tg = elbv2.ApplicationTargetGroup(
            self,'ApiTargetGroup',
            port=8080,
            protocol=elbv2.ApplicationProtocol.HTTP,
            vpc=vpc
        )

        # Setup Web Target Group
        web_tg = elbv2.ApplicationTargetGroup(
            self,'WebTargetGroup',
            port=3030,
            protocol=elbv2.ApplicationProtocol.HTTP,
            vpc=vpc
        )

        # Setup API Target Group
        tca_tg = elbv2.ApplicationTargetGroup(
            self,'TcaTargetGroup',
            port=8080,
            protocol=elbv2.ApplicationProtocol.HTTP,
            vpc=vpc
        )
        
        # Setup ECS Cluster
        ecs_cluster = ecs.Cluster(
            self,
            'ECSCluster',
            vpc=vpc,
            cluster_name="{0}-{1}".format(my_service_name, stage)
        )

        # ECS Execution Role - Grants ECS agent to call AWS APIs
        ecs_execution_role = iam.Role(
            self, 'ECSExecutionRole',
            assumed_by=iam.ServicePrincipal('ecs-tasks.amazonaws.com'),
            role_name="{0}-{1}-execution-role".format(my_service_name, stage)
        )

        # Setup Role Permissions
        ecs_execution_role.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    'elasticloadbalancing:DeregisterInstancesFromLoadBalancer',
                    'elasticloadbalancing:DeregisterTargets',
                    'elasticloadbalancing:Describe*',
                    'elasticloadbalancing:RegisterInstancesWithLoadBalancer',
                    'elasticloadbalancing:RegisterTargets',
                    'ec2:Describe*',
                    'ec2:AuthorizeSecurityGroupIngress',
                    'sts:AssumeRole',
                    'ssm:GetParameters',
                    'secretsmanager:GetSecretValue',
                    'ecr:GetAuthorizationToken',
                    'ecr:BatchCheckLayerAvailability',
                    'ecr:GetDownloadUrlForLayer',
                    'ecr:BatchGetImage',
                    'logs:CreateLogStream',
                    'logs:PutLogEvents',
                    "application-autoscaling:*",
                    "cloudwatch:DescribeAlarms",
                    "cloudwatch:PutMetricAlarm"
                ],
                resources=["*"]
            )
        )

        # ECS Task Role - Grants containers in task permission to AWS APIs
        ecs_task_role = iam.Role(
            self, 'ECSTaskRole',
            assumed_by=iam.ServicePrincipal('ecs-tasks.amazonaws.com'),
            role_name="{0}-{1}-task-role".format(my_service_name, stage)
        )

        # Setup Role Permissions
        ecs_task_role.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    'logs:CreateLogStream',
                    'logs:PutLogEvents',
                    'dynamodb:Query',
                    'dynamodb:ListTables',
                    'secretsmanager:GetSecretValue',
                    'kms:Decrypt'
                ],
                resources=["*"]
            )
        )

        # Setup API Task Definition
        api_taskdef = ecs.FargateTaskDefinition(
            self,'APIFargateTask',
            memory_limit_mib=512,
            cpu=256,
            execution_role=ecs_execution_role,
            task_role=ecs_task_role,
            family="{0}-{1}-api".format(my_service_name, stage)
        )

        # Setup Web Task Definition
        web_taskdef = ecs.FargateTaskDefinition(
            self,'WebFargateTask',
            memory_limit_mib=512,
            cpu=256,
            execution_role=ecs_execution_role,
            task_role=ecs_task_role,
            family="{0}-{1}-web".format(my_service_name, stage)
        )

        # # Setup TCA Task Definition
        tca_taskdef = ecs.FargateTaskDefinition(
            self,'TcaFargateTask',
            memory_limit_mib=512,
            cpu=256,
            execution_role=ecs_execution_role,
            task_role=ecs_task_role,
            family="{0}-{1}-tca".format(my_service_name, stage)
        )

        api_repo = ecr.Repository.from_repository_arn(
            self,'ApiImage',
            repository_arn="arn:aws:ecr:us-east-1:346147488134:repository/oculus-api"
        )

        web_repo = ecr.Repository.from_repository_arn(
            self,'WebImage',
            repository_arn="arn:aws:ecr:us-east-1:346147488134:repository/oculus-web"
        )

        tca_repo = ecr.Repository.from_repository_arn(
            self,'TcaImage',
            repository_arn="arn:aws:ecr:us-east-1:346147488134:repository/oculus-tca-api"
        )

        # Add Container API to Task
        api_container = api_taskdef.add_container(
            "oculus-cdk-{}-api".format(stage),
            image=ecs.EcrImage(
                repository=api_repo, tag="devqaurl"
            ),
            logging=ecs.LogDriver.aws_logs(
                stream_prefix="{0}-{1}-api".format(my_service_name, stage),
                log_group=log_group
            )
        )

        # Add Container Web to Task
        web_container = web_taskdef.add_container(
            "oculus-cdk-{}-web".format(stage),
            image=ecs.EcrImage(
                repository=web_repo, tag="removeMetaMockup"
            ),
            logging=ecs.LogDriver.aws_logs(
                stream_prefix="{0}-{1}-web".format(my_service_name, stage),
                log_group=log_group
            )
        )

        # # Add Container TCA to Task
        tca_container = tca_taskdef.add_container(
            "oculus-cdk-{}-tca".format(stage),
            image=ecs.EcrImage(
                repository=tca_repo, tag="ocu-1109"
            ),
            logging=ecs.LogDriver.aws_logs(
                stream_prefix="{0}-{1}-tca".format(my_service_name, stage),
                log_group=log_group
            )
        )

        # Setup API Port Mappings
        api_container.add_port_mappings(
            ecs.PortMapping(
                container_port=8080,
                host_port=8080,
                protocol=ecs.Protocol.TCP
            )
        )

        # Setup Web Port Mappings
        web_container.add_port_mappings(
            ecs.PortMapping(
                container_port=3030,
                host_port=3030,
                protocol=ecs.Protocol.TCP
            )
        )

        # # Setup TCA Port Mappings
        tca_container.add_port_mappings(
            ecs.PortMapping(
                container_port=8080,
                host_port=8080,
                protocol=ecs.Protocol.TCP
            )
        )

        # Setup API Fargate Service
        api_service = ecs.FargateService(
            self,"FargateServiceAPI",
            task_definition=api_taskdef,
            cluster=ecs_cluster,
            desired_count=1,
            service_name="{0}-{1}-api".format(my_service_name, stage)
        )

        api_scaling = api_service.auto_scale_task_count(max_capacity=5)
        api_scaling.scale_on_cpu_utilization('ApiCpuScaling', target_utilization_percent=50)


        # Setup Web Fargate Service
        web_service = ecs.FargateService(
            self,"FargateServiceWeb",
            task_definition=web_taskdef,
            cluster=ecs_cluster,
            desired_count=1,
            service_name="{0}-{1}-web".format(my_service_name, stage)
        )

        web_scaling = web_service.auto_scale_task_count(max_capacity=5)
        web_scaling.scale_on_cpu_utilization('WebCpuScaling', target_utilization_percent=50)

        # # Setup TCA Fargate Service
        tca_service = ecs.FargateService(
            self,"FargateServiceTCA",
            task_definition=tca_taskdef,
            cluster=ecs_cluster,
            desired_count=1,
            service_name="{0}-{1}-tca".format(my_service_name, stage)
        )

        tca_scaling = tca_service.auto_scale_task_count(max_capacity=5)
        tca_scaling.scale_on_cpu_utilization('TcaCpuScaling', target_utilization_percent=50)


        # Setup ALB Listener
        alb_listener = alb.add_listener(
            'Listener',
            certificate_arns=[
                "arn:aws:acm:us-east-1:829809672214:certificate/a84bb369-03ce-4e5e-9d32-8c84609cad1e"
            ],
            port=443,
            open=False,
            protocol=elbv2.ApplicationProtocol.HTTPS
        )

        # Attach ALB to ECS API Service
        api_target = alb_listener.add_targets(
            'ECSAPI',
            port=8080,
            priority=1,
            targets=[api_service],
            health_check=elbv2.HealthCheck(
                path=api_health_path
            ),
            path_pattern='/oculus-api/*'   
        )

        # # Attach ALB to ECS TCA Service
        tca_target = alb_listener.add_targets(
            'ECSTCA',
            port=8080,
            priority=2,
            targets=[tca_service],
            health_check=elbv2.HealthCheck(
                path=tca_health_path
            ),
            path_pattern='/tca/*'   
        )

        # Attach ALB to ECS Web Service
        web_target = alb_listener.add_targets(
            'ECSWeb',
            port=3030,
            protocol=elbv2.ApplicationProtocol.HTTP,
            targets=[web_service],
            health_check=elbv2.HealthCheck(
                path='/'
            ), 
        )

        

        core.CfnOutput(self,
            'LoadBalancerDNS',
            value=alb.load_balancer_dns_name
        )

        zone = route53.HostedZone.from_lookup(
            self,
            'MyHostedZone',
            domain_name = props['zoneDomain']
        )

        route53.ARecord(
            self,
            'ServiceAliasRecord',
            record_name=props['siteDomain'],
            target=route53.RecordTarget(
                alias_target=aws_route53_targets.LoadBalancerTarget(load_balancer=alb)
            ),
            zone=zone
        )
