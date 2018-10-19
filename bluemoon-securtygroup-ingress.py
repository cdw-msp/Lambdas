import boto3
import botocore
import json

 
APPLICABLE_RESOURCES = ["AWS::EC2::SecurityGroup"]


# normalize_parameters
#
# Normalize all rule parameters so we can handle them consistently.
# All keys are stored in lower case.  Only boolean and numeric keys are stored.

def normalize_parameters(rule_parameters):
    for key, value in rule_parameters.iteritems():
        normalized_key=key.lower()
        normalized_value=value.lower()

        if normalized_value == "true":
            rule_parameters[normalized_key] = True
        elif normalized_value == "false":
            rule_parameters[normalized_key] = False
        elif normalized_value.isdigit():
            rule_parameters[normalized_key] = int(normalized_value)
        else:
            rule_parameters[normalized_key] = True
    return rule_parameters

def evaluate_compliance(configuration_item, debug_enabled, arn, revoked_permissions):
    if configuration_item["resourceType"] not in APPLICABLE_RESOURCES:
        return {
            "compliance_type" : "NOT_APPLICABLE",
            "annotation" : "The rule doesn't apply to resources of type " +
            configuration_item["resourceType"] + "."
        }

    if configuration_item["configurationItemStatus"] == "ResourceDeleted":
        return {
            "compliance_type": "NOT_APPLICABLE",
            "annotation": "The configurationItem was deleted and therefore cannot be validated."
        }

    group_id = configuration_item["configuration"]["groupId"]
    client = boto3.client("ec2");
    sns = boto3.client("sns")
    lambda_client = boto3.client('lambda')
    try:
        response = client.describe_security_groups(GroupIds=[group_id])
    except botocore.exceptions.ClientError as e:
        return {
            "compliance_type" : "NON_COMPLIANT",
            "annotation" : "describe_security_groups failure on group " + group_id
        }
        
    if debug_enabled:
        print("security group definition: ", json.dumps(response, indent=2))

    ip_permissions = response["SecurityGroups"][0]["IpPermissions"]
    # authorize_permissions = [item for item in REQUIRED_PERMISSIONS if item not in ip_permissions]
    revoke_permissions = [item for item in revoked_permissions if item in ip_permissions]

    if revoke_permissions:
        annotation_message = "Permissions were modified."
    else:
        annotation_message = "Permissions are correct."

    if revoke_permissions:
        if debug_enabled:
            print("revoking for ", group_id, ", ip_permissions ", json.dumps(revoke_permissions, indent=2))

        try:
            #client.revoke_security_group_ingress(GroupId=group_id, IpPermissions=revoke_permissions)
            message = {"groupId": group_id, "permissions": revoke_permissions}
            response = sns.publish(
                 TopicArn=arn,
                 MessageStructure='json',
                 Message=json.dumps({"default":json.dumps(message)})
            )
            # invoke_response = lambda_client.invoke(FunctionName="ingress-delete-no-sns",
            # InvocationType='Event',
            # Payload=json.dumps(message))
            return {
                "compliance_type": "NON_COMPLIANT",
                "annotation": annotation_message
                    }
        except botocore.exceptions.ClientError as e:
            return {
                "compliance_type" : "NON_COMPLIANT",
                "annotation" : "revoke_security_group_ingress failure on group " + group_id
            }

    return {
        "compliance_type": "COMPLIANT",
        "annotation": annotation_message
    }

# lambda_handler
# 
# This is the main handle for the Lambda function.  AWS Lambda passes the function an event and a context.
# If "debug" is specified as a rule parameter, then debugging is enabled.

def lambda_handler(event, context):
    invoking_event = json.loads(event['invokingEvent'])
    configuration_item = invoking_event["configurationItem"]
    rule_parameters = normalize_parameters(json.loads(event["ruleParameters"]))
    non_normalized_parameters = json.loads(event["ruleParameters"])

    debug_enabled = False

    if "debug" in rule_parameters:
        debug_enabled = rule_parameters["debug"] 
    if "sns" in non_normalized_parameters:
        arn = non_normalized_parameters["sns"]
    if "ip" in non_normalized_parameters:
        ip = non_normalized_parameters["ip"]
    if "port" in non_normalized_parameters:
        port = non_normalized_parameters["port"]
    port = int(port)
    revoked_permissions = [
        {
        "IpProtocol" : "tcp",
        "FromPort" : port,
        "ToPort" : port,
        "UserIdGroupPairs" : [],
        "IpRanges" : [{"CidrIp" : ip}],
        "PrefixListIds" : [],
        "Ipv6Ranges": []
        }]

    if debug_enabled:
        print("Received event: " + json.dumps(event, indent=2))
        

    evaluation = evaluate_compliance(configuration_item, debug_enabled, arn, revoked_permissions)

    config = boto3.client('config')

    response = config.put_evaluations(
       Evaluations=[
           {
               'ComplianceResourceType': invoking_event['configurationItem']['resourceType'],
               'ComplianceResourceId': invoking_event['configurationItem']['resourceId'],
               'ComplianceType': evaluation["compliance_type"],
               "Annotation": evaluation["annotation"],
               'OrderingTimestamp': invoking_event['configurationItem']['configurationItemCaptureTime']
           },
       ],
       ResultToken=event['resultToken'])