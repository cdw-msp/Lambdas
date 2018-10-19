import boto3
import botocore
import json


ec2 = boto3.client("ec2")
def lambda_handler(event, context):
    print(event)
    message = event["Records"][0]["Sns"]["Message"]
    message = json.loads(message)
    group_id = message["groupId"]
    permissions = message["permissions"]
    try:
        ec2.revoke_security_group_ingress(GroupId=group_id, IpPermissions=permissions)
    except botocore.exceptions.ClientError as e:
        print(e)