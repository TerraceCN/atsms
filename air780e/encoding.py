# -*- coding: utf-8 -*-

from typing import Union


def tohex(data: Union[bytes, int], pair_flip: bool = False, with_space: bool = False):
    if isinstance(data, int):
        data = bytes([data])

    data_hex = [f"{b:02x}" for b in data]
    if pair_flip:
        data_hex = [h[::-1] for h in data_hex]

    sep = ""
    if with_space:
        sep = " "

    return sep.join(data_hex)


def number_decode(data: Union[bytes, int]):
    return tohex(data, pair_flip=True).rstrip("f")


def gsm7bit_decode(f):
    gsm = "@£$¥èéùìòÇ\nØø\rÅåΔ_ΦΓΛΩΠΨΣΘΞ\x1bÆæßÉ !\"#¤%&'()*+,-./0123456789:;<=>?¡ABCDEFGHIJKLMNOPQRSTUVWXYZÄÖÑÜ`¿abcdefghijklmnopqrstuvwxyzäöñüà"
    ext = "````````````````````^```````````````````{}`````\\````````````[~]`|````````````````````````````````````€``````````````````````````"

    if len(f) == 0:
        return ""

    f = "".join([f"{i:08b}" for i in f][::-1])
    padlen = len(f) % 7
    f = f[padlen::]

    ints = [int(f[i : i + 7], 2) for i in range(0, len(f), 7)][::-1]
    result = []
    if ints[0] == 0:
        ints.pop(0)
    is_ext = False
    for i in ints:
        if is_ext:
            result.append(ext[i])
            is_ext = False
        elif i == 0x1B:
            is_ext = True
        else:
            result.append(gsm[i])
    return "".join(result)


def gsm8bit_decode(data: bytes):
    return "".join([chr(b) for b in data])


def ucs2_decode(data: bytes):
    return data.decode("utf-16-be")


def decode_by_dcs(data: bytes, dcs: int):
    if dcs == 0:
        decoded = gsm7bit_decode(data)
    elif dcs == 4:
        decoded = gsm8bit_decode(data)
    elif dcs == 8:
        decoded = ucs2_decode(data)
    else:
        raise ValueError(f"Unsupported data decoding scheme: {dcs}")
    return decoded
