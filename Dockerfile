# Python Base Image from https://hub.docker.com/r/arm32v7/python/
# FROM arm64v8/python:3.11-rc-bullseye
FROM python:3.9.13-alpine

RUN apk add iw
COPY iwscan.py ./

# Trigger test
#ENTRYPOINT ["tail", "-f", "/dev/null"]
CMD ["python", "./iwscan.py"]

EXPOSE 5024