#include "rclcpp/rclcpp.hpp"
#include "sensor_msgs/msg/compressed_image.hpp"

#include <arpa/inet.h>
#include <sys/socket.h>
#include <unistd.h>
#include <cstring>

class DroneBridge : public rclcpp::Node
{
public:
    DroneBridge()
    : Node("drone_bridge")
    {
      sockfd_ = socket(AF_INET, SOCK_DGRAM, 0);
      if (sockfd_ < 0)
      {
          perror("socket creation failed");
          exit(EXIT_FAILURE);
      }

      memset(&servaddr_, 0, sizeof(servaddr_));
      memset(&cliaddr_, 0, sizeof(cliaddr_));

      servaddr_.sin_family = AF_INET;
      servaddr_.sin_addr.s_addr = INADDR_ANY;
      servaddr_.sin_port = htons(5000);

      if (bind(sockfd_, (const struct sockaddr *)&servaddr_, sizeof(servaddr_)) < 0)
      {
          perror("bind failed");
          exit(EXIT_FAILURE);
      }

      RCLCPP_INFO(this->get_logger(), "UDP Image server started, waiting for client");
      
      recvfrom(sockfd_, NULL, 0,  
              MSG_WAITALL, ( struct sockaddr *) &cliaddr_, 
              &len_); 

      subscription_ = this->create_subscription<sensor_msgs::msg::CompressedImage>(
          "/image_raw/compressed",
          10,
          std::bind(&DroneBridge::topic_callback, this, std::placeholders::_1));

      RCLCPP_INFO(this->get_logger(), "Client connected");
    }

private:
    int sockfd_;
    struct sockaddr_in servaddr_;
    struct sockaddr_in cliaddr_;
    socklen_t len_;

    rclcpp::Subscription<sensor_msgs::msg::CompressedImage>::SharedPtr subscription_;

    void topic_callback(const sensor_msgs::msg::CompressedImage::SharedPtr msg)
    {
      ssize_t sent = sendto(
          sockfd_,
          msg->data.data(),
          msg->data.size(),
          MSG_CONFIRM,
          (const struct sockaddr *)&cliaddr_,
          len_);

      if (sent < 0)
      {
          perror("sendto failed");
      }
      else
      {
          RCLCPP_INFO(this->get_logger(), "Sent image: %ld bytes", sent);
      }
    }
};

int main(int argc, char *argv[])
{
    rclcpp::init(argc, argv);
    rclcpp::spin(std::make_shared<DroneBridge>());
    rclcpp::shutdown();
    return 0;
}