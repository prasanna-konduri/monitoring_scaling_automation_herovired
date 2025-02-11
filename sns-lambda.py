import json
import boto3

sns_client = boto3.client('sns')

def lambda_handler(event, context):
    message = {
        "alert": "High traffic detected",
        "timestamp": str(context.aws_request_id)  
    }
    with open('resources.json', 'r') as f:
            resources = json.load(f)

    response = sns_client.publish(
        TopicArn=resources['sns_topic'],
        Message=json.dumps(message),
        Subject='Alert Notification'
    )
    
    return {
        'statusCode': 200,
        'body': json.dumps('Notification sent!')
    }
