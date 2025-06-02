import requests
import pandas as pd
from datetime import datetime

class ContractAnalyzer:
    def __init__(self, contract_address, api_key):
        """
        Initialize the ContractAnalyzer with contract details and API credentials.

        This constructor sets up the necessary parameters for analyzing a smart contract,
        including the contract address, Etherscan API key, and Infura project ID for Web3 access.
        It also initializes attributes to store contract creation details and total token supply.

        Args:
            contract_address (str): Ethereum contract address (e.g., '0x...').
            api_key (str): Etherscan API key for accessing blockchain data.
        """
        self.contract_address = contract_address.lower()  # Ensure address is lowercase for consistency
        self.api_key = api_key  # Store Etherscan API key
        self.base_url = "https://api.etherscan.io/api"  # Base URL for Etherscan API
        self.creation_tx = None  # Store contract creation transaction details
        self.deployer_address = None  # Store deployer wallet address
        self.creation_timestamp = None  # Store timestamp of contract creation
        self.total_supply = None  # Store total token supply

    def _make_api_request(self, params):
        """
        Helper method to make Etherscan API requests and handle responses.

        This method constructs and sends an API request to Etherscan, appending the API key
        to the provided parameters. It processes the response, returning the result if successful
        or an empty list if the request fails.

        Args:
            params (dict): Dictionary of API query parameters (e.g., module, action).

        Returns:
            list: API response data if successful, else an empty list.
        """
        params["apikey"] = self.api_key  # Add API key to parameters
        response = requests.get(self.base_url, params=params).json()  # Send GET request
        if response["status"] == "1":  # Check if request was successful
            return response["result"]  # Return result data
        return []  # Return empty list on failure

    def get_contract_creation_tx(self):
        """
        Retrieve the contract creation transaction and deployer address.

        This method queries Etherscan to get the transaction that created the contract,
        extracting the deployer’s wallet address and transaction hash. It stores these
        details in instance attributes for later use.

        Returns:
            dict: Contract creation transaction details (deployer address, tx hash) if found, else None.
        """
        params = {
            "module": "contract",
            "action": "getcontractcreation",
            "contractaddress": self.contract_address
        }  # API parameters for contract creation query
        result = self._make_api_request(params)  # Make API request
        if result:  # If result is non-empty
            self.creation_tx = result[0]  # Store first result (creation tx)
            self.deployer_address = self.creation_tx["contractCreator"]  # Store deployer address
            return self.creation_tx  # Return creation tx details
        return None  # Return None if no creation tx found

    def get_eth_transactions(self, wallet_address, startblock=0, endblock=99999999):
        """
        Fetch ETH transactions for a specified wallet.

        This method retrieves all ETH transactions (both incoming and outgoing) for a given wallet
        using the Etherscan API. It converts transaction values from Wei to ETH and ensures timestamps
        are integers for consistency.

        Args:
            wallet_address (str): Wallet address to query transactions for.
            startblock (int): Starting block number for transaction query (default: 0).
            endblock (int): Ending block number for transaction query (default: 99999999).

        Returns:
            pd.DataFrame: DataFrame of ETH transactions with columns like hash, from, to, value, timeStamp.
        """
        params = {
            "module": "account",
            "action": "txlist",
            "address": wallet_address,
            "startblock": startblock,
            "endblock": endblock,
            "sort": "asc"
        }  # API parameters for ETH transaction query
        txs = self._make_api_request(params)  # Fetch transactions
        df = pd.DataFrame(txs)  # Convert to DataFrame
        if not df.empty:  # If transactions exist
            df["value"] = df["value"].astype(float) / 1e18  # Convert Wei to ETH
            df["timeStamp"] = df["timeStamp"].astype(int)  # Ensure timestamp is integer
        return df  # Return transaction DataFrame

    def get_token_transfers(self, wallet_address=None):
        """
        Fetch ERC-20 token transfers for the contract or a specific wallet.

        This method retrieves token transfer events for the specified contract, optionally
        filtered by a wallet address. It adjusts token amounts based on the contract’s decimal
        places and ensures timestamps are integers.

        Args:
            wallet_address (str, optional): Wallet address to filter transfers (default: None, all transfers).

        Returns:
            pd.DataFrame: DataFrame of token transfers with columns like hash, to, value, timeStamp.
        """
        params = {
            "module": "account",
            "action": "tokentx",
            "contractaddress": self.contract_address,
            "startblock": 0,
            "endblock": 99999999,
            "sort": "asc"
        }  # API parameters for token transfer query
        if wallet_address:  # If wallet address is provided
            params["address"] = wallet_address  # Filter by wallet
        txs = self._make_api_request(params)  # Fetch token transfers
        df = pd.DataFrame(txs)  # Convert to DataFrame
        if not df.empty:  # If transfers exist
            decimals = int(df["tokenDecimal"].iloc[0]) if "tokenDecimal" in df else 18  # Get token decimals
            df["value"] = df["value"].astype(float) / 10**decimals  # Adjust token amounts
            df["timeStamp"] = df["timeStamp"].astype(int)  # Ensure timestamp is integer
        return df  # Return transfer DataFrame

    def get_token_supply(self):
        """
        Fetch the total token supply of the contract.

        This method queries Etherscan to get the total supply of the ERC-20 token,
        adjusting for 18 decimals (standard for most tokens). The result is stored
        in the instance for use in other methods.

        Returns:
            float: Total token supply, or None if the query fails.
        """
        params = {
            "module": "stats",
            "action": "tokensupply",
            "contractaddress": self.contract_address
        }  # API parameters for token supply query
        result = self._make_api_request(params)  # Fetch token supply
        if result:  # If result is non-empty
            self.total_supply = float(result) / 1e18  # Convert to human-readable (assuming 18 decimals)
            return self.total_supply  # Return total supply
        return None  # Return None if query fails

    def get_wallet_creation_time(self, wallet_address):
        """
        Estimate wallet creation time based on its first transaction.

        This method fetches the earliest transaction for a wallet to approximate its creation time,
        returning both the timestamp and block number of the first transaction.

        Args:
            wallet_address (str): Wallet address to check.

        Returns:
            tuple: (timestamp, block_number) of the first transaction, or (None, None) if no transactions.
        """
        txs = self.get_eth_transactions(wallet_address)  # Fetch wallet transactions
        if not txs.empty:  # If transactions exist
            first_tx = txs.iloc[0]  # Get earliest transaction
            return int(first_tx["timeStamp"]), int(first_tx["blockNumber"])  # Return timestamp and block
        return None, None  # Return None if no transactions

    def analyze_funding_transactions(self):
        """
        Analyze ETH transactions funding the deployer wallet.

        This method retrieves ETH transactions where the deployer wallet received funds,
        printing key details (hash, sender, amount, timestamp). It also sets the creation
        timestamp if the contract creation transaction is found in the transaction list.

        Returns:
            pd.DataFrame: DataFrame of funding transactions to the deployer.
        """
        if not self.deployer_address:  # If deployer address not set
            self.get_contract_creation_tx()  # Fetch creation tx
        if not self.deployer_address:  # If still no deployer
            return pd.DataFrame()  # Return empty DataFrame
        
        eth_txs = self.get_eth_transactions(self.deployer_address)  # Fetch deployer’s transactions
        funding_txs = eth_txs[eth_txs["to"] == self.deployer_address.lower()]  # Filter incoming ETH
        if not funding_txs.empty:  # If funding transactions exist
            print("Funding Transactions to Deployer:")  # Print header
            print(funding_txs[["hash", "from", "value", "timeStamp"]])  # Print key details
            if self.creation_tx:  # If creation tx exists
                # Set creation timestamp if creation tx hash is in funding transactions
                creation_txs = funding_txs[funding_txs["hash"] == self.creation_tx["txHash"]]
                if not creation_txs.empty:
                    self.creation_timestamp = int(creation_txs["timeStamp"].iloc[0])
        return funding_txs  # Return funding transactions

    def analyze_token_distribution(self):
        """
        Analyze token transfers from the contract to other wallets.

        This method fetches and prints all token transfers from the contract, showing
        transaction hash, recipient address, token amount, and timestamp.

        Returns:
            pd.DataFrame: DataFrame of token transfers from the contract.
        """
        token_txs = self.get_token_transfers()  # Fetch token transfers
        if not token_txs.empty:  # If transfers exist
            print("Token Distribution from Contract:")  # Print header
            print(token_txs[["hash", "to", "value", "timeStamp"]])  # Print key details
        return token_txs  # Return transfer DataFrame

    def analyze_recipient_wallets(self):
        """
        Analyze transactions from wallets that received tokens.

        This method iterates through wallets that received tokens from the contract,
        fetching their ETH and token transactions. It prints the transaction counts
        for each wallet to identify activity levels.

        Returns:
            dict: Dictionary mapping wallet addresses to their ETH and token transactions.
        """
        token_txs = self.get_token_transfers()  # Fetch token transfers
        if token_txs.empty:  # If no transfers
            return {}  # Return empty dict
        
        recipient_wallets = token_txs["to"].unique()  # Get unique recipient addresses
        wallet_txs = {}  # Store transaction data for each wallet
        for wallet in recipient_wallets:  # Iterate through recipients
            eth_txs = self.get_eth_transactions(wallet)  # Fetch ETH transactions
            token_txs_wallet = self.get_token_transfers(wallet)  # Fetch token transactions
            wallet_txs[wallet] = {
                "eth_txs": eth_txs,
                "token_txs": token_txs_wallet
            }  # Store transactions
            print(f"Wallet {wallet}:")  # Print wallet address
            print(f"  ETH Transactions: {len(eth_txs)}")  # Print ETH tx count
            print(f"  Token Transactions: {len(token_txs_wallet)}")  # Print token tx count
        return wallet_txs  # Return transaction data

    def find_suspicious_wallets(self, time_window=86400*7):
        """
        Identify wallets created around deployment with round token amounts and low activity.

        This method analyzes token recipient wallets to find those created within a specified
        time window (default: 7 days) of the contract deployment, holding round token amounts
        (e.g., 1M tokens or ~1% of supply), and having low transaction activity (<5 ETH txs,
        <3 token txs). These are potential bonus or airdrop wallets.

        Args:
            time_window (int): Time window in seconds to consider for wallet creation (default: 7 days).

        Returns:
            pd.DataFrame: DataFrame of suspicious wallets with wallet address, token amount,
                          percentage of supply, transaction count, and creation time.
        """
        if not self.total_supply:  # If total supply not set
            self.get_token_supply()  # Fetch token supply
        if not self.creation_timestamp:  # If creation timestamp not set
            self.analyze_funding_transactions()  # Fetch funding transactions
        if not self.total_supply or not self.creation_timestamp:  # If required data missing
            return pd.DataFrame()  # Return empty DataFrame
        
        token_txs = self.get_token_transfers()  # Fetch token transfers
        if token_txs.empty:  # If no transfers
            return pd.DataFrame()  # Return empty DataFrame
        
        suspicious_wallets = []  # List to store suspicious wallet data
        for wallet in token_txs["to"].unique():  # Iterate through recipient wallets
            wallet_txs = self.get_eth_transactions(wallet)  # Fetch ETH transactions
            token_txs_wallet = self.get_token_transfers(wallet)  # Fetch token transactions
            creation_time, _ = self.get_wallet_creation_time(wallet)  # Get wallet creation time
            
            if creation_time and abs(creation_time - self.creation_timestamp) <= time_window:  # Check time window
                token_amount = token_txs_wallet[token_txs_wallet["to"] == wallet]["value"].sum()  # Total tokens received
                percentage = (token_amount / self.total_supply) * 100  # Percentage of total supply
                # Check for round amounts (1M tokens or ~1% of supply)
                is_round = (token_amount >= 1_000_000 or abs(percentage - 1) < 0.1 or abs(percentage - round(percentage)) < 0.1)
                # Check for low transaction activity
                low_activity = len(wallet_txs) < 5 and len(token_txs_wallet) < 3
                if is_round and low_activity:  # If wallet meets criteria
                    suspicious_wallets.append({
                        "wallet": wallet,
                        "token_amount": token_amount,
                        "percentage": percentage,
                        "tx_count": len(wallet_txs),
                        "creation_time": datetime.fromtimestamp(creation_time).strftime("%Y-%m-%d %H:%M:%S")
                    })  # Add to suspicious wallets
        
        df = pd.DataFrame(suspicious_wallets)  # Convert to DataFrame
        if not df.empty:  # If suspicious wallets found
            print("Suspicious Wallets (Round Amounts, Low Activity):")  # Print header
            print(df)  # Print suspicious wallets
        return df  # Return suspicious wallets DataFrame