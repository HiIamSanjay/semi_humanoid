import rclpy
from rclpy.node import Node
from std_msgs.msg import String
import serial
import time

# --- Serial Communication Setup ---
ARDUINO_PORT = '/dev/ttyUSB0'  # ❗ IMPORTANT: Change this to your Arduino's port
BAUD_RATE = 9600

class ArduinoBridgeNode(Node):
    """
    This node listens for motor commands on the /motor_command topic
    and sends them to the Arduino via serial communication.
    """
    def __init__(self):
        super().__init__('arduino_bridge_node')
        
        # Connect to Arduino
        self.arduino = None
        try:
            self.arduino = serial.Serial(port=ARDUINO_PORT, baudrate=BAUD_RATE, timeout=.1)
            self.get_logger().info(f"✅ Successfully connected to Arduino on {ARDUINO_PORT}")
        except Exception as e:
            self.get_logger().error(f"❌ Could not connect to Arduino: {e}")
            # Allow the node to run, but it won't be able to send commands
        
        # Subscribe to motor commands
        self.command_subscription = self.create_subscription(
            String,
            '/motor_command',
            self.command_callback,
            10)
            
        self.get_logger().info("Arduino Bridge node started. Waiting for motor commands.")

    def command_callback(self, msg):
        """Receives a command and sends the corresponding character to the Arduino."""
        if not self.arduino:
            self.get_logger().warn("Cannot send command, Arduino not connected.")
            return

        command = msg.data
        command_char = ''
        if command == 'forward':
            command_char = 'f'
        elif command == 'backward':
            command_char = 'b'
        elif command == 'left':
            command_char = 'l'
        elif command == 'right':
            command_char = 'r'
        elif command == 'stop':
            command_char = 's'
        
        if command_char:
            try:
                self.arduino.write(command_char.encode())
                self.get_logger().info(f"Sent '{command_char}' to Arduino for command '{command}'.")
            except Exception as e:
                self.get_logger().error(f"Error writing to Arduino: {e}")

def main(args=None):
    rclpy.init(args=args)
    arduino_bridge_node = ArduinoBridgeNode()
    rclpy.spin(arduino_bridge_node)
    arduino_bridge_node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()

