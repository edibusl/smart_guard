import json
import os
from datetime import datetime as dt

import boto3


def lambda_handler(event, context):
    print(f"Received {event}")

    # Save record in DynamoDB
    record = create_record(event)
    save_dynamo_db(record)

    # Prepare s3 image file upload details and send the topic back to device
    body = {
        'month': record['month'],
        'report_time': record['report_time'],
        'frame_upload': {},
        'frame_features_upload': {}
    }
    fill_image_upload_url(body, record['s3_frame']['s3_filepath'], 'frame_upload')
    fill_image_upload_url(body, record['s3_frame_features']['s3_filepath'], 'frame_features_upload')
    publish_topic(f"to/device/{event['client_id']}", body)


def fill_image_upload_url(body, filepath, out_key):
    presigned_image_url, s3_bucket, s3_image_path = create_upload_url(filepath)
    body[out_key] = {
        'upload_url': presigned_image_url,
        'bucket': s3_bucket,
        'image_path': s3_image_path,
    }


def create_record(event):
    now = dt.now()
    report_time = f"{now.day:02}_{now.hour:02}_{now.minute:02}_{now.second:02}_{now.microsecond}"
    s3_filename = f"{report_time}.jpg"
    s3_filepath = f"{dt.now().year}/{dt.now().month:02}/{s3_filename}"
    s3_features_filename = f"{report_time}_features.jpg"
    s3_features_filepath = f"{dt.now().year}/{dt.now().month:02}/{s3_features_filename}"

    record = {
        **event,
        'month': f"{now.year}_{now.month}",  # DynamoDB Partition Key
        'report_time': report_time,  # DynamoDB Sort Key
        's3_frame': {
            's3_filename': s3_filename,
            's3_filepath': s3_filepath
        },
        's3_frame_features': {
            's3_filename': s3_features_filename,
            's3_filepath': s3_features_filepath
        }
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
