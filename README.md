# hyperliquid-analysis

# Hyperliquid Vault Updates Tracker

This project retrieves and tracks the vault details from Hyperliquid's API and sends updates about vault changes (TVL and asset positions) to Telegram.

## Overview

The script fetches information about the vaults with the highest Total Value Locked (TVL) from the Hyperliquid stats API, filters out vaults based on a minimum TVL threshold, and retrieves detailed asset position data for each vault. If any changes are detected in the asset positions or vault TVL, the script sends these updates to a specified Telegram chat.

## Features

- Fetches the top vaults by TVL.
- Tracks changes in asset positions, including leverage, direction (LONG/SHORT), and unrealized PnL.
- Sends vault updates to a Telegram group or user.
- Retries failed requests a specified number of times.
- Stores tracked vault data in a local JSON file for reference.
- Supports customization through configuration parameters (e.g., minimum TVL, excluded vault addresses).

## Requirements

Before running the script, ensure you have the following installed:

- Python 3.7 or higher
- Required Python libraries (listed in `requirements.txt`)

### Install dependencies:

```bash
pip install -r requirements.txt
```

## Configuration

The script requires a few configuration settings in the `config.py` file:

- **MIN_VAULT_TVL**: Minimum TVL value for vaults to be tracked.
- **EXCLUDED_VAULT_ADDRESSES**: List of vault addresses to exclude from tracking.
- **MAX_RETRIES**: Maximum number of retries for failed API requests.
- **RETRY_AFTER**: Number of seconds to wait between retries.
- **USER_ID**: Telegram user ID to send messages to (if `chat` is set to `USER`).
- **TEST_TG_CHAT_ID**: Telegram chat ID to send messages to (if `chat` is set to `GROUP`).
- **TELEGRAM_BOT_TOKEN**: Token for the Telegram bot used to send messages.

### Additional Setup

1. Rename the `private_temp.ini` file to `private.ini`.
2. Fill in the following details in the `private.ini` file under the `[telegram]` section:

```ini
[telegram]
TELEGRAM_BOT_TOKEN = <your telegram bot token>
TEST_TG_CHAT_ID = <your telegram group chat id>
USER_ID = <your telegram user id>
```

## Usage

### Run the script:

To run the script, execute the following command:

```bash
python vault_updates_tracker.py
```

You can also specify the target chat for the updates (either `GROUP` or `USER`):

```bash
python vault_updates_tracker.py -c GROUP
```

- `GROUP`: Send updates to a Telegram group using the `TEST_TG_CHAT_ID`.
- `USER`: Send updates to a Telegram group using the `USER_ID`.

## Data Storage

- The script saves vault data in the `saved_data/tracked_top_tvl_vaults/tracked_top_tvl_vaults.json` file.
- Vaults and their positions are tracked, and updates are compared to previous data to identify changes.

## Error Handling

- The script retries failed requests up to `MAX_RETRIES` times.
- If an error occurs during API interaction, a retry will be attempted after `RETRY_AFTER` seconds.