from xrpl.account import get_balance
from xrpl.models import Payment, Tx
from xrpl.wallet import Wallet
from xrpl.transaction import submit_and_wait
from xrpl.models.transactions.transaction import Memo
from xrpl.asyncio.clients import AsyncWebsocketClient
from xrpl.asyncio.transaction import (
    safe_sign_and_autofill_transaction,
    send_reliable_submission,
)
from xrpl.models.currencies import (
    IssuedCurrency,
    XRP,
)
import xrpl
import pandas as pd
import os
import time
import datetime
import asyncio
import pprint

send_issuer = "rcoreNywaoz2ZCQ8Lg2EbSLnGuRBmun6D"
send_currency = "434F524500000000000000000000000000000000"

# print("Enter your XRP address")
# send_wallet = input()
# print("Enter your Secret for the XRP address")
# send_secret = input()

### debuggin or hard code sending wallet below ###
send_wallet = ''
send_secret = ''

send_wallet = Wallet(seed=send_secret, sequence=0)
print("Enter the amount to airdrop per NFT held")
drop_amount = input()

print("Enter the Memo for the Airdrop")
memo_data = input()
memo_type = "Text"
memo_format = "text/plain"

memo_data = memo_data.encode('utf-8').hex()
memo_type = memo_type.encode('utf-8').hex()
memo_format = memo_format.encode('utf-8').hex()

print(f"Using {send_wallet.classic_address} to send {drop_amount} per NFT held...")
print("Continue? Enter Y or N")
scan = input()
if scan == "Y":
    print("Scanning Airdrop Recipients and Calculating Amounts")
    df = pd.read_csv ('SoloNationOG.csv',
                     header=None,
                     names=['og #', 'wallet'])
    # print(df)

    wallet_counts = pd.Series(df['wallet']).value_counts()
    print("HOLDERS                               # of NFTS")
    print(wallet_counts)
    wallet_dict = {'wallet':[], 'multiplier': []}
    for wallet, count in wallet_counts.items():
        wallet_dict['wallet'].append(wallet)
        wallet_dict['multiplier'].append(count)

    unique_wallets_df = pd.DataFrame(wallet_dict)
    print(unique_wallets_df)

    ### scan through csv here ###\
    print("Continue? Enter Y or N")
    start = input()


async def balance_check(wallet):
    async with AsyncWebsocketClient("wss://s2.ripple.com") as client:

        t = await time()
        print(f"{t}: {wallet}")
        response = await client.request(xrpl.models.requests.AccountInfo(account=wallet, ledger_index="validated"))
        xrp_balance = response.result['account_data']['Balance']
        xrp_balance = float(xrp_balance) * 0.000001
        print(f"{t}: XRP Balance: {xrp_balance:.6f}")

        response = await client.request(xrpl.models.requests.AccountLines(account=wallet, ledger_index="validated"))
        
        balances = 0
        for line in response.result['lines']:
            if line['account'] == send_issuer:
                t = await time()
                asset = line['currency']
                trustline = line['account']
                balance = line['balance']
                balances += 1 
                print(f"{t}: Asset: {asset}")
                print(f"{t}: TL: {trustline}")
                print(f"{t}: Balance: {balance}")
                
        return balances

async def time():
    now = datetime.datetime.now()
    t = now.strftime("%H:%M:%S")

    return t

async def main() -> int:
    # Define the network client
    async with AsyncWebsocketClient("wss://s2.ripple.com") as client:
        if start == "Y":
            data = []
            t = await time()
            print(f"{t}: Connecting Websockets to wss://s2.ripple.com")
            t = await time()
            print(f"{t}: Starting SoloNationOG Core Airdrop Now")
            for i in unique_wallets_df.index:
                result_data = ''
                total_drop = round(int(unique_wallets_df['multiplier'][i]) * float(drop_amount),6)
                wallet = unique_wallets_df['wallet'][i]
                print(f"{t}: Sending {wallet} calculated airdrop amount: {total_drop} - Airdrop #{(i+1)} of {len(unique_wallets_df.index)}")
                t = await time()
                print(f"{t}: Balances of wallets before Payment tx")
                balance = await balance_check(send_wallet.classic_address)
                t = await time()
                balance = await balance_check(wallet)
                if balance == 0:
                    print(f"{t}: Core trustline not found at {wallet}!!!!!!!!!!!!!!!!!!!!!!!!!!!")
                    data.append({
                        'Wallet': wallet,
                        'Drop Amount': total_drop,
                        'Time': t,
                        'TX Hash': 'NO TL',
                        })
                else:
                # Create a Payment transaction
                    payment_tx = Payment(
                        account=send_wallet.classic_address,
                        destination=wallet,
                        memos=[
                            Memo(
                                memo_type=memo_type,
                                memo_data=memo_data,
                                memo_format=memo_format
                            ),
                        ],
                        amount=xrpl.models.amounts.issued_currency_amount.IssuedCurrencyAmount(
                            currency=send_currency,
                            issuer=send_issuer,
                            value=total_drop,
                        )
                    )
                    t = await time()
                    signed_tx = await safe_sign_and_autofill_transaction(payment_tx, send_wallet, client)
                    pprint.pprint(signed_tx) #move to logging

                    # Submit the transaction and wait for response (validated or rejected)
                    t = await time()
                    print(f"{t}: Sending Airdrop transaction...")
                    result = await send_reliable_submission(signed_tx, client)
                    if result.is_successful():
                        print(f"{t}: Payment succeeded: "
                              f"https://mainnet.xrpl.org/transactions/{signed_tx.get_hash()}")
                    data.append({
                        'Wallet': wallet,
                        'Drop Amount': total_drop,
                        'Time': t,
                        'TX Hash': signed_tx.get_hash(),
                        })
                    print(data)
                    else:
                        raise Exception(f"{t}: Error sending transaction: {result}")
                    print(f"{t}: Balances of wallets after Payment tx")
                    t = await time()
                    balance = await balance_check(send_wallet.classic_address)
                    t = await time()
                    balance = await balance_check(wallet)


                print(f"{t}: Pausing for 1 second...")
                await asyncio.sleep(1)
        df = pd.DataFrame(data)
        current_date = datetime.datetime.now()
        month_abbreviation = current_date.strftime('%b')
        new_file_name = f"{month_abbreviation}_airdrop.csv"
        df.to_csv(new_file_name, index=False)
        
        print("Airdrop Complete!!!")
if __name__ == "__main__":
    asyncio.run(main())
