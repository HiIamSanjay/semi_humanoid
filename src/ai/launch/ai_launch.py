from launch import LaunchDescription
from launch_ros.actions import Node

def generate_launch_description():
    """
    Generates the launch description for the ai package.
    All nodes are set to respawn to ensure high availability for a product deployment.
    """
    return LaunchDescription([
        Node(
            package='ai',
            executable='gemini_node',
            name='gemini_node',
            output='screen',
            respawn=True,
            respawn_delay=2.0, # Brief delay before restarting.
        ),
        Node(
            package='ai',
            executable='emotion_recognition',
            name='emotion_recognition_node',
            output='screen',
            respawn=True,
            respawn_delay=5.0, # Longer delay as this node can be slow to initialize.
        ),
        Node(
            package='ai',
            executable='person_detection',
            name='person_detection_node',
            output='screen',
            respawn=True,
            respawn_delay=2.0,
        ),
    ])

