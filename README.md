# 0G Galileo Auto Bot

This bot provides automated functionality for interacting with the 0G Galileo testnet, including storage scanning and token swapping capabilities.

## Features

### 1. Storage Scan Auto Bot
- Automatically uploads files to the 0G storage network
- Generates random images and submits them with proper hashing
- Handles multiple wallets with rotation
- Supports proxy rotation for requests
- Saves transaction results with detailed logs

### 2. Zer0 DEX Auto Swap (In Development)
- **Note:** The Zer0 DEX auto swap functionality is currently under development and not fully operational
- Planned features:
  - Automated token swaps between ETH, USDT, and BTC on 0G testnet
  - Multi-wallet support with automatic rotation
  - Slippage tolerance configuration
  - Multiple fee tier attempts for successful swaps
- Current limitations:
  - Swap transactions may fail due to contract changes or liquidity issues
  - Some token pairs may not be fully supported yet

## Setup

1. Setup Virtual Environtment:
   ```bash
   python3 -m venv venv
   ```

2. Open Virtual Environtment:
   ```bash
   source venv/bin/activates
   ```

3. Install requirements:
   ```bash
   pip install -r requirements.txt
   ```

4. (Optional) Add proxies to `proxies.txt`

## Usage

Run the main script and fill with your credentials:
```bash
python main.py
```

Follow the on-screen menu to select either storage uploads or token swaps.

## Configuration

- Edit constants in `storage.py` and `zero.py` for:
  - RPC endpoints
  - Contract addresses
  - Gas settings
  - Slippage tolerance (for swaps)

## Important Notes

- The Zer0 DEX swap functionality is experimental and may not work reliably
- Always test with small amounts first
- The bot is designed for the 0G Galileo testnet
- Monitor your transactions on [0G Chainscan](https://chainscan-galileo.0g.ai/)

Thanks to Airdrop Insiders for Reference on Storage Scan Auto Bot


