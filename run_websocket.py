import signal
import telebot
from datetime import datetime
import pytz
import asyncio
from websocket_manager import WebsocketManager
from utils import *
from config import (TIMEZONE, TELEGRAM_BOT_TOKEN, TEST_TG_CHAT_ID_2,
                    MAX_RETRIES, ADDRESSES_TO_TRACK, SUBSCRIPTION_TYPE)

bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN, threaded=False)
is_first_message = True
send_to_tg = True

try:
    timezone = pytz.timezone(TIMEZONE)
except:
    timezone = pytz.timezone('Asia/Singapore')


def get_direction_icon(direction):
    if direction in ["Open Long", "Long"]:
        return "🟢"
    elif direction == ["Open Short", 'Short']:
        return "🔴"
    elif direction in ["Close Long", "Close Short"]:
        return "🔵"
    else:
        return "⚪"


def on_user_fills_message(ws_msg):
    global is_first_message

    if not isinstance(ws_msg, dict):
        print("Unexpected message format:", type(ws_msg))
        return

    try:
        fills = ws_msg.get("data", {}).get("fills", [])

        if not fills:
            print("No fills found in the message.")
            return

        if is_first_message:
            is_first_message = False
            print("Skipping alert for historical data.")
            return

        msg_list = []
        msg = f"🚨 **Trade Filled Alert** 🚨\n\n"

        print("Received user fills:")
        for fill in fills:
            coin = fill.get("coin")
            px = float(fill.get("px", 0))
            sz = float(fill.get("sz", 0))
            sz_usd = px * sz
            timestamp = fill.get("time")
            direction = fill.get("dir")

            dt_utc = datetime.utcfromtimestamp(timestamp / 1000)
            dt_sg = pytz.utc.localize(dt_utc).astimezone(timezone)
            dt_str = dt_sg.strftime('%Y-%m-%d %H:%M:%S')

            msg = msg + (
                f"🔗 *Tracked Address*: {ADDRESSES_TO_TRACK[0]}\n"
                f"⏰ **Time**: {dt_str}\n"
                f"💰 **Coin**: {coin}\n"
                f"📊 **Price**: ${px:,.2f}\n"
                f"💵 **Size (in USD)**: ${sz_usd:,.2f}\n"
                f"{get_direction_icon(direction)} **Direction**: {direction}\n"
            )

            print(msg)

            msg_list.append(msg)

        if send_to_tg:
            send_to_telegram(msg_list, bot, TEST_TG_CHAT_ID_2, MAX_RETRIES, 1,
                             5)

    except Exception as e:
        print(f"Error processing userFills message: {e}")
        if send_to_tg:
            error_message += f"❌ **An error occurred while processing the userFills message** ❌\n\n"
            error_message += f"**Error Message**: {e}\n"
            error_message += f"Please investigate the issue."
            msg_list = [error_message]
            send_to_telegram(msg_list, bot, TEST_TG_CHAT_ID_2, MAX_RETRIES, 1,
                             5)


