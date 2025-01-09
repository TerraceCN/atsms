# -*- coding: utf-8 -*-

from datetime import datetime, timedelta, timezone
from dataclasses import dataclass
from math import ceil
from typing import Optional

from .encoding import number_decode, gsm7bit_decode, decode_by_dcs


@dataclass
class Address:
    ton: int  # 地址类型
    # 000: Unknown
    # 001: International number
    # 010: National number
    # 011: Network specific number
    # 100: Subscriber number
    # 101: Alphanumeric, (coded according to 3GPP TS 23.038 [9] GSM 7-bit default alphabet)
    # 110: Abbreviated number
    # 111: Reserved for extension
    npi: int  # 地址鉴别
    # 0000: Unknown
    # 0001: ISDN/telephone numbering plan (E.164/E.163)
    # 0011: Data numbering plan (X.121)
    # 0100: Telex numbering plan
    # 0101: Service Centre Specific plan 1)
    # 0110: Service Centre Specific plan 2)
    # 1000: National numbering plan
    # 1001: Private numbering plan
    # 1010: ERMES numbering plan (ETSI DE/PS 3 01 3)
    # 1111: Reserved for extension
    addr: str  # 地址

    @classmethod
    def decode(cls, data: bytes):
        ton = int(data[0] >> 4 & 0b0111)
        npi = int(data[0] & 0b1111)

        if ton == 0b101:  # Alphanumeric
            addr = gsm7bit_decode(data[1:])
        else:
            addr = number_decode(data[1:])  # 去掉尾部填充的f

        return cls(ton=ton, npi=npi, addr=addr)

    def __str__(self):
        if self.ton == 0b001:
            return f"+{self.addr}"
        else:
            return self.addr


@dataclass
class UserData:
    iei: Optional[int]  # 消息元素标识符
    ied: Optional[bytes]  # 消息元素数据
    content: str  # 消息内容

    @classmethod
    def decode(cls, data: bytes, tp_udhi: bool, dcs: int):
        iei = None
        ied = None
        if tp_udhi:  # 如果有用户数据头
            udhl = data[0] + 1
            iei = data[1]
            iedl = data[2]
            ied = data[3 : 3 + iedl]

            # 去除用户数据头
            if dcs == 0:  # GSM-7bit 编码
                f = "".join([f"{i:08b}" for i in data][::-1])
                f = f[len(f) % 7 : -ceil(udhl * 8 / 7) * 7]
                f = "0" * (8 - len(f) % 8) + f
                data = bytes([int(f[i : i + 8], 2) for i in range(0, len(f), 8)][::-1])
            else:
                data = data[udhl:]

        content = decode_by_dcs(data, dcs)  # 用户数据

        return cls(iei=iei, ied=ied, content=content)


@dataclass
class MTPDU:
    sca: Address  # 短信中心地址
    oa: Address  # 源地址
    scts: datetime  # 短信中心时间戳
    ud: UserData  # 用户数据

    @classmethod
    def decode(cls, data_hex: str):
        data = bytes.fromhex(data_hex)
        pt = 0

        scal = data[pt]  # 短信中心地址长度
        pt += 1
        sca = Address.decode(data[pt : pt + scal])  # 短信中心地址
        pt += scal

        tp_udhi = bool(data[pt] >> 6 & 0b1)
        pt += 1

        oal = (data[pt] + 1) // 2 + 1  # 源地址长度
        pt += 1
        oa = Address.decode(data[pt : pt + oal])  # 源地址
        pt += oal

        pt += 1  # 跳过PID
        dcs = data[pt]  # 数据编码
        pt += 1

        scts = data[pt : pt + 7]  # 短信中心时间戳
        dt = [int(number_decode(t)) for t in scts[:6]]  # 年, 月, 日, 时, 分, 秒
        dt[0] += datetime.now().year // 100 * 100  # 加上世纪
        tz = timezone(  # 时区
            timedelta(
                minutes=int(number_decode(scts[6] & 0xF7))
                * (-1 if (scts[6] & 0x08) >> 3 else 1)
                * 15
            )
        )
        scts = datetime(*dt, tzinfo=tz)
        pt += 7

        udl = data[pt]  # 用户数据长度
        pt += 1

        ud = UserData.decode(data[pt : pt + udl], tp_udhi, dcs)  # 用户数据

        return cls(
            sca=sca,
            oa=oa,
            scts=scts,
            ud=ud,
        )
