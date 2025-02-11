from optparse import Values
import boto3
import time
import json
import yaml

AWS_REGION = 'us-west-2'

# Create a session using 'herovired' profile
session = boto3.Session(profile_name="herovired", region_name=AWS_REGION)

# Initialize all clients
s3 = session.client('s3')
ec2 = session.client('ec2')
elb = session.client('elbv2')
autoscaling = session.client('autoscaling')
sns = session.client('sns')

# Step 1: Providing all values by using yaml file
def read_values_from_file(file_path):
    with open(file_path, 'r') as file:
        values = yaml.safe_load(file)
    return values

# Step 2: Create S3 Bucket before checking if it exists
def create_s3_bucket(bucket_name):
    try:
        # Check if the bucket exists
        response = s3.head_bucket(Bucket=bucket_name)
        print(f"S3 bucket already exists: {bucket_name}")
        return bucket_name
    except s3.exceptions.ClientError as e:
        error_code = e.response['Error']['Code']
        if error_code == '403':
            print(f"Access denied to check bucket {bucket_name}. Ensure you have correct permissions.")
            return None
        elif error_code == '404':
            # Bucket doesn't exist, proceed to create it
            try:
                response = s3.create_bucket(
                    Bucket=bucket_name,
                    CreateBucketConfiguration={
                        'LocationConstraint': session.region_name
                    }
                )
                print(f"S3 bucket created: {bucket_name}")
                return bucket_name
            except s3.exceptions.BucketAlreadyExists:
                print(f"Bucket name '{bucket_name}' already exists globally. Please choose a different name.")
                return None
            except Exception as e:
                print(f"Error creating bucket: {e}")
                return None
        else:
            print(f"Error checking bucket: {e}")
            return None

# Step 3: Create Security Group or use existing
def create_security_group(description, security_group_name):
    try:
        # Check if the security group already exists
        response = ec2.describe_security_groups(
            Filters=[{'Name': 'group-name', 'Values': [security_group_name]}]
        )
        
        if response['SecurityGroups']:
            security_group_id = response['SecurityGroups'][0]['GroupId']
            print(f"Security group already exists: {security_group_id}")
            return security_group_id
        else:
            # If the security group doesn't exist, create a new one
            response = ec2.create_security_group(
                GroupName=security_group_name,
                Description=description
            )
            security_group_id = response['GroupId']
            print(f"Security group created: {security_group_id}")

            ec2.create_tags(
                Resources=[security_group_id],
                Tags=[{'Key': 'Name', 'Value': security_group_name}]
            )
            print(f"Tags added to security group: {security_group_name}")
            # Set inbound rules
            ec2.authorize_security_group_ingress(
                GroupId=security_group_id,
                IpPermissions=[
                    {
                        'IpProtocol': 'tcp',
                        'FromPort': 80,
                        'ToPort': 80,
                        'IpRanges': [{'CidrIp': '0.0.0.0/0'}]
                    },
                    {
                        'IpProtocol': 'tcp',
                        'FromPort': 22,
                        'ToPort': 22,
                        'IpRanges': [{'CidrIp': '0.0.0.0/0'}]
                    }
                ]
            )
            print("Inbound traffic rules applied to security group")
            return security_group_id

    except Exception as e:
        print(f"Error creating or checking security group: {e}")

# Step 4: Launch an EC2 instance or use existing
def launch_ec2_instance(security_group_id, ami_id, instance_type, ec2_name):
    try:
        # Check if an instance with the tag 'WebServer' already exists
        response = ec2.describe_instances(
            Filters=[
                {'Name': 'tag:Name', 'Values': [ec2_name]},
                {'Name': 'instance-state-name', 'Values': ['running', 'pending']}
            ]
        )
        if response['Reservations']:
            instance_id = response['Reservations'][0]['Instances'][0]['InstanceId']
            print(f"EC2 instance already exists: {instance_id}")
            return instance_id
        else:
            # Launch new instance if not found
            response = ec2.run_instances(
                ImageId=ami_id, 
                InstanceType=instance_type,
                MinCount=1,
                MaxCount=1,
                UserData='''
                    #!/bin/bash
                    sudo apt update
                    sudo apt install -y nginx
                    sudo systemctl start nginx
                    sudo systemctl enable nginx
                    echo "<html><body><h1>Welcome to My Web App</h1></body></html>" > /var/www/html/index.html
                ''',
                TagSpecifications=[{
                    'ResourceType': 'instance',
                    'Tags': [{'Key': 'Name', 'Value': ec2_name}]
                }],
                SecurityGroupIds=[security_group_id]
            )
            instance_id = response['Instances'][0]['InstanceId']
            print(f"EC2 Instance launched: {instance_id}")
            return instance_id
    except Exception as e:
        print(f"Error launching EC2 instance: {e}")

