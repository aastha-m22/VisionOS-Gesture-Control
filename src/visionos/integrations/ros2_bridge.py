"""Placeholder for future ROS 2 robot-control bridge.

Intended design: recognised gestures are published as ``geometry_msgs/Twist`` or
custom command messages on a ROS 2 topic, letting the same hand gestures that
drive the desktop cursor also tele-operate a robot (e.g. a manipulator or mobile
base). The bridge would subscribe to the application's gesture event stream and
translate each :class:`~visionos.gestures.gesture_types.Gesture` into a robot
command, keeping robotics concerns fully decoupled from the vision pipeline.
"""

from __future__ import annotations

from visionos.gestures.gesture_types import Gesture
from visionos.utils.logger import get_logger

logger = get_logger("integrations.ros2_bridge")


class ROS2Bridge:
    """Stub ROS 2 publisher. Requires rclpy; not active by default."""

    def __init__(self, topic: str = "/visionos/gesture_cmd") -> None:
        self.topic = topic
        self.connected = False
        logger.debug("ROS2Bridge stub created for topic '%s'", topic)

    def publish(self, gesture: Gesture) -> bool:
        """Publish a gesture command. Returns False until rclpy is wired up."""
        return False
