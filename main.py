# -*- coding: utf-8 -*-
import sys
import argparse
import re
import time

import serial
import serial.threaded
from serial.tools.list_ports import comports
from loguru import logger

from pdu import *


class Air780E:
    def __init__(self, port, baudrate=115200, timeout=1):
        self.port = port
        self.baudrate = baudrate
        self.s = serial.Serial(timeout=timeout)
        self.s.port = port
        self.s.baudrate = baudrate

    def open(self):
        self.s.open()

    def close(self):
        self.s.close()

    def send(self, command: str):
        self.s.write(command.encode("utf-8") + b"\r\n")
        self.s.flush()
        logger.debug(f"Serial send: {command}")

    def readline(self, raise_timeout: bool = True) -> str:
        line_raw = b""
        while True:
            raw = self.s.readline()
            if not raw:
                if raise_timeout:
                    raise RuntimeError("Serial timeout")
                break
            line_raw += raw
            if raw.endswith(b"\r\n"):
                break
        line = line_raw.decode("utf-8").strip()
        if line:
            logger.debug(f"Serial recv: {line}")
        return line

    def send_recv(self, command: str):
        self.send(command)

        lines = []
        status = "OK"
        while True:
            line = self.readline()

            if not line or line == command:
                continue
            if line == "OK":
                break
            if line == "ERROR":
                status = "ERROR"
                continue

            lines.append(line)

        data = "\n".join(lines)
        if status == "ERROR":
            raise RuntimeError(f"AT command error: {data}")
        return data

    def set_config(self):
        self.send_recv("ATE0")
        self.send_recv('AT+UPGRADE="AUTO",0')
        self.send_recv("AT+CMGF=0")
        self.send_recv('AT+CSCS="UCS2"')
        self.send_recv("AT+CNMI=2,2,0,0,0")

    def send_regex(self, command: str, regex: str):
        resp = self.send_recv(command)
        if (r := re.match(regex, resp)) is None:
            raise RuntimeError(f"Cannnot get {regex}")
        return r.groups()

    def cgmm(self) -> str:
        return self.send_regex("AT+CGMM", r"\+CGMM: \"(.*?)\"")[0]

    def simdetec(self) -> bool:
        return (
            self.send_regex("AT*SIMDETEC=1", r"\*SIMDETEC: (\d),(NOS|SIM)")[1] == "SIM"
        )

    def iccid(self) -> str:
        return self.send_regex("AT+ICCID", r"\+ICCID: (\d+)")[0]

    def cgatt(self) -> bool:
        return self.send_regex("AT+CGATT?", r"\+CGATT: (\d)")[0] == "1"

    def sms_loop(self):
        while True:
            line = self.readline(False)

            if not line.startswith("+CMT:"):
                continue

            _, length = line[5:].split(",")
            pdu = self.readline()
            try:
                sms = decode_pdu(pdu, int(length))
                logger.info(
                    f"SMS from {sms[0]}, time: {sms[1].strftime('%Y-%m-%d %H:%M:%S %z')}, content: {sms[2]}"
                )
            except Exception:
                logger.error(f"Failed to decode PDU, raw data: {pdu}")

    def check_device(self):
        self.send_recv("AT")
        return self.cgmm() == "Air780E"


def main(arg):
    if arg.port == "auto":
        detected = False
        for s in comports():
            s = Air780E(s.device, arg.baudrate)
            try:
                s.open()
                if s.check_device():
                    detected = True
                    break
                else:
                    s.close()
            except Exception:
                s.close()
        if not detected:
            logger.error("Cannot find Air780E")
            return
    else:
        s = Air780E(arg.port, arg.baudrate)
        s.open()
        assert s.check_device()

    logger.info(f"Air780E connected, port: {s.s.portstr}")

    if not s.simdetec():
        logger.error("SIM card is not detected")
        return
    logger.info(f"SIM card is detected, ICCID: {s.iccid()}")

    s.set_config()

    while not s.cgatt():
        logger.info("Waiting for GPRS...")
        time.sleep(1)
    logger.info("GPRS is attached")

    logger.info("Waiting for SMS...")
    s.sms_loop()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="AT command SMS client",
    )
    parser.add_argument(
        "-p", "--port", default="auto", required=False, help="serial port"
    )
    parser.add_argument(
        "-b", "--baudrate", type=int, default=115200, required=False, help="baudrate"
    )
    parser.add_argument("--log-level", default="INFO", required=False, help="log level")
    args = parser.parse_args()

    logger.remove()
    logger.add(sys.stderr, level=args.log_level)

    main(args)
