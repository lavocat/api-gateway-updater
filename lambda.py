#!/usr/bin/python3

import botocore
from botocore.exceptions import ClientError

import boto3


# Read policy from file
def read_policy():
    with open('policy.json', 'r') as f:
        _policy = f.read()
    return _policy


# Update the REST API
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
def deploy_api(_client, _apigw, _stage):
    print(f'Creating deployment for {_apigw}:{_stage}')
    _client.create_deployment(
        restApiId=_apigw,
        stageName=_stage,
    )

# Notifies e-mail address that API Gateway has been modified
def send_update_notice(_region, _policy, _apigw, _stages):
    formatted_stages = ', '.join(_stages)
    SENDER = "API Gateway Updater <lavocat85@gmail.com>"
    RECIPIENT = "lavocat85@gmail.com"
    SUBJECT = "Resource Policy Update Notification"
    BODY_HTML = f'''<html>
                <head></head>
                <body>
                <h3>A new resource policy has been deployed to your API Gateway</h3>
                <p>
                <b>API Gateway Name:</b> {_apigw} <br>
                <b>Stages:</b> {formatted_stages} <br>
                <b>Policy Contents:</b>
                <br>
                </p>
                <pre>
                {_policy}
                </pre>
                </body>
                </html>
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
                    'Html': {
                        'Charset': CHARSET,
                        'Data': BODY_HTML,
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
        print(f"Email sent to {RECIPIENT}, ID:{response['MessageId']}")


def lambda_handler(event, context):
    region = 'us-west-2'
    client = boto3.client('apigateway', region)
    target = event["Records"][0]["body"]
    apigw, stage = target.split(':')

    policy = read_policy()
    # Apply update to resource policy
    update_api(policy, client, apigw)
    # Get stage names for deployment
    stage_list = get_api_stages(client, apigw)

    if stage not in stage_list:
        print("FATAL: Stage not found")
    else:
        # Create deployment for each stage
        # NOTE:
        # The console displays deployments in a weird way, 
        # each stages' deployment history contains the complete history
        # for the API Gateway, not just deployments for that stage
        deploy_api(client, apigw, stage)
        # Send notice that the API Gateway has been modified
        send_update_notice(region, policy, apigw, stage)
