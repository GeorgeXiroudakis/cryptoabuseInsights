import json
import os
from collections import defaultdict
from datetime import datetime
import matplotlib.pyplot as plt

# Paths for input files
wallets_by_abuse_type_path = '../../data/wallets_by_abuse_type.json'
wallets_folder = '../../data/bitcoin'

# Load the wallets_by_abuse_type data
with open(wallets_by_abuse_type_path, 'r') as f:
    wallets_by_abuse_type = json.load(f)

# Initialize a dictionary to store the count of wallets per year for each abuse type
wallets_per_year_per_abuse = defaultdict(lambda: defaultdict(int))

# Track total wallets processed and the threshold criteria
total_wallets = sum(len(set(wallets)) for wallets in wallets_by_abuse_type.values())
processed_wallets = 0
included_wallets = 0

# Store all unique wallets in sets per abuse type right after loading
wallets_by_abuse_type = {abuse_type: set(wallets) for abuse_type, wallets in wallets_by_abuse_type.items()}

# Process each abuse type and its wallets
for abuse_type, unique_wallets in wallets_by_abuse_type.items():
    for wallet in unique_wallets:
        wallet_file_path = os.path.join(wallets_folder, f"{wallet[:3]}/{wallet}.json")

        if os.path.exists(wallet_file_path):
            with open(wallet_file_path, 'r') as wf:
                try:
                    wallet_data = json.load(wf)
                except json.JSONDecodeError:
                    print(f"Error: Could not decode JSON for wallet {wallet}. Skipping...")
                    continue

                # Check if wallet meets the thresholds
                total_received = wallet_data.get('total_received', 0)
                n_tx = wallet_data.get('n_tx', 0)
                if total_received > 10_000_000_000_000 or n_tx > 100_000:
                    print(f"Skipping wallet {wallet} due to high total_received ({total_received}) or n_tx ({n_tx}).")
                    continue

                wallet_included = False
                years_with_transactions = set()

                # Check transactions and count wallets per year
                for tx in wallet_data.get('txs', []):
                    timestamp = tx.get('time')
                    if timestamp:
                        transaction_year = datetime.utcfromtimestamp(timestamp).year
                        if transaction_year >= 2012:  # Only consider transactions from 2012 onwards
                            years_with_transactions.add(transaction_year)
                            wallet_included = True

                # Update the count of wallets for each year in the given abuse type
                for year in years_with_transactions:
                    wallets_per_year_per_abuse[abuse_type][year] += 1

                if wallet_included:
                    included_wallets += 1

        # Track progress
        processed_wallets += 1
        if processed_wallets % 500 == 0 or processed_wallets == total_wallets:
            print(f"Processed {processed_wallets}/{total_wallets} wallets. Included wallets: {included_wallets}.")

# Output final logs
print(f"Finished processing all wallets.")
print(f"Total wallets processed: {processed_wallets}")
print(f"Total wallets included in the result: {included_wallets}")

# Prepare data for visualization
years = sorted({year for yearly_data in wallets_per_year_per_abuse.values() for year in yearly_data})
abuse_types = sorted(wallets_by_abuse_type.keys())

# Define custom colors for the abuse types
colors = [
    "#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd",
    "#8c564b", "#e377c2", "#7f7f7f", "#bcbd22", "#17becf"
]

# Create a dictionary to store the values for each abuse type across years
abuse_type_values = {abuse_type: [wallets_per_year_per_abuse[abuse_type].get(year, 0) for year in years] for abuse_type in abuse_types}

# Plot the stacked bar chart
fig, ax = plt.subplots(figsize=(12, 6))

# Bottom for stacking bars
bottom = [0] * len(years)

# Plot each abuse type as a stacked bar, using the custom colors
for i, abuse_type in enumerate(abuse_types):
    values = abuse_type_values[abuse_type]
    ax.bar(
        years,
        values,
        bottom=bottom,
        label=abuse_type,
        color=colors[i % len(colors)]  # Cycle through colors if there are more abuse types than colors
    )
    # Update the bottom for stacking
    bottom = [b + v for b, v in zip(bottom, values)]

# Set the title and labels
ax.set_title('Number of Wallets with Transactions Each Year per Crime', fontsize=14)
ax.set_xlabel('Year', fontsize=12)
ax.set_ylabel('Number of Wallets', fontsize=12)

# Add a legend
ax.legend(title='Abuse Type', bbox_to_anchor=(1.05, 1), loc='upper left')

# Adjust layout for better spacing
plt.tight_layout()

# Show the plot
plt.show()
