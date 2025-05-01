import os
from dotenv import load_dotenv
from web3 import Web3
import requests
import json
import time
from datetime import datetime
import random
import asyncio
from typing import Dict, List, Optional, Any
from pathlib import Path
from web3.exceptions import ContractLogicError

# Constants
CHAIN_ID = 80087
RPC_URL = 'https://evmrpc-testnet.0g.ai'
SWAP_CONTRACT_ADDRESS = '0x16a811adc55A99b4456F62c54F12D3561559a268'
ETH_TOKEN_ADDRESS = '0x2619090fcfDB99a8CCF51c76C9467F7375040eeb'
USDT_TOKEN_ADDRESS = '0xA8F030218d7c26869CADd46C5F10129E635cD565'
BTC_TOKEN_ADDRESS = '0x6dc29491a8396bd52376b4f6da1f3e889c16ca85'
PROXY_FILE = 'proxies.txt'
APPROVE_METHOD_ID = '0x095ea7b3'  # approve(address,uint256)
SLIPPAGE = 0.05  # 5%
POOL_FEE = 500  # 0.05%, adjustable (try 3000 or 10000)

# Token mappings
TOKEN_ADDRESSES = {
    'ETH': ETH_TOKEN_ADDRESS,
    'USDT': USDT_TOKEN_ADDRESS,
    'BTC': BTC_TOKEN_ADDRESS
}

TOKEN_DECIMALS = {
    ETH_TOKEN_ADDRESS: 18,
    USDT_TOKEN_ADDRESS: 6,
    BTC_TOKEN_ADDRESS: 18
}

# Exchange rates (placeholder, ideally query from contract/API)
EXCHANGE_RATES = {
    ('ETH', 'USDT'): 1003.32,  # 1 ETH = 1003.32 USDT
    ('USDT', 'ETH'): 1 / 1003.32,
    ('USDT', 'BTC'): 0.000014320695857672,  # 1 USDT = 0.00001432 BTC
    ('BTC', 'USDT'): 1 / 0.000014320695857672,
    ('ETH', 'BTC'): 1003.32 * 0.000014320695857672,  # ~0.01437 BTC
    ('BTC', 'ETH'): 1 / (1003.32 * 0.000014320695857672)
}

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
        print(" 0G Zero DEX Swap Auto Bot - aetrna")
        print("---------------------------------------------")
        print(f"{Colors.RESET}\n")

logger = Logger()

# Global variables
private_keys: List[str] = []
current_key_index: int = 0
proxies: List[str] = []
current_proxy_index: int = 0

# Web3 setup
w3 = Web3(Web3.HTTPProvider(RPC_URL))

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

def initialize_wallet() -> Any:
    private_key = get_next_private_key()
    logger.debug(f"Initializing wallet with private key: {private_key[:10]}...")
    wallet = w3.eth.account.from_key(private_key)
    logger.debug(f"Wallet address: {wallet.address}")
    return wallet

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
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
        'accept': 'application/json, text/plain, */*',
        'accept-language': 'en-US,en;q=0.8',
    })
    proxy = get_next_proxy()
    if proxy:
        logger.debug(f"Using proxy: {proxy}")
        session.proxies = {'https': proxy}
    return session

async def check_balance(token_address: str, wallet_address: str) -> int:
    logger.loading(f"Checking balance for {token_address}...")
    erc20_abi = [
        {
            "constant": True,
            "inputs": [{"name": "_owner", "type": "address"}],
            "name": "balanceOf",
            "outputs": [{"name": "balance", "type": "uint256"}],
            "type": "function"
        }
    ]
    token_contract = w3.eth.contract(address=token_address, abi=erc20_abi)
    balance = token_contract.functions.balanceOf(wallet_address).call()
    logger.debug(f"Balance for {wallet_address}: {balance}")
    return balance

