# -*- coding: utf-8 -*-
from typing import Union
import datetime


def tohex(data: Union[str, int, bytes], with_space: bool = True):
    if isinstance(data, str):
        data = bytes.fromhex(data)
    if isinstance(data, int):
        data = bytes([data])
    if with_space:
        return " ".join(f"{b:02x}" for b in data)
    else:
        return "".join(f"{b:02x}" for b in data)


def print_hex(data: Union[str, int, bytes]):
    print(tohex(data))


def decode_number(data: Union[str, int, bytes]):
    number = ""
    if isinstance(data, str):
        data = bytes.fromhex(data)
    if isinstance(data, int):
        data = bytes([data])
    for b in data:
        number += f"{b:02x}"[::-1]
    i = len(number)
    while number[i - 1] == "f":
        i -= 1
    return number[:i]


def gsm_7bit_decode(ud: bytes) -> str:
    f = tohex(ud, False)
    f = "".join(
        ["{0:08b}".format(int(f[i : i + 2], 16)) for i in range(0, len(f), 2)][::-1]
    )
    chrs = [chr(int(f[::-1][i : i + 7][::-1], 2)) for i in range(0, len(f), 7)]
    return "".join([c for c in chrs if c != "\x00"])


def gsm_8bit_decode(ud: bytes) -> str:
    return "".join([chr(b) for b in ud])


def gsm_usc2_decode(ud: bytes) -> str:
    return ud.decode("utf-16-be")


def decode_udl(data: Union[bytes, int], dcs: int) -> str:
    if isinstance(data, int):
        data = bytes([data])
    if dcs == 0:
        return gsm_7bit_decode(data)
    elif dcs == 4:
        return gsm_8bit_decode(data)
    elif dcs == 8:
        return gsm_usc2_decode(data)
    else:
        raise ValueError(f"Unknown DCS: {dcs}")


def decode_pdu(data: str, length: int):
    b = bytes.fromhex(data)
    i = 0

    n = int(b[i + i])
    i += 1
    sca_ton = int(b[i] >> 4 & 0b111)
    sca_npi = int(b[i] & 0b1111)
    i += 1
    sca = b[i : i + n - 1]
    i += n - 1

    _ = b[i]
    i += 1

    m = int(b[i])
    i += 1
    oa_ton = int(b[i] >> 4 & 0b111)
    oa_npi = int(b[i] & 0b1111)
    i += 1
    oa = b[i : i + (m + 1) // 2]
    from_number = decode_number(oa)
    i += (m + 1) // 2

    pid = int(b[i])
    i += 1

    dcs = int(b[i])
    i += 1

    scts = b[i : i + 7]
    recv_dt = datetime.datetime(
        2000 + int(decode_number(scts[0])),
        int(decode_number(scts[1])),
        int(decode_number(scts[2])),
        int(decode_number(scts[3])),
        int(decode_number(scts[4])),
        int(decode_number(scts[5])),
        tzinfo=datetime.timezone(
            datetime.timedelta(
                minutes=int(decode_number(scts[6] & 0b11110111))
                * (-1 if (scts[6] & 0b00001000) >> 3 else 1)
                * 15
            )
        ),
    )
    i += 7

    udl = int(b[i])
    i += 1

    ud = b[i : i + udl]
    i += udl

    return (
        ("+" if oa_ton else "") + from_number,
        recv_dt,
        decode_udl(ud, dcs),
    )
