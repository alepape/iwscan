# Python Base Image from https://hub.docker.com/r/arm32v7/python/
# FROM arm64v8/python:3.11-rc-bullseye
FROM python:3.9.13-alpine

RUN apk add iw
COPY iwscan.py ./
COPY paho_mqtt-2.1.0-py3-none-any.whl ./
RUN pip install paho_mqtt-2.1.0-py3-none-any.whl

# TODO: refer to config file / ENV vars from container config?
# see yacje for an example

# Trigger test
#ENTRYPOINT ["tail", "-f", "/dev/null"]
CMD ["python", "./iwscan.py"]

EXPOSE 5024