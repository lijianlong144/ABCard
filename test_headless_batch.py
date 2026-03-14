#!/usr/bin/env python3
"""
批量测试 headless CDP 跳过 hCaptcha 的概率。
每次创建新 checkout session, 尝试 headless 支付, 记录是否跳过 hCaptcha。
"""
import logging
import json
import glob
import sys
import time

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logging.getLogger("browser_payment").setLevel(logging.INFO)
logging.getLogger("http_client").setLevel(logging.WARNING)
logger = logging.getLogger("batch_test")

PROXY = "http://172.25.16.1:7897"
CARD_NUMBER = "4462220004624356"
CARD_EXP_MONTH = "03"
CARD_EXP_YEAR = "2029"
CARD_CVC = "173"
BILLING_NAME = "Test User"
BILLING_COUNTRY = "GB"
BILLING_ZIP = "N2 8EY"
BILLING_LINE1 = "Langley House"

NUM_TESTS = int(sys.argv[1]) if len(sys.argv) > 1 else 5


def load_credentials():
    cred_files = sorted(glob.glob("test_outputs/credentials_*.json"))
    if not cred_files:
        print("没有找到保存的凭证")
        sys.exit(1)
    return json.load(open(cred_files[-1]))


def main():
    cred = load_credentials()
    logger.info(f"邮箱: {cred['email']}")
    logger.info(f"测试次数: {NUM_TESTS}")

    from browser_payment import BrowserPayment

    results = []

    for i in range(NUM_TESTS):
        logger.info(f"\n{'='*50}")
        logger.info(f"测试 {i+1}/{NUM_TESTS}")

        bp = BrowserPayment(
            proxy=PROXY,
            headless=True,
            slow_mo=0,
        )

        try:
            result = bp.run_full_flow(
                session_token=cred["session_token"],
                access_token=cred["access_token"],
                device_id=cred.get("device_id", ""),
                card_number=CARD_NUMBER,
                card_exp_month=CARD_EXP_MONTH,
                card_exp_year=CARD_EXP_YEAR,
                card_cvc=CARD_CVC,
                billing_name=BILLING_NAME,
                billing_country=BILLING_COUNTRY,
                billing_zip=BILLING_ZIP,
                billing_line1=BILLING_LINE1,
                billing_email=cred.get("email", ""),
                chatgpt_proxy=PROXY,
                timeout=60,  # 60秒整体超时
            )
        except Exception as e:
            result = {"success": False, "error": str(e), "step": "exception"}

        step = result.get("step", "")
        error = result.get("error", "")[:80]
        hcaptcha_skipped = step == "confirm" and "card" in error.lower()
        hcaptcha_timeout = step == "hcaptcha_timeout"
        hcaptcha_passed = step == "hcaptcha" and "unable to authenticate" not in error.lower()

        status = "SKIP_HC" if hcaptcha_skipped else ("PASS_HC" if hcaptcha_passed else ("TIMEOUT" if hcaptcha_timeout else "FAIL"))
        results.append(status)

        logger.info(f"  结果: {status} | step={step} | error={error}")

        # 短暂间隔
        if i < NUM_TESTS - 1:
            time.sleep(2)

    # 统计
    logger.info(f"\n{'='*50}")
    logger.info(f"统计: {NUM_TESTS} 次测试")
    for s in ["SKIP_HC", "PASS_HC", "TIMEOUT", "FAIL"]:
        count = results.count(s)
        pct = count / NUM_TESTS * 100
        logger.info(f"  {s}: {count} ({pct:.0f}%)")
    logger.info(f"序列: {' → '.join(results)}")


if __name__ == "__main__":
    main()
