import json
import os
from datetime import datetime
from decimal import Decimal
import matplotlib.pyplot as plt
from collections import defaultdict

# Paths
benign_wallets_path = '../../data/benign.txt'
wallets_folder = '../../data/bitcoin'
exchange_rates_path = '../../data/BitcoinExchangeRates.json'

# Load Bitcoin to Euro exchange rates
with open(exchange_rates_path) as f:
    exchange_rates = json.load(f)

# Initialize variables
total_received_funds_eur = Decimal('0')
total_received_funds_btc = Decimal('0')
total_sent_funds_eur = Decimal('0')
total_sent_funds_btc = Decimal('0')
wallets_with_json_files = 0  # Counter for wallets with JSON files


# Convert satoshis to BTC using Decimal for precision
def satoshis_to_btc(satoshis):
    return Decimal(satoshis) / Decimal('100000000')


# Get EUR value for a timestamp
def get_euro_value(timestamp):
    date_str = datetime.utcfromtimestamp(timestamp).strftime('%Y-%m-%d')
    return Decimal(exchange_rates.get(date_str, '0'))


# Exclude data before 2012
def is_transaction_valid(timestamp):
    transaction_year = datetime.utcfromtimestamp(timestamp).year
    return transaction_year >= 2012


# Process each wallet
def process_wallet_batch(wallet_batch):
    wallets_included = 0

    for wallet in wallet_batch:
        wallet_file_path = os.path.join(wallets_folder, f"{wallet[:3]}/{wallet}.json")

        # Skip if the JSON file doesn't exist
        if not os.path.exists(wallet_file_path):
            print(f"Warning: JSON file for wallet {wallet} not found. Skipping...")
            continue

        # Increment the counter for wallets with JSON files
        global wallets_with_json_files
        wallets_with_json_files += 1

        # Attempt to load the wallet data
        try:
            with open(wallet_file_path) as wf:
                wallet_data = json.load(wf)
        except (json.JSONDecodeError, OSError):
            print(f"Warning: Could not decode JSON for wallet {wallet}. Skipping...")
            continue

        # Handle wallet data wrapped in a list
        if isinstance(wallet_data, list):
            wallet_data = wallet_data[0] if wallet_data else {}

        # Check if wallet_data is a dictionary
        if not isinstance(wallet_data, dict):
            print(f"Warning: Unexpected format in JSON for wallet {wallet}. Skipping...")
            continue

        # Skip wallets with extremely large total_received or n_tx values
        total_received = wallet_data.get('total_received', 0)
        n_tx = wallet_data.get('n_tx', 0)
        if total_received > 10_000_000_000_000 or n_tx > 100_000:
            continue

        wallet_included_in_result = False  # Flag to track if wallet has valid transactions

        # Loop through transactions
        for tx in wallet_data.get('txs', []):
            timestamp = tx.get('time')
            if not timestamp or not is_transaction_valid(timestamp):
                continue

            conversion_rate = get_euro_value(timestamp)
            tx_date = datetime.utcfromtimestamp(timestamp).strftime('%Y-%m-%d')

            # Process received funds
            for output_tx in tx.get('out', []):
                if 'addr' in output_tx and output_tx['addr'] == wallet:
                    value_in_btc = satoshis_to_btc(output_tx.get('value', 0))
                    total_received_funds_btc += value_in_btc
                    value_in_euros = value_in_btc * conversion_rate
                    total_received_funds_eur += value_in_euros

                    wallet_included_in_result = True

            # Process sent funds
            for input_tx in tx.get('inputs', []):
                prev_out = input_tx.get('prev_out', {})
                if 'addr' in prev_out and prev_out['addr'] == wallet:
                    value_in_btc = satoshis_to_btc(prev_out.get('value', 0))
                    total_sent_funds_btc += value_in_btc
                    value_in_euros = value_in_btc * conversion_rate
                    total_sent_funds_eur += value_in_euros

                    wallet_included_in_result = True

        if wallet_included_in_result:
            wallets_included += 1

    return wallets_included


# Load the benign wallets from the text file
with open(benign_wallets_path) as f:
    benign_wallets = [line.strip() for line in f]

# Process wallets in batches
batch_size = 1000
total_wallets = len(benign_wallets)
processed_wallets = 0
total_included_wallets = 0

for i in range(0, total_wallets, batch_size):
    batch = benign_wallets[i:i + batch_size]
    included = process_wallet_batch(batch)
    total_included_wallets += included
    processed_wallets += len(batch)

    print(f"Processed {processed_wallets}/{total_wallets} wallets. Included in results: {total_included_wallets}")

# Output the total number of wallets with JSON files
print(f"\nTotal wallets with JSON files: {wallets_with_json_files}")

# Output the total funds received and sent
print(f"\nTotal wallets included in the result: {total_included_wallets}")
print(f"Total funds received: {total_received_funds_btc} BTC, {total_received_funds_eur:.2f} EUR")
print(f"Total funds sent: {total_sent_funds_btc} BTC, {total_sent_funds_eur:.2f} EUR")
