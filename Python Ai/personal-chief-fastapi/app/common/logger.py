import logging
import sys

LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

def setup_logging():
    """
    设置日志记录
    """
    logging.basicConfig(
        format=LOG_FORMAT,
        level=logging.INFO,
        handlers=[
            logging.StreamHandler(sys.stdout),  # 打印到控制台
            # logging.FileHandler("app.log", encoding="utf-8")  # 可选：将日志写入文件
        ]
    )

logger = logging.getLogger("personal")