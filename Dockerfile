FROM python:3.12-slim

WORKDIR /app

ENV COM_PORT=auto
ENV COM_BAUD=115200

RUN pip install pyserial loguru --no-cache-dir -i https://pypi.tuna.tsinghua.edu.cn/simple

ADD . /app/

ENTRYPOINT [ "sh", "-c", "python main.py -p ${COM_PORT} -b ${COM_BAUD}" ]