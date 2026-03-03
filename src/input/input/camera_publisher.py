import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
import cv2
from cv_bridge import CvBridge, CvBridgeError
import subprocess
import re

def find_camera_by_name(logger, target_name: str) -> int:
    """
    Finds the video device index for a camera by its name using 'v4l2-ctl'.
    
    Args:
        logger: The ROS 2 node logger for output.
        target_name: The name of the camera to search for (e.g., "Camera").

    Returns:
        The integer index of the camera, or -1 if not found.
    """
    try:
        # Execute the command to list video devices. This is standard on Linux.
        result = subprocess.run(
            ['v4l2-ctl', '--list-devices'], 
            capture_output=True, 
            text=True, 
            check=True
        )
        output = result.stdout
        
        # The output groups devices. We split by double newlines to process each group.
        devices = output.strip().split('\n\n')
        
        for device_block in devices:
            # Check if the target name is in the device's description block.
            if target_name in device_block:
                # Use regex to find the corresponding /dev/videoX path.
                match = re.search(r'/dev/video(\d+)', device_block)
                if match:
                    # Extract the number from the path and return it as an integer.
                    index = int(match.group(1))
                    return index
                    
    except FileNotFoundError:
        logger.error("The 'v4l2-ctl' command was not found.")
        logger.error("Please install it to enable camera auto-detection (e.g., 'sudo apt-get install v4l-utils').")
        return -1
    except subprocess.CalledProcessError as e:
        logger.error(f"Error executing 'v4l2-ctl': {e}")
        return -1
    except Exception as e:
        logger.error(f"An unexpected error occurred while finding the camera: {e}")
        return -1
        
    return -1

class CameraPublisher(Node):
    def __init__(self):
        super().__init__('camera_publisher_node')
        self.publisher_ = self.create_publisher(Image, '/video_feed', 10)
        
        # --- MODIFIED SECTION: Auto-detect camera ---
        camera_name_to_find = "HD Web Camera"
        self.get_logger().info(f"Searching for camera device named '{camera_name_to_find}'...")
        
        camera_index = find_camera_by_name(self.get_logger(), camera_name_to_find)

        if camera_index == -1:
            self.get_logger().error(f"Could not find a camera named '{camera_name_to_find}'.")
            self.get_logger().error("Please check the camera connection and ensure the name is correct.")
            rclpy.shutdown()
            return

        self.get_logger().info(f"Found '{camera_name_to_find}' at device index {camera_index}.")
        self.cap = cv2.VideoCapture(camera_index)
        # --- END OF MODIFICATION ---
        
        if not self.cap.isOpened():
            self.get_logger().error(f"Failed to open video capture device at index {camera_index}.")
            rclpy.shutdown()
            return

        timer_period = 1.0 / 30.0  # 30 fps
        self.timer = self.create_timer(timer_period, self.timer_callback)
        self.bridge = CvBridge()
        self.get_logger().info(f"Camera Publisher node started, streaming from '{camera_name_to_find}'.")

    def timer_callback(self):
        ret, frame = self.cap.read()
        if ret:
            try:
                ros_image_msg = self.bridge.cv2_to_imgmsg(frame, "bgr8")
                self.publisher_.publish(ros_image_msg)
            except CvBridgeError as e:
                self.get_logger().error(f'Could not convert frame to Image message: {e}')
        else:
            self.get_logger().warn('Could not read frame from camera.')

    def destroy_node(self):
        # Ensure cap exists and is opened before trying to release it
        if hasattr(self, 'cap') and self.cap.isOpened():
            self.cap.release()
        super().destroy_node()

def main(args=None):
    rclpy.init(args=args)
    camera_publisher = CameraPublisher()
    # If initialization failed, the node will shutdown, and spin will not be reached
    if rclpy.ok():
        try:
            rclpy.spin(camera_publisher)
        except KeyboardInterrupt:
            pass
        finally:
            camera_publisher.destroy_node()
            rclpy.shutdown()

if __name__ == '__main__':
    main()


