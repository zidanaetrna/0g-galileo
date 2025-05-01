import asyncio
import os
from dotenv import load_dotenv
from web3 import Web3
from eth_account import Account
from storage import main as storage_main, Logger, Colors, w3
from zero import execute_swap
from pathlib import Path
from decimal import Decimal, InvalidOperation

logger = Logger()

def clear_screen():
    """Clear the console screen."""
    os.system('cls' if os.name == 'nt' else 'clear')

def is_valid_private_key(key: str) -> bool:
    """Check if a string is a valid private key."""
    try:
        if len(key) == 64 or (len(key) == 66 and key.startswith('0x')):
            Account.from_key(key if not key.startswith('0x') else key[2:])
            return True
        return False
    except Exception as e:
        logger.error(f"Invalid private key format: {str(e)}")
        return False

def is_valid_seed_phrase(phrase: str) -> bool:
    """Check if a string is a valid seed phrase (12 or 24 words)."""
    words = phrase.strip().split()
    return len(words) in [12, 24]

def derive_private_key_from_seed(phrase: str) -> str:
    """Derive private key from seed phrase (simplified, using eth-account)."""
    try:
        account = Account.from_mnemonic(phrase)
        return account.key.hex()[2:]  # Remove '0x' prefix
    except Exception as e:
        logger.error(f"Error deriving private key from seed phrase: {str(e)}")
        return ""

def save_wallets_to_env(wallets: list) -> None:
    """Save wallets to .env file."""
    env_path = Path('.env')
    env_content = ""
    
    for i, wallet in enumerate(wallets, 1):
        env_content += f"PRIVATE_KEY_{i}={wallet}\n"
    
    try:
        with env_path.open('w') as f:
            f.write(env_content)
        logger.success(f"Saved {len(wallets)} wallet(s) to .env file")
    except Exception as e:
        logger.error(f"Failed to save wallets to .env: {str(e)}")

def prompt_for_wallets() -> list:
    """Prompt user to input up to three wallets (private keys or seed phrases)."""
    wallets = []
    print(f"{Colors.CYAN}Please input your wallet(s)!{Colors.RESET}")
    
    for i in range(1, 4):
        wallet_input = input(f"Wallet {i} (private key or seed phrase 12/24, press Enter to continue): ").strip()
        
        if not wallet_input:  # User pressed Enter
            break
        
        if is_valid_private_key(wallet_input):
            wallets.append(wallet_input if not wallet_input.startswith('0x') else wallet_input[2:])
        elif is_valid_seed_phrase(wallet_input):
            private_key = derive_private_key_from_seed(wallet_input)
            if private_key:
                wallets.append(private_key)
            else:
                logger.error(f"Invalid seed phrase for Wallet {i}. Skipping...")
        else:
            logger.error(f"Invalid input for Wallet {i}. Please provide a valid private key or seed phrase.")
    
    return wallets

def load_and_display_wallets() -> bool:
    """Load wallets from .env and display them. Return True if wallets are found, False otherwise."""
    global private_keys
    load_dotenv()
    private_keys = []
    seen_addresses = set()
    
    try:
        logger.info("Loading wallets from .env file...")
        index = 1
        key = os.getenv(f"PRIVATE_KEY_{index}")
        if not key and index == 1 and os.getenv("PRIVATE_KEY"):
            key = os.getenv("PRIVATE_KEY")
        
        while key:
            # Validate and check for duplicates
            if is_valid_private_key(key):
                wallet = w3.eth.account.from_key(key)
                address = wallet.address
                if address not in seen_addresses:
                    private_keys.append(key)
                    seen_addresses.add(address)
                else:
                    logger.warn(f"Duplicate wallet address {address} found for PRIVATE_KEY_{index}. Skipping...")
            else:
                logger.error(f"Invalid private key for PRIVATE_KEY_{index}. Skipping...")
            index += 1
            key = os.getenv(f"PRIVATE_KEY_{index}")
        
        if private_keys:
            print(f"{Colors.CYAN}Available wallets:{Colors.RESET}")
            for i, key in enumerate(private_keys):
                wallet = w3.eth.account.from_key(key)
                print(f"{Colors.GREEN}[{i + 1}]{Colors.RESET} {Colors.YELLOW}{wallet.address}{Colors.RESET}")
            print()
            return True
        logger.warn("No valid wallets found in .env file.")
        return False
    except Exception as e:
        logger.critical(f"Error loading wallets: {str(e)}")
        return False

def display_menu():
    """Display the main menu."""
    print(f"{Colors.CYAN}{'=' * 19} 0g Auto-Bot {'=' * 19}{Colors.RESET}")
    print("[1] Automatic Upload Files (Storage Scan)")
    print("[2] Automatic Zer0 Swap")
    print(f"{Colors.CYAN}{'=' * 19} author: aetrna {'=' * 19}{Colors.RESET}")
    print()

def convert_amount_to_wei(amount: str, token: str) -> int:
    """Convert decimal amount to integer in token's smallest unit."""
    token_decimals = {
        'ETH': 18,
        'USDT': 6,
        'BTC': 18  # Updated to 18 decimals
    }
    try:
        amount_decimal = Decimal(amount)
        if amount_decimal <= 0:
            raise ValueError("Amount must be greater than 0")
        # Convert to smallest unit (e.g., wei for ETH/BTC, 10^6 for USDT)
        amount_int = int(amount_decimal * (10 ** token_decimals[token]))
        return amount_int
    except (InvalidOperation, ValueError) as e:
        raise ValueError(f"Invalid amount: {str(e)}")

async def main():
    try:
        logger.info("Starting 0g Auto-Bot...")
        # Check Web3 connection
        if not w3.is_connected():
            logger.critical("Failed to connect to 0g testnet RPC. Check network or RPC URL.")
            return
        
        logger.info("Web3 connection established.")
        
        # Check if .env exists and has wallets
        env_exists = Path('.env').exists()
        logger.info(f".env file exists: {env_exists}")
        
        wallets_loaded = load_and_display_wallets() if env_exists else False
        
        # If no wallets are found or .env doesn't exist, prompt for wallet input
        if not wallets_loaded:
            logger.info("Prompting for wallet input...")
            wallets = prompt_for_wallets()
            if not wallets:
                logger.critical("No valid wallets provided. Exiting...")
                return
            save_wallets_to_env(wallets)
            # Reload wallets after saving
            if not load_and_display_wallets():
                logger.critical("Failed to load wallets after saving. Exiting...")
                return
        
        # Clear screen before showing UI
        clear_screen()
        
        while True:
            display_menu()
            choice = input("Select an option (1-2, or 'q' to quit): ").strip()
            
            if choice == '1':
                logger.info("Starting Storage Scan...")
                await storage_main()
            elif choice == '2':
                logger.info("Starting Zero DEX Swap...")
                print("Available tokens: ETH, USDT, BTC")
                
                # Prompt for swap details
                token_in = input("Which token do you want to swap (e.g., ETH): ").strip().upper()
                token_out = input("Swap with (e.g., USDT): ").strip().upper()
                count = input("How many times do you want to swap: ").strip()
                amount = input(f"Enter amount to swap (in decimal, e.g., 0.001 for {token_in}): ").strip()
                
                # Validate inputs
                valid_tokens = ['ETH', 'USDT', 'BTC']
                if token_in not in valid_tokens:
                    logger.error(f"Invalid token to swap from: {token_in}. Choose from {valid_tokens}.")
                    continue
                if token_out not in valid_tokens:
                    logger.error(f"Invalid token to swap to: {token_out}. Choose from {valid_tokens}.")
                    continue
                if token_in == token_out:
                    logger.error("Cannot swap a token with itself.")
                    continue
                
                try:
                    count = int(count)
                    if count <= 0:
                        logger.error("Please enter a valid number greater than 0 for count.")
                        continue
                    amount_int = convert_amount_to_wei(amount, token_in)
                    await execute_swap(token_in, token_out, amount_int, count)
                except ValueError as e:
                    logger.error(f"Invalid input: {str(e)}")
            elif choice.lower() == 'q':
                logger.info("Exiting 0g Auto-Bot...")
                break
            else:
                logger.error("Invalid option. Please select 1, 2, or 'q'.")
    except Exception as e:
        logger.critical(f"Fatal error in main: {str(e)}")

if __name__ == "__main__":
    try:
        logger.info("Initializing script...")
        # Enable mnemonic support for seed phrases
        Account.enable_unaudited_hdwallet_features()
        asyncio.run(main())
    except Exception as e:
        logger.critical(f"Script failed to start: {str(e)}")