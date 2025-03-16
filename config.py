import os
from configparser import ConfigParser

root_dir = os.path.abspath(os.path.dirname(__file__))
config_file = os.path.join(root_dir, "private.ini")
cfg = ConfigParser()

if os.path.exists(config_file):
    cfg.read(config_file)
else:
    cfg = None

if cfg:
    if cfg.has_section('telegram'):
        telegram = dict(cfg.items('telegram'))
        TELEGRAM_BOT_TOKEN = telegram.get('telegram_bot_token', '')
        TEST_TG_CHAT_ID = telegram.get('test_tg_chat_id', '')
        TEST_TG_CHAT_ID_2 = telegram.get('test_tg_chat_id_2', '')
        USER_ID = telegram.get('user_id', '')
    else:
        TELEGRAM_BOT_TOKEN = ''
        TEST_TG_CHAT_ID = ''
        TEST_TG_CHAT_ID_2 = ''
        USER_ID = ''
    if cfg.has_section('hyperliquid'):
        hyperliquid = dict(cfg.items('hyperliquid'))
        cleaned_addresses = hyperliquid.get('addresses_to_track',
                                            '').replace("\\\n", "")
        ADDRESSES_TO_TRACK = [
            item.strip() for item in cleaned_addresses.split(",")
        ]
    else:
        ADDRESSES_TO_TRACK = ['']

else:
    TELEGRAM_BOT_TOKEN = ''
    TEST_TG_CHAT_ID = ''
    TEST_TG_CHAT_ID_2 = ''
    USER_ID = ''
    ADDRESSES_TO_TRACK = ['']

TIMEZONE = 'Asia/Singapore'
MIN_VAULT_TVL = 1e5
MIN_VAULT_APR = 10  # in %
MAX_RETRIES = 10
RETRY_AFTER = 10
MIN_POSITION_COUNTS = 3
EXCLUDED_VAULT_ADDRESSES = [
    "0xdfc24b077bc1425ad1dea75bcb6f8158e10df303",  # Hyperliquidity Provider (HLP)
    "0x010461c14e146ac35fe42271bdc1134ee31c703a",  # HLP Strategy A
    "0x2e3d94f0562703b25c83308a05046ddaf9a8dd14",  # HLP Liquidator
    "0x31ca8395cf837de08b24da3f660e77761dfb974b",  # HLP Strategy B
]
SUBSCRIPTION_TYPE = 'userFills'
