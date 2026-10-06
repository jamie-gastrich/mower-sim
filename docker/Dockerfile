FROM ros:lyrical-ros-base
WORKDIR /ws
# Copy only source to keep build fresh
COPY ros2_ws/src /ws/ros2_ws/src

COPY docker/entrypoint.sh /ws/entrypoint.sh
RUN chmod +x /ws/entrypoint.sh
CMD ["/ws/entrypoint.sh"]