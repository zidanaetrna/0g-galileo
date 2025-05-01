import os
from dotenv import load_dotenv
from web3 import Web3
import requests
import readline
import hashlib
import json
import time
from datetime import datetime
import random
import base64
import asyncio
from typing import Dict, List, Optional, Any
from pathlib import Path

System: time
from datetime import datetime
import random
import base64
import asyncio
from typing import Dict, List, Optional, Any
from pathlib import Path

# Constants
CHAIN_ID = 80087
RPC_URL = 'https://evmrpc-testnet.0g.ai'
CONTRACT_ADDRESS = '0x56A565685C9992BF5ACafb940ff68922980DBBC5'
METHOD_ID = '0xef3e12dc'
PROXY_FILE = 'proxies.txt'

# Color codes for console output
class Colors:
    RESET = "\033[0m"
    CYAN = "\033[36m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    RED = "\033[31m"
    WHITE = "\033[37m"
    GRAY = "\033[90m"
    BOLD = "\033[1m"

# Logger class for formatted console output
class Logger:
    @staticmethod
    def info(msg: str) -> None:
        print(f"{Colors.GREEN}[✓] {msg}{Colors.RESET}")

    @staticmethod
    def warn(msg: str) -> None:
        print(f"{Colors.YELLOW}[⚠] {msg}{Colors.RESET}")

    @staticmethod
    def error(msg: str) -> None:
        print(f"{Colors.RED}[✗] {msg}{Colors.RESET}")

    @staticmethod
    def success(msg: str) -> None:
        print(f"{Colors.GREEN}[✅] {msg}{Colors.RESET}")

    @staticmethod
    def loading(msg: str) -> None:
        print(f"{Colors.CYAN}[⟳] {msg}{Colors.RESET}")

    @staticmethod
    def step(msg: str) -> None:
        print(f"{Colors.WHITE}[➤] {msg}{Colors.RESET}")

    @staticmethod
    def debug(msg: str) -> None:
        print(f"{Colors.GRAY}[…] {msg}{Colors.RESET}")

    @staticmethod
    def critical(msg: str) -> None:
        print(f"{Colors.RED}{Colors.BOLD}[❌] {msg}{Colors.RESET}")

    @staticmethod
    def banner() -> None:
        print(f"{Colors.CYAN}{Colors.BOLD}")
        print("---------------------------------------------")
        print(" 0G Storage Scan Auto Bot - Airdrop Insiders")
        print("---------------------------------------------")
        print(f"{Colors.RESET}\n")

logger = Logger()

# Global variables
private_keys: List[str] = []
current_key_index: int = 0
proxies: List[str] = []
current_proxy_index: int = 0

def load_private_keys() -> None:
    global private_keys
    load_dotenv()
    try:
        index = 1
        key = os.getenv(f"PRIVATE_KEY_{index}")
        
        if not key and index == 1 and os.getenv("PRIVATE_KEY"):
            key = os.getenv("PRIVATE_KEY")
        
        while key:
            private_keys.append(key)
            index += 1
            key = os.getenv(f"PRIVATE_KEY_{index}")
        
        if not private_keys:
            logger.critical("No private keys found in .env file")
            exit(1)
        
        logger.success(f"Loaded {len(private_keys)} private key(s) from .env file")
    except Exception as e:
        logger.critical(f"Failed to load private keys: {str(e)}")
        exit(1)

def get_next_private_key() -> str:
    return private_keys[current_key_index]

def rotate_private_key() -> str:
    global current_key_index
    current_key_index = (current_key_index + 1) % len(private_keys)
    return private_keys[current_key_index]

def get_random_user_agent() -> str:
    user_agents = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15',
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:124.0) Gecko/20100101 Firefox/124.0',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36 Edg/122.0.0.0',
        'Mozilla/5.0 (iPhone; CPU iPhone OS 17_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1',
        'Mozilla/5.0 (iPad; CPU OS 17_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) CriOS/122.0.6261.89 Mobile/15E148 Safari/604.1',
        'Mozilla/5.0 (Linux; Android 14; SM-S918B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.6261.119 Mobile Safari/537.36',
        'Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.6261.119 Mobile Safari/537.36'
    ]
    return random.choice(user_agents)

