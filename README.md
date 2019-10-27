API Gateway Updater
======

Lambda function to automate updating the resource policy on an API Gateway and creating a deployment.  This is useful for controlling the resource policy outside of your build pipeline e.g. rapidly changing whitelist/blacklist requirements.

SQS messages should be in the following format `apigateway-id:target-stage` for example `ada9dad:default`
