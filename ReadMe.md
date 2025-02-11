### AWS Web Application Infrastructure Project

This project automates the deployment and management of a scalable web application infrastructure on AWS using Python and boto3.

### Project Overview

This system automatically manages the lifecycle of a web application hosted on EC2 instances, monitors its health, and scales resources based on traffic. It also notifies administrators about infrastructure health and scaling events.

### Components

1. Web Application Deployment
2. Load Balancing with ELB
3. Auto Scaling Group (ASG) Configuration
4. SNS Notifications
5. Infrastructure Automation
6. Dynamic Content Handling (Optional Enhancement)

### Step-by-Step Flow

1. **Setup and Configuration**
   - Install required libraries (boto3, etc.)
   - Configure AWS credentials

2. **S3 Bucket Creation**
   - Create an S3 bucket for static files
   - Upload static content to the bucket

3. **EC2 Instance Deployment**
   - Launch an EC2 instance
   - Install and configure web server (Apache/Nginx)
   - Deploy web application code

4. **Load Balancer Setup**
   - Create an Application Load Balancer (ALB)
   - Configure listeners and target groups
   - Register EC2 instance(s) with the ALB

5. **Auto Scaling Group Configuration**
   - Create a launch template or configuration
   - Set up an Auto Scaling Group
   - Define scaling policies (CPU utilization, network traffic)

6. **SNS Topic Creation**
   - Create SNS topics for different alert types
   - Set up subscription(s) for admin notifications

7. **Lambda Function for Notifications**
   - Create a Lambda function to process SNS messages
   - Configure the function to send emails or SMS

8. **CloudWatch Alarms**
   - Set up alarms for monitoring (CPU, network, etc.)
   - Link alarms to appropriate SNS topics

9. **S3 Event Triggers (Optional)**
   - Configure S3 event notifications for user uploads
   - Create a Lambda function to process uploads and update the database

10. **Infrastructure Automation Script**
    - Develop a Python script using boto3 to:
      - Deploy the entire infrastructure
      - Update components as needed
      - Tear down the infrastructure when no longer needed

11. **Testing and Validation**
    - Test the deployment process
    - Verify auto-scaling functionality
    - Confirm SNS notifications are working

12. **Documentation**
    - Update README with setup and usage instructions
    - Document any configuration parameters or environment variables

### Setup and Usage

1. Clone this repository:
   ```
   git clone https://github.com/MrSRE/Monitoring-Scalling-Automation.git
   cd aws-webapp-infrastructure
   ```

2. Install required dependencies:
   ```
   pip install -r requirements.txt
   ```

3. Configure AWS credentials:
   ```
   aws configure
   ```

4. Update the configuration file `values.yaml` with your specific settings.

5. Run the main deployment script:
   ```
   python main.py
   ```

6. To tear down the infrastructure:
   ```
   python delete.py
   ```

#### Steps

1. First update required values in values.yaml file
2. execute app.py file, it will take values from values.yaml file, initially script will check resorces is there or not, if there it will use exiting else create new one.
3. Once script completely executed all resources id will store in resources.json file
4. By json and delete.py file delete all resources.

#### Main.py file explaination
1. creating s3 bucket
2. creating security group
3. creating ec2 instance and install nginx 
4. Creating Load balancer and Targeting groups
5. Register EC2 Instances with Target Group
6. Creating Listners for LB
7. Create Launch-templete for ASG
8. Creating Auto Scaling Group using previously created launch templete
9. Creating dynamic scaling policy for in/out
10. Create SNS Topic for Alert
11. Subscribe to SNS Topic
12. Publish Message to SNS Topic
