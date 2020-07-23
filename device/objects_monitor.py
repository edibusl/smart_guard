import sys
import itertools

from datetime import datetime as dt
from typing import List
from collections import deque

from numpy import ndarray

from device.common import FrameObject, MonitoredFrame
from device import frames_sender


SEND_BAD_FRAMES_WITH_MOTION_AFTER_SEC = 60
SKIP_CHECKS_AFTER_UPLOAD_MIN = 7
CHECK_ACTIVITY_PERIOD_SEC = 5

this = sys.modules[__name__]
this.circular_buffer = None
this.last_activity_check = None
this.last_motion_detection = None
this.last_frame_sent = None
this.last_good_frame_sent = None
this.fps = None


def init(fps: int) -> None:
    this.fps = fps
    this.circular_buffer = deque(maxlen=max(fps * 60 * 2, 1200))
    this.last_activity_check = dt.now()


def add_frame(frame: ndarray, objects: List[FrameObject], faces: List[FrameObject]) -> None:
    # Insert frame only if objects were detected
    frame = MonitoredFrame(time=dt.now(), frame=frame.copy() if objects else None, objects=objects, faces=faces, score=None)
    this.circular_buffer.append(frame)


def check_activity() -> None:
    # Every X seconds, check the last X seconds in the buffer
    if (dt.now() - this.last_activity_check).seconds <= CHECK_ACTIVITY_PERIOD_SEC:
        # TODO - Use logger instead of prints
        return
    else:
        this.last_activity_check = dt.now()

    # If a *good* frame was sent, then skip no matter what
    if this.last_good_frame_sent:
        sent_before = dt.now() - this.last_good_frame_sent
        if sent_before.seconds <= 60 * SKIP_CHECKS_AFTER_UPLOAD_MIN:
            print(f"Uploaded a good frame before {int(sent_before.total_seconds() / 60)} minutes, skipping activity check.")
            return

    # If we detected something in the last X seconds, find "good" frames in the last 60 seconds
    start = max(0, len(this.circular_buffer) - (60 * this.fps))
    stop = len(this.circular_buffer) - 1
    frames = list(itertools.islice(this.circular_buffer, start, stop))

    # Give score to all frames
    qualify_frames(frames)

    # Set motion detection time
    if not this.last_motion_detection and has_motion(frames):
        print("Detected motion")
        this.last_motion_detection = dt.now()

    if has_good_frames(frames):
        # If found good frames, send the best frames
        send_frames(frames)
    elif this.last_motion_detection:
        sent_before = dt.now() - this.last_frame_sent if this.last_frame_sent else None
        detected_motion_since = (dt.now() - this.last_motion_detection).seconds
        print(f"detected_motion_since: {detected_motion_since}, sent a frame before: {sent_before}")

        # If motion detected X seconds ago and still no good frames, send the best frame
        # but don't send if there is any frame sent in the last SKIP_CHECKS_AFTER_UPLOAD_MIN time
        if detected_motion_since > SEND_BAD_FRAMES_WITH_MOTION_AFTER_SEC and \
                (not sent_before or sent_before.seconds >= 60 * SKIP_CHECKS_AFTER_UPLOAD_MIN):
            print(f"Motion detected {SEND_BAD_FRAMES_WITH_MOTION_AFTER_SEC} seconds ago and nothing sent. Sending the best we can.")
            send_frames(frames)


def send_frames(frames: List[MonitoredFrame]):
    best_frame = choose_best_frame(frames)
    print(f"Best frame score: {best_frame.score}, objects: {len(best_frame.objects)}, faces: {len(best_frame.faces)}")

    frames_sender.send_motion_frames([best_frame])

    this.last_motion_detection = None
    this.last_frame_sent = dt.now()
    if has_good_frames(frames):
        this.last_good_frame_sent = dt.now()


def qualify_frames(frames: List[MonitoredFrame]) -> None:
    for frame in frames:
        """
        1. Detected objects amount
        2. Detected faces amount

        """
        if frame.score:
            continue

        frame.score = (1 * len(frame.objects))
        frame.score += (5 * len(frame.faces))
        # TODO -  * Size of objects
        #         * Size of faces - highest weight
        #         * Location of objects and faces (shouldn't be in the boundaries of the image) - lowest weiht


def has_motion(frames: List[MonitoredFrame]) -> bool:
    """
    Find a frame with a score larger than X
    """
    return any([frame.score and frame.score >= 1 for frame in frames])


def has_good_frames(frames: List[MonitoredFrame]) -> bool:
    """
    Find a frame with a score larger than X
    """
    return any([frame.score and frame.score > 3 for frame in frames])


def choose_best_frame(frames: List[MonitoredFrame]) -> MonitoredFrame:
    return max(frames, key=lambda f: f.score)
