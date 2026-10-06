# Copyright 2026 Jamie
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from diagnostic_msgs.msg import DiagnosticStatus, KeyValue
import rclpy
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node

from .status_format import format_status_message


class StatusNode(Node):
    """Mower Status node: reports the mower's health as a DiagnosticStatus."""

    def __init__(self) -> None:
        super().__init__('status_node')
        self.declare_parameter('robot_id', 'mower-01')
        self.declare_parameter('publish_rate', 2.0)
        self.declare_parameter('base_frame', 'base_link')
        self.declare_parameter('state', 'nominal')
        self.rate = float(self.get_parameter('publish_rate').value)
        self.robot_id = str(self.get_parameter('robot_id').value)
        self.base_frame = str(self.get_parameter('base_frame').value)
        self.state = str(self.get_parameter('state').value)
        self.publish_count = 0
        if self.rate <= 0.0:
            self.get_logger().warning('Publish rate must be positive, defaulting to 2.0 Hz')
            self.rate = 2.0
        self.publisher = self.create_publisher(DiagnosticStatus, '~/diagnostics', 1)
        self.timer = self.create_timer(1.0 / self.rate, self.on_timer)
        self.get_logger().info(f'status_node up at {self.rate} Hz for {self.robot_id}')

    def on_timer(self) -> None:
        msg = DiagnosticStatus()
        levels = {
            'nominal': DiagnosticStatus.OK,
            'degraded': DiagnosticStatus.WARN,
        }
        msg.level = levels.get(self.state, DiagnosticStatus.WARN)
        msg.name = 'status_node'
        msg.hardware_id = self.robot_id
        msg.message = format_status_message(self.robot_id, self.state)
        msg.values = [KeyValue(key='publish_count', value=str(self.publish_count))]
        msg.values.append(KeyValue(key='base_frame', value=self.base_frame))
        self.publisher.publish(msg)
        self.publish_count += 1


def main() -> None:
    rclpy.init()
    node = StatusNode()
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