async def check_allowance(token_address: str, owner: str, spender: str) -> int:
    logger.loading(f"Checking allowance for {token_address}...")
    erc20_abi = [
        {
            "constant": True,
            "inputs": [
                {"name": "_owner", "type": "address"},
                {"name": "_spender", "type": "address"}
            ],
            "name": "allowance",
            "outputs": [{"name": "", "type": "uint256"}],
            "type": "function"
        }
    ]
    token_contract = w3.eth.contract(address=token_address, abi=erc20_abi)
    allowance = token_contract.functions.allowance(owner, spender).call()
    logger.debug(f"Allowance for {owner} to {spender}: {allowance}")
    return allowance

async def approve_token(token_address: str, wallet: Any, amount: int) -> Dict[str, Any]:
    logger.loading(f"Approving {token_address} for swap contract...")
    max_retries = 3
    attempt = 1
    
    while attempt <= max_retries:
        try:
            token_contract = w3.eth.contract(address=token_address, abi=[
                {
                    "constant": False,
                    "inputs": [
                        {"name": "_spender", "type": "address"},
                        {"name": "_value", "type": "uint256"}
                    ],
                    "name": "approve",
                    "outputs": [{"name": "", "type": "bool"}],
                    "type": "function"
                }
            ])
            
            data = token_contract.encodeABI(fn_name='approve', args=[SWAP_CONTRACT_ADDRESS, amount])
            
            tx = {
                'to': token_address,
                'data': data,
                'gas': 100000,
                'nonce': w3.eth.get_transaction_count(wallet.address),
                'chainId': CHAIN_ID,
                'gasPrice': w3.to_wei('1.029599997', 'gwei'),
                'value': 0
            }
            
            try:
                gas_estimate = w3.eth.estimate_gas(tx)
                tx['gas'] = int(gas_estimate * 1.5)
            except Exception as e:
                logger.warn(f"Gas estimation failed: {str(e)}, using default gas limit")
            
            signed_tx = w3.eth.account.sign_transaction(tx, wallet.key)
            logger.debug(f"Signed transaction attributes: {dir(signed_tx)}")
            raw_tx = signed_tx.raw_transaction
            
            tx_hash = w3.eth.send_raw_transaction(raw_tx)
            logger.info(f"Approval transaction sent! Hash: {tx_hash.hex()}")
            logger.info(f"Explorer: https://chainscan-galileo.0g.ai/tx/{tx_hash.hex()}")
            
            logger.loading("Waiting for approval confirmation (60s)...")
            receipt = await asyncio.wait_for(
                asyncio.to_thread(w3.eth.wait_for_transaction_receipt, tx_hash),
                timeout=60
            )
            
            if receipt['status'] == 1:
                logger.success(f"Approval confirmed in block {receipt['blockNumber']}")
                return receipt
            else:
                raise Exception(f"Approval failed: https://chainscan-galileo.0g.ai/tx/{tx_hash.hex()}")
        
        except Exception as e:
            logger.error(f"Approval attempt {attempt} failed: {str(e)}")
            if attempt < max_retries:
                delay = 5 + random.random() * 10
                logger.warn(f"Retrying after {delay:.2f}s...")
                await asyncio.sleep(delay)
                attempt += 1
            else:
                raise

async def check_pool_liquidity(token_in: str, token_out: str, fee: int) -> Dict[str, int]:
    logger.loading(f"Checking liquidity for {token_in}/{token_out} pool with fee {fee}...")
    POOL_ADDRESS = '0xB093d6FFd0c9A0E0eCe0fEC0F4c527bE73404554'  # Checksum address
    erc20_abi = [
        {
            "constant": True,
            "inputs": [{"name": "_owner", "type": "address"}],
            "name": "balanceOf",
            "outputs": [{"name": "balance", "type": "uint256"}],
            "type": "function"
        }
    ]
    try:
        token_in_contract = w3.eth.contract(address=token_in, abi=erc20_abi)
        token_out_contract = w3.eth.contract(address=token_out, abi=erc20_abi)
        token_in_balance = token_in_contract.functions.balanceOf(POOL_ADDRESS).call()
        token_out_balance = token_out_contract.functions.balanceOf(POOL_ADDRESS).call()
        logger.debug(f"Pool liquidity: {token_in_balance} {token_in}, {token_out_balance} {token_out}")
        return {'token_in_balance': token_in_balance, 'token_out_balance': token_out_balance}
    except Exception as e:
        logger.warn(f"Failed to check pool liquidity: {str(e)}")
        return {'token_in_balance': 0, 'token_out_balance': 0}

