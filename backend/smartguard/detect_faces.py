try:
  import unzip_requirements
except ImportError:
  pass


# Needed for detection and embeddings extraction
import io
import re
import json
import boto3
import imutils
import cv2
import os
import logging
import numpy as np
import pickle

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def handler(event, context):
    logger.info("Starting")
    logger.info(event)

    args = {
        'bucket': 'smart-guard-files',
        's3_image_filepath':  event['Records'][0]['s3']['object']['key'],
        'local_image_filepath': '/tmp/image.jpg',
        'detector': 'models/face_detection_model',
        'embedding_model': 'models/embeddings/openface_nn4.small2.v1.t7',
        'recognizer_model': 'models/recognizer/recognizer.pickle',
        'le': 'models/recognizer/le.pickle',
        'confidence': 0.3
    }

    if any(txt in args['s3_image_filepath'] for txt in ['features', 'recognition']):
        logger.info(f"Skipping file {args['s3_image_filepath']}")

        return
    
    logger.info(f"Handling S3 image file {args['s3_image_filepath']}")

    # load our serialized face detector from disk
    logger.info("loading face detector...")
    protoPath = os.path.sep.join([args["detector"], "deploy.prototxt"])
    modelPath = os.path.sep.join([args["detector"], "res10_300x300_ssd_iter_140000.caffemodel"])
    detector = cv2.dnn.readNetFromCaffe(protoPath, modelPath)

    # load our serialized face embedding model from disk
    logger.info("loading face recognizer...")
    embedder = cv2.dnn.readNetFromTorch(args["embedding_model"])

    # load the actual face recognition model along with the label encoder
    recognizer = pickle.loads(open(args["recognizer_model"], "rb").read())
    le = pickle.loads(open(args["le"], "rb").read())

    # load the image, resize it to have a width of 600 pixels (while maintaining the aspect ratio), and then grab the image dimensions
    logger.info(f"Downloading file from s3://{args['bucket']}/{args['s3_image_filepath']}")
    s3 = boto3.client('s3')
    try:
        s3.download_file(args['bucket'], args['s3_image_filepath'], args['local_image_filepath'])
    except Exception:
        logger.exception("")
        return
    logger.info("Downloaded file successfully")

    image = cv2.imread(args['local_image_filepath'])
    image = imutils.resize(image, width=600)
    (h, w) = image.shape[:2]

    logger.info(f"Image size - h: {h}, w: {w}")

    # construct a blob from the image
    image_blob = cv2.dnn.blobFromImage(cv2.resize(image, (300, 300)), 1.0, (300, 300), (104.0, 177.0, 123.0), swapRB=False, crop=False)

    # apply OpenCV's deep learning-based face detector to localize
    # faces in the input image
    detector.setInput(image_blob)
    detections = detector.forward()
    recognition_resuls = {}

    # loop over the detections
    for i in range(0, detections.shape[2]):
        # extract the confidence (i.e., probability) associated with the
        # prediction
        confidence = detections[0, 0, i, 2]

        # filter out weak detections
        if confidence > args["confidence"]:
            logger.info(f"Found high confidence: {confidence}. Conf confidence: {args['confidence']}")

            # compute the (x, y)-coordinates of the bounding box for the
            # face
            box = detections[0, 0, i, 3:7] * np.array([w, h, w, h])
            (startX, startY, endX, endY) = box.astype("int")

            # extract the face ROI
            face = image[startY:endY, startX:endX]
            (fH, fW) = face.shape[:2]

            # ensure the face width and height are sufficiently large
            if fW < 20 or fH < 20:
                continue

            # construct a blob for the face ROI, then pass the blob
            # through our face embedding model to obtain the 128-d
            # quantification of the face
            faceBlob = cv2.dnn.blobFromImage(face, 1.0 / 255, (96, 96), (0, 0, 0), swapRB=True, crop=False)
            embedder.setInput(faceBlob)
            vec = embedder.forward()

            logger.debug(f"Found vec: {vec}")

            # perform classification to recognize the face
            preds = recognizer.predict_proba(vec)[0]
            j = np.argmax(preds)
            proba = preds[j]
            name = le.classes_[j]

            # draw the bounding box of the face along with the associated
            # probability
            recognition_resuls[name] = {
                'probability': int(proba * 100),
                'start_x': startX,
                'start_y': startY,
                'end_x': endX,
                'end_y': endY
            }

    if not recognition_resuls:
        logger.info("Didn't find any recognition results")

    month, report_time = parse_key(args['s3_image_filepath'])
    update_dynamo(month.replace('/', '_'), report_time, recognition_resuls)

    if recognition_resuls:
        # Choose best result
        best_recognition_key = max(recognition_resuls, key=lambda k: recognition_resuls[k]['probability'])
        best_recognition = recognition_resuls[best_recognition_key]
        logger.info(f"Recognition Results: {recognition_resuls}.\nBest: {best_recognition_key}")

        upload_recognitions_image(image, best_recognition_key, best_recognition, month, report_time)


def parse_key(s3_file_key):
    """
    2020/09/28_09_14_26_283950__test1.jpg
    2020/09/28_09_14_26_283950.jpg
    """
    s3_file_key = s3_file_key.replace('__test1', '')
    match = re.match("([0-9]{4}/[0-9]{2})/(.*).jpg", s3_file_key)
    month = match.group(1)
    report_time = match.group(2)

    return month, report_time


def update_dynamo(month, report_time, recognitions):
    table = boto3.resource('dynamodb').Table('detections')

    # get item
    dynamo_key = {'month': month, 'report_time': report_time}
    response = table.get_item(Key=dynamo_key)
    if not response or not response.get('Item'):
        logger.info(f"Couldn't find key in DynamoDB. Dynamo key: {dynamo_key}")
        return

    # update
    item = response['Item']
    item['recognitions'] = [{k: v['probability']} for k, v in recognitions.items()]

    # put (idempotent)
    table.put_item(Item=item)

    logger.info("Updated DynamoDB successfully")


def upload_recognitions_image(image, best_recognition_key, best_recognition, month, report_time):
    # Draw rectangle and text
    text = f"{best_recognition_key} ({best_recognition['probability']}%)"
    y = best_recognition['start_y'] - 10 if best_recognition['start_y'] - 10 > 10 else best_recognition['start_y'] + 10
    cv2.rectangle(image, (best_recognition['start_x'], best_recognition['start_y']), (best_recognition['end_x'], best_recognition['end_y']),
                  (0, 0, 255), 2)
    cv2.putText(image, text, (best_recognition['start_x'], y), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 255), 2)
    encoded_image_bytes = cv2.imencode('.jpg', image)[1]
    stream = io.BytesIO(encoded_image_bytes)

    # Upload new image with rectangle and text
    s3 = boto3.client('s3')
    s3.upload_fileobj(stream, 'smart-guard-files', f"{month}/{report_time}_recognition.jpg")
    logger.info("Uploaded recognitions image successfully")


if __name__ == '__main__':
    with open('mocks/detectf_s3_object_create_mock.json', 'r') as mock_file:
        event_dict = json.load(mock_file)
        handler(event_dict, None)
