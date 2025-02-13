import requests
import time
import re
import argparse
import telebot
from utils import *
from config import (MIN_VAULT_TVL, MIN_VAULT_APR, EXCLUDED_VAULT_ADDRESSES,
                    MAX_RETRIES, RETRY_AFTER, MIN_POSITION_COUNTS, USER_ID,
                    TEST_TG_CHAT_ID, TELEGRAM_BOT_TOKEN)


def get_top_tvl_vaults():

    response = requests.get(
        "https://stats-data.hyperliquid.xyz/Mainnet/vaults", verify=False)

    if response.status_code == 200:
        data = response.json()
        sorted_data = sorted(data,
                             key=lambda x: float(x['summary']['tvl']),
                             reverse=True)
        filtered_vaults = []

        for vault in sorted_data:
            vault_summary = vault.get('summary', {})
            vault_address = vault_summary.get('vaultAddress', '')
            vault_tvl = float(vault_summary.get('tvl', 0))
            if (vault_address) and (vault_address
                                    not in EXCLUDED_VAULT_ADDRESSES) and (
                                        vault_tvl >= MIN_VAULT_TVL):
                filtered_vaults.append(vault_summary)

        return filtered_vaults
    else:
        print(f"Error: {response.status_code}, {response.text}")
        return []


def get_vault_details(vault_address):

    url = "https://api.hyperliquid.xyz/info"
    headers = {"Content-Type": "application/json"}
    payload = {"type": "vaultDetails", "vaultAddress": vault_address}

    response = requests.post(url, headers=headers, json=payload, verify=False)

    if response.status_code == 200:
        data = response.json()
        return data
    else:
        print(f"Error: {response.status_code}, {response.text}")
        return {}


