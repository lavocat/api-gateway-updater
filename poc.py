import json
import logging
import pprint

import boto3

# Configuration items
pp = pprint.PrettyPrinter(indent=4)
logging.basicConfig(level=logging.INFO)


# Get current deployments (Probably not required)
def get_api_deployments(_client, _apigw):
    _deployments = _client.get_deployments(
        restApiId=_apigw
    )
    return _deployments


# Get all currently active stages
def get_api_stages(_client, _apigw):
    _stage_list = []
    _stages = _client.get_stages(
        restApiId=_apigw
    )
    for stage in _stages["item"]:
        _stage_list.append(stage["stageName"])

    return _stage_list


# Read in policy from a file and update the rest api
def update_api(_client, _apigw):
    with open('policy.json', 'r') as f:
        policy = f.read()
    logging.info(f'Replacing resource policy on {_apigw}')
    _client.update_rest_api(
        restApiId=_apigw,
        patchOperations=[
            {
                'op': 'replace',
                'path': '/policy',
                'value': policy
            },
        ]
    )

# Deploy API changes to each stage
def deploy_api(_client, _apigw, _stage_list):
    for stage in _stage_list:
        logging.info(f'Creating deployment for {_apigw}:{stage}')
        _client.create_deployment(
            restApiId=_apigw,
            stageName=stage,
        )


# TODO: Complete, or more likely de-scope this
# Validate current resource policy against update policy
def validate_api_changes(_client, _apigw):
    _validate = _client.get_rest_api(
        restApiId=_apigw
    )
    json_policy = json.loads(_validate["policy"].replace("\\", ""))
    for statement in json_policy["Statement"]:
        ranges = statement["Condition"]["IpAddress"]["aws:SourceIp"]

    return ranges


if __name__ == '__main__':
    session = boto3.Session(profile_name='default')
    client = session.client('apigateway')

    apigw = 'a5vvhhkki4'

    # Apply update to resource policy
    update_api(client, apigw)

    # Get stage names for deployment
    stage_list = get_api_stages(client, apigw)

    # Create deployment for each stage
    # NOTE:
    # The console displays deployments in a weird way, 
    # each stages' deployment history contains the complete history
    # for the API Gateway, not just deployments for that stage

    deploy_api(client, apigw, stage_list)

    #TODO: Compare current resource policy against provided policy.json
    whitelist = validate_api_changes(client, apigw)
    print(whitelist)
