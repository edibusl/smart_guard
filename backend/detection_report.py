import json
import os
from datetime import datetime as dt

import boto3


def lambda_handler(event, context):
    print(f"Received {event}")

    # Save record in DynamoDB
    record = create_record(event)
    save_dynamo_db(record)

    presigned_image_url, s3_bucket, s3_image_path = create_upload_url(record['s3_filepath'])
    publish_topic(f"to/device/{event['client_id']}", {
        'month': record['month'],
        'report_time': record['report_time'],
        'upload_url': presigned_image_url,
        'bucket': s3_bucket,
        'image_path': s3_image_path
    })


def create_record(event):
    now = dt.now()
    report_time = f"{now.day}_{now.hour}_{now.minute}_{now.second}_{now.microsecond}"
    s3_filename = f"{report_time}.jpg"
    s3_filepath = f"{dt.now().year}/{dt.now().month}/{s3_filename}"

    record = {
        **event,
        'month': f"{now.year}_{now.month}",  # DynamoDB Partition Key
        'report_time': report_time,  # DynamoDB Sort Key
        's3_filename': s3_filename,
        's3_filepath': s3_filepath
    }

    return record


def save_dynamo_db(record):
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table('detections')
    response = table.put_item(Item=record)

    return response


def create_upload_url(s3_image_path):
    s3_client = boto3.client('s3')

    # AWS Bucket
    s3_bucket = os.environ['BUCKET_NAME']

    # Generate presigned product image urls:
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
