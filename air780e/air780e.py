# -*- coding: utf-8 -*-

import re

from loguru import logger
import serial
from serial.tools.list_ports import comports

from .error import ModuleNotFoundError


class BaseATDevice:
    def __init__(self, port: str, baudrate: int = 115200, timeout: float = 1):
        self.port = port
        self.baudrate = baudrate

        self.s = serial.Serial(timeout=timeout)
        # 手动赋值, 否则Serial会在创建后直接连接
        self.s.port = port
        self.s.baudrate = baudrate

    def open(self):
        self.s.open()
        logger.debug(f"Serial opened on {self.s.portstr}")

    def close(self):
        self.s.close()

    def __enter__(self):
        self.open()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def send(self, command: str):
        if self.s.closed:
            raise RuntimeError("Serial closed")

        self.s.write(command.encode("utf-8") + b"\r\n")
        self.s.flush()
        logger.debug(f"TX: {command}")

    def readline(self, raise_timeout: bool = True) -> str:
        line_raw = b""
        while True:
            raw = self.s.readline()
            if not raw:
                if raise_timeout:
                    raise TimeoutError("Serial timeout")
                break
            line_raw += raw
            if raw.endswith(b"\r\n"):
                break
        if line := line_raw.decode("utf-8").strip():
            logger.debug(f"RX: {line}")
        return line

    def send_recv(self, command: str):
        self.send(command)

        lines = []
        status = "OK"
        while True:
            line = self.readline().strip()

            if not line or line == command:
                continue
            if line == "OK":
                break
            if line == "ERROR":
                status = "ERROR"
                break

            lines.append(line)

        data = "\n".join(lines)
        if status == "ERROR":
            raise RuntimeError("Module Error")
        return data

    def send_regex(self, command: str, regex: str):
        resp = self.send_recv(command)
        if (r := re.search(regex, resp)) is None:
            raise RuntimeError(f"Cannnot get {regex}")
        return r.groups()


class Air780E(BaseATDevice):
    def get_full_info(self) -> dict[str, str]:
        resp = self.send_recv("AT*I")
        manufacturer = re.search(r"Manufacturer:(.+)", resp).group(1).strip()
        model = re.search(r"Model:(.+)", resp).group(1).strip()
        revision = re.search(r"Revision:(.+)", resp).group(1).strip()
        hw_ver = re.search(r"HWver:(.+)", resp).group(1).strip()
        build_time = re.search(r"Buildtime:(.+)", resp).group(1).strip()
        imei = re.search(r"IMEI:(.+)", resp).group(1).strip()
        iccid = re.search(r"ICCID:(.*)", resp).group(1).strip()
        imsi = re.search(r"IMSI:(.*)", resp).group(1).strip()
        return {
            "Manufacturer": manufacturer,
            "Model": model,
            "Revision": revision,
            "HWVer": hw_ver,
            "Buildtime": build_time,
            "IME": imei,
            "ICCID": iccid,
            "IMSI": imsi,
        }

    def reset(self):
        self.send_recv("AT+RESET")

    def check_module(self):
        self.send_recv("AT")
        model = self.send_regex("AT+CGMM", r"\+CGMM: \"(.+?)\"")[0]
        assert model == "Air780E"

    @classmethod
    def find_module(cls, baudrate: int = 115200, timeout: float = 1):
        com_list = comports()
        logger.debug(f"COM ports: {[com.device for com in com_list]}")
        for com in com_list:
            s = cls(com.device, baudrate, timeout=timeout)
            try:
                s.open()
                s.check_module()
                return s
            except Exception:
                s.close()
        raise ModuleNotFoundError("Cannot find Air780E")


class FakeAir780E:
    def __init__(self, *args, **kwargs):
        self.port = "FAKE"
        self.ptr = 0
        self.sms = [
            "+CMT: ,24",
            "0791448720003023600ED0E7B4D97C0E9BCD000052108060510200A005000390030190E53C68880ECBD9E9320B742FB3C7EF7619447F8386E8B43BEC0235C3EB32685E979741F9775D0E0A8FC7EFBA9B0E4ACF416937682C2F93D37410FD0DAACFCB20F93BDC4EBBCFA079596E4F8FCB7310BA2C2FBB148A6198CD9E83C6EF391D1488B960AF76DA5DA79741F437A81D5E9741613719242F8FCB697BD905A296F1F439282C2F8366",
            "+CMT: ,24",
            "0791448720003023440ED0E7B4D97C0E9BCD000052108060510200A0050003900302607010FD0D9A97DD6490B84E0799E5E53288FE06C9CBE372DA5E768188617A18949E83C6E8B0FC5C2683C274900C067F35852E85C2F89683DA6F791994769BDFA0B71B549FA7DD6750FE5D9783E0E8B7BB0C0A8BE5EF3099051AA3CBE335E85DA783CE69B3F91C369B5DE377FB257F87DB69F7B9354687E5E7F21C04022914D9771D340EBB41",
            "+CMT: ,24",
            "0791448720003023400ED0E7B4D97C0E9BCD0000521080605102009A050003900303DA6F779AFE9683F2EFBA1C549F87CF6516A81D7687CF65D01C5E7693D3EE330B34BFA7E96334C8FDA6A7CDE971989E7EBBE7A0B7FBF5369B416F39885E97BB41F277B89D769F416FB319947683F2EFBA1C141E8FDF75375D073AA7CDE673D86C768DDFED17393C478BDF613959A118A2CB65F9DC059A86CD65105D1EB697D97317",
            "+CMT: ,24",
            "0891683108200105F0040D91683129634152F600002180804184422304F7349B0D",
        ]

    @classmethod
    def find_module(cls, *args, **kwargs):
        return cls()

    def check_module(self, *args, **kwargs):
        pass

    def get_full_info(self, *args, **kwargs):
        return {}

    def send_recv(self, *args, **kwargs):
        pass

    def send_regex(self, command: str, *args, **kwargs):
        if "AT*SIMDETEC" in command:
            return ["SIM"]
        if "AT+ICCID" in command:
            return ["12345678901234567890"]
        if "AT+COPS?" in command:
            return ["FAKE"]
        if "AT+CGATT?" in command:
            return ["1"]
        if "AT+CGREG?" in command:
            return ["1"]

    def readline(self, *args, **kwargs):
        if self.ptr >= len(self.sms):
            self.ptr = 0
        line = self.sms[self.ptr]
        self.ptr += 1
        return line