def load_proxies() -> None:
    global proxies
    try:
        if os.path.exists(PROXY_FILE):
            with open(PROXY_FILE, 'r') as f:
                proxies = [line.strip() for line in f if line.strip() and not line.startswith('#')]
            
            if proxies:
                logger.info(f"Loaded {len(proxies)} proxies from {PROXY_FILE}")
            else:
                logger.warn(f"No proxies found in {PROXY_FILE}, will proceed without proxies")
        else:
            logger.warn(f"Proxy file {PROXY_FILE} not found, will proceed without proxies")
    except Exception as e:
        logger.error(f"Failed to load proxies: {str(e)}")

def get_next_proxy() -> Optional[str]:
    global current_proxy_index
    if not proxies:
        return None
    proxy = proxies[current_proxy_index]
    current_proxy_index = (current_proxy_index + 1) % len(proxies)
    return proxy

def create_requests_session() -> requests.Session:
    session = requests.Session()
    session.headers.update({
        'User-Agent': get_random_user_agent(),
        'accept': 'application/json, text/plain, */*',
        'accept-language': 'en-US,en;q=0.8',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'same-site',
        'sec-gpc': '1',
        'Referer': 'https://storagescan-galileo.0g.ai/',
        'Referrer-Policy': 'strict-origin-when-cross-origin'
    })
    proxy = get_next_proxy()
    if proxy:
        logger.debug(f"Using proxy: {proxy}")
        session.proxies = {'https': proxy}
    return session

# Web3 setup
w3 = Web3(Web3.HTTPProvider(RPC_URL))

def initialize_wallet() -> Any:
    private_key = get_next_private_key()
    logger.debug(f"Initializing wallet with private key: {private_key[:10]}...")
    wallet = w3.eth.account.from_key(private_key)
    logger.debug(f"Wallet address: {wallet.address}")
    return wallet

async def fetch_random_image() -> bytes:
    logger.loading('Fetching random image...')
    try:
        session = create_requests_session()
        response = session.get('https://picsum.photos/800/600', timeout=10)
        response.raise_for_status()
        logger.success('Random image fetched successfully')
        return response.content
    except requests.RequestException as e:
        logger.error(f"Error fetching image: {str(e)}")
        raise

async def prepare_image_data(image_buffer: bytes) -> Dict[str, str]:
    hash_value = '0x' + hashlib.sha256(image_buffer).hexdigest()
    logger.success(f"Generated file hash: {hash_value}")
    
    image_base64 = base64.b64encode(image_buffer).decode('utf-8')
    
    return {
        'root': hash_value,
        'data': image_base64
    }

def encode_transaction_data(file_root: str) -> bytes:
    content_hash = os.urandom(32)
    return b''.join([
        bytes.fromhex(METHOD_ID[2:]),
        bytes.fromhex('0000000000000000000000000000000000000000000000000000000000000020'),
        bytes.fromhex('0000000000000000000000000000000000000000000000000000000000000014'),
        bytes.fromhex('0000000000000000000000000000000000000000000000000000000000000060'),
        bytes.fromhex('0000000000000000000000000000000000000000000000000000000000000080'),
        bytes.fromhex('0000000000000000000000000000000000000000000000000000000000000000'),
        bytes.fromhex('0000000000000000000000000000000000000000000000000000000000000001'),
        content_hash,
        bytes.fromhex(('0000000000000000000000000000000000000000000000000000000000000000'))
    ])

