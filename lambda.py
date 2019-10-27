#!/usr/bin/python3

import json

import boto3
import botocore
from botocore.exceptions import ClientError


# Read policy from file
def generate_policy(_account, _region):
    ip_list = get_ips_from_sg(_region)
    with open('policy.json', 'r') as f:
        _policy = f.read()
    _policy = _policy.replace('ACCOUNT_NUM', _account)


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

    validate_dict = {
        "api_id": None,
        "stage": None, 
        "email": None,
    }

    for api in api_map["apigateway"]:
        if api["id"] == _target_api:
            validate_dict.update({"api_id": api["id"]})
            validate_dict.update({"email": api["email"]})
            if _stage == "prod":
                validate_dict.update({"stage": api["prod_stage"]})
            elif _stage == "test":
                validate_dict.update({"stage": api["test_stage"]})
    
    return validate_dict

def get_ips_from_sg(_region):
    client = boto3.client('ec2', _region)
    response = client.describe_security_groups(GroupNames=['apigateway-poc'])
    ips = []
    for sg in response['SecurityGroups']:
        for perms in sg['IpPermissions']:
            for iprange in perms['IpRanges']:
                ips.append(iprange['CidrIp'])

    return ips


def lambda_handler(event, context):
    # Get SQS message from Lambda event
    message = event["Records"][0]["body"]
    target_api, target_stage = message.split(':')
    # Validate message maps to an onboarded APIGateway & Stage
    target_dict = {}
    target_dict = validate_message(target_api, target_stage)

    if None in target_dict.values():
        print("FATAL: Target ApiGatewayId or Stage could not be validated")
        print(f'ApiGateWayId={target_dict["api_id"]}')
        print(f'Stage={target_dict["stage"]}')
    else:
        ACCOUNT_ID = context.invoked_function_arn.split(":")[4]
        region = 'us-west-2'
        client = boto3.client('apigateway', region)
        policy = generate_policy(ACCOUNT_ID, region)
        api_id = target_dict["api_id"]
        stage = target_dict["stage"]
        email = target_dict["email"]
        # Apply update to resource policy
        update_api(policy, client, api_id)
        # Create deployment for each stage
        deploy_api(client, api_id, stage)
        # Send notice that the API Gateway has been modified
        send_update_notice(email, region, policy, api_id, stage)