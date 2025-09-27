from binance.client import Client
client = Client(api_key='yo3hNmQZQGmsX8RvhMmjMG76j7vXUleB73ww7UkF6kBMU7goabKsmKsdRP7Vlnva', api_secret='lMBNnjiXlF8eA1US6llLQNX93oWpOmAEKkExFaSeaRAR1NgiQq2kVevsKLx8nOdQ',testnet=False)



# account_info = client.get_account()
# balances = account_info['balances']
# # 过滤掉可用余额和冻结余额都为零的资产，只显示有余额的资产
# non_zero_balances = [asset for asset in balances if float(asset['free']) > 0 or float(asset['locked']) > 0]
# print("现货账户持仓:")
# for asset in non_zero_balances:
#      print(f"资产: {asset['asset']}, 可用: {asset['free']}, 锁定: {asset['locked']}")

# all_tickers = client.get_all_tickers()
# for ticker in all_tickers:
#     print(ticker['symbol'])
# exchange_info = client.get_exchange_info()
# symbols = [s['symbol'] for s in exchange_info['symbols']]
#
# # Filter symbols containing 'NUMI'
# numi_symbols = [s for s in symbols if 'NUMI' in s]
# print("Available NUMI symbols:", numi_symbols)

ticker = client.get_symbol_ticker(symbol='BTCUSDT')
print(ticker['price'])

# ticker = client.get_symbol_ticker(symbol="ALPHANUMIUSDT")
# print(ticker['price'])