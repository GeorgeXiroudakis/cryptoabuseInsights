import json
import os
from datetime import datetime
from decimal import Decimal
import matplotlib.pyplot as plt
from collections import defaultdict

# Paths
abuse_json_path = '../../data/Abuses.json'
wallets_folder = '../../data/bitcoin'
exchange_rates_path = '../../data/BitcoinExchangeRates.json'

# Load the abuse data and store unique wallets
unique_wallets = set()
with open(abuse_json_path) as f:
    abuse_data = json.load(f)
    for source, abuse_types in abuse_data.items():
        all_wallets = abuse_types.get("All", [])
        unique_wallets.update(all_wallets)

# Load Bitcoin to Euro exchange rates
with open(exchange_rates_path) as f:
    exchange_rates = json.load(f)

# Helper function to convert satoshis to BTC
def satoshis_to_btc(satoshis):
    return Decimal(satoshis) / Decimal('100000000')  # 1 BTC = 100 million satoshis

# Helper function to get EUR value for a given timestamp
def get_euro_value(timestamp):
    date_str = datetime.utcfromtimestamp(timestamp).strftime('%Y-%m-%d')
    return Decimal(exchange_rates.get(date_str, '0'))

# Check if transaction is after 2012
def is_transaction_valid(timestamp):
    transaction_year = datetime.utcfromtimestamp(timestamp).year
    return transaction_year >= 2012

# Dictionary to store yearly stolen funds
annual_stolen_funds = defaultdict(Decimal)

# Track progress
total_wallets = len(unique_wallets)
processed_wallets = 0
wallets_included = 0

# Process each unique wallet
for wallet in unique_wallets:
    wallet_file_path = os.path.join(wallets_folder, f"{wallet[:3]}/{wallet}.json")

    if os.path.exists(wallet_file_path):
        processed_wallets += 1
        with open(wallet_file_path) as wf:
            try:
                wallet_data = json.load(wf)
            except json.JSONDecodeError:
                print(f"Error: Could not decode JSON for wallet {wallet}. Skipping...")
                continue

            # Skip wallets with extremely large total_received or n_tx values
            total_received = wallet_data.get('total_received', 0)
            n_tx = wallet_data.get('n_tx', 0)
            if (total_received > 10_000_000_000_000) or (n_tx > 100_000):
                continue

            wallet_included_in_result = False  # Flag to check if wallet is included

            # Loop through transactions
            for tx in wallet_data.get('txs', []):
                timestamp = tx.get('time')
                if not timestamp or not is_transaction_valid(timestamp):
                    continue

                conversion_rate = get_euro_value(timestamp)
                tx_year = datetime.utcfromtimestamp(timestamp).year

                # Process received funds (outputs where the wallet is the recipient)
                for output_tx in tx.get('out', []):
                    if 'addr' in output_tx and output_tx['addr'] == wallet:
                        value_in_btc = satoshis_to_btc(output_tx.get('value', 0))
                        value_in_euros = value_in_btc * conversion_rate
                        annual_stolen_funds[tx_year] += value_in_euros

            if wallet_included_in_result:
                wallets_included += 1

        # Print progress for every 500 wallets processed
        if processed_wallets % 500 == 0 or processed_wallets == total_wallets:
            print(f"Processed {processed_wallets}/{total_wallets} wallets...")

# Prepare data for visualization
years = sorted(annual_stolen_funds.keys())
stolen_funds = [annual_stolen_funds[year] for year in years]

# Plotting the bar chart
plt.figure(figsize=(10, 6))
plt.bar(years, stolen_funds, color='teal')
plt.title('Annual Crime - Total Money Stolen')
plt.xlabel('Year')
plt.ylabel('Total Money Stolen (EUR)')
plt.grid(axis='y', linestyle='--', alpha=0.7)
plt.tight_layout()
plt.show()

print(f"Total wallets included in analysis: {wallets_included}")
