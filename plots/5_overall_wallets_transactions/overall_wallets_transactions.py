import json
import os
from decimal import Decimal
import matplotlib.pyplot as plt

# Paths
wallets_folder = '../../data/bitcoin'
wallets_by_abuse_type_path = '../../data/wallets_by_abuse_type.json'

# Load the wallets by type and store them in sets to ensure no duplicates
all_wallets = set()
with open(wallets_by_abuse_type_path) as f:
    data = json.load(f)
    for abuse_type, wallets in data.items():
        all_wallets.update(wallets)

# Initialize counters for transactions
total_wallets = 0
total_transactions = 0
total_incoming_transactions = 0
total_outgoing_transactions = 0
total_received_btc = Decimal('0')
total_sent_btc = Decimal('0')

# Track progress
processed_wallets = 0

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

            # Skip wallets with extremely large total_received or n_tx values
            total_received = wallet_data.get('total_received', 0)
            n_tx = wallet_data.get('n_tx', 0)
            if (total_received > 10_000_000_000_000) or (n_tx > 100_000):
                continue

            # Count this wallet only if it's not skipped
            total_wallets += 1
            total_transactions += n_tx

            # Count incoming transactions (outputs where this wallet is the recipient)
            for tx in wallet_data.get('txs', []):
                for output in tx.get('out', []):
                    if 'addr' in output and output['addr'] == wallet:
                        total_incoming_transactions += 1
                        total_received_btc += Decimal(output.get('value', 0)) / Decimal('100000000')

                # Count outgoing transactions (inputs where this wallet is the sender)
                for input_tx in tx.get('inputs', []):
                    prev_out = input_tx.get('prev_out', {})
                    if 'addr' in prev_out and prev_out['addr'] == wallet:
                        total_outgoing_transactions += 1
                        total_sent_btc += Decimal(prev_out.get('value', 0)) / Decimal('100000000')

        processed_wallets += 1

        # Print progress after every 500 wallets processed
        if processed_wallets % 500 == 0 or processed_wallets == len(all_wallets):
            print(f"Processed {processed_wallets}/{len(all_wallets)} wallets...")

# Output the results
print("\nOverall Statistics:")
print(f"Total unique wallets: {total_wallets}")
print(f"Total transactions: {total_transactions}")
print(f"Total incoming transactions: {total_incoming_transactions}")
print(f"Total outgoing transactions: {total_outgoing_transactions}")
print(f"Total BTC received: {total_received_btc} BTC")
print(f"Total BTC sent: {total_sent_btc} BTC")

# Visualization
fig, axs = plt.subplots(2, 3, figsize=(15, 10))

# Data for visualization
labels = ['Total Wallets', 'Total Transactions', 'Incoming Transactions', 'Outgoing Transactions', 'BTC Received',
          'BTC Sent']
values = [
    total_wallets,
    total_transactions,
    total_incoming_transactions,
    total_outgoing_transactions,
    float(total_received_btc),
    float(total_sent_btc)
]

# Use a professional color palette for variety
colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b']

# Plot each metric in a slim bar with exact values on top
for i, (label, value, ax) in enumerate(zip(labels, values, axs.flat)):
    ax.bar([label], [value], color=colors[i], width=0.3)
    ax.set_title(label)
    ax.set_ylabel('Count' if i < 4 else 'BTC')
    ax.set_xticks([])

    # Add the exact value on top of the bar with black text
    ax.text(0, value, f'{value:,.2f}', ha='center', va='bottom', fontsize=10, color='black')

# Adjust layout for better readability
plt.tight_layout()
plt.show()
