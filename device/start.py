import logging
import os
from device import capture_video
from device import mqtt


logger = logging.getLogger(__name__)


def init_logger():
    FORMAT = '%(asctime)-15s %(levelno)s %(name)s %(funcName)s - %(message)s'
    logging.basicConfig(format=FORMAT, level=logging.INFO)
    logger = logging.getLogger(__name__)
    logger.info("Starting")


def start_capture():
    capture_video.init(os.environ.get('DISPLAY_VIDEO') == '1', 10, None)
    # capture_video.init(True, 600, "test1.mp4")

    logger.info("Initialized successfully. Start capturing...")
    capture_video.capture()


if __name__ == '__main__':
    init_logger()
    mqtt.Mqtt().connect({'topic': 'to/device/raspberrypi_edi'})
    start_capture()
