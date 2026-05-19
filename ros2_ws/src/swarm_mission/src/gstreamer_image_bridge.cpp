#include <memory>
#include <string>

#include "rclcpp/rclcpp.hpp"
#include "sensor_msgs/msg/image.hpp"

#include <cv_bridge/cv_bridge.h>
#include <opencv2/opencv.hpp>

class GStreamerImageBridge : public rclcpp::Node
{
public:
  GStreamerImageBridge()
  : Node("gstreamer_image_bridge")
  {
    topic_ = this->declare_parameter<std::string>("topic", "/drone1/image_raw");
    host_ = this->declare_parameter<std::string>("host", "127.0.0.1");
    port_ = this->declare_parameter<int>("port", 5601);
    width_ = this->declare_parameter<int>("width", 640);
    height_ = this->declare_parameter<int>("height", 480);
    fps_ = this->declare_parameter<int>("fps", 30);
    bitrate_ = this->declare_parameter<int>("bitrate", 1500);

    std::string pipeline =
    "appsrc is-live=true block=false format=time ! "
    "queue leaky=downstream max-size-buffers=2 ! "
    "videoconvert ! "
    "video/x-raw,format=I420,width=" + std::to_string(width_) +
    ",height=" + std::to_string(height_) +
    ",framerate=" + std::to_string(fps_) + "/1 ! "
    "x264enc tune=zerolatency bitrate=" + std::to_string(bitrate_) +
    " speed-preset=ultrafast key-int-max=15 bframes=0 ! "
    "rtph264pay config-interval=1 pt=96 ! "
    "udpsink host=" + host_ +
    " port=" + std::to_string(port_) + " sync=false async=false";

    RCLCPP_INFO(this->get_logger(), "Subscribing to: %s", topic_.c_str());
    RCLCPP_INFO(this->get_logger(), "Streaming to UDP: %s:%d", host_.c_str(), port_);
    RCLCPP_INFO(this->get_logger(), "Pipeline: %s", pipeline.c_str());

    writer_.open(
      pipeline,
      cv::CAP_GSTREAMER,
      0,
      static_cast<double>(fps_),
      cv::Size(width_, height_),
      true
    );

    if (!writer_.isOpened()) {
      RCLCPP_ERROR(this->get_logger(), "Failed to open GStreamer VideoWriter.");
      RCLCPP_ERROR(this->get_logger(), "Check if OpenCV has GStreamer support and if x264enc is installed.");
    } else {
      RCLCPP_INFO(this->get_logger(), "GStreamer VideoWriter opened successfully.");
    }

    auto qos = rclcpp::SensorDataQoS();

    image_sub_ = this->create_subscription<sensor_msgs::msg::Image>(
      topic_,
      qos,
      std::bind(&GStreamerImageBridge::imageCallback, this, std::placeholders::_1)
    );
  }

private:
  void imageCallback(const sensor_msgs::msg::Image::SharedPtr msg)
  {
    if (!writer_.isOpened()) {
      return;
    }

    try {
      cv_bridge::CvImageConstPtr cv_ptr;

      if (msg->encoding == "rgb8") {
        cv_ptr = cv_bridge::toCvShare(msg, "rgb8");
        cv::Mat bgr_frame;
        cv::cvtColor(cv_ptr->image, bgr_frame, cv::COLOR_RGB2BGR);
        processAndWriteFrame(bgr_frame);
      } else {
        cv_ptr = cv_bridge::toCvShare(msg, "bgr8");
        processAndWriteFrame(cv_ptr->image);
      }
    } catch (const cv_bridge::Exception & e) {
      RCLCPP_ERROR(this->get_logger(), "cv_bridge error: %s", e.what());
    } catch (const std::exception & e) {
      RCLCPP_ERROR(this->get_logger(), "Image processing error: %s", e.what());
    }
  }

  void processAndWriteFrame(const cv::Mat & frame)
  {
    cv::Mat resized;

    if (frame.cols != width_ || frame.rows != height_) {
      cv::resize(frame, resized, cv::Size(width_, height_));
    } else {
      resized = frame;
    }

    writer_.write(resized);
  }

  std::string topic_;
  std::string host_;
  int port_;
  int width_;
  int height_;
  int fps_;
  int bitrate_;

  cv::VideoWriter writer_;
  rclcpp::Subscription<sensor_msgs::msg::Image>::SharedPtr image_sub_;
};

int main(int argc, char ** argv)
{
  rclcpp::init(argc, argv);
  auto node = std::make_shared<GStreamerImageBridge>();
  rclcpp::spin(node);
  rclcpp::shutdown();
  return 0;
}