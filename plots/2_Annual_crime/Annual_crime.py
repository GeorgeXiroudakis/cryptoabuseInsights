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
        for wallets in abuse_types.values():
            unique_wallets.update(wallets)  # Add wallets to the set to remove duplicates

# Load Bitcoin to Euro exchange rates
with open(exchange_rates_path) as f:
    exchange_rates = json.load(f)

# Convert satoshis to BTC using Decimal for precision
def satoshis_to_btc(satoshis):
    return Decimal(satoshis) / Decimal('100000000')  # 1 BTC = 100 million satoshis

# Get EUR value for a timestamp
def get_euro_value(timestamp):
    date_str = datetime.utcfromtimestamp(timestamp).strftime('%Y-%m-%d')  # Use UTC time
    return Decimal(exchange_rates.get(date_str, '0'))

# Exclude data before 2012
def is_transaction_valid(timestamp):
    transaction_year = datetime.utcfromtimestamp(timestamp).year
    return transaction_year >= 2012

# Track progress
total_wallets = len(unique_wallets)
processed_wallets = 0
wallets_included = 0  # Number of wallets taken into account

# Dictionary to store total received funds per year
annual_stolen_funds = defaultdict(Decimal)

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

            # Skip wallets with extremely large total_received or n_tx values to avoid noise
            total_received = wallet_data.get('total_received', 0)
            n_tx = wallet_data.get('n_tx', 0)
            if (total_received > 10_000_000_000_000) or (n_tx > 100_000):
                continue

            wallet_included_in_result = False

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
                        wallet_included_in_result = True

            if wallet_included_in_result:
                wallets_included += 1  # Increment if wallet has valid transactions

        # Print progress after every 500 wallets processed
        if processed_wallets % 500 == 0 or processed_wallets == total_wallets:
            print(f"Processed {processed_wallets}/{total_wallets} wallets...")

# Output the number of included wallets
print(f"\nTotal wallets included in analysis: {wallets_included}")

# Sort the years for plotting
sorted_years = sorted(annual_stolen_funds.keys())
amounts_per_year = [float(annual_stolen_funds[year]) / 1_000_000_000 for year in sorted_years]  # Convert to billions for better readability

# Calculate the total amount of money displayed in the graph
total_euros_in_billions = sum(amounts_per_year)
print(f"\nTotal money received across all years (in billions of EUR): {total_euros_in_billions:.2f} B EUR")

# Create the bar chart with the specified color
plt.figure(figsize=(10, 6))
bars = plt.bar(sorted_years, amounts_per_year, color='#091057')
plt.title('Annual Crime: Total Money Received Per Year (in Billions of EUR)')
plt.xlabel('Year')
plt.ylabel('Total Money Received (Billions of EUR)')
plt.xticks(sorted_years, rotation=45)

# Add labels above each bar
for bar in bars:
    yval = bar.get_height()
    plt.text(
        bar.get_x() + bar.get_width() / 2,
        yval,
        f'{yval:.2f} B',  # Format as billions
        ha='center',
        va='bottom',
        fontsize=10,
        color='black'
    )

plt.tight_layout()
plt.show()
