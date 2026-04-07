FROM andrius/asterisk:latest
RUN apt-get update && apt-get install -y python3-pip ffmpeg sox && \
    pip3 install python-dotenv openai pydub pyst2 --break-system-packages
