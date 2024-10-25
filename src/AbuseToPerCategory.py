import json
from collections import defaultdict

# Paths for input and output files
abuse_json_path = '../data/Abuses.json'
wallets_by_abuse_type_path = '../data/wallets_by_abuse_type.json'

# Load the Abuses.json file
with open(abuse_json_path, 'r') as f:
    abuse_data = json.load(f)

# Initialize a dictionary to store wallets by abuse type
wallets_by_abuse_type = defaultdict(set)

# Populate the dictionary
for source, abuse_types in abuse_data.items():
    for abuse_type, wallets in abuse_types.items():
        if abuse_type.lower() != "all":  # Ignore the "All" category if present
            wallets_by_abuse_type[abuse_type].update(wallets)

# Convert sets to lists for JSON serialization
wallets_by_abuse_type = {k: list(v) for k, v in wallets_by_abuse_type.items()}

# Write the output to wallets_by_abuse_type.json
with open(wallets_by_abuse_type_path, 'w') as f:
    json.dump(wallets_by_abuse_type, f, indent=4)

print(f"Converted {abuse_json_path} to {wallets_by_abuse_type_path}")
