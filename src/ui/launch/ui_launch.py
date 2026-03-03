from launch import LaunchDescription
from launch_ros.actions import Node
import os

def generate_launch_description():
    """
    Launches the main GUI, eye animation, and the new interaction manager.
    """
    main_gui_node = Node(
        package='ui',
        executable='main_gui',
        name='main_gui_node',
        output='screen',
        respawn=True,
        respawn_delay=2.0,
        emulate_tty=True,
        parameters=[{'use_sim_time': False}],
    )

    # --- COORDINATE CALCULATION FOR SECONDARY DISPLAY ---
    # Assumption: 
    #   Display 1: 1920x1080 (Laptop, Left)
    #   Display 2: 1280x720 (External, Right)
    #   App Window: 1280x720
    #
    # X Position = Width of Display 1 (1920) + Offset to center on Display 2
    # Offset X = (1280 - 1280) / 2 = 0
    # Total X = 1920 + 0 = 1920
    #
    # Y Position = Offset to center vertically on Display 2
    # Offset Y = (720 - 720) / 2 = 0
    #
    # Result: 1920,1080
    
    # NOTE: If this doesn't work, try "1920,1080" to just put it at the top-left of screen 2.
    
    eye_animation_node = Node(
        package='ui',
        executable='eye_animation',
        name='eye_animation_node',
        output='screen',
        respawn=True,
        respawn_delay=2.0,
        emulate_tty=True,
        parameters=[{'use_sim_time': False}],
        # Using env to set the position for SDL/Pygame
        prefix="env SDL_VIDEO_WINDOW_POS=1920,1080" 
    )

    # --- INTERACTION MANAGER ---
    interaction_manager_node = Node(
        package='ui', 
        executable='interaction_manager', 
        name='interaction_manager_node',
        output='screen',
        respawn=True,
        respawn_delay=2.0,
    )

    return LaunchDescription([
        main_gui_node,
        eye_animation_node,
        interaction_manager_node, 
    ])