# Step 5: Create Load Balancer and Target Group or use existing
def create_load_balancer(instance_id, security_group_id, subnet_id, vpc_id, loadbalancer_name, lb_targetgroup):
    try:
        # Check if the ALB exists
        response = elb.describe_load_balancers(
            Names=[loadbalancer_name]
        )
        load_balancer_arn = response['LoadBalancers'][0]['LoadBalancerArn']
        print(f"Load Balancer already exists: {load_balancer_arn}")

        # Check if the target group exists
        tg_response = elb.describe_target_groups(
            Names=[lb_targetgroup]
        )
        target_group_arn = tg_response['TargetGroups'][0]['TargetGroupArn']
        print(f"Target Group already exists: {target_group_arn}")

    except elb.exceptions.LoadBalancerNotFoundException:
        # If load balancer doesn't exist, create a new one
        response = elb.create_load_balancer(
            Name=loadbalancer_name,
            Subnets=subnet_id, 
            SecurityGroups=[security_group_id], 
            Scheme='internet-facing',
            Type='application',
            Tags=[{'Key': 'Name', 'Value': loadbalancer_name}]
        )
        load_balancer_arn = response['LoadBalancers'][0]['LoadBalancerArn']
        print(f"Load Balancer created: {load_balancer_arn}")

        # Create target group
        tg_response = elb.create_target_group(
            Name=lb_targetgroup,
            Protocol='HTTP',
            Port=80,
            VpcId=vpc_id,
            TargetType='instance',
            HealthCheckProtocol='HTTP',
            HealthCheckPort='80',
            HealthCheckPath='/',
            Matcher={'HttpCode': '200'}
        )
        target_group_arn = tg_response['TargetGroups'][0]['TargetGroupArn']
        print(f"Target Group created: {target_group_arn}")

    return load_balancer_arn, target_group_arn

# Step 6: Register EC2 Instances with Target Group
def register_instances_with_target_group(target_group_arn, instance_id):
    try:
        response = elb.register_targets(
            TargetGroupArn=target_group_arn,
            Targets=[
                {
                    'Id': instance_id,
                    'Port': 80
                }
            ]
        )
        print(f"EC2 instance {instance_id} registered with target group {target_group_arn}")

    except Exception as e:
        print(f"Error registering instance with target group: {e}")

# Step 7: Create Listener for ALB
def create_listener(load_balancer_arn, target_group_arn):
    try:
        response = elb.create_listener(
            LoadBalancerArn=load_balancer_arn,
            Protocol='HTTP',
            Port=80,
            DefaultActions=[{
                'Type': 'forward',
                'TargetGroupArn': target_group_arn
            }]
        )
        listener_arn = response['Listeners'][0]['ListenerArn']
        print(f"Listener created: {listener_arn}")


        #  # Create HTTPS listener (port 443)
        # https_response = elb.create_listener(
        #     LoadBalancerArn=load_balancer_arn,
        #     Protocol='HTTPS',
        #     Port=443,
        #     Certificates=[{
        #         'CertificateArn': certificate_arn  # provided certificate ARN
        #     }],
        #     DefaultActions=[{
        #         'Type': 'forward',
        #         'TargetGroupArn': target_group_arn
        #     }]
        # )
        # https_listener_arn = https_response['Listeners'][0]['ListenerArn']
        # print(f"HTTPS Listener created: {https_listener_arn}")

    except Exception as e:
        print(f"Error creating listener: {e}")

