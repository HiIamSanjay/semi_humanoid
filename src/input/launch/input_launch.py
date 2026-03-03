from launch import LaunchDescription
from launch_ros.actions import Node

def generate_launch_description():
    """
    Launches the camera and speech-to-text nodes.
    Both nodes interface with hardware and are set to respawn to handle
    potential temporary device failures.
    """
    return LaunchDescription([
        Node(
            package='input',
            executable='camera_publisher',
            name='camera_publisher_node',
            output='screen',
            respawn=True,
            respawn_delay=4.0, # Give the camera time to re-initialize.
        ),
        Node(
            package='input',
            executable='speech_to_text',
            name='speech_to_text_node',
            output='screen',
            respawn=True,
            respawn_delay=1.0,
        ),
    ])

