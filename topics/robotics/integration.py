"""Robotics — ROS2 / MoveIt2 / Gazebo integrations."""
from __future__ import annotations


class RoboticsTopic:
    name = "robotics"
    tools = ["ros2", "moveit2", "gazebo", "micro-ros", "lerobot", "isaac-lab"]

    def ros2_available(self) -> bool:
        try:
            import rclpy
            return True
        except ImportError:
            return False
