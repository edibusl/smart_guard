from datetime import datetime as dt
import time
import sys

import cv2

from device import video_processing, objects_monitor


this = sys.modules[__name__]
this.conf = {}
this.video_output = None
this.should_save_video = False


def init(display: bool, fps: int, input: str) -> None:
    this.conf['display'] = display
    this.conf['fps'] = fps
    this.conf['input'] = input

    objects_monitor.init(fps)


def capture() -> None:
    if not this.conf['input']:
        cap = cv2.VideoCapture(0)
    else:
        cap = cv2.VideoCapture(this.conf['input'])

    width = cap.get(cv2.CAP_PROP_FRAME_WIDTH)
    height = cap.get(cv2.CAP_PROP_FRAME_HEIGHT)

    ret, frame1 = cap.read()
    prev_time = time.time()
    while cap.isOpened():
        ret, frame2 = cap.read()

        process_frame = False
        if this.conf['input']:
            # When reading from a file, we need to wait explicitly the fps time
            time.sleep(1/this.conf['fps'])
            process_frame = True
        else:
            # When reading from camera, we need to continue processing the frames with the cameras capability
            # and process only the wanted frames according to the user requested frame rate
            cur_time = time.time()
            elapsed_time = cur_time - prev_time
            if elapsed_time > 1/this.conf['fps']:
                process_frame = True
                prev_time = cur_time

        if process_frame:
            # Detect motion
            detected_objects = video_processing.detect_motion(frame1, frame2, draw=this.conf['display'])

            # Detect faces
            detected_faces = []
            if detected_objects:
                detected_faces = video_processing.detect_faces(frame1, detected_objects, draw=this.conf['display'])

            # Blur faces (just for debugging)
            # frame1 = video_processing.blur(frame1, detected_faces)

            objects_monitor.add_frame(frame2, detected_objects, detected_faces)

        save_video(frame2, width, height)

        # On every frame we need to check the last activity
        objects_monitor.check_activity()

        if this.conf['display']:
            cv2.imshow("Live video", frame1)

            ret_key = cv2.waitKey(1)
            if ret_key & 0xFF == ord('q'):
                print('"q" pressed. Finishing video capturing')
                break
            elif ret_key & 0xFF == ord('s'):
                filename = dt.now().strftime("%H_%M_%S.jpg")
                print(f"'s' pressed. Saving image to {filename}")
                cv2.imwrite(filename, frame2)
            elif ret_key & 0xFF == ord('v'):
                this.should_save_video = not this.should_save_video

        # Prev frame is now current frame
        frame1 = frame2

    cap.release()

    # TODO - Move to some generic place
    if this.video_output:
        this.video_output.release()
        this.video_output = None

    cv2.destroyAllWindows()


def save_video(frame, width, height):
    if not this.should_save_video:
        return

    if not this.video_output:
        fourcc = cv2.VideoWriter_fourcc('m', 'p', '4', 'v')
        this.video_output = cv2.VideoWriter('output.mp4', fourcc, this.conf['fps'], (int(width), int(height)))

    this.video_output.write(frame)