async def swap_tokens(wallet: Any, wallet_index: int, token_in: str, token_out: str, amount_in: int, min_amount_out: int, fee: int = POOL_FEE) -> Dict[str, Any]:
    logger.loading(f"Executing swap from {token_in} to {token_out} with fee {fee}...")
    max_retries = 3
    timeout_seconds = 300
    attempt = 1
    
    while attempt <= max_retries:
        try:
            logger.loading(f"Checking wallet balance for {wallet.address}...")
            balance = w3.eth.get_balance(wallet.address)
            min_balance = w3.to_wei('0.0001', 'ether')
            if balance < min_balance:
                raise Exception(f"Insufficient OG balance: {w3.from_wei(balance, 'ether')} OG")
            logger.success(f"Wallet balance: {w3.from_wei(balance, 'ether')} OG")
            
            # Check token balance
            token_balance = await check_balance(token_in, wallet.address)
            if token_balance < amount_in:
                raise Exception(f"Insufficient token balance: {token_balance} < {amount_in}")
            logger.success(f"Token balance: {token_balance}")
            
            # Check pool liquidity
            liquidity = await check_pool_liquidity(token_in, token_out, fee)
            if liquidity['token_out_balance'] < min_amount_out:
                logger.warn(f"Pool may have insufficient liquidity: {liquidity['token_out_balance']} {token_out}")
            
            # Use exactInputSingle (Uniswap V3-like)
            method_id = '0x414bf389'  # exactInputSingle
            data = (
                bytes.fromhex(method_id[2:]) +
                w3.to_bytes(hexstr=token_in[2:].lower()).rjust(32, b'\0') +
                w3.to_bytes(hexstr=token_out[2:].lower()).rjust(32, b'\0') +
                w3.to_bytes(fee).rjust(32, b'\0') +
                w3.to_bytes(hexstr=wallet.address[2:].lower()).rjust(32, b'\0') +
                w3.to_bytes(int(time.time() + 3600)).rjust(32, b'\0') +
                w3.to_bytes(amount_in).rjust(32, b'\0') +
                w3.to_bytes(min_amount_out).rjust(32, b'\0') +
                w3.to_bytes(0).rjust(32, b'\0')  # sqrtPriceLimitX96
            )
            
            logger.debug(f"Swap data: {data.hex()}")
            
            tx = {
                'to': SWAP_CONTRACT_ADDRESS,
                'data': data,
                'gas': 200000,
                'nonce': w3.eth.get_transaction_count(wallet.address),
                'chainId': CHAIN_ID,
                'gasPrice': w3.to_wei('1.029599997', 'gwei'),
                'value': 0
            }
            
            try:
                gas_estimate = w3.eth.estimate_gas(tx)
                tx['gas'] = int(gas_estimate * 1.5)
            except ContractLogicError as e:
                logger.error(f"Gas estimation failed for exactInputSingle: {str(e)}")
                raise Exception(f"Swap method failed: {str(e)}")
            
            signed_tx = w3.eth.account.sign_transaction(tx, wallet.key)
            logger.debug(f"Signed transaction attributes: {dir(signed_tx)}")
            raw_tx = signed_tx.raw_transaction
            
            tx_hash = w3.eth.send_raw_transaction(raw_tx)
            logger.info(f"Swap transaction sent! Hash: {tx_hash.hex()}")
            logger.info(f"Explorer: https://chainscan-galileo.0g.ai/tx/{tx_hash.hex()}")
            
            logger.loading(f"Waiting for swap confirmation ({timeout_seconds}s)...")
            receipt = await asyncio.wait_for(
                asyncio.to_thread(w3.eth.wait_for_transaction_receipt, tx_hash),
                timeout=timeout_seconds
            )
            
            if receipt['status'] == 1:
                logger.success(f"Swap confirmed in block {receipt['blockNumber']}")
                return receipt
            else:
                raise Exception(f"Swap failed: https://chainscan-galileo.0g.ai/tx/{tx_hash.hex()}")
        
        except Exception as e:
            logger.error(f"Swap attempt {attempt} failed: {str(e)}")
            if attempt < max_retries:
                delay = 10 + random.random() * 20
                logger.warn(f"Retrying after {delay:.2f}s...")
                await asyncio.sleep(delay)
                attempt += 1
            else:
                raise

