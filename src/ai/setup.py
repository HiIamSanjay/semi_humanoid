from setuptools import find_packages, setup
import os
from glob import glob

package_name = 'ai'

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
    description='ROS 2 package for Gemini AI integration.',
    license='Apache License 2.0',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'gemini_node = ai.gemini_node:main',
            'emotion_recognition = ai.emotion_recognition_node:main',
            'person_detection = ai.person_detection_node:main',
            'performance_logger_node = ai.performance_logger_node:main',
        ],
    },
)
