import json
import os
import random
from datetime import datetime as dt

import boto3


def lambda_handler(event, context):
    # TODO - Save to DynamoDB and get the PK
    print(f"Received {event}")
    report_id = random.randint(0, 1000)

    presigned_image_url, s3_bucket, s3_image_path = create_upload_url(report_id)
    publish_topic(f"to/device/{event['client_id']}", {
        'report_id': report_id,
        'upload_url': presigned_image_url,
        'bucket': s3_bucket,
        'image_path': s3_image_path
    })


def create_upload_url(report_id):
    s3_client = boto3.client('s3')

    # AWS Bucket
    s3_bucket = os.environ['BUCKET_NAME']

    # Generate presigned product image urls:
    s3_image_path = f"{dt.now().year}/{dt.now().month}/{dt.now().day}/{dt.now().hour}/{report_id}.jpg"

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

    print(f"presigned_image_url: {presigned_image_url}")

    return presigned_image_url, s3_bucket, s3_image_path


def publish_topic(topic, message):
    client = boto3.client('iot-data', region_name='us-east-1')
    response = client.publish(
        topic=topic,
        qos=1,
        payload=json.dumps(message)
    )
    print(f"Sent message to topic {topic}: {message}")
    print(f"Response: {response}")