# Step 8: Create Launch-templete or use existing
def create_launch_template(instance_id, launch_template_name):
    try:
        # Check if Launch Template already exists
        response = ec2.describe_launch_templates(
            LaunchTemplateNames=[launch_template_name]
        )
        if response['LaunchTemplates']:
            print(f"Launch Template {launch_template_name} already exists.")
            return response['LaunchTemplates'][0]['LaunchTemplateId']

    except ec2.exceptions.ClientError as e:
        error_code = e.response['Error']['Code']
        if error_code == 'InvalidLaunchTemplateName.NotFoundException':
            print(f"Launch Template {launch_template_name} not found. Proceeding to create it.")
        else:
            print(f"Error checking for launch template: {e}")
            return None

    try:
        # Fetch instance details
        response = ec2.describe_instances(InstanceIds=[instance_id])
        instance = response['Reservations'][0]['Instances'][0]

        # Create the Launch Template
        launch_template_data = {
            'ImageId': instance['ImageId'],
            'InstanceType': instance['InstanceType'],
            'SecurityGroupIds': [sg['GroupId'] for sg in instance['SecurityGroups']],
            'TagSpecifications': [{
                'ResourceType': 'instance',
                'Tags': instance['Tags']
            }]
        }

        # Only add KeyName if it's not None
        if instance.get('KeyName'):
            launch_template_data['KeyName'] = instance['KeyName']

        response = ec2.create_launch_template(
            LaunchTemplateName=launch_template_name,
            LaunchTemplateData=launch_template_data
        )

        launch_template_id = response['LaunchTemplate']['LaunchTemplateId']
        print(f"Launch Template created: {launch_template_id}")
        return launch_template_id

    except Exception as e:
        print(f"Error creating launch template: {e}")
        return None
# Step 9: Creating Auto Scaling Group
      # Check if Auto Scaling Group exists and create if it doesn't
def auto_scaling_group(launch_template_id, target_group_arn, subnet_id, auto_scaling_group_name, desired_capacity, min_size, max_size ):
    try:
        # Check if the Auto Scaling Group already exists
        response = autoscaling.describe_auto_scaling_groups(
            AutoScalingGroupNames=[auto_scaling_group_name]
        )
        if response['AutoScalingGroups']:
            print(f"Auto Scaling Group {auto_scaling_group_name} already exists.")
            return  # ASG exists, no need to create

    except Exception as e:
        print(f"Auto Scaling Group not found or error occurred: {e}")

    # Create an Auto Scaling Group if it doesn't exist
    try:
        autoscaling.create_auto_scaling_group(
            AutoScalingGroupName=auto_scaling_group_name,
            LaunchTemplate={
                'LaunchTemplateId': launch_template_id,
                'Version': '$Latest'
            },
            MinSize=min_size,
            MaxSize=max_size,
            DesiredCapacity=desired_capacity,
            VPCZoneIdentifier=','.join(subnet_id),
            TargetGroupARNs=[target_group_arn],
            HealthCheckType='EC2',
            HealthCheckGracePeriod=300,
            Tags=[{
                'Key': 'Name',
                'Value': auto_scaling_group_name,
                'PropagateAtLaunch': True
            }]
        )
        print("Auto Scaling Group created successfully.")
    except Exception as e:
        print(f"Error creating Auto Scaling Group: {e}")


# Step 10: Creating scaling policies to scale in/out
def manage_scaling_policy(auto_scaling_group_name):
    try:
        # Check if the target tracking policy already exists
        response = autoscaling.describe_policies(
            AutoScalingGroupName=auto_scaling_group_name,
            PolicyTypes=['TargetTrackingScaling']
        )
        
        existing_policies = {policy['PolicyName'] for policy in response['ScalingPolicies']}

        # Create or update a single target tracking policy if it doesn't exist
        if 'cpu-target-tracking-policy' not in existing_policies:
            target_tracking_policy = autoscaling.put_scaling_policy(
                AutoScalingGroupName=auto_scaling_group_name,
                PolicyName='cpu-target-tracking-policy',
                PolicyType='TargetTrackingScaling',
                TargetTrackingConfiguration={
                    'PredefinedMetricSpecification': {
                        'PredefinedMetricType': 'ASGAverageCPUUtilization'  
                    },
                    'TargetValue': 70.0,  
                    'DisableScaleIn': False, 
                }
            )
            print(f"Target Tracking Policy ARN: {target_tracking_policy['PolicyARN']}")
        else:
            print("Target tracking policy already exists.")

    except Exception as e:
        print(f"Error managing scaling policy: {e}")

# Step 11: Create SNS Topic for Alerts
def create_sns_topic(sns_topic_name):
    try:
        response = sns.create_topic(Name=sns_topic_name)
        topic_arn = response['TopicArn']
        print(f"SNS topic created: {topic_arn}")
        return topic_arn
    except Exception as e:
        print(f"Error creating SNS topic: {e}")
        return None

# Step 12: Subscribe to SNS Topic
def subscribe_to_topic(topic_arn, protocol, endpoint):
    try:
        response = sns.subscribe(
            TopicArn=topic_arn,
            Protocol=protocol,
            Endpoint=endpoint  
        )
        subscription_arn = response['SubscriptionArn']
        print(f"Subscription created: {subscription_arn}")
    except Exception as e:
        print(f"Error subscribing to SNS topic: {e}")

# Step 13: Publish Message to SNS Topic
def publish_sns_message(topic_arn, subject, message):
    try:
        response = sns.publish(
            TopicArn=topic_arn,
            Subject=subject,
            Message=message
        )
        print(f"Message published to topic {topic_arn}: {response['MessageId']}")
    except Exception as e:
        print(f"Error publishing message to SNS topic: {e}")


# Full Deployment Script
def deploy_web_application():
    file_path = 'values.yaml'
    values = read_values_from_file(file_path)

    # Step 1: Create S3 Bucket
    bucket_name = create_s3_bucket(values['bucket_name'])

    # Step 2: Create Security Group
    security_group_id = create_security_group('Security group for Web App', values['security_group_name'])

    # Step 3: Launch EC2 Instance
    instance_id = launch_ec2_instance(security_group_id, values['image_id'], values['instance_type'], values['ec2_name'])
    waiter = ec2.get_waiter('instance_running')
    waiter.wait(InstanceIds=[instance_id]) 

    # Step 4: Create Load Balancer and Target group
    load_balancer_arn, target_group_arn = create_load_balancer(instance_id, security_group_id, values['subnet_id'], values['vpc_id'], values['loadbalancer_name'], values['lb_targetgroup'])

    # Step 5: Register EC2 Instances with Target Group
    register_instances_with_target_group(target_group_arn, instance_id)

    # Step 6: Create Listener for Load Balancer
    create_listener(load_balancer_arn, target_group_arn)

    # Step 7: Check/Create Launch Template
    launch_template_id = create_launch_template(instance_id, values['launch_template_name'])

    # Step 8: Create Auto Scaling Group
    auto_scaling_group_name = auto_scaling_group(launch_template_id, target_group_arn, values['subnet_id'], values['auto_scaling_group_name'], values['desired_capacity'], values['min_size'], values['max_size'])

    # Step 9: Creating Scaling policy for ASG
    manage_scaling_policy(values['auto_scaling_group_name'])

    # Step 10: Creating SNS topics for alerts
    health_alert_topic = create_sns_topic(values['sns_topic_name'])
    subscribe_to_topic(health_alert_topic, values['protocol'], values['email_id'])
    publish_sns_message(health_alert_topic, values['subject'], values['message'])

    # Store resource IDs in a JSON file
    resources = {
        'bucket_name': bucket_name,
        'security_group_id': security_group_id,
        'instance_id': instance_id,
        'load_balancer_arn': load_balancer_arn,
        'target_group_arn': target_group_arn,
        'launch_template_id': launch_template_id,
        'auto_scaling_group_name': values['auto_scaling_group_name'],
        'sns_topic': health_alert_topic
    }
    with open('resources.json', 'w') as f:
        json.dump(resources, f, indent=4)

# Run the deployment
deploy_web_application()
