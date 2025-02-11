import boto3
import json
import time

AWS_REGION = 'us-west-2'

# Create a session using 'herovired' profile
session = boto3.Session(profile_name="herovired", region_name=AWS_REGION)

# Initialize all clients
s3 = session.client('s3')
ec2 = session.client('ec2')
elb = session.client('elbv2')
autoscaling = session.client('autoscaling')
sns = session.client('sns')

def delete_resources():
    try:
        with open('resources.json', 'r') as f:
            resources = json.load(f)

        # Deleting S3 bucket
        try:
            print(f"Deleting S3 bucket: {resources['bucket_name']}...")
            s3.delete_bucket(Bucket=resources['bucket_name'])
            print("S3 bucket deleted successfully.")
        except s3.exceptions.ClientError as e:
            print(f"Error deleting S3 bucket: {e}")

        # Deleting Auto Scaling Group
        try:
            print(f"Deleting Auto Scaling Group: {resources['auto_scaling_group_name']}...")
            autoscaling.delete_auto_scaling_group(AutoScalingGroupName=resources['auto_scaling_group_name'], ForceDelete=True)
            print("Auto Scaling Group deleted successfully.")
        except Exception as e:
            print(f"Error deleting Auto Scaling Group: {e}")

        # Deleting Launch Templete
        try:
            print(f"Deleting Launch Template: {resources['launch_template_id']}...")
            ec2.delete_launch_template(LaunchTemplateId=resources['launch_template_id'])
            print("Launch Template deleted successfully.")
        except Exception as e:
            print(f"Error deleting Launch Template: {e}")

        # Deleting Load Balancer
        try:
            print(f"Deleting Load Balancer: {resources['load_balancer_arn']}...")
            elb.delete_load_balancer(LoadBalancerArn=resources['load_balancer_arn'])
            print("Load Balancer deleted successfully.")
        except elb.exceptions.LoadBalancerNotFoundException:
            print("Load Balancer not found. It may have already been deleted.")
        except Exception as e:
            print(f"Error deleting Load Balancer: {e}")

        # Deleting EC2 instance
        try:
            print(f"Terminating EC2 Instance: {resources['instance_id']}...")
            ec2.terminate_instances(InstanceIds=[resources['instance_id']])
            waiter = ec2.get_waiter('instance_terminated')
            print("Waiting for instance to terminate...")
            waiter.wait(InstanceIds=[resources['instance_id']])
            print("EC2 Instance terminated successfully.")
        except Exception as e:
            print(f"Error terminating EC2 Instance: {e}")

        # Deleting Target Group
        try:
            print(f"Deleting Target Group: {resources['target_group_arn']}...")
            elb.delete_target_group(TargetGroupArn=resources['target_group_arn'])
            time.sleep(60)
            print("Target Group deleted successfully.")
        except elb.exceptions.TargetGroupNotFoundException:
            print("Target Group not found. It may have already been deleted.")
        except Exception as e:
            print(f"Error deleting Target Group: {e}")

        # Deleting Security Group
        try:
            print(f"Deleting Security Group: {resources['security_group_id']}...")
            ec2.delete_security_group(GroupId=resources['security_group_id'])
            print("Security Group deleted successfully.")
        except ec2.exceptions.ClientError as e:
            print(f"Error deleting Security Group: {e}")

        # Deleting SNS Topic
        try:
            print(f"Deleting SNS Topic: {resources['sns_topic']}...")
            sns.delete_topic(TopicArn=resources['sns_topic'])
            print("SNS Topic deleted successfully.")
        except sns.exceptions.ClientError as e:
            print(f"Error deleting SNS Topic: {e}")

        print("Resource deletion process completed.")

    except Exception as e:
        print(f"An error occurred during resource deletion: {e}")

# Call the delete_resources function
delete_resources()