def save_transaction_result(tx_data: Dict[str, Any]) -> None:
    try:
        results_dir = Path('results')
        results_dir.mkdir(exist_ok=True)
        
        timestamp = datetime.now().isoformat().replace(':', '-').replace('.', '-')
        file_path = results_dir / f'tx-{timestamp}.json'
        
        with open(file_path, 'w') as f:
            json.dump(tx_data, f, indent=2)
        
        logger.debug(f"Transaction details saved to {file_path}")
    except Exception as e:
        logger.error(f"Failed to save transaction results: {str(e)}")

async def upload_to_storage(image_data: Dict[str, str], wallet: Any, wallet_index: int) -> Dict[str, Any]:
    max_retries = 3
    timeout_seconds = 300
    attempt = 1
    
    while attempt <= max_retries:
        try:
            logger.loading(f"Checking wallet balance for {wallet.address}...")
            balance = w3.eth.get_balance(wallet.address)
            min_balance = w3.to_wei('0.0015', 'ether')
            if balance < min_balance:
                raise Exception(f"Insufficient balance: {w3.from_wei(balance, 'ether')} OG")
            logger.success(f"Wallet balance: {w3.from_wei(balance, 'ether')} OG")
            
            logger.loading(f"Uploading file segment to indexer using wallet #{wallet_index + 1} [{wallet.address}] (Attempt {attempt}/{max_retries})...")
            session = create_requests_session()
            response = session.post('https://indexer-storage-testnet-turbo.0g.ai/file/segment', json={
                'root': image_data['root'],
                'index': 0,
                'data': image_data['data'],
                'proof': {
                    'siblings': [image_data['root']],
                    'path': []
                }
            }, headers={'content-type': 'application/json'})
            response.raise_for_status()
            
            logger.success('Segment uploaded, submitting transaction to blockchain...')
            
            data = encode_transaction_data(image_data['root'])
            
            logger.loading('Estimating gas for transaction...')
            tx_params = {
                'to': CONTRACT_ADDRESS,
                'data': data,
                'from': wallet.address,
                'value': w3.to_wei('0.000839233398436224', 'ether')
            }
            try:
                gas_estimate = w3.eth.estimate_gas(tx_params)
            except Exception as e:
                logger.warn(f"Gas estimation failed: {str(e)}, using default gas limit")
                gas_estimate = 300000
            
            gas_limit = int(gas_estimate * 1.5)
            logger.success(f"Gas limit set: {gas_limit}")
            
            gas_price = w3.to_wei('1.029599997', 'gwei')
            required_balance = gas_price * gas_limit + w3.to_wei('0.000839233398436224', 'ether')
            if balance < required_balance:
                raise Exception(f"Insufficient balance for transaction: {w3.from_wei(balance, 'ether')} OG")
            
            logger.loading('Sending transaction...')
            tx = {
                'to': CONTRACT_ADDRESS,
                'data': data,
                'gas': gas_limit,
                'nonce': w3.eth.get_transaction_count(wallet.address),
                'chainId': CHAIN_ID,
                'gasPrice': gas_price,
                'value': w3.to_wei('0.000839233398436224', 'ether')
            }
            
            # Sign the transaction
            signed_tx = w3.eth.account.sign_transaction(tx, wallet.key)
            
            # Debug: Log signed transaction attributes
            logger.debug(f"Signed transaction attributes: {dir(signed_tx)}")
            
            # Use raw_transaction for Web3.py >= 6.0.0
            raw_tx = signed_tx.raw_transaction
            
            tx_hash = w3.eth.send_raw_transaction(raw_tx)
            
            logger.info(f"Transaction sent! Hash: {tx_hash.hex()}")
            logger.info(f"Explorer: https://chainscan-galileo.0g.ai/tx/{tx_hash.hex()}")
            
            logger.loading(f"Waiting for transaction confirmation ({timeout_seconds}s)...")
            receipt = await asyncio.wait_for(
                asyncio.to_thread(w3.eth.wait_for_transaction_receipt, tx_hash),
                timeout=timeout_seconds
            )
            
            if receipt['status'] == 1:
                logger.success(f"Transaction confirmed in block {receipt['blockNumber']}")
                logger.success(f"File uploaded with root hash: {image_data['root']}")
                return receipt
            else:
                raise Exception(f"Transaction failed: https://chainscan-galileo.0g.ai/tx/{tx_hash.hex()}")
        
        except Exception as e:
            logger.error(f"Upload attempt {attempt} failed: {str(e)}")
            if attempt < max_retries:
                delay = 10 + random.random() * 20
                logger.warn(f"Retrying after {delay:.2f}s...")
                await asyncio.sleep(delay)
                attempt += 1
            else:
                raise

