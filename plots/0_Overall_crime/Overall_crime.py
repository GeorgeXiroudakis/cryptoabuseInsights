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

# Load the abuse data and store unique wallets, using only the "All" type
unique_wallets = set()
with open(abuse_json_path) as f:
    abuse_data = json.load(f)
    for source, abuse_types in abuse_data.items():
        all_wallets = abuse_types.get("All", [])
        unique_wallets.update(all_wallets)  # Add wallets to the set to remove duplicates

# Load Bitcoin to Euro exchange rates
with open(exchange_rates_path) as f:
    exchange_rates = json.load(f)

# Initialize variables
total_received_funds_eur = Decimal('0')  # Total incoming funds in EUR
total_received_funds_btc = Decimal('0')  # Total incoming funds in BTC
total_sent_funds_eur = Decimal('0')      # Total outgoing funds in EUR
total_sent_funds_btc = Decimal('0')      # Total outgoing funds in BTC

# Dictionaries to hold daily totals for visualization
daily_received_btc = defaultdict(Decimal)
daily_sent_btc = defaultdict(Decimal)

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

            # Skip wallets with extremely large total_received or n_tx values
            total_received = wallet_data.get('total_received', 0)
            n_tx = wallet_data.get('n_tx', 0)
            if (total_received > 10_000_000_000_000) or (n_tx > 100_000):
                continue

            wallet_included_in_result = False  # Flag to check if wallet is included

            # Loop through transactions
            for tx in wallet_data.get('txs', []):
                timestamp = tx.get('time')
                if not timestamp:
                    print(f"Error: Missing timestamp for transaction in wallet {wallet}. Skipping transaction...")
                    continue

                # Exclude data before 2012
                if not is_transaction_valid(timestamp):
                    continue  # Skip transactions before 2012

                conversion_rate = get_euro_value(timestamp)
                # Proceed even if conversion_rate is zero

                tx_date = datetime.utcfromtimestamp(timestamp).strftime('%Y-%m-%d')

                # Process received funds (outputs where the wallet is the recipient)
                for output_tx in tx.get('out', []):
                    if 'addr' in output_tx and output_tx['addr'] == wallet:
                        value_in_btc = satoshis_to_btc(output_tx.get('value', 0))
                        total_received_funds_btc += value_in_btc
                        value_in_euros = value_in_btc * conversion_rate
                        total_received_funds_eur += value_in_euros

                        # Update daily total
                        daily_received_btc[tx_date] += value_in_btc

                        wallet_included_in_result = True  # Wallet has valid transactions


                # Process sent funds (inputs where the wallet is the sender)
                for input_tx in tx.get('inputs', []):
                    prev_out = input_tx.get('prev_out', {})
                    if 'addr' in prev_out and prev_out['addr'] == wallet:
                        value_in_btc = satoshis_to_btc(prev_out.get('value', 0))
                        total_sent_funds_btc += value_in_btc
                        value_in_euros = value_in_btc * conversion_rate
                        total_sent_funds_eur += value_in_euros

                        # Update daily total
                        daily_sent_btc[tx_date] += value_in_btc

                        wallet_included_in_result = True  # Wallet has valid transactions


            if wallet_included_in_result:
                wallets_included += 1  # Increment if wallet has valid transactions

        # Print progress after every 500 wallets processed
        if processed_wallets % 500 == 0 or processed_wallets == total_wallets:
            print(f"Processed {processed_wallets}/{total_wallets} wallets...")

# Output the total funds received and sent in BTC and EUR
total_received_funds_in_billions_eur = total_received_funds_eur / Decimal('1000000000')  # Convert to billions
total_sent_funds_in_billions_eur = total_sent_funds_eur / Decimal('1000000000')          # Convert to billions

print(f"\nTotal wallets taken into account in the result: {wallets_included}")

print(f"\nTotal funds received (across all abuse types):")
print(f" - {total_received_funds_btc} BTC")
print(f" - {total_received_funds_in_billions_eur:.2f} billion EUR")

print(f"\nTotal funds sent (across all abuse types):")
print(f" - {total_sent_funds_btc} BTC")
print(f" - {total_sent_funds_in_billions_eur:.2f} billion EUR")


#visualize the results

# Prepare data for visualization
funds = ['Received', 'Sent']
btc_values = [float(total_received_funds_btc), float(total_sent_funds_btc)]
# Convert EUR values to billions for visualization
eur_values = [float(total_received_funds_eur) / 1_000_000_000, float(total_sent_funds_eur) / 1_000_000_000]

# Create subplots for EUR and BTC
fig, axs = plt.subplots(1, 2, figsize=(12, 6))

# Define professional colors
btc_color = '#EC8305'
eur_color = '#091057'

# Plot EUR values in billions (on the left)
bars_eur = axs[0].bar(funds, eur_values, color=eur_color)
axs[0].set_title('Total Funds in Billions of EUR', fontsize=14)
axs[0].set_ylabel('EUR (Billions)', fontsize=12)
axs[0].set_ylim([0, max(eur_values) * 1.1])

# Add labels above each bar for EUR
for bar in bars_eur:
    yval = bar.get_height()
    axs[0].text(
        bar.get_x() + bar.get_width() / 2,
        yval,
        f'{yval:.2f} Billion EUR',
        ha='center',
        va='bottom',
        fontsize=10,
        color='black'
    )

# Plot BTC values (on the right)
bars_btc = axs[1].bar(funds, btc_values, color=btc_color)
axs[1].set_title('Total Funds in BTC', fontsize=14)
axs[1].set_ylabel('BTC', fontsize=12)
axs[1].set_ylim([0, max(btc_values) * 1.1])

# Add labels above each bar for BTC
for bar in bars_btc:
    yval = bar.get_height()
    axs[1].text(
        bar.get_x() + bar.get_width() / 2,
        yval,
        f'{yval:.2f} BTC',
        ha='center',
        va='bottom',
        fontsize=10,
        color='black'
    )

# Adjust layout for a clean look
plt.tight_layout()
plt.show()




