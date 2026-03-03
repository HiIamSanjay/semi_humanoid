# pylint: disable=no-member
import rclpy
from rclpy.node import Node
from std_msgs.msg import Bool, String
from sensor_msgs.msg import Image
import cv2
from cv_bridge import CvBridge, CvBridgeError
import face_recognition
import threading
import time


class PersonDetectionNode(Node):
    """
    Subscribes to a video feed, detects the presence of a face with debouncing,
    and publishes a stable status to the /person_detected_status topic.
    """

    def __init__(self):
        super().__init__('person_detection_node')

        # --- Subscribers and Publishers ---
        self.subscription = self.create_subscription(
            Image, '/video_feed', self.video_callback, 10)
        self.status_publisher = self.create_publisher(
            Bool, '/person_detected_status', 10)

        self.bridge = CvBridge()

        # --- State and Debouncing Configuration ---
        self.person_present_last_state = False
        self.PRESENCE_CONFIRM_FRAMES = 1  # Needs 1 consecutive frames to confirm presence
        self.ABSENCE_CONFIRM_FRAMES = 30  # Needs 10 consecutive frames to confirm absence
        self.seen_streak = 0
        self.unseen_streak = 0

        self.frame_lock = threading.Lock()
        self.latest_frame = None

        # Timer runs at 2 Hz for analysis
        self.analysis_timer = self.create_timer(0.5, self.analyze_frame)

        self.get_logger().info("Person Detection node started with debouncing logic.")
        self.perf_publisher = self.create_publisher(
            String, '/performance_metrics', 10)

    def video_callback(self, msg):
        """Stores the latest video frame."""
        with self.frame_lock:
            try:
                self.latest_frame = self.bridge.imgmsg_to_cv2(msg, "bgr8")
            except CvBridgeError as e:
                self.get_logger().error(f"CV Bridge error: {e}")

    def analyze_frame(self):
        """Periodically called by a timer to analyze the latest frame."""
        frame_to_analyze = None
        with self.frame_lock:
            if self.latest_frame is not None:
                frame_to_analyze = self.latest_frame.copy()

        if frame_to_analyze is None:
            return

        threading.Thread(target=self.run_detection, args=(
            frame_to_analyze,), daemon=True).start()

    def run_detection(self, frame):
        start_time = time.time()
        """The actual face detection logic with debouncing."""
        try:
            small_frame = cv2.resize(frame, (0, 0), fx=0.25, fy=0.25)
            rgb_small_frame = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)
            face_locations = face_recognition.face_locations(rgb_small_frame)
            person_currently_present = bool(face_locations)

            # --- Debouncing and State Change Logic ---
            if person_currently_present:
                self.unseen_streak = 0
                self.seen_streak += 1
                # If we have seen a person long enough and the state was previously 'False'
                if self.seen_streak >= self.PRESENCE_CONFIRM_FRAMES and not self.person_present_last_state:
                    self.person_present_last_state = True
                    msg = Bool()
                    msg.data = True
                    self.status_publisher.publish(msg)
                    self.get_logger().info('CONFIRMED: Person detected status changed to: True')
            else:  # Person is not present in this frame
                self.seen_streak = 0
                self.unseen_streak += 1
                # If we have NOT seen a person for long enough and the state was previously 'True'
                if self.unseen_streak >= self.ABSENCE_CONFIRM_FRAMES and self.person_present_last_state:
                    self.person_present_last_state = False
                    msg = Bool()
                    msg.data = False
                    self.status_publisher.publish(msg)
                    self.get_logger().info('CONFIRMED: Person detected status changed to: False')

        except Exception as e:
            self.get_logger().error(f"Error: {e}")
        finally:
            end_time = time.time()  # <--- END TIMER
            duration = end_time - start_time

            msg = String()
            msg.data = f"person_detection_node,face_locations,{duration:.4f}"
            self.perf_publisher.publish(msg)


def main(args=None):
    rclpy.init(args=args)
    person_detection_node = PersonDetectionNode()
    rclpy.spin(person_detection_node)
    person_detection_node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
