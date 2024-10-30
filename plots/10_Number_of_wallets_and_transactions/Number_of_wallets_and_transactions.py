import json
import os
from datetime import datetime
from collections import defaultdict
import matplotlib.pyplot as plt

# Paths
wallets_by_abuse_type_path = '../../data/wallets_by_abuse_type.json'
wallets_folder = '../../data/bitcoin'

# Initialize structures to store annual counts
annual_wallet_count = defaultdict(int)
annual_transaction_count = defaultdict(int)

# Load wallets by abuse type to gather unique wallets
with open(wallets_by_abuse_type_path) as f:
    wallets_by_abuse_type = json.load(f)
    unique_wallets = set(wallet for wallets in wallets_by_abuse_type.values() for wallet in wallets)

# Track progress
total_wallets = len(unique_wallets)
processed_wallets = 0

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

            # Apply threshold conditions to skip large wallets
            total_received = wallet_data.get('total_received', 0)
            n_tx = wallet_data.get('n_tx', 0)
            if (total_received > 10_000_000_000_000) or (n_tx > 100_000):
                continue

            # Increment wallet count for the years of this wallet's transactions
            years_with_transactions = set()

            for tx in wallet_data.get('txs', []):
                timestamp = tx.get('time')
                if not timestamp:
                    continue

                tx_year = datetime.utcfromtimestamp(timestamp).year

                # Only include data from 2012 onwards
                if tx_year >= 2012:
                    annual_transaction_count[tx_year] += 1
                    years_with_transactions.add(tx_year)

            # Count wallet only once per year if it has transactions
            for year in years_with_transactions:
                annual_wallet_count[year] += 1

        # Print progress every 500 wallets
        if processed_wallets % 500 == 0 or processed_wallets == total_wallets:
            print(f"Processed {processed_wallets}/{total_wallets} wallets...")

# Prepare data for plotting
sorted_years = sorted(annual_wallet_count.keys())
wallet_counts = [annual_wallet_count[year] for year in sorted_years]
transaction_counts = [annual_transaction_count[year] for year in sorted_years]

# Plotting the data
fig, ax = plt.subplots(figsize=(12, 8))

# Bar chart with two sets of bars: one for wallet count, one for transaction count
width = 0.35  # Width of the bars

# Bar positions for each year
years_indices = range(len(sorted_years))
wallet_bars = ax.bar([x - width / 2 for x in years_indices], wallet_counts, width, label='Number of Wallets')
transaction_bars = ax.bar([x + width / 2 for x in years_indices], transaction_counts, width, label='Total Transactions')

# Adding exact numbers above each bar
for bar in wallet_bars:
    yval = bar.get_height()
    ax.text(
        bar.get_x() + bar.get_width() / 2,
        yval,
        f'{int(yval)}',
        ha='center',
        va='bottom',
        fontsize=9,
        fontweight='bold'
    )

for bar in transaction_bars:
    yval = bar.get_height()
    ax.text(
        bar.get_x() + bar.get_width() / 2,
        yval,
        f'{int(yval)}',
        ha='center',
        va='bottom',
        fontsize=9,
        fontweight='bold'
    )

# Labeling and aesthetics
ax.set_title('Annual Number of Wallets and Transactions', fontsize=16)
ax.set_xlabel('Year', fontsize=12)
ax.set_ylabel('Count', fontsize=12)
ax.set_xticks(years_indices)
ax.set_xticklabels(sorted_years, rotation=45)
ax.legend()

# Adjust layout for better display
plt.tight_layout()
plt.show()