def get_vaults_updates(chat_id, send_to_tg=True):

    start_time = time.time()

    saved_data_base_dir = "./saved_data"
    tracked_top_tvl_vaults_dir = saved_data_base_dir + "/tracked_top_tvl_vaults"
    os.makedirs(tracked_top_tvl_vaults_dir, exist_ok=True)
    tracked_top_tvl_vaults_file_path = f"{tracked_top_tvl_vaults_dir}/tracked_top_tvl_vaults.json"
    tracked_top_tvl_vaults_dict = load_json_file(
        tracked_top_tvl_vaults_file_path)

    curr_top_tvl_vaults = get_top_tvl_vaults()

    if not curr_top_tvl_vaults:
        print("No vaults found. Exiting...")
        return

    count = 1
    valid_vaults_count = 0
    total_long_positions_value = 0
    total_short_positions_value = 0
    total_curr_top_tvl_vaults = len(curr_top_tvl_vaults)
    updated_top_tvl_vaults = {}
    long_short_counter = {"LONG": {}, "SHORT": {}}
    url = "https://api.hyperliquid.xyz/info"
    headers = {"Content-Type": "application/json"}

    for vault in curr_top_tvl_vaults:

        retry_count = 0
        break_flag = False
        vault_name = vault.get('name')
        vault_address = vault.get('vaultAddress')
        vault_tvl = float(vault.get('tvl', 0))

        if not vault_name:
            vault_name = vault_address

        print('\n')

        while retry_count < MAX_RETRIES:

            print("Retrieving vault details for {} ({}/{})...".format(
                vault_name, count, total_curr_top_tvl_vaults))

            vault_details = get_vault_details(vault_address)

            if not vault_details:
                print('No vault details found. Skipping...')
                break_flag = True
                break
            else:
                vault_apr = float(vault_details.get('apr', 0)) * 100

            payload = {"type": "clearinghouseState", "user": vault_address}
            response = requests.post(url,
                                     headers=headers,
                                     json=payload,
                                     verify=False)

            if response.status_code == 200:
                vault_details = response.json()
                vault_asset_positions = vault_details.get('assetPositions', [])

                if not vault_asset_positions:
                    print('No asset positions found. Skipping...')
                    break_flag = True
                    break

                positions_dict = {}

                for asset_position in vault_asset_positions:
                    coin = asset_position.get('position', {}).get('coin', '')
                    leverage = float(
                        asset_position.get('position',
                                           {}).get('leverage',
                                                   {}).get('value', 1))
                    position_value = float(
                        asset_position.get('position',
                                           {}).get('positionValue', 0))
                    size = float(
                        asset_position.get('position', {}).get('szi', 0))
                    unrealised_pnl = float(
                        asset_position.get('position',
                                           {}).get('unrealizedPnl', 0))

                    if size >= 0:
                        direction = "LONG"
                        total_long_positions_value += position_value
                    else:
                        direction = "SHORT"
                        total_short_positions_value += position_value

                    positions_dict[coin] = {
                        "leverage": leverage,
                        "position_value": position_value,
                        "size": size,
                        "unrealised_pnl": unrealised_pnl,
                        "direction": direction
                    }

                    if vault_apr >= MIN_VAULT_APR:
                        if coin in long_short_counter[direction]:
                            long_short_counter[direction][coin] += 1
                        else:
                            long_short_counter[direction][coin] = 1

                updated_top_tvl_vaults[vault_address] = {
                    "vault_name": vault_name,
                    "vault_tvl": vault_tvl,
                    "vault_apr": vault_apr,
                    "positions": positions_dict,
                }

                if vault_apr >= MIN_VAULT_APR:
                    valid_vaults_count += 1

                break_flag = True
                time.sleep(0.5)
                break

            else:
                retry_count += 1

                print(
                    'Query failed and return code is {}. Retrying ({}) after {} seconds...'
                    .format(response.status_code, retry_count, RETRY_AFTER))

                time.sleep(RETRY_AFTER)

        if not break_flag:
            print('Maximum retries reached. Skipping...')

        count += 1

    if os.path.exists(tracked_top_tvl_vaults_file_path):
        os.remove(tracked_top_tvl_vaults_file_path)
    save_json_file(tracked_top_tvl_vaults_file_path, updated_top_tvl_vaults)

    differences = {}

    for vault_address, updated_vault in updated_top_tvl_vaults.items():
        updated_positions = updated_vault.get("positions", {})
        tracked_positions = tracked_top_tvl_vaults_dict.get(
            vault_address, {}).get("positions", {})

        changed_positions = {}

        for coin, updated_position in updated_positions.items():
            tracked_position = tracked_positions.get(coin)

            if tracked_position:
                if (updated_position["leverage"]
                        != tracked_position["leverage"]
                        or updated_position["direction"]
                        != tracked_position["direction"]):
                    changed_positions[coin] = {
                        "before": tracked_position,
                        "after": updated_position
                    }
            else:
                changed_positions[coin] = {
                    "before": {},
                    "after": updated_position
                }

        for coin, tracked_position in tracked_positions.items():
            if coin not in updated_positions:
                changed_positions[coin] = {
                    "before": tracked_position,
                    "after": {}
                }

        if changed_positions:
            differences[vault_address] = {
                "vault_name": updated_vault["vault_name"],
                "vault_tvl": updated_vault["vault_tvl"],
                "vault_apr": updated_vault["vault_apr"],
                "positions": changed_positions
            }

    filtered_differences = {
        vault_address: data
        for vault_address, data in differences.items()
        if data["vault_apr"] >= MIN_VAULT_APR
    }

    if not filtered_differences:
        terminal_msg = "\nNo vault updates found.\n"
        print(terminal_msg)
    else:
        terminal_msg = f"\n{'='*40}\nHyperliquid Vaults Updates (TVL >= {MIN_VAULT_TVL:,.2f} USD & APR >= {MIN_VAULT_APR:,.2f}%):\n{'='*40}"
        print(terminal_msg)

        sorted_differences = sorted(filtered_differences.items(),
                                    key=lambda x: x[1]["vault_tvl"],
                                    reverse=True)

        terminal_output = terminal_msg
        tg_msg_list = []
        tg_msg_title_list = [
            f"**Hyperliquid Vaults Updates (TVL >= {MIN_VAULT_TVL:,.2f} USD & APR >= {MIN_VAULT_APR:,.2f}%):**\n"
        ]

        for vault_address, vault_updates in sorted_differences:

            vault_name = vault_updates["vault_name"]
            vault_tvl = vault_updates["vault_tvl"]
            vault_apr = vault_updates["vault_apr"]
            positions_updates = vault_updates["positions"]

            terminal_msg = f"\n📌 Vault: {vault_name}\n🔗 Address: {vault_address}\n💰 TVL: {vault_tvl:,.2f} USD\n📈 APR: {vault_apr:,.2f}%\n{'-'*40}"
            print(terminal_msg)
            terminal_output += terminal_msg

            escaped_vault_name = re.escape(vault_name)
            escaped_vault_name = escaped_vault_name.replace(r'\ ', ' ')
            tg_msg_list.append(f"*_**📌 Vault: {escaped_vault_name}**_*\n"
                               f"_**🔗 Address: `{vault_address}`**_\n"
                               f"💰 TVL: {vault_tvl:,.2f} USD\n"
                               f"📈 APR: {vault_apr:,.2f}%")

            for coin, updates in positions_updates.items():
                before = updates.get('before', {})
                after = updates.get('after', {})

                before_leverage = before.get("leverage", "OPENED")
                after_leverage = after.get("leverage", "CLOSED")
                before_direction = before.get("direction", "OPENED")
                after_direction = after.get("direction", "CLOSED")

                if before_direction in ["SHORT", "OPENED"
                                        ] and after_direction == "LONG":
                    dot = "🟢"
                elif before_direction in ["LONG", "OPENED"
                                          ] and after_direction == "SHORT":
                    dot = "🔴"
                elif after_direction == "LONG":
                    dot = "🟢"
                elif after_direction == "SHORT":
                    dot = "🔴"
                else:
                    dot = "🔹"

                terminal_msg = (
                    f"\n{dot} Coin: {coin}"
                    f"\n   - Leverage: {before_leverage} → {after_leverage}"
                    f"\n   - Direction: {before_direction} → {after_direction}"
                    f"\n{'-'*40}")
                print(terminal_msg)
                terminal_output += terminal_msg

                escaped_coin = re.escape(coin)
                escaped_coin = escaped_coin.replace(r'\ ', ' ')
                tg_msg_list.append(
                    f"\n{dot} *Coin: {escaped_coin}*\n"
                    f"• Leverage: {before_leverage} → {after_leverage}\n"
                    f"• Direction: {before_direction} → {after_direction}")

            terminal_output += terminal_msg
            tg_msg_list.append(f"{'_'*32}\n")

        summary_msg = f"\n📊 **Summary of Long/Short Positions (Count >= {MIN_POSITION_COUNTS}):**\n\nTotal No. of Vaults: {valid_vaults_count}"
        tg_summary_msg = f"\n📊 *Summary of Long/Short Positions (Count >= {MIN_POSITION_COUNTS}):*\n\n*Total No. of Vaults:* {valid_vaults_count}"

        print(summary_msg)
        terminal_output += summary_msg
        tg_msg_list.append(tg_summary_msg)
        count = 1

        for direction, coins in long_short_counter.items():
            direction_icon = "🟢" if direction == "LONG" else "🔴"
            total_positions_value = total_long_positions_value if direction == "LONG" else total_short_positions_value
            direction_msg = f"\n{direction} Positions (Total Positions Value = {total_positions_value:,.2f} USD):"
            print(direction_msg)
            terminal_output += direction_msg
            if count == 1:
                tg_msg_list.append(
                    f"*{direction} Positions (Total Positions Value = {total_positions_value:,.2f} USD):*"
                )
            else:
                tg_msg_list.append(
                    f"\n*{direction} Positions (Total Positions Value = {total_positions_value:,.2f} USD):*"
                )

            sorted_coins = sorted(coins.items(),
                                  key=lambda x: x[1],
                                  reverse=True)

            for coin, count in sorted_coins:
                if count >= MIN_POSITION_COUNTS:
                    coin_msg = f"{direction_icon} {coin}: {count} time(s)"
                    print(coin_msg)
                    terminal_output += f"\n{coin_msg}"
                    tg_msg_list.append(
                        f"{direction_icon} {coin}: {count} time(s)")

            count += 1

        print("\n" + "-" * 40)
        terminal_output += "\n" + "-" * 40
        tg_msg_list.append(f"{'_'*32}\n")

        file_path = "latest_vault_updates_terminal_output.txt"
        with open(file_path, "w") as file:
            file.write(terminal_output)

        print(f"\nTerminal output saved to {file_path}\n")

        if send_to_tg:
            if tg_msg_list:
                print("Sending vault updates to Telegram...\n")
                bot = telebot.TeleBot(token=TELEGRAM_BOT_TOKEN, threaded=False)
                tg_msg_title_list.extend(tg_msg_list)
                chunks = chunk_message(tg_msg_title_list)
                for chunk in chunks:
                    retry_count = 0
                    while retry_count < MAX_RETRIES:
                        try:
                            bot.send_message(chat_id,
                                             chunk,
                                             parse_mode='MarkdownV2')
                            time.sleep(3)
                            break
                        except:
                            retry_count += 1
                            time.sleep(60)
                    else:
                        print(
                            "Max retries reached. No new message will be sent.\n"
                        )
                        break

                print('Vault updates sent to Telegram.\n')

            else:
                print(
                    'No vault update found, so no message sent to Telegram.\n')

    print('Total time taken: {:.2f} seconds\n'.format(time.time() -
                                                      start_time))


if __name__ == "__main__":
    from urllib3.exceptions import InsecureRequestWarning
    import urllib3

    urllib3.disable_warnings(InsecureRequestWarning)

    parser = argparse.ArgumentParser(
        description="Get parameters for the script.")
    parser.add_argument('-c',
                        '--chat',
                        type=str,
                        default='GROUP',
                        help="GROUP: Send to TEST_TG_CHAT_ID Telegram group, \
        USER: Send to USER_ID Telegram user")
    args = parser.parse_args()
    chat = str(args.chat).upper()

    if chat not in ['GROUP', 'USER']:
        print(
            "\nChat {} is not supported. Supported options are GROUP and USER.\n"
            .format(chat))
        sys.exit(1)
    elif chat == 'GROUP':
        chat_id = TEST_TG_CHAT_ID
    else:
        chat_id = USER_ID

    get_vaults_updates(chat_id)