async def main():
    try:
        logger.banner()
        load_private_keys()
        load_proxies()
        
        print(f"{Colors.CYAN}Available wallets:{Colors.RESET}")
        for i, key in enumerate(private_keys):
            wallet = w3.eth.account.from_key(key)
            print(f"{Colors.GREEN}[{i + 1}]{Colors.RESET} {Colors.YELLOW}{wallet.address}{Colors.RESET}")
        print()
        
        count = input("How many files to upload per wallet? ")
        count = int(count)
        
        if count <= 0:
            logger.error("Please enter a valid number greater than 0.")
            return
        
        total_uploads = count * len(private_keys)
        logger.info(f"Starting upload process for {count} files per wallet ({total_uploads} total uploads)")
        
        results = []
        successful = 0
        failed = 0
        
        for wallet_index in range(len(private_keys)):
            global current_key_index
            current_key_index = wallet_index
            wallet = initialize_wallet()
            
            logger.info(f"{Colors.BOLD}Starting uploads with wallet #{wallet_index + 1} [{wallet.address}]{Colors.RESET}")
            
            for i in range(1, count + 1):
                upload_number = (wallet_index * count) + i
                total_count = len(private_keys) * count
                
                logger.step(f"Processing upload {upload_number} of {total_count} (Wallet #{wallet_index + 1}, Upload #{i})")
                
                try:
                    image_buffer = await fetch_random_image()
                    image_data = await prepare_image_data(image_buffer)
                    receipt = await upload_to_storage(image_data, wallet, wallet_index)
                    
                    result = {
                        'walletIndex': wallet_index + 1,
                        'walletAddress': wallet.address,
                        'uploadIndex': i,
                        'globalIndex': upload_number,
                        'timestamp': datetime.now().isoformat(),
                        'hash': receipt['transactionHash'].hex(),
                        'blockNumber': receipt['blockNumber'],
                        'fileHash': image_data['root'],
                        'status': 'success'
                    }
                    results.append(result)
                    save_transaction_result(result)
                    
                    successful += 1
                    logger.success(f"Upload #{upload_number} completed successfully!")
                    
                    if upload_number < total_count:
                        logger.loading('Waiting before next upload...')
                        await asyncio.sleep(3)
                except Exception as e:
                    failed += 1
                    result = {
                        'walletIndex': wallet_index + 1,
                        'walletAddress': wallet.address,
                        'uploadIndex': i,
                        'globalIndex': upload_number,
                        'timestamp': datetime.now().isoformat(),
                        'error': str(e),
                        'status': 'failed'
                    }
                    results.append(result)
                    save_transaction_result(result)
                    
                    logger.error(f"Upload #{upload_number} failed: {str(e)}")
                    await asyncio.sleep(5)
            
            if wallet_index < len(private_keys) - 1:
                logger.loading("Waiting before switching to next wallet...")
                await asyncio.sleep(10)
        
        print()
        logger.info('Upload session summary:')
        logger.info(f'Total wallets used: {len(private_keys)}')
        logger.info(f'Uploads per wallet: {count}')
        logger.info(f'Total uploads attempted: {total_uploads}')
        logger.success(f'Successful uploads: {successful}')
        if failed > 0:
            logger.error(f'Failed uploads: {failed}')
        logger.success('All operations completed!')
    
    except Exception as e:
        logger.critical(f"Error in main process: {str(e)}")

if __name__ == "__main__":
    asyncio.run(main())