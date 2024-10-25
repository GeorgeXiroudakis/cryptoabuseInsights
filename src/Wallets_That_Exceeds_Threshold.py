import json
import os

# Paths for input files
wallets_by_abuse_type_path = '../data/wallets_by_abuse_type.json'
wallets_folder = '../data/bitcoin'
output_path = '../data/wallets_exceeding_thresholds.json'

# Load the wallets_by_abuse_type data
with open(wallets_by_abuse_type_path, 'r') as f:
    wallets_by_abuse_type = json.load(f)

# Store all unique wallets in sets per abuse type right after loading
wallets_by_abuse_type = {abuse_type: set(wallets) for abuse_type, wallets in wallets_by_abuse_type.items()}

# Initialize a dictionary to store wallets exceeding thresholds
wallets_exceeding_thresholds = {}

# Thresholds for transactions and total received
total_received_threshold = 10_000_000_000_000  # 10 trillion satoshis
n_tx_threshold = 100_000

# Process each abuse type and its wallets
for abuse_type, unique_wallets in wallets_by_abuse_type.items():
    wallets_exceeding_thresholds[abuse_type] = []

    for wallet in unique_wallets:
        wallet_file_path = os.path.join(wallets_folder, f"{wallet[:3]}/{wallet}.json")

        if os.path.exists(wallet_file_path):
            with open(wallet_file_path, 'r') as wf:
                try:
                    wallet_data = json.load(wf)
                except json.JSONDecodeError:
                    print(f"Error: Could not decode JSON for wallet {wallet}. Skipping...")
                    continue

                # Check if wallet exceeds the thresholds
                total_received = wallet_data.get('total_received', 0)
                n_tx = wallet_data.get('n_tx', 0)
                if total_received > total_received_threshold or n_tx > n_tx_threshold:
                    wallets_exceeding_thresholds[abuse_type].append(wallet)
                    print(f"Wallet {wallet} exceeds thresholds: total_received={total_received}, n_tx={n_tx}")

# Write the wallets exceeding thresholds to a JSON file
with open(output_path, 'w') as f:
    json.dump(wallets_exceeding_thresholds, f, indent=4)

print(f"\nFinished processing wallets. Results saved to {output_path}")
