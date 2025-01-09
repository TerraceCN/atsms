# -*- coding: utf-8 -*-

import argparse
import sys
import time

from loguru import logger

from air780e import Air780E, ModuleNotFoundError, MTPDU

sms_tmp: dict[bytes, list[MTPDU]] = {}  # 长短信暂存


def handle_cmt(data: bytes):
    global sms_tmp
    try:
        sms = MTPDU.decode(data)
        logger.debug(f"Receive SMS: {sms}")
    except Exception:
        logger.error(f"Failed to decode PDU, raw data: {data}")
        return

    logger.debug(f"Receive SMS: {sms}")
    if sms.ud.iei == 0x00:  # 长短信
        ident = sms.ud.ied[0:-2]  # 短信标识
        total = sms.ud.ied[-2]  # 短信总条数
        index = sms.ud.ied[-1]  # 短信序号

        logger.info(f"[Receive long SMS] Ident: {ident}, Progress: {index}/{total}")

        if ident not in sms_tmp:
            sms_tmp[ident] = []
        sms_tmp[ident].append(sms)

        if len(sms_tmp[ident]) != total:  # 消息未接收完整
            return

        sms_tmp[ident].sort(key=lambda x: x.ud.ied[-1])  # 排序

        sender = str(sms_tmp[ident][0].oa)
        sc_time = sms_tmp[ident][0].scts.strftime("%Y-%m-%d %H:%M:%S %z")
        content = "".join(x.ud.content for x in sms_tmp[ident])

        sms_tmp.pop(ident)
    else:
        sender = str(sms.oa)
        sc_time = sms.scts.strftime("%Y-%m-%d %H:%M:%S %z")
        content = sms.ud.content

    logger.info(f"[Receive SMS] FROM: {sender}, TIME: {sc_time}, CONTENT: {content!r}")


def main(arg):
    if arg.port == "auto":
        try:
            module = Air780E.find_module(baudrate=arg.baudrate, timeout=30)
        except ModuleNotFoundError:
            logger.error("Air780E is not found")
            return
    else:
        module = Air780E(arg.port, arg.baudrate)
        module.open()
        module.check_module()

    logger.info(f"Air780E connected, port: {module.port}")

    info = module.get_full_info()
    for k, v in info.items():
        logger.info(f"{k}: {v}")

    module.send_recv("ATE1")  # 启动命令回显
    module.send_recv("AT+CMEE=0")  # 禁用结果码
    module.send_recv("AT+CSCS=UCS2")  # 设置TE字符集为UCS-2
    module.send_recv("AT+CMGF=0")  # 设置短信格式为PDU
    module.send_recv("AT+CNMI=2,2,0,0,0")  # 设置新消息指示
    module.send_recv("AT&W")  # 保存配置

    sim_detect = module.send_regex("AT*SIMDETEC=1", r"\*SIMDETEC: \d+,(NOS|SIM)")[0]
    if sim_detect != "SIM":  # SIM卡检测
        logger.error("SIM card is not detected")
        return
    iccid = module.send_regex("AT+ICCID", r"\+ICCID: (.+)")[0]  # 获取ICCID
    logger.info(f"SIM card is detected, ICCID: {iccid}")

    # module.send_recv("AT^SYSCONFIG=2,0,1,1")  # 设置网络模式
    # module.send_recv("AT+COPS=4,2,46001")  # 设置运营商
    # module.send_recv("AT+CPNETAPN=2,giffgaff.com,gg,p")  # 设置APN

    while int(module.send_regex("AT+CGATT?", r"\+CGATT: (\d)")[0]) == 0:  # 等待GPRS附着
        gprs_status = int(module.send_regex("AT+CGREG?", r"\+CGREG: \d+,(\d)")[0])
        logger.info(f"Waiting for GPRS attaching (current status: {gprs_status})")
        time.sleep(1)

    module.send_recv("AT+COPS=3,0")  # 设置运营商格式
    cper = module.send_regex("AT+COPS?", r"\+COPS: \d+,\d+,\"(.+?)\"")[0]  # 获取运营商
    logger.info(f"GPRS attached, Operator: {cper}")

    # module.send_recv("AT+CGREG=1")  # 打开网络注册状态主动上报
    # module.send_recv("AT*CSQ=1")  # 打开信号质量主动上报

    logger.info("Waiting for SMS...")
    while True:
        line = module.readline(False)

        if line.startswith("+CMT:"):
            try:
                pdu = module.readline()
                handle_cmt(pdu)
            except Exception:
                logger.exception(f"Failed to handle CMT")

        if line.startswith("+CSQ"):
            pass


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
