import json
import os
from collections import defaultdict
from datetime import datetime
import matplotlib.pyplot as plt
from decimal import Decimal

# Paths for input files
wallets_by_abuse_type_path = '../../data/wallets_by_abuse_type.json'
wallets_folder = '../../data/bitcoin'

# Load the wallets_by_abuse_type data
with open(wallets_by_abuse_type_path, 'r') as f:
    wallets_by_abuse_type = json.load(f)

# Store all unique wallets in sets per abuse type right after loading
wallets_by_abuse_type = {abuse_type: set(wallets) for abuse_type, wallets in wallets_by_abuse_type.items()}

# Initialize dictionaries to store transaction counts per year
inputs_per_year = defaultdict(int)
outputs_per_year = defaultdict(int)
total_per_year = defaultdict(int)

# Thresholds for transactions and total received
total_received_threshold = 10_000_000_000_000  # 10 trillion satoshis
n_tx_threshold = 100_000

# Convert satoshis to BTC using Decimal for precision
def satoshis_to_btc(satoshis):
    return Decimal(satoshis) / Decimal('100000000')  # 1 BTC = 100 million satoshis

# Track total wallets processed and included
total_wallets = sum(len(set(wallets)) for wallets in wallets_by_abuse_type.values())
processed_wallets = 0
included_wallets = 0

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
                if total_received > total_received_threshold or n_tx > n_tx_threshold:
                    print(f"Skipping wallet {wallet} due to high total_received ({total_received}) or n_tx ({n_tx}).")
                    continue

                included_wallets += 1

                # Loop through transactions and count inputs, outputs, and total transactions per year
                for tx in wallet_data.get('txs', []):
                    timestamp = tx.get('time')
                    if not timestamp:
                        continue
                    transaction_year = datetime.utcfromtimestamp(timestamp).year
                    if transaction_year < 2012:
                        continue  # Skip transactions before 2012

                    input_count = 0
                    output_count = 0

                    # Process received funds (outputs where the wallet is the recipient)
                    for output_tx in tx.get('out', []):
                        if 'addr' in output_tx and output_tx['addr'] == wallet:
                            outputs_per_year[transaction_year] += 1  # Count this as an output transaction
                            output_count += 1

                    # Process sent funds (inputs where the wallet is the sender)
                    for input_tx in tx.get('inputs', []):
                        prev_out = input_tx.get('prev_out', {})
                        if 'addr' in prev_out and prev_out['addr'] == wallet:
                            inputs_per_year[transaction_year] += 1  # Count this as an input transaction
                            input_count += 1

                    # Count this transaction for the total if it has inputs or outputs
                    if input_count > 0 or output_count > 0:
                        total_per_year[transaction_year] += 1

        # Track progress
        processed_wallets += 1
        if processed_wallets % 500 == 0 or processed_wallets == total_wallets:
            print(f"Processed {processed_wallets}/{total_wallets} wallets. Included wallets: {included_wallets}.")

# Output final logs
print(f"Finished processing all wallets.")
print(f"Total wallets processed: {processed_wallets}")
print(f"Total wallets included in the result: {included_wallets}")

# Prepare data for visualization
years = sorted(set(inputs_per_year.keys()) | set(outputs_per_year.keys()) | set(total_per_year.keys()))
input_values = [inputs_per_year[year] for year in years]
output_values = [outputs_per_year[year] for year in years]
total_values = [total_per_year[year] for year in years]

# Create a bar chart with three bars per year (inputs, outputs, total)
fig, ax = plt.subplots(figsize=(12, 6))
bar_width = 0.25  # Width of each bar

# Define bar positions
input_bar_positions = range(len(years))
output_bar_positions = [pos + bar_width for pos in input_bar_positions]
total_bar_positions = [pos + bar_width * 2 for pos in input_bar_positions]

# Professional color palette
input_color = '#4A90E2'   # Blue
output_color = '#ff7f0e'  # Orange
total_color = '#2ca02c'   # Green

# Plot the bars
bars_input = ax.bar(input_bar_positions, input_values, width=bar_width, label='Inputs', color=input_color)
bars_output = ax.bar(output_bar_positions, output_values, width=bar_width, label='Outputs', color=output_color)
bars_total = ax.bar(total_bar_positions, total_values, width=bar_width, label='Total', color=total_color)

# Add exact numbers inside each bar, rotated vertically
for bars in [bars_input, bars_output, bars_total]:
    for bar in bars:
        yval = bar.get_height()
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            yval / 2,  # Positioning inside the bar
            f'{yval}',
            ha='center',
            va='center',
            fontsize=9,
            color='white',
            rotation=90  # Rotate the text vertically
        )

# Set the x-axis labels to the years
ax.set_xticks([pos + bar_width for pos in input_bar_positions])
ax.set_xticklabels(years)

# Set the title and labels
ax.set_title('Number of Transactions Each Year', fontsize=14)
ax.set_xlabel('Year', fontsize=12)
ax.set_ylabel('Number of Transactions', fontsize=12)

# Add a legend
ax.legend(title='Transaction Type', bbox_to_anchor=(1.05, 1), loc='upper left')

# Adjust layout for better spacing
plt.tight_layout()

# Show the plot
plt.show()
