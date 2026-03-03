import rclpy
from rclpy.node import Node
from std_msgs.msg import String
import csv
import os
from datetime import datetime
import json


class PerformanceLoggerNode(Node):
    def __init__(self):
        super().__init__('performance_logger_node')
        # Save log in the home directory or specific path
        self.log_file_path = os.path.expanduser('~/robot_performance_log.csv')
        self.csv_header = ['timestamp', 'node_name',
                           'operation', 'duration_sec']

        # Subscribe to a common performance topic
        self.subscription = self.create_subscription(
            String,
            '/performance_metrics',
            self.log_callback,
            10
        )

        self.setup_csv_file()
        self.get_logger().info(
            f"Performance Logger started. Writing to {self.log_file_path}")

    def setup_csv_file(self):
        # Create file with header if it doesn't exist
        if not os.path.exists(self.log_file_path):
            with open(self.log_file_path, 'w', newline='') as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(self.csv_header)

    def log_callback(self, msg):
        try:
            # Expecting data in format: "node_name,operation,duration"
            data_parts = msg.data.split(',')
            if len(data_parts) == 3:
                timestamp = datetime.now().strftime('%H:%M:%S.%f')
                node_name = data_parts[0]
                operation = data_parts[1]
                duration = data_parts[2]

                with open(self.log_file_path, 'a', newline='') as csvfile:
                    writer = csv.writer(csvfile)
                    writer.writerow(
                        [timestamp, node_name, operation, duration])
        except Exception as e:
            self.get_logger().error(f"Error logging data: {e}")


def main(args=None):
    rclpy.init(args=args)
    node = PerformanceLoggerNode()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
