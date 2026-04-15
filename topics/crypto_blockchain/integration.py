"""Crypto / Blockchain — web3.py / Foundry / Hardhat integrations."""
from __future__ import annotations
import os


class CryptoBlockchainTopic:
    name = "crypto_blockchain"
    tools = ["web3.py", "ethers.js", "foundry", "hardhat", "brownie", "ape", "solidity"]

    async def get_eth_balance(self, address: str) -> str:
        rpc = os.getenv("ETH_RPC_URL", "https://eth.public-rpc.com")
        try:
            from web3 import Web3
            w3 = Web3(Web3.HTTPProvider(rpc))
            bal = w3.eth.get_balance(address)
            return f"{w3.from_wei(bal, 'ether')} ETH"
        except ImportError:
            return "web3 not installed"