def on_order_updates_message(ws_msg):

    if not isinstance(ws_msg, dict):
        print("Unexpected message format:", type(ws_msg))
        return

    try:
        orders = ws_msg.get("data", [])

        if not orders:
            print("No order found in the message.")
            return

        msg_list = []
        msg = f"🚨 **Order Updates Alert** 🚨\n\n"

        print("Received user fills:")
        for order in orders:
            basic_order = order.get("order", {})
            status = order.get("status", '')

            coin = basic_order.get("coin", '')
            side = basic_order.get("side", '')
            limit_px = float(basic_order.get("limitPx", 0))
            sz = float(basic_order.get("sz", 0))
            timestamp = basic_order.get("timestamp", 0)

            if side.upper() == 'A':
                direction = 'Short'
            elif side.upper() == 'B':
                direction = 'Long'
            else:
                direction = 'Unknown'

            sz_usd = limit_px * sz

            dt_utc = datetime.utcfromtimestamp(timestamp / 1000)
            dt_sg = pytz.utc.localize(dt_utc).astimezone(timezone)
            dt_str = dt_sg.strftime('%Y-%m-%d %H:%M:%S')

            msg = msg + (
                f"🔗 *Tracked Address*: {ADDRESSES_TO_TRACK[0]}\n"
                f"⏰ **Time**: {dt_str}\n"
                f"💰 **Coin**: {coin}\n"
                f"📊 **Limit Price**: ${limit_px:,.2f}\n"
                f"💵 **Size (in USD)**: ${sz_usd:,.2f}\n"
                f"{get_direction_icon(direction)} **Direction**: {direction}\n"
                f"🛒 **Order Status**: {status.capitalize()}\n")

            print(msg)

            msg_list.append(msg)

        if send_to_tg:
            send_to_telegram(msg_list, bot, TEST_TG_CHAT_ID_2, MAX_RETRIES, 1,
                             5)

    except Exception as e:
        print(f"Error processing orderUpdates message: {e}")
        if send_to_tg:
            error_message = f"❌ **An error occurred while processing the orderUpdates message** ❌\n\n"
            error_message += f"**Error Message**: {e}\n"
            error_message += f"Please investigate the issue."
            msg_list = [error_message]
            send_to_telegram(msg_list, bot, TEST_TG_CHAT_ID_2, MAX_RETRIES, 1,
                             5)


def on_ws_close(ws):
    print("WebSocket closed. Reconnecting...")
    if send_to_tg:
        error_message = f"❌ **WebSocket Closed** ❌\n\n"
        error_message += f"Attempting to reconnect..."
        msg_list = [error_message]
        send_to_telegram(msg_list, bot, TEST_TG_CHAT_ID_2, MAX_RETRIES, 1, 5)
    reconnect()


def on_ws_error(ws, error):
    print(f"WebSocket error: {error}. Reconnecting...")
    if send_to_tg:
        error_message = f"❌ **WebSocket Error** ❌\n\n"
        error_message += f"**Error**: {error}\n"
        error_message += f"Attempting to reconnect..."
        msg_list = [error_message]
        send_to_telegram(msg_list, bot, TEST_TG_CHAT_ID_2, MAX_RETRIES, 1, 5)
    reconnect()


async def create_ws_manager_and_subscribe():
    global ws_manager
    ws_manager = WebsocketManager("http://api.hyperliquid.xyz")
    ws_manager.on_close = on_ws_close
    ws_manager.on_error = on_ws_error
    ws_manager.start()
    if SUBSCRIPTION_TYPE == "userFills":
        subscription = {
            "type": "userFills",
            "user": ADDRESSES_TO_TRACK[0],
        }
        ws_manager.subscribe(subscription, on_user_fills_message)
    else:
        subscription = {"type": "orderUpdates", "user": ADDRESSES_TO_TRACK[0]}
        ws_manager.subscribe(subscription, on_order_updates_message)

    if send_to_tg:
        init_message = f"🚀 **WebSocket Started** 🚀\n\n"
        init_message += f"**Subscription Type**: {SUBSCRIPTION_TYPE}\n"
        init_message += f"**Tracked User Address**: {ADDRESSES_TO_TRACK[0]}"
        msg_list = [init_message]
        send_to_telegram(msg_list, bot, TEST_TG_CHAT_ID_2, MAX_RETRIES, 1, 5)


async def reconnect():
    global ws_manager
    await asyncio.sleep(2)
    print("Attempting to reconnect...")

    if ws_manager:
        ws_manager.stop()

    await create_ws_manager_and_subscribe()


async def main():
    global ws_manager
    await create_ws_manager_and_subscribe()

    while True:
        await asyncio.sleep(1)


def signal_handler(sig, frame):
    print("Stopping WebSocketManager...")
    if ws_manager:
        ws_manager.stop()
    print("WebSocketManager stopped. Exiting.")
    exit(0)


signal.signal(signal.SIGINT, signal_handler)

if __name__ == "__main__":
    asyncio.run(main())
