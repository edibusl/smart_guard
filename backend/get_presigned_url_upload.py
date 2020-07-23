import json
import os
import random
from datetime import datetime as dt

import boto3


def lambda_handler(event, context):
    s3_client = boto3.client('s3')

    # AWS Bucket
    s3_bucket = os.environ['BUCKET_NAME']

    # Generate presigned product image urls:
    s3_image_path = f"{dt.now().year}/{dt.now().month}/{dt.now().day}/{dt.now().hour}/{dt.now().minute}_{dt.now().second}.jpg"

    presigned_image_url = s3_client.generate_presigned_post(
        Bucket=s3_bucket,
        Key=s3_image_path,
        Fields={"acl": "private", "Content-Type": "jpeg"},
        Conditions=[
            {"acl": "private"},
            {"Content-Type": "jpeg"}
        ],
        ExpiresIn=3600
    )

    return {
        'statusCode': 200,
        'body': json.dumps({
            'upload_url': presigned_image_url,
            'bucket': s3_bucket,
            'image_path': s3_image_path
        })
    }