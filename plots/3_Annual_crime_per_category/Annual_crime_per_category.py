import json
import os
from datetime import datetime
from decimal import Decimal
import matplotlib.pyplot as plt
from collections import defaultdict

# Paths
wallets_by_abuse_type_path = '../../data/wallets_by_abuse_type.json'
wallets_folder = '../../data/bitcoin'
exchange_rates_path = '../../data/BitcoinExchangeRates.json'

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

# Initialize a set to store unique wallets
unique_wallets = set()
wallets_by_abuse_type = {}

# Load wallets by abuse type and store in the set for uniqueness
with open(wallets_by_abuse_type_path) as f:
    wallets_by_abuse_type = json.load(f)
    for abuse_type, wallets in wallets_by_abuse_type.items():
        unique_wallets.update(wallets)  # Add wallets to the set to remove duplicates

# Track progress
total_wallets = len(unique_wallets)  # Total number of unique wallets
processed_wallets = 0
wallets_included = 0

# Dictionary to store total received funds per year for each abuse type
annual_stolen_funds_by_category = defaultdict(lambda: defaultdict(Decimal))

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

            # Determine the abuse types associated with the wallet
            wallet_abuse_types = [
                abuse_type for abuse_type, wallets in wallets_by_abuse_type.items() if wallet in wallets
            ]

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

                        # Add the received value to each associated abuse type for the year
                        for abuse_type in wallet_abuse_types:
                            annual_stolen_funds_by_category[abuse_type][tx_year] += value_in_euros

                        wallet_included_in_result = True

            if wallet_included_in_result:
                wallets_included += 1  # Increment if wallet has valid transactions

        # Print progress after every 500 wallets processed
        if processed_wallets % 500 == 0 or processed_wallets == total_wallets:
            print(f"Processed {processed_wallets}/{total_wallets} wallets...")

# Output the number of included wallets
print(f"\nTotal wallets included in analysis: {wallets_included}")

# Calculate the total stolen money across all categories and years
total_eur = sum(
    sum(year_data.values()) for year_data in annual_stolen_funds_by_category.values()
)
print(f"\nTotal money received across all categories: {total_eur / Decimal('1_000_000_000'):.2f} billion EUR")

# Prepare data for plotting
sorted_years = sorted(
    {year for year_data in annual_stolen_funds_by_category.values() for year in year_data}
)
abuse_types = sorted(annual_stolen_funds_by_category.keys())

# Prepare amounts per year for each abuse type
amounts_per_year = {
    abuse_type: [annual_stolen_funds_by_category[abuse_type].get(year, 0) / Decimal('1_000_000_000') for year in sorted_years]
    for abuse_type in abuse_types
}

# Create a stacked bar chart
fig, ax = plt.subplots(figsize=(12, 8))

# Define colors for each abuse type
colors = [
    "#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd", "#8c564b", "#e377c2", "#7f7f7f", "#bcbd22", "#17becf"
]

# Stack bars for each abuse type
# Define a threshold for displaying values (in billions of EUR)
display_threshold = 0.1

# Stack bars for each abuse type
bottom = [0] * len(sorted_years)
for abuse_type, color in zip(abuse_types, colors):
    values = amounts_per_year[abuse_type]
    bars = ax.bar(sorted_years, values, bottom=bottom, label=abuse_type, color=color)

    # Add labels inside each segment that exceed the threshold for better readability
    for bar in bars:
        yval = bar.get_height()
        if yval >= display_threshold:  # Only display labels above the threshold
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                bar.get_y() + yval - 0.05,  # Adjust position to place text inside the bar
                f'{yval:.2f}',
                ha='center',
                va='top',  # Align text to the top of the bar segment
                fontsize=9,  # Adjust font size for readability
                color='black',  # Use white color for contrast against darker colors
                fontweight='bold'  # Bold for better visibility
            )

    # Update the bottom to stack the next set of values correctly
    bottom = [b + v for b, v in zip(bottom, values)]



# Configure plot aesthetics
ax.set_title('Annual Crime Per Category (in Billions of EUR)', fontsize=16)
ax.set_xlabel('Year', fontsize=12)
ax.set_ylabel('Total Money Received (Billion EUR)', fontsize=12)
ax.set_xticks(sorted_years)
ax.set_xticklabels(sorted_years, rotation=45)
ax.legend(title='Abuse Types', bbox_to_anchor=(1.05, 1), loc='upper left')

# Adjust layout for better display
plt.tight_layout()
plt.show()
