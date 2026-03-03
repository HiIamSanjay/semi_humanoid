import rclpy
from rclpy.node import Node
from std_msgs.msg import String
from sensor_msgs.msg import Image
# --- KEY CHANGE: Import the necessary Flask components ---
from flask import Flask, Response, request, jsonify
from flask_cors import CORS
import cv2
from cv_bridge import CvBridge
import threading
import socket
import time

# --- Flask Web App Setup ---
app = Flask(__name__)
CORS(app)

# Global variable to store the latest frame from the camera
latest_frame = None
frame_lock = threading.Lock()

class WebServerNode(Node):
    """
    This node runs a Flask web server to stream video and receive motor commands.
    """
    def __init__(self):
        super().__init__('web_server_node')
        
        self.video_subscription = self.create_subscription(
            Image,
            '/video_feed',
            self.video_callback,
            10)
            
        self.motor_command_publisher = self.create_publisher(String, '/motor_command', 10)
        
        self.bridge = CvBridge()
        self.get_logger().info("Web Server node started.")

    def video_callback(self, msg):
        """Store the latest video frame."""
        global latest_frame
        with frame_lock:
            latest_frame = self.bridge.imgmsg_to_cv2(msg, "bgr8")
            
    def publish_motor_command(self, command):
        """Publishes a motor command to the /motor_command topic."""
        msg = String()
        msg.data = command
        self.motor_command_publisher.publish(msg)
        self.get_logger().info(f'Published motor command: "{command}"')

# --- Flask API Routes ---
@app.route('/move', methods=['POST'])
def move():
    # Now that 'request' and 'jsonify' are imported, this will work correctly.
    direction = request.json.get('direction')
    if web_server_node and direction:
        web_server_node.publish_motor_command(direction)
    return jsonify({"action": direction, "status": "ok"})

@app.route('/video_feed')
def video_feed():
    """Streams the webcam feed from the ROS topic as an MJPEG stream."""
    def generate_frames():
        while True:
            with frame_lock:
                if latest_frame is None:
                    time.sleep(0.1)
                    continue
                frame_copy = latest_frame.copy()

            _, buffer = cv2.imencode('.jpg', frame_copy, [int(cv2.IMWRITE_JPEG_QUALITY), 80])
            frame_bytes = buffer.tobytes()
            
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
            time.sleep(0.05)

    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

# --- Network Discovery Service ---
def get_ip_address():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('10.255.255.255', 1))
        IP = s.getsockname()[0]
    except Exception:
        IP = '127.0.0.1'
    finally:
        s.close()
    return IP

def run_discovery_service():
    host_ip = get_ip_address()
    broadcast_address = '<broadcast>'
    discovery_port = 5000
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        print(f"📢 Discovery service started. Broadcasting IP {host_ip}")
        message = f"robot_server:{host_ip}".encode('utf-8')
        while True:
            sock.sendto(message, (broadcast_address, discovery_port))
            time.sleep(2)

def main(args=None):
    rclpy.init(args=args)
    
    global web_server_node
    web_server_node = WebServerNode()
    
    # Run Flask and Discovery in separate threads
    flask_thread = threading.Thread(target=lambda: app.run(host='0.0.0.0', port=5000, debug=False), daemon=True)
    discovery_thread = threading.Thread(target=run_discovery_service, daemon=True)
    
    flask_thread.start()
    discovery_thread.start()
    
    rclpy.spin(web_server_node)
    
    web_server_node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()


