from launch import LaunchDescription
from launch_ros.actions import Node

def generate_launch_description():
    """
    Launches the web server and Arduino bridge for remote control.
    These nodes will respawn to maintain remote access.
    """
    return LaunchDescription([
        Node(
            package='remote_control',
            executable='arduino_bridge',
            name='arduino_bridge_node',
            output='screen',
            respawn=True,
            respawn_delay=3.0, # Allow time for serial port to reset.
        ),
        Node(
            package='remote_control',
            executable='web_server',
            name='web_server_node',
            output='screen',
            respawn=True,
            respawn_delay=2.0,
        ),
    ])

