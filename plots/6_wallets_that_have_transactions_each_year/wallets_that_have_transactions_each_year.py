import json
import os
from datetime import datetime
from collections import defaultdict
import matplotlib.pyplot as plt

# Paths
wallets_folder = '../../data/bitcoin'
wallets_by_abuse_type_path = '../../data/wallets_by_abuse_type.json'

# Load the wallets by type and store them in a set to ensure no duplicates
all_wallets = set()
with open(wallets_by_abuse_type_path) as f:
    data = json.load(f)
    for abuse_type, wallets in data.items():
        all_wallets.update(wallets)

# Initialize a dictionary to count wallets per year
wallets_per_year = defaultdict(set)

# Track progress
processed_wallets = 0

# Function to check if a transaction is valid (i.e., from 2012 onwards)
def is_transaction_valid(timestamp):
    transaction_year = datetime.utcfromtimestamp(timestamp).year
    return transaction_year >= 2012

# Process each wallet
for wallet in all_wallets:
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

            # Track each transaction year for this wallet if it's from 2012 or later
            for tx in wallet_data.get('txs', []):
                timestamp = tx.get('time')
                if timestamp and is_transaction_valid(timestamp):
                    year = datetime.utcfromtimestamp(timestamp).year
                    wallets_per_year[year].add(wallet)

        processed_wallets += 1

        # Print progress after every 500 wallets processed
        if processed_wallets % 500 == 0 or processed_wallets == len(all_wallets):
            print(f"Processed {processed_wallets}/{len(all_wallets)} wallets...")

# Count the number of unique wallets with transactions per year
wallets_count_per_year = {year: len(wallets) for year, wallets in sorted(wallets_per_year.items())}

# Output the results
print("\nNumber of wallets with transactions each year:")
for year, count in wallets_count_per_year.items():
    print(f"{year}: {count}")

# Visualization
years = list(wallets_count_per_year.keys())
counts = list(wallets_count_per_year.values())

plt.figure(figsize=(10, 6))
plt.bar(years, counts, color='#1f77b4', width=0.5)
plt.title('Number of Wallets with Transactions Each Year')
plt.xlabel('Year')
plt.ylabel('Number of Wallets')
plt.xticks(years, rotation=45)
plt.tight_layout()

# Add exact numbers on top of the bars
for i, count in enumerate(counts):
    plt.text(years[i], count, f'{count}', ha='center', va='bottom', fontsize=10, color='black')

plt.show()
