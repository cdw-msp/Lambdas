import boto3
def lambda_handler(event, context):
    dynamodb = boto3.resource('dynamodb')
    s3 = boto3.resource('s3')
    table = dynamodb.Table('BLUEMOON_MOVIE')
    response = table.scan()
    html='''
    <html>
   <head>
      <title>BlueMoon Movie</title>
   </head>
   <body>
      <table border = "1">
         <tr>
            <th>MOVIE </th>
            <th>MOVIE_TIME</th>
            <th>MOVIE_COUNT</th>
         </tr>
    '''
    for i in response['Items']:
        html=html+"<tr><td>"+i["MOVIE"]+"</td><td>"+i["MOVIE_TIME"]+"</td><td>"+str(i["MOVIE_COUNT"])+"</td></tr>"
    html=html+'''
            </table>
        </body>
        </html> 
    '''
    s3.Bucket('bluemoon-movie.awsmanagedbycdw.com').put_object(Key='index.html', Body=html, ContentType='text/html')
    object_acl = s3.ObjectAcl('bluemoon-movie.awsmanagedbycdw.com','index.html')
    response = object_acl.put(ACL='public-read')
    return html