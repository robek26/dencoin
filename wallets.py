import json
import hashlib
import time
import math
import pickle
import os
import datetime
from ecdsa import SigningKey,VerifyingKey,SECP256k1,BadSignatureError
from base58 import b58encode_check,b58encode,b58decode_check,b58decode
import binascii

from utils import *
from transaction import *

class Wallet(object):
    def __init__(self,name):
        self.wallet_name = name#hashlib.sha256(str(time.time())).hexdigest()[:10] 
        self.private_key,self.public_addr = Crypto.generate_priv_pub_key_pair()
        self.account_balance = 0
        self.conf_acc_balance = 0
        self.myutxopool = UTXOpool()
        self.conf_myutxopool = UTXOpool()
    def __eq__(self, other): 
        return self.__dict__ == other.__dict__
    
class WalletManager:
    def __init__(self,utxopool,conf_utxopool,name,Portal):
        self.wallets = []
        self.TOTAL_ACC_BALANCE = 0
        self.TOTAL_CONF_ACC_BALANCE = 0
        self.MAX_TX_FEE = 0
        self.utxopool = utxopool
        self.Portal = Portal
        self.conf_utxopool = conf_utxopool
        self.tx_history = []
        
        
        self.Portal.update_balance(self.TOTAL_ACC_BALANCE,self.TOTAL_CONF_ACC_BALANCE)
        self.Portal.update_wallet_num(len(self.wallets))
        
        self.file_fnd = False
        for fls in os.listdir("wallet"):
            if fls.find(name) > -1 and fls.find(".wal") > -1:
                self.file_path = "wallet/" + fls
                self.file_fnd = True
        if not self.file_fnd:
            self.file_path = "wallet/{}_{}.wal".format(name,hashlib.sha256(str(time.time())).hexdigest()[:20]) 
        
        
    def append_to_file(self,wallet):
        with open(self.file_path,"a") as handle:
            handle.write(wallet.wallet_name + "," + wallet.private_key + "," + wallet.public_addr + "\n")
    def load_wallets(self):
        self.wallets = []
        try:
            with open(self.file_path,"r") as handler:
                for line in handler:
                    name,prkey,pubkey = line.split(",")
                    wallet = Wallet(name)
                    wallet.wallet_name = name
                    wallet.private_key = prkey
                    wallet.public_addr = pubkey.strip()
                    self.wallets.append(wallet)
                self.Portal.update_wallet_num(len(self.wallets))
        except:
            return
    def create_wallet(self,name):
        wallet = Wallet(name)
        self.wallets.append(wallet)
        self.append_to_file(wallet)
        self.Portal.update_wallet_num(len(self.wallets))
        return wallet
    
    def set_utxopool(self,utxopool):
        self.utxopool = utxopool
    
   
    def get_utxopool_for_wallet(self,addr):
        myutxopool = UTXOpool()
        conf_myutxopool = UTXOpool()
        
        for txout in self.utxopool.txouts:
            if txout.address == addr:
                myutxopool.add_to_pool(self.utxopool.get_utxo_from_pool(txout),txout)
                
        for txout in self.conf_utxopool.txouts:
            if txout.address == addr:
                conf_myutxopool.add_to_pool(self.conf_utxopool.get_utxo_from_pool(txout),txout)
                
        return myutxopool,conf_myutxopool
    
    def update_utxopool_on_wallet(self):
        for wallet in self.wallets:
            wallet.myutxopool,wallet.conf_myutxopool = self.get_utxopool_for_wallet(wallet.public_addr)
    
    def find_wallet_by_addr(self,addr):
        for wallet in self.wallets:
            if wallet.public_addr == addr:
                return wallet
        return None
            
                
    def get_account_balance(self,wallet):
        tot_balance = 0
        conf_balance = 0
        for txout in wallet.myutxopool.txouts:
            if txout.address == wallet.public_addr:
                tot_balance += txout.amount
        for txout in wallet.conf_myutxopool.txouts:
            if txout.address == wallet.public_addr:
                conf_balance += txout.amount
        return tot_balance,conf_balance
    
    def update_all_wallets_account_balance(self):
        self.TOTAL_ACC_BALANCE = 0
        self.TOTAL_CONF_ACC_BALANCE = 0
        for wallet in self.wallets:
            wallet.account_balance,wallet.conf_acc_balance = self.get_account_balance(wallet)
            self.TOTAL_ACC_BALANCE += wallet.account_balance
            self.TOTAL_CONF_ACC_BALANCE += wallet.conf_acc_balance
        self.Portal.update_balance(self.TOTAL_ACC_BALANCE,self.TOTAL_CONF_ACC_BALANCE)
        self.Portal.update_lst_wallet(self)
        self.Portal.display_wallet_table(self)
    
    def is_addr_valid(self,addr):
        # used to check destination addr is valid before sending money
        return Crypto.is_pubkey_valid(addr)
    
    
    
    def set_tx_history(self,date,amnt):
        self.tx_history.append({"date" : date,"amount" : amnt})
        self.Portal.add_row_2_txhist(date,amnt)
        tx_hist_file = "wallet/" + self.file_path.split("/")[1].split(".")[0] + "_TX_HIST.dat"
        with open(tx_hist_file,"a") as handle:
            handle.write(date + "," + str(amnt) + "\n")

    def load_tx_history_local(self):
        tx_hist_file = "wallet/" + self.file_path.split("/")[1].split(".")[0] + "_TX_HIST.dat"
        try:
            with open(tx_hist_file,"r") as handle:
                for line in handle:
                    cols = line.split(",")
                    # eg 123123,234324,12,unconfirmed
                    self.tx_history.append({"date" : cols[0],"amount" : cols[1]})
                    self.Portal.add_row_2_txhist(cols[0],cols[1])
        except:
            return

    def get_tx_history_from_blockchain(self,txs):
        # fetch all txs history of all wallets from block chain
        return
            
    
        
    def create_txins(self,amnt_to_pay,wallet,max_tx_fee = 0):
        myutxopool = wallet.conf_myutxopool
        txins = []
        total_amount = amnt_to_pay + max_tx_fee
        curr_amount = 0
        resid_amnt = 0
        if myutxopool is not None:
            for utxo in myutxopool.utxos:
                amount = myutxopool.get_txout_from_pool(utxo).amount
                txin = TxIn(utxo.txoutid,utxo.txoutix)
                txin.set_signature(Crypto.sign_document(wallet.private_key,txin.to_json()))
                txins.append(txin)
                curr_amount += amount
                if curr_amount >= total_amount:
                    resid_amnt = curr_amount - total_amount
                    return txins,resid_amnt,curr_amount
        else:
            return None,None,None
        
        
    def create_txouts(self,wallet,recepients,resid_amnt,total_to_pay):
        txouts = []
        total_out = 0
        for recepient in recepients:
            txouts.append(TxOut(recepient[1],str(recepient[0])))
            total_out += recepient[1]
            
        if resid_amnt > 0:
            txouts.append(TxOut(resid_amnt,wallet.public_addr.strip()))
            total_out += resid_amnt
            
        txfee = total_to_pay - total_out
        #if txfee > 0:
        #    txouts.append(TxOut(txfee,"miner_addr"))
        return txouts
    
     
    
    def create_transaction(self,tx_sheet):
        # dont forget to pay remaining coin to this wallet(immutable coin)
        # tx_sheet -> {'sender wallet_pub_key':[[pk1,amnt],[pk2,amnt]],'sender wallet2_pubkey':[[pk3,amnt],[pk4,amnt]]}
        
       
        
        
        
        tx_sheet = json.loads(tx_sheet)
        txins = []
        txouts = []
        fee_per_wallet = self.MAX_TX_FEE / float(len(tx_sheet))
        
        for sender_wallet_addr in tx_sheet:
            sender_wallet = self.find_wallet_by_addr(sender_wallet_addr)
            recipients = tx_sheet[sender_wallet_addr]
            total_payment = sum([i[1] for i in recipients])
            address_validity = [i[0] for i in recipients]
            rec_address_invalid = False in address_validity
            if sender_wallet.account_balance < total_payment:
                print("(Create tx error) acc balance of wallet '{}' not enough to make payment.".format(sender_wallet.public_addr))
                return None,"acc balance of wallet '{}' not enough to make payment.".format(sender_wallet.public_addr),0
            if rec_address_invalid:
                print("(Create tx error) pub key invalid '{}'".format(address_validity.index(False)))
                return None,"pub key invalid '{}'".format(address_validity.index(False)),0
            
            # create transaction
            
            tmp_txins,resid_amnt,total_to_pay = self.create_txins(total_payment,sender_wallet,max_tx_fee = fee_per_wallet)
            if tmp_txins is None:
                print("(Create tx error) No Confirmed tx input found!")
                return None,"No Confirmed tx input found!",0
            tmp_txouts = self.create_txouts(sender_wallet,recipients,resid_amnt,total_to_pay)
            
            txins += tmp_txins
            txouts += tmp_txouts
            
        
        new_tx = Transaction(txIns = txins,txOuts = txouts)
        new_tx.hash_tx()
        return new_tx,"SUCCESS",total_to_pay - resid_amnt
            