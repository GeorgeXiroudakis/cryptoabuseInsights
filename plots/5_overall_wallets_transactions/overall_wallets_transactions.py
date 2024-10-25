import json
import os
from decimal import Decimal
import matplotlib.pyplot as plt
from datetime import datetime
from matplotlib.patches import FancyBboxPatch

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

            # Count incoming and outgoing transactions and BTC amounts
            for tx in wallet_data.get('txs', []):
                timestamp = tx.get('time')
                if not timestamp:
                    continue

                # Convert timestamp to year and exclude transactions before 2012
                transaction_year = datetime.utcfromtimestamp(timestamp).year
                if transaction_year < 2012:
                    continue

                # Process incoming transactions (outputs where this wallet is the recipient)
                for output in tx.get('out', []):
                    if 'addr' in output and output['addr'] == wallet:
                        total_incoming_transactions += 1
                        total_received_btc += Decimal(output.get('value', 0)) / Decimal('100000000')

                # Process outgoing transactions (inputs where this wallet is the sender)
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
fig, axs = plt.subplots(2, 3, figsize=(15, 8))

# Data for visualization
metrics = {
    'Total Wallets': total_wallets,
    'Total Transactions': total_transactions,
    'Incoming Transactions': total_incoming_transactions,
    'Outgoing Transactions': total_outgoing_transactions,
    'BTC Received': float(total_received_btc),
    'BTC Sent': float(total_sent_btc)
}

# Define background colors for each metric
background_colors = ['#d1e8ff', '#ffe0b2', '#d4edda', '#f8d7da', '#e2e3e5', '#f5f5f5']

# Display each metric as large, centered text with distinct backgrounds
for ax, (label, value), color in zip(axs.flat, metrics.items(), background_colors):
    # Draw a colored rectangle as the background
    bbox = FancyBboxPatch((0.1, 0.1), 0.8, 0.8, boxstyle="round,pad=0.1", color=color, transform=ax.transAxes)
    ax.add_patch(bbox)

    # Add the text for the value
    ax.text(0.5, 0.6, f"{value:,.2f}", ha='center', va='center', fontsize=26, fontweight='bold', color='#333')
    ax.set_title(label, fontsize=18, fontweight='bold')
    ax.axis('off')  # Turn off the axis for a cleaner look

# Adjust layout for better readability
plt.tight_layout()
plt.show()
