import io
from typing import List, Any

import cv2
import requests

from device.common import MonitoredFrame
from device import video_processing


def send_motion_frames(frames: List[MonitoredFrame], upload_url_data: dict) -> None:
    # TODO - Send concurrently
    """
    Send only the face in the frame (extract a larger area around the head)
    If no face, send only metadata
    """
    for monitored_frame in frames:
        # Upload head only if possible
        blurred_frame = video_processing.blur(monitored_frame.frame, monitored_frame.faces)

        # Compress frame to jpg and convert ndarray to a stream
        encoded_image_bytes = cv2.imencode('.jpg', blurred_frame)[1]
        stream = io.BytesIO(encoded_image_bytes)

        upload_file_s3(upload_url_data, stream)


def get_upload_url_data() -> dict:
    response = requests.get('https://3yhxtqrdvk.execute-api.us-east-1.amazonaws.com/default/getPresignedUrl')
    res = response.json()

    return res['upload_url']


def upload_file_s3(upload_url_data: dict, frame_stream: Any) -> None:
    url = upload_url_data['url']

    """
    curl -X POST \
      https://smart-guard-files.s3.amazonaws.com/ \
      -H 'cache-control: no-cache' \
      -H 'content-type: multipart/form-data; boundary=----WebKitFormBoundary7MA4YWxkTrZu0gW' \
      -F AWSAccessKeyId=ASI... \
      -F signature=YzATDe... \
      -F policy=eyJleHBpc... \
      -F Content-Type=jpeg \
      -F key=4446.jpg \
      -F 'x-amz-security-token=IQoJb3JpZ2luX2VjEHoaCXVzLWVhc3Qt...' \
      -F acl=private \
      -F file=@9076.jpg
    """

    response = requests.post(url, data=upload_url_data['fields'], files={
        'file': (upload_url_data['fields']['key'], frame_stream, 'image/jpeg')
    })

    if 300 > response.status_code >= 200:
        print("Uploaded frame successfully")
    else:
        print("Failed uploading frame. " + response.text)


if __name__ == '__main__':
    # Testing
    from datetime import datetime as dt
    img = cv2.imread('/home/edi/Downloads/9076.jpg', 1)
    frame = MonitoredFrame(time=dt.now(), frame=img, objects=[], faces=[], score=0)
    send_motion_frames([frame])
