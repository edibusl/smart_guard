from typing import List

import cv2
from device.common import FrameObject
from numpy import ndarray


UNBLURRED_FACE_MARGIN_PERCENT = 0.35


def detect_motion(prev_frame: ndarray, cur_frame: ndarray, draw: bool = False) -> List[FrameObject]:
    # Diff between this and previous frame
    diff = cv2.absdiff(prev_frame, cur_frame)

    # Convert the diff to gray scale and blur in order to amplify the diff between the moving objects
    # All the non moving objects will be dark
    gray = cv2.cvtColor(diff, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (5, 5), 0)

    # Remove non moving objects and dilate the moving ones
    _, thresh = cv2.threshold(blur, 20, 255, cv2.THRESH_BINARY)
    dilated = cv2.dilate(thresh, None, iterations=20)

    # Draw contours across the (moving) objects that are in the remainng image after all filters
    contours, _ = cv2.findContours(dilated, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

    detected_objects = []

    for i, contour in enumerate(contours):
        # Get the area of the contour and ignore small moving objects
        area = cv2.contourArea(contour)
        if area > 10000:
            # Draw the contour
            # cv2.drawContours(prev_frame, contours, i, (0, 255, 0), 2)

            x, y, w, h = cv2.boundingRect(contour)
            detected_objects.append(FrameObject(x, y, w, h, area))

            if draw:
                # Draw a bounding box around the contour
                cv2.rectangle(prev_frame, (x, y), (x + w, y + h), (0, 255, 0), 2)

    return detected_objects


def detect_faces(frame: ndarray, detected_objects: List[FrameObject], draw: bool = False) -> List[FrameObject]:
    face_cascade = cv2.CascadeClassifier('device/haarcascade_frontalface_default.xml')
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    faces = face_cascade.detectMultiScale(gray, 1.1, 4)

    detected_faces = []

    for (x, y, w, h) in faces:
        # Check if the detected face is moving (and not just some false positive of a static object)
        # Do this by going through all detected objects and checking if the center of the face is inside the bounds of any of those objects
        center_face_x = int(x + w/2)
        center_face_y = int(y + h/2)
        for detected_object in detected_objects:
            if detected_object.x < center_face_x < detected_object.x + detected_object.w \
                    and detected_object.y < center_face_y < detected_object.y + detected_object.h:
                break
        else:
            continue

        detected_faces.append(FrameObject(x, y, w, h, w * h))

        if draw:
            cv2.rectangle(frame, (x, y), (x + w, y + h), (255, 0, 0), 2)

    # if len(detected_faces) > 0:
    #     print(f"Detected {len(detected_faces)} faces")

    return detected_faces


def blur(frame: ndarray, faces: List[FrameObject]) -> ndarray:
    def get_face_range(face, frame):
        margins_y = int(face.h * UNBLURRED_FACE_MARGIN_PERCENT)
        margins_x = int(face.w * UNBLURRED_FACE_MARGIN_PERCENT)

        yfrom = max(0, face.y - margins_y)
        yto = min(frame.shape[0], face.y + face.h + margins_y)
        xfrom = max(0, face.x - margins_x)
        xto = min(frame.shape[1], face.x + face.w + margins_x)

        return yfrom, yto, xfrom, xto

    original_face_images = []

    # Save original faces
    for face in faces:
        yfrom, yto, xfrom, xto = get_face_range(face, frame)
        original_face_image = frame.copy()[yfrom:yto, xfrom:xto]
        original_face_images.append(original_face_image)

    # Blur the whole image
    frame_blurred = cv2.GaussianBlur(frame, (51, 51), 0)

    # Return the original faces to their places ontop of the blurred image
    for i, face in enumerate(faces):
        original_face_image = original_face_images[i]
        yfrom, yto, xfrom, xto = get_face_range(face, frame)
        frame_blurred[yfrom:yto, xfrom:xto] = original_face_image

    # TODO - Bug - Check video with 2 faces - both of them should be blurred, and if 1 face detected and the other is not,

    return frame_blurred


def draw_objects_in_frame(frame: ndarray, frame_objects: List[FrameObject], color: tuple = (0, 255, 0)):
    for frame_object in frame_objects:
        x, y, w, h = frame_object.x, frame_object.y, frame_object.w, frame_object.h
        cv2.rectangle(frame, (x, y), (x + w, y + h), color, 2)


def detect_door_opening():
    # Future
    pass


# Testing
if __name__ == '__main__':
    # Read in image
    image = cv2.imread('/home/edi/code/smartguard/device/18_07_17.jpg')
    blurred = blur(image, [FrameObject(x=384, y=183, w=97, h=97, area=9409)])

    cv2.imshow('blur', blurred)
    cv2.imshow('image', image)
    cv2.waitKey()
