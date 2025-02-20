import os, base64, cryptography.fernet

def get_secure_value(name):
    key_file = 'secure/.key'
    with open(key_file, 'rb') as f:
        key = f.read()
    fernet = cryptography.fernet.Fernet(key)
    encrypted_value = ''
    file_path = f'secure/{name}.enc'
    with open(file_path, 'r') as f:
        encrypted_value = f.read()
    return fernet.decrypt(base64.urlsafe_b64decode(encrypted_value.encode())).decode()

# Get both addresses
wallet_address = get_secure_value('WALLET_ADDRESS')
profit_recipient = get_secure_value('PROFIT_RECIPIENT')

print(f"Trading Wallet: {wallet_address}")
print(f"Profit Recipient: {profit_recipient}")
