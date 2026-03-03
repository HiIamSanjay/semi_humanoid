from setuptools import find_packages, setup
import os
from glob import glob

package_name = 'ui'

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        (os.path.join('share', package_name, 'launch'), glob('launch/*launch.py')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='Your Name',
    maintainer_email='user@example.com',
    description='ROS 2 package for media UI elements.',
    license='Apache License 2.0',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'main_gui = ui.main_gui_node:main',
            'eye_animation = ui.eye_animation_node:main',
            'interaction_manager = ui.interaction_manager_node:main'
        ],
    },
)

