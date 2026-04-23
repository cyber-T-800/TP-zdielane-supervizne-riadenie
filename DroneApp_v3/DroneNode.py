from rclpy.node import Node
from sensor_msgs.msg import Image, CompressedImage
from geometry_msgs.msg import PoseStamped, Twist
from sensor_msgs.msg import BatteryState
from mavros_msgs.msg import State
from PyQt5.QtGui import QImage
from rclpy.qos import QoSProfile, ReliabilityPolicy
from mavros_msgs.srv import SetMode

class DroneNode(Node):
    def __init__(self, drone_id, cam, comunicator, img_topic="image_raw"):
        super().__init__(f"drone_node_{drone_id}", namespace=f"drone{drone_id+1}")
        
        qos = QoSProfile(
            reliability=ReliabilityPolicy.BEST_EFFORT,
            depth=10
        )
        self.drone_id = drone_id
        self.comunicator = comunicator
        self.img_topic = img_topic
        self.cam = cam

        self.manual = False

        timer_period = 0.5

        self.timer = self.create_timer(timer_period, self.timer_callback)

        self.mode_client = self.create_client(SetMode, 'set_mode')

        self.req = SetMode.Request()
        
        if cam:
            if img_topic.endswith("/compressed"):
                self.img_sub = self.create_subscription(
                    CompressedImage,
                    img_topic,
                    self._on_compressed,
                    10,
                )
            else:
                self.img_sub = self.create_subscription(
                    Image,
                    img_topic,
                    self._on_raw,
                    10,
                )

        self.position_sub = self.create_subscription(
            PoseStamped,
            "local_position/pose",
            self._on_position,
            qos,
        )

        self.battery_sub = self.create_subscription(
            BatteryState,
            "battery",
            self._on_battery,
            qos,
        )

        self.state_sub = self.create_subscription(
            State,
            "state",
            self._on_state,
            10,
        )

        self.vel_pub = self.create_publisher(
            Twist,
            "setpoint_velocity/cmd_vel_unstamped",
            10,
        )


    def change_mode_request(self):

        if(self.manual):
            self.req.base_mode = 216
        else:
            self.req.base_mode = 192

        response = self.mode_client.call_async(self.req)

        if (response):
            self.manual = not self.manual
            print("mode change")
        else:
            print("cant change")
        
        return response

    def timer_callback(self):
        msg = Twist()

        try:
            lin = self.comunicator.get_linear_vel()
            ang = self.comunicator.get_angular_vel()

            msg.linear.x = float(lin) if lin is not None else 0.0
            msg.linear.y = 0.0
            msg.linear.z = 0.0

            msg.angular.x = 0.0
            msg.angular.y = 0.0
            msg.angular.z = float(ang) if ang is not None else 0.0

        except Exception as e:
            self.get_logger().error(f"Velocity error: {e}")
            return

        self.vel_pub.publish(msg)

    def _on_compressed(self, msg):
        image = QImage.fromData(bytes(msg.data))
        if not image.isNull():
            self.comunicator.handle_image(drone_id=self.drone_id, qimage=image.copy())

    def _on_raw(self, msg):
        image = self.image_msg_to_qimage(msg)
        if image is not None and not image.isNull():
            self.comunicator.handle_image(drone_id=self.drone_id, qimage=image)

    def _on_position(self, msg):
        x = msg.pose.position.x
        y = msg.pose.position.y
        z = msg.pose.position.z
        self.comunicator.handle_position(drone_id=self.drone_id, x = x, y = y, z = z)

    def _on_battery(self, msg):
        percentage = msg.percentage
        voltage = msg.voltage
        self.comunicator.handle_battery(drone_id=self.drone_id, percentage= percentage, voltage = voltage)

    def _on_state(self, msg):
        connected = msg.connected
        armed = msg.armed
        guided = msg.guided
        manual_input = msg.manual_input
        mode = msg.mode
        self.comunicator.handle_state(drone_id=self.drone_id, connected = connected, armed = armed, guided = guided, manual_input = manual_input, mode = mode)


    def image_msg_to_qimage(self, msg):
        width = msg.width
        height = msg.height
        step = msg.step
        encoding = msg.encoding.lower()

        data = bytes(msg.data)

        if encoding == "rgb8":
            img = QImage(data, width, height, step, QImage.Format_RGB888)
            return img.copy()

        if encoding == "bgr8":
            img = QImage(data, width, height, step, QImage.Format_RGB888)
            return img.rgbSwapped().copy()

        if encoding == "mono8":
            img = QImage(data, width, height, step, QImage.Format_Grayscale8)
            return img.copy()

        if encoding == "rgba8" and hasattr(QImage, "Format_RGBA8888"):
            img = QImage(data, width, height, step, QImage.Format_RGBA8888)
            return img.copy()

        if encoding == "bgra8" and hasattr(QImage, "Format_RGBA8888"):
            img = QImage(data, width, height, step, QImage.Format_RGBA8888)
            return img.rgbSwapped().copy()

        return None
