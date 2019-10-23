#!/usr/bin/python3

import json
import sys

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


# Deploy API changes to each stage
def deploy_api(_client, _apigw, _stage):
    print(f'Creating deployment for {_apigw}:{_stage}')
    _client.create_deployment(
        restApiId=_apigw,
        stageName=_stage,
    )


# Notifies e-mail address that API Gateway has been modified
def send_update_notice(_email, _region, _policy, _apigw, _stage):
    SENDER = "API Gateway Updater <lavocat85@gmail.com>"
    SUBJECT = "Resource Policy Update Notification"
    BODY_HTML = f'''<html>
                <head></head>
                <body>
                <h3>A new resource policy has been deployed to your API Gateway</h3>
                <p>
                <b>API Gateway Name:</b> {_apigw} <br>
                <b>Stage:</b> {_stage} <br>
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
                    _email,
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
        print(f"Email sent to {_email}, ID:{response['MessageId']}")


# Ensure that the message contains valid API Gateway ID and Stage
def validate_message(_target_api, _stage):
    with open('map.json', 'r') as f:
        api_map = json.load(f)

    onboarded = False

    for api in api_map["apigateway"]:
        if api["id"] == _target_api:
            onboarded = True
            test_stage = api["test_stage"]
            prod_stage = api["prod_stage"]
            email = api["email"]
            break
    
    if onboarded is False:
        print("FATAL: ApiGatewayId not in map")
        return None
    else:
        if _stage == "test":
            return api["id"], test_stage, email
        elif _stage == "prod":
            return api["id"], prod_stage, email
        else:
            print('FATAL: Stage must be test or prod')
            return None

def lambda_handler(event, context):
    region = 'us-west-2'
    client = boto3.client('apigateway', region)

    # Get SQS message from Lambda event
    message = event["Records"][0]["body"]
    target_api, target_stage = message.split(':')
    # Validate message maps to an onboarded APIGateway & Stage
    api_id, stage, email = validate_message(target_api, target_stage)
    policy = read_policy()
    # Apply update to resource policy
    update_api(policy, client, api_id)
    # Create deployment for each stage
    deploy_api(client, api_id, stage)
    # Send notice that the API Gateway has been modified
    send_update_notice(email, region, policy, api_id, stage)
