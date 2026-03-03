import rclpy
from rclpy.node import Node
from std_msgs.msg import Bool, String
from sensor_msgs.msg import Image
import cv2
from cv_bridge import CvBridge, CvBridgeError
import face_recognition
import threading
import numpy as np
from deepface import DeepFace
import time


class EmotionRecognitionNode(Node):
    """
    Analyzes faces for emotions, but only when activated by a control message
    on the /emotion_recognition_control topic.
    """

    def __init__(self):
        super().__init__('emotion_recognition_node')

        # --- Subscribers and Publishers ---
        self.video_subscription = self.create_subscription(
            Image, '/video_feed', self.video_callback, 10)
        self.emotion_publisher = self.create_publisher(String, '/emotion', 10)

        self.control_subscription = self.create_subscription(
            String,
            '/emotion_recognition_control',
            self.control_callback,
            10)

        self.bridge = CvBridge()
        self.last_emotion = "neutral"

        self.is_active = False

        self.frame_lock = threading.Lock()
        self.latest_frame = None

        self.analysis_timer = self.create_timer(1.0, self.analyze_frame)

        self.get_logger().info("Emotion Recognition node started. Waiting for activation command.")
        threading.Thread(target=self.preload_model, daemon=True).start()
        self.perf_publisher = self.create_publisher(
            String, '/performance_metrics', 10)

    def preload_model(self):
        """Preloads the DeepFace model to reduce the first analysis delay."""
        dummy_frame = np.zeros((224, 224, 3), dtype=np.uint8)
        try:
            self.get_logger().info("Preloading DeepFace emotion model...")
            DeepFace.analyze(dummy_frame, actions=[
                             'emotion'], enforce_detection=False)
            self.get_logger().info("DeepFace model loaded successfully.")
        except Exception as e:
            self.get_logger().warn(f"Could not preload model: {e}")

    def control_callback(self, msg):
        """Activates or deactivates emotion analysis based on specific commands."""
        # --- KEY CHANGE: Listen for the correct commands from the Gemini node ---
        if msg.data == "start_mirroring":
            self.is_active = True
            self.get_logger().info("Emotion recognition has been ACTIVATED for mirroring.")
        elif msg.data == "stop_mirroring":
            self.is_active = False
            self.get_logger().info("Emotion recognition has been DEACTIVATED.")

    def video_callback(self, msg):
        """Stores the latest video frame."""
        with self.frame_lock:
            try:
                self.latest_frame = self.bridge.imgmsg_to_cv2(msg, "bgr8")
            except CvBridgeError as e:
                self.get_logger().error(f"CV Bridge error: {e}")

    def analyze_frame(self):
        """
        Periodically called, but will only run analysis if the node is active.
        """
        if not self.is_active:
            return

        frame_to_analyze = None
        with self.frame_lock:
            if self.latest_frame is not None:
                frame_to_analyze = self.latest_frame.copy()

        if frame_to_analyze is None:
            return

        threading.Thread(target=self.run_deepface_analysis,
                         args=(frame_to_analyze,), daemon=True).start()

    def run_deepface_analysis(self, frame):
        start_time = time.time()  # <--- START TIMER
        try:
            # The heavy operation
            analysis = DeepFace.analyze(
                frame, actions=['emotion'], enforce_detection=False)

            if analysis and isinstance(analysis, list) and analysis[0]:
                detected_emotion = analysis[0]['dominant_emotion']

                if detected_emotion != self.last_emotion:
                    self.last_emotion = detected_emotion
                    msg = String()
                    msg.data = detected_emotion
                    self.emotion_publisher.publish(msg)
                    self.get_logger().info(
                        f'Detected Emotion for Mirroring: "{detected_emotion}"')
        except Exception:
            pass
        finally:
            end_time = time.time()  # <--- END TIMER
            duration = end_time - start_time

            # Publish the metric
            msg = String()
            msg.data = f"emotion_node,deepface_analyze,{duration:.4f}"
            self.perf_publisher.publish(msg)


def main(args=None):
    rclpy.init(args=args)
    emotion_node = EmotionRecognitionNode()
    rclpy.spin(emotion_node)
    emotion_node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
