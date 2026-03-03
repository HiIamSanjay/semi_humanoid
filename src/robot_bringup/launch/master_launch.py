import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription, TimerAction
from launch.launch_description_sources import PythonLaunchDescriptionSource

def generate_launch_description():
    """
    Master launch file that starts:
    1. AI (Brain)
    2. Input (Camera/Mic)
    3. UI (Face/Screen)
    4. Remote Control (if available)
    """

    # --- Get Package Directories ---
    ai_share_dir = get_package_share_directory('ai')
    input_share_dir = get_package_share_directory('input')
    ui_share_dir = get_package_share_directory('ui')
    
    # Check if remote_control exists (optional safety check)
    try:
        remote_share_dir = get_package_share_directory('remote_control')
        has_remote = True
    except:
        has_remote = False
        print("Warning: 'remote_control' package not found. Skipping.")

    # --- Define Launch Inclusions ---
    
    # 1. Input: Start hardware first (Camera/Mic)
    input_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(input_share_dir, 'launch', 'input_launch.py')
        )
    )

    # 2. AI: Start processing nodes
    ai_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(ai_share_dir, 'launch', 'ai_launch.py')
        )
    )

    # 3. UI: Start the face/GUI
    ui_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(ui_share_dir, 'launch', 'ui_launch.py')
        )
    )

    # 4. Remote Control (Optional)
    remote_launch = None
    if has_remote:
        remote_launch = IncludeLaunchDescription(
            PythonLaunchDescriptionSource(
                os.path.join(remote_share_dir, 'launch', 'remote_control_launch.py')
            )
        )

    # --- Create Launch Description ---
    # We use lists to group them. You can add TimerActions here if you want 
    # specific delays between packages (e.g., wait for camera before starting AI).
    
    objs_to_launch = [input_launch, ai_launch, ui_launch]
    if remote_launch:
        objs_to_launch.append(remote_launch)

    return LaunchDescription(objs_to_launch)
