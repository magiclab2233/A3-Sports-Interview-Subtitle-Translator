import argparse
import sys
import time
from picamera2 import Picamera2
import cv2
import mediapipe as mp
import numpy as np

from mediapipe.tasks import python
from mediapipe.tasks.python import vision
from mediapipe.framework.formats import landmark_pb2

from judge import judge_pose
from led_ctl import led_on, led_off

mp_pose = mp.solutions.pose
mp_drawing = mp.solutions.drawing_utils
mp_drawing_styles = mp.solutions.drawing_styles

# Global variables to calculate FPS and handle async detection
COUNTER, FPS = 0, 0
START_TIME = time.time()
DETECTION_RESULT = None
DETECTION_BUSY = False  # Indicates if a detection is in progress


def run(model: str, num_poses: int,
        min_pose_detection_confidence: float,
        min_pose_presence_confidence: float, min_tracking_confidence: float,
        output_segmentation_masks: bool,
        camera_id: int, width: int, height: int) -> None:
    """Continuously run inference on the latest image, skipping frames if detection is busy."""
    global COUNTER, FPS, START_TIME, DETECTION_RESULT, DETECTION_BUSY

    # Visualization settings
    row_size = 50  # pixels
    left_margin = 24  # pixels
    text_color = (0, 0, 0)  # black
    font_size = 1
    font_thickness = 1
    fps_avg_frame_count = 10
    overlay_alpha = 0.5
    mask_color = (100, 100, 0)  # cyan

    # Initialize camera
    picam2 = Picamera2()
    config = picam2.create_video_configuration(
        main={"format": "RGB888", "size": (width, height)}
    )
    picam2.configure(config)
    picam2.start()

    # Set full resolution crop
    full_crop = picam2.camera_properties["ScalerCropMaximum"]
    picam2.set_controls({"ScalerCrop": full_crop})

    def save_result(result: vision.PoseLandmarkerResult,
                    unused_output_image: mp.Image, timestamp_ms: int):
        global FPS, COUNTER, START_TIME, DETECTION_RESULT, DETECTION_BUSY

        # Update FPS
        if COUNTER % fps_avg_frame_count == 0:
            FPS = fps_avg_frame_count / (time.time() - START_TIME)
            START_TIME = time.time()

        DETECTION_RESULT = result
        COUNTER += 1
        DETECTION_BUSY = False  # Ready for next detection

    # Initialize the pose landmarker model
    base_options = python.BaseOptions(model_asset_path=model)
    options = vision.PoseLandmarkerOptions(
        base_options=base_options,
        running_mode=vision.RunningMode.LIVE_STREAM,
        num_poses=num_poses,
        min_pose_detection_confidence=min_pose_detection_confidence,
        min_pose_presence_confidence=min_pose_presence_confidence,
        min_tracking_confidence=min_tracking_confidence,
        output_segmentation_masks=output_segmentation_masks,
        result_callback=save_result)
    detector = vision.PoseLandmarker.create_from_options(options)

    try:
        while True:
            # Grab the latest frame
            frame = picam2.capture_array()

            # Convert to RGB for model
            rgb_image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_image)

            # If no detection in progress, start async detection
            if not DETECTION_BUSY:
                detector.detect_async(mp_image, time.time_ns() // 1_000_000)
                DETECTION_BUSY = True

            # Display FPS
            fps_text = f'FPS = {FPS:.1f}'
            cv2.putText(frame, fps_text, (left_margin, row_size),
                        cv2.FONT_HERSHEY_DUPLEX, font_size,
                        text_color, font_thickness, cv2.LINE_AA)

            # If we have a detection result, draw landmarks and posture
            if DETECTION_RESULT:
                for pose_landmarks in DETECTION_RESULT.pose_landmarks:
                    proto = landmark_pb2.NormalizedLandmarkList()
                    proto.landmark.extend([
                        landmark_pb2.NormalizedLandmark(
                            x=lm.x, y=lm.y, z=lm.z) for lm in pose_landmarks
                    ])
                    mp_drawing.draw_landmarks(
                        frame, proto,
                        mp_pose.POSE_CONNECTIONS,
                        mp_drawing_styles.get_default_pose_landmarks_style())

                # Judge posture every 3 frames
                if COUNTER % 3 == 0:
                    neck, body = judge_pose(DETECTION_RESULT)
                    print(f"neck: {neck}; body: {body}")
                    if (neck and neck != 'normal') or (body and body != 'normal'):
                        led_on()
                    else:
                        led_off()
                    status_text = f'neck: {neck}, body: {body}'
                    cv2.putText(frame, status_text,
                                (left_margin, row_size + 20),
                                cv2.FONT_HERSHEY_DUPLEX, font_size,
                                text_color, font_thickness, cv2.LINE_AA)

            # Optional: draw segmentation mask if enabled
            if output_segmentation_masks and DETECTION_RESULT and DETECTION_RESULT.segmentation_masks:
                mask = DETECTION_RESULT.segmentation_masks[0].numpy_view()
                mask_img = np.zeros(frame.shape, dtype=np.uint8)
                mask_img[:] = mask_color
                cond = np.stack((mask,) * 3, axis=-1) > 0.1
                vis_mask = np.where(cond, mask_img, frame)
                frame = cv2.addWeighted(frame, overlay_alpha,
                                        vis_mask, overlay_alpha, 0)

            # Resize for display
            resized = cv2.resize(frame, (0, 0), fx=0.5, fy=0.5)
            cv2.imshow('pose_landmarker', resized)

            if cv2.waitKey(1) == 27:  # ESC key
                break

    finally:
        detector.close()
        picam2.stop()
        cv2.destroyAllWindows()


def main():
    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('--model', default='pose_landmarker_full.task',
                        help='Path to pose landmarker model bundle')
    parser.add_argument('--numPoses', type=int, default=1,
                        help='Max number of poses')
    parser.add_argument('--minPoseDetectionConfidence', type=float, default=0.5,
                        help='Min detection confidence')
    parser.add_argument('--minPosePresenceConfidence', type=float, default=0.5,
                        help='Min presence confidence')
    parser.add_argument('--minTrackingConfidence', type=float, default=0.5,
                        help='Min tracking confidence')
    parser.add_argument('--outputSegmentationMasks', action='store_true',
                        help='Visualize segmentation mask')
    parser.add_argument('--cameraId', type=int, default=0,
                        help='Camera ID')
    parser.add_argument('--frameWidth', type=int, default=1280,
                        help='Frame width')
    parser.add_argument('--frameHeight', type=int, default=960,
                        help='Frame height')
    args = parser.parse_args()
    run(args.model, args.numPoses,
        args.minPoseDetectionConfidence,
        args.minPosePresenceConfidence,
        args.minTrackingConfidence,
        args.outputSegmentationMasks,
        args.cameraId, args.frameWidth, args.frameHeight)


if __name__ == '__main__':
    main()