async def execute_swap(token_in: str, token_out: str, amount_in: int, count: int) -> None:
    """
    Execute swaps for the given token pair, amount, and count.
    Called by main.py, handles wallet iteration and swap logic.
    """
    logger.banner()
    load_private_keys()
    load_proxies()
    
    token_in_address = TOKEN_ADDRESSES.get(token_in.upper())
    token_out_address = TOKEN_ADDRESSES.get(token_out.upper())
    
    if not token_in_address or not token_out_address:
        logger.error(f"Invalid token pair: {token_in} to {token_out}")
        return
    
    # Calculate min_amount_out
    token_in_decimals = TOKEN_DECIMALS[token_in_address]
    token_out_decimals = TOKEN_DECIMALS[token_out_address]
    exchange_rate = EXCHANGE_RATES.get((token_in.upper(), token_out.upper()))
    
    if not exchange_rate:
        logger.error(f"No exchange rate available for {token_in} to {token_out}")
        return
    
    # Convert amount_in to expected output
    amount_in_float = amount_in / (10 ** token_in_decimals)
    expected_out_float = amount_in_float * exchange_rate
    expected_out = int(expected_out_float * (10 ** token_out_decimals))
    min_amount_out = int(expected_out * (1 - SLIPPAGE))
    
    total_swaps = min(count, len(private_keys))
    logger.info(f"Starting swap process for {total_swaps} swap(s)")
    
    results = []
    successful = 0
    failed = 0
    
    # Try multiple fee tiers
    fee_tiers = [500, 3000, 10000]  # 0.05%, 0.3%, 1%
    
    for swap_index in range(total_swaps):
        wallet_index = swap_index % len(private_keys)  # Cycle through wallets
        global current_key_index
        current_key_index = wallet_index
        wallet = initialize_wallet()
        
        logger.info(f"{Colors.BOLD}Starting swap #{swap_index + 1} with wallet #{wallet_index + 1} [{wallet.address}]{Colors.RESET}")
        
        # Try each fee tier
        for fee in fee_tiers:
            try:
                logger.info(f"Trying swap with fee tier {fee}...")
                
                # Check OG balance
                balance = w3.eth.get_balance(wallet.address)
                min_balance = w3.to_wei('0.0001', 'ether')
                if balance < min_balance:
                    raise Exception(f"Insufficient OG balance: {w3.from_wei(balance, 'ether')} OG")
                logger.success(f"Wallet balance: {w3.from_wei(balance, 'ether')} OG")
                
                # Check token balance
                token_balance = await check_balance(token_in_address, wallet.address)
                if token_balance < amount_in:
                    raise Exception(f"Insufficient token balance: {token_balance} < {amount_in}")
                logger.success(f"Token balance: {token_balance}")
                
                # Check allowance
                allowance = await check_allowance(token_in_address, wallet.address, SWAP_CONTRACT_ADDRESS)
                if allowance < amount_in:
                    logger.info(f"Insufficient allowance ({allowance} < {amount_in}), approving...")
                    await approve_token(token_in_address, wallet, amount_in)
                
                # Execute swap
                receipt = await swap_tokens(wallet, wallet_index, token_in_address, token_out_address, amount_in, min_amount_out, fee)
                
                result = {
                    'walletIndex': wallet_index + 1,
                    'walletAddress': wallet.address,
                    'swapIndex': swap_index + 1,
                    'timestamp': datetime.now().isoformat(),
                    'hash': receipt['transactionHash'].hex(),
                    'blockNumber': receipt['blockNumber'],
                    'tokenIn': token_in,
                    'tokenOut': token_out,
                    'amountIn': amount_in,
                    'fee': fee,
                    'status': 'success'
                }
                results.append(result)
                save_transaction_result(result)
                
                successful += 1
                logger.success(f"Swap #{swap_index + 1} completed successfully with fee {fee}!")
                
                break  # Exit fee tier loop on success
            
            except Exception as e:
                logger.error(f"Swap with fee {fee} failed: {str(e)}")
                if fee == fee_tiers[-1]:  # Last fee tier
                    failed += 1
                    result = {
                        'walletIndex': wallet_index + 1,
                        'walletAddress': wallet.address,
                        'swapIndex': swap_index + 1,
                        'timestamp': datetime.now().isoformat(),
                        'error': str(e),
                        'status': 'failed'
                    }
                    results.append(result)
                    save_transaction_result(result)
                    logger.error(f"Swap #{swap_index + 1} failed after trying all fee tiers")
                continue
        
        if swap_index < total_swaps - 1:
            logger.loading("Waiting before next swap...")
            await asyncio.sleep(10)
    
    print()
    logger.info('Swap session summary:')
    logger.info(f'Total wallets used: {len(set([r['walletIndex'] for r in results]))}')
    logger.info(f'Total swaps attempted: {total_swaps}')
    logger.success(f'Successful swaps: {successful}')
    if failed > 0:
        logger.error(f'Failed swaps: {failed}')
    logger.success('All operations completed!')

