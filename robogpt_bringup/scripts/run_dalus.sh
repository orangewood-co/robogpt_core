#!/bin/bash

# Use $USER to set a default home directory if USER_HOME is not already set
USER_HOME="${USER_HOME:-/home/owl-desktop}"
CONTAINER_NAME="${CONTAINER_NAME:-dalus-owl}"
DOCKER_IMAGE="${DOCKER_IMAGE:-dalus-owl:latest}"
DOCKER_ENTRYPOINT="${DOCKER_ENTRYPOINT:-/ros_entrypoint.sh}"
ROBASSETS_PATH="${ROBASSETS_PATH:-${USER_HOME}/robogpt-assets}"
DEV_PATH="${DEV_PATH:-${USER_HOME}/orangewood_ws/src/robogpt_apps/scripts/sf_demo/dalus_files}"

# X11 configuration for GUI forwarding
xhost local:root
XAUTH=/tmp/.docker.xauth

# Launch the Docker container command in a new terminal
gnome-terminal -- bash -c "\
docker run -it \
    --name \"${CONTAINER_NAME}\" \
    --entrypoint \"${DOCKER_ENTRYPOINT}\" \
    --gpus all \
    --network=host \
    --privileged \
    --runtime nvidia \
    -e DISPLAY=\"$DISPLAY\" \
    -v \"$XAUTH\":/root/.Xauthority \
    -v \"$ROBASSETS_PATH\":/root/owl_assets \
    -v \"$DEV_PATH\":/root/dev \
    \"${DOCKER_IMAGE}\" \
    bash -c \"cd root && source setup_env.sh && python DalusSimCoreRelease/dalus_sim_app.py; exec bash\"; \
echo 'Press any key to exit...'; read -n 1"


# Terminal 2: Open a new terminal for the secondary command
gnome-terminal -- bash -c 'docker exec -it dalus-owl bash -c "cd /root && source setup_sim.sh && python3 dev/custom_bg.py; exec bash"'

