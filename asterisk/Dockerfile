FROM andrius/asterisk:latest
USER root
RUN apt-get update && apt-get install -y python3-pip ffmpeg sox && \
    pip3 install python-dotenv openai pyst2 --break-system-packages