def save_transaction_result(tx_data: Dict[str, Any]) -> None:
    try:
        results_dir = Path('results')
        results_dir.mkdir(exist_ok=True)
        
        timestamp = datetime.now().isoformat().replace(':', '-').replace('.', '-')
        file_path = results_dir / f'swap-{timestamp}.json'
        
        with open(file_path, 'w') as f:
            json.dump(tx_data, f, indent=2)
        
        logger.debug(f"Transaction details saved to {file_path}")
    except Exception as e:
        logger.error(f"Failed to save transaction results: {str(e)}")

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
        
        print(f"{Colors.CYAN}Select token pair:{Colors.RESET}")
        print(f"{Colors.GREEN}[1]{Colors.RESET} ETH to USDT")
        print(f"{Colors.GREEN}[2]{Colors.RESET} USDT to ETH")
        print(f"{Colors.GREEN}[3]{Colors.RESET} USDT to BTC")
        print(f"{Colors.GREEN}[4]{Colors.RESET} BTC to USDT")
        print(f"{Colors.GREEN}[5]{Colors.RESET} ETH to BTC")
        print(f"{Colors.GREEN}[6]{Colors.RESET} BTC to ETH")
        pair_choice = input("Enter choice (1-6): ")
        pair_choice = int(pair_choice)
        
        if pair_choice not in [1, 2, 3, 4, 5, 6]:
            logger.error("Invalid pair choice.")
            return
        
        amount = input("Enter input amount (e.g., 0.01 for ETH/BTC, 12 for USDT): ")
        amount = float(amount)
        count = input("How many times do you want to swap: ")
        count = int(count)
        
        if amount <= 0 or count <= 0:
            logger.error("Please enter valid amount and count greater than 0.")
            return
        
        # Configure token pair
        if pair_choice == 1:
            token_in, token_out = 'ETH', 'USDT'
        elif pair_choice == 2:
            token_in, token_out = 'USDT', 'ETH'
        elif pair_choice == 3:
            token_in, token_out = 'USDT', 'BTC'
        elif pair_choice == 4:
            token_in, token_out = 'BTC', 'USDT'
        elif pair_choice == 5:
            token_in, token_out = 'ETH', 'BTC'
        else:
            token_in, token_out = 'BTC', 'ETH'
        
        # Convert amount to integer
        token_decimals = {'ETH': 18, 'USDT': 6, 'BTC': 18}
        amount_in = int(amount * (10 ** token_decimals[token_in]))
        
        await execute_swap(token_in, token_out, amount_in, count)
    
    except Exception as e:
        logger.critical(f"Error in main process: {str(e)}")

if __name__ == "__main__":
    asyncio.run(main())