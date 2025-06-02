from contract_analyzer import ContractAnalyzer

# Example usage
if __name__ == "__main__":
    contract_address = "0x...YOUR_CONTRACT_ADDRESS..."  # Replace with actual contract address
    api_key = "YOUR_ETHERSCAN_API_KEY"  # Replace with Etherscan API key
    
    analyzer = ContractAnalyzer(contract_address, api_key)  # Initialize analyzer
    
    # Analyze funding transactions
    funding_txs = analyzer.analyze_funding_transactions()  # Get deployer funding txs
    
    # Analyze token distribution
    token_txs = analyzer.analyze_token_distribution()  # Get token transfers
    
    # Analyze recipient wallets
    wallet_txs = analyzer.analyze_recipient_wallets()  # Get recipient wallet txs
    
    # Find suspicious wallets
    suspicious_wallets = analyzer.find_suspicious_wallets()  # Find suspicious wallets