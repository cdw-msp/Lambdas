# Please uncomment the below code as it fit your needs.

from __future__ import print_function
import boto3
import base64
from json import loads

dynamodb_client = boto3.client('dynamodb')
s3_client = boto3.client('s3')
# The block below creates the DDB table with the specified column names.

table_name ='BLUEMOON_MOVIE'
row_id ='MOVIE'
row_timestamp ='MOVIE_TIME'
count ='MOVIE_COUNT'

try:
    response = dynamodb_client.create_table(
        AttributeDefinitions=[
            {
                'AttributeName': row_id,
                'AttributeType': 'S',
            },
            {
                'AttributeName': row_timestamp,
                'AttributeType': 'S',
            }
        ],
        KeySchema=[
            {
                'AttributeName': row_id,
                'KeyType': 'HASH',
            },
            {
                'AttributeName': row_timestamp,
                'KeyType': 'RANGE',
            },
        ],
        ProvisionedThroughput={
            'ReadCapacityUnits': 5,
            'WriteCapacityUnits': 5,
        },
        TableName=table_name
    )
except dynamodb_client.exceptions.ResourceInUseException:
    # Table is created, skip
    pass



def lambda_handler(event, context):
    payload = event['records']
    output = []
    success = 0
    failure = 0

    for record in payload:
        try:
            # # This block parses the record, and writes it to the DDB table.
            
            payload = base64.b64decode(record['data'])
            data_item = loads(payload)

            ddb_item = { row_id: { 'S': data_item[row_id] },
                count: { 'N': str(data_item[count]) },
                row_timestamp: { 'S': data_item[row_timestamp] }
            }
            dynamodb_client.put_item(TableName=table_name, Item=ddb_item)
            #s3_client.Bucket('bluemoon-movie.awsmanagedbycdw.com').put_item(Key=(data_item[row_id]+'_'+data_item[row_timestamp]),Body=payload)
            

            success += 1
            output.append({'recordId': record['recordId'], 'result': 'Ok'})
        except Exception:
            failure += 1
            output.append({'recordId': record['recordId'], 'result': 'DeliveryFailed'})

    print('Successfully delivered {0} records, failed to deliver {1} records'.format(success, failure))
    return {'records': output}
