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
wallets_by_abuse_type_path = '../../data/wallets_by_abuse_type.json'

# Load the wallets by type and store them in sets to ensure no duplicates
wallets_by_abuse_type = {}
with open(wallets_by_abuse_type_path) as f:
    data = json.load(f)
    for abuse_type, wallets in data.items():
        wallets_by_abuse_type[abuse_type] = set(wallets)

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

# Aggregate received funds per year by abuse type
annual_funds_by_type = defaultdict(lambda: defaultdict(Decimal))  # {abuse_type: {year: total_eur}}

# Track progress
processed_wallets = 0
total_wallets = sum(len(wallets) for wallets in wallets_by_abuse_type.values())

# Process each abuse type
for abuse_type, wallets in wallets_by_abuse_type.items():
    for wallet in wallets:
        wallet_file_path = os.path.join(wallets_folder, f"{wallet[:3]}/{wallet}.json")

        if os.path.exists(wallet_file_path):
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
                            annual_funds_by_type[abuse_type][tx_year] += value_in_euros

            processed_wallets += 1
            # Print progress after every 500 wallets processed
            if processed_wallets % 500 == 0:
                print(f"Processed {processed_wallets}/{total_wallets} wallets...")

# Calculate YoY changes for each abuse type
yoy_changes = defaultdict(lambda: defaultdict(float))  # {abuse_type: {year: change}}

for abuse_type, yearly_funds in annual_funds_by_type.items():
    sorted_years = sorted(yearly_funds.keys())
    for i in range(1, len(sorted_years)):
        previous_year = sorted_years[i - 1]
        current_year = sorted_years[i]
        previous_value = yearly_funds[previous_year]
        current_value = yearly_funds[current_year]

        if previous_value != 0:
            change = ((current_value - previous_value) / previous_value) * 100
        else:
            change = float('inf') if current_value > 0 else -100

        yoy_changes[abuse_type][current_year] = change

# Prepare data for plotting
sorted_years = sorted(set(year for changes in yoy_changes.values() for year in changes))
abuse_types = list(yoy_changes.keys())

# Generate the stacked bar chart for positive and negative values separately
fig, ax = plt.subplots(figsize=(12, 8))

# Colors for each abuse type
colors = [
    '#FF7F0E', '#1F77B4', '#2CA02C', '#D62728', '#9467BD',
    '#8C564B', '#E377C2', '#7F7F7F', '#BCBD22', '#17BECF'
]

# Store the positive and negative values separately for proper stacking
positive_changes = defaultdict(list)
negative_changes = defaultdict(list)
for year in sorted_years:
    for abuse_type in abuse_types:
        change = yoy_changes[abuse_type].get(year, 0)
        if change >= 0:
            positive_changes[abuse_type].append(change)
            negative_changes[abuse_type].append(0)
        else:
            positive_changes[abuse_type].append(0)
            negative_changes[abuse_type].append(change)

# Plot positive changes
for idx, abuse_type in enumerate(abuse_types):
    ax.bar(
        sorted_years, positive_changes[abuse_type],
        label=abuse_type, color=colors[idx % len(colors)],
        bottom=[sum(positive_changes[abuse][i] for abuse in abuse_types[:idx])
                for i in range(len(sorted_years))]
    )

# Plot negative changes
for idx, abuse_type in enumerate(abuse_types):
    ax.bar(
        sorted_years, negative_changes[abuse_type],
        label=f"{abuse_type} (negative)", color=colors[idx % len(colors)],
        bottom=[sum(negative_changes[abuse][i] for abuse in abuse_types[:idx])
                for i in range(len(sorted_years))]
    )

# Add labels for readability with a threshold for visibility
for year_idx, year in enumerate(sorted_years):
    for abuse_type in abuse_types:
        pos_value = positive_changes[abuse_type][year_idx]
        neg_value = negative_changes[abuse_type][year_idx]
        if pos_value > 10:
            ax.text(year, pos_value / 2, f'{pos_value:.1f}%', ha='center', va='center', fontsize=8)
        if neg_value < -10:
            ax.text(year, neg_value / 2, f'{neg_value:.1f}%', ha='center', va='center', fontsize=8)

# Final adjustments to the plot
ax.set_title('YoY Change in Annual Crime by Abuse Type', fontsize=14)
ax.set_xlabel('Year', fontsize=12)
ax.set_ylabel('Year-over-Year Change (%)', fontsize=12)
ax.set_xticks(sorted_years)
ax.set_xticklabels(sorted_years, rotation=45)
ax.legend(title='Abuse Type', bbox_to_anchor=(1.05, 1), loc='upper left')
ax.axhline(0, color='black', linewidth=0.8)

# Adjust layout for better readability
plt.tight_layout()
plt.show()

# Print the total money considered in the graph
total_eur = sum(sum(yearly_funds.values()) for yearly_funds in annual_funds_by_type.values())
print(f"\nTotal money received across all categories: {total_eur / 1_000_000_000:.2f} billion EUR")
