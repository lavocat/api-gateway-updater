import botocore
from botocore.exceptions import ClientError

import boto3


def read_policy():
    with open('policy.json', 'r') as f:
        _policy = f.read()
    return _policy


# Read in policy from a file and update the rest api
def update_api(_policy, _client, _apigw):
    print(f'Replacing resource policy on {_apigw}')
    _client.update_rest_api(
        restApiId=_apigw,
        patchOperations=[
            {
                'op': 'replace',
                'path': '/policy',
                'value': _policy
            },
        ]
    )


# Get all currently active stages
def get_api_stages(_client, _apigw):
    _stage_list = []
    _stages = _client.get_stages(
        restApiId=_apigw
    )
    for stage in _stages["item"]:
        _stage_list.append(stage["stageName"])

    return _stage_list


# Deploy API changes to each stage
def deploy_api(_client, _apigw, _stage_list):
    for stage in _stage_list:
        print(f'Creating deployment for {_apigw}:{stage}')
        _client.create_deployment(
            restApiId=_apigw,
            stageName=stage,
        )

# Notifies e-mail address that API Gateway has been modified
def send_update_notice(_region, _policy):
    SENDER = "Sender Name <lavocat85@gmail.com>"
    RECIPIENT = "lavocat85@gmail.com"
    SUBJECT = "Resource Policy Update Notification"
    # The email body for recipients with non-HTML email clients.
    BODY_TEXT = f'''
                Greetings,
                The resource policy attached to your API Gateway
                has been automatically updated.
                Policy contents:
                {_policy}
                '''
    CHARSET = "UTF-8"
    _client = boto3.client('ses', _region)
    # Try to send the email.
    try:
        #Provide the contents of the email.
        response = _client.send_email(
            Destination={
                'ToAddresses': [
                    RECIPIENT,
                ],
            },
            Message={
                'Body': {
                    'Text': {
                        'Charset': CHARSET,
                        'Data': BODY_TEXT,
                    },
                },
                'Subject': {
                    'Charset': CHARSET,
                    'Data': SUBJECT,
                },
            },
            Source=SENDER,
        )
    except ClientError as e:
        print(e.response['Error']['Message'])
    else:
        print(f"Email sent to {RECIPIENT}, Message ID:{response['MessageId']}"),

def lambda_handler(event, context):
    region = 'us-west-2'
    client = boto3.client('apigateway', region)
    apigw = 'a5vvhhkki4'

    policy = read_policy()
    # Apply update to resource policy
    update_api(policy, client, apigw)
    # Get stage names for deployment
    stage_list = get_api_stages(client, apigw)
    # Create deployment for each stage
    # NOTE:
    # The console displays deployments in a weird way, 
    # each stages' deployment history contains the complete history
    # for the API Gateway, not just deployments for that stage
    deploy_api(client, apigw, stage_list)
    # Send notice that the API Gateway has been modified
    send_update_notice(region, policy)
