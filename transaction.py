import json
import hashlib
import time
import math
import pickle
import os
from ecdsa import SigningKey,VerifyingKey,SECP256k1,BadSignatureError
from base58 import b58encode_check,b58encode,b58decode_check,b58decode
import binascii

from utils import *


"""
Txout - transaction out class 

init 

amount - amount to be paid
address - address of the recipent

"""
class TxOut(object):
    def __init__(self,amount,address):
        self.amount = amount
        self.address = address
        self.timestamp = time.time()
    def to_dict(self):
        txdict = {}
        txdict["amount"] = self.amount
        txdict["address"] = self.address
        return txdict
    def to_json(self):
        return json.dumps(self.to_dict())
    def __eq__(self, other): 
        return self.__dict__ == other.__dict__
    
        
"""
TxIn - transaction in class

init

txoutid - hash of prev closed transaction list that contains the tx to be spent
txoutix - index of the specific tx in tx list
sig - signature of the tx to be spent

"""
class TxIn(object):
    def __init__(self,txoutid,txoutix):
        self.txoutid = txoutid
        self.txoutix = txoutix
        #self.timestamp = time.time()
    def to_dict(self):
        txdict = {}
        txdict["txoutid"] = self.txoutid
        txdict["txoutix"] = self.txoutix
        return txdict
    def to_json(self):
        return json.dumps(self.to_dict())
    def set_signature(self,sig):
        self.sig = sig
    def __eq__(self, other): 
        return self.__dict__ == other.__dict__
    
    
class Transaction(object):
    def __init__(self,txIns = [],txOuts = [],txtype = 'NORMAL'):
        self.txid = ""
        self.txIns = txIns
        self.txOuts = txOuts
        self.timestamp = time.time()
        self.txtype = txtype
        
        
    def txin_to_sign(self,txid,txix):
        for txin in self.txIns:
            if txin.txoutid == txid and txin.txoutix == txix:
                return txin.to_json()
        
        return None
        
    
    def add_signature(self,index,signaure):
        if index < len(self.txIns):
            self.txIns[index].sig = signaure
        
    def dict_hash(self):
        txdict = {}
        txinarr = []
        txoutarr = []
        for txin in self.txIns:
            txinarr.append(txin.to_dict())
        for txout in self.txOuts:
            txoutarr.append(txout.to_dict())
        txdict["txIns"] = txinarr
        txdict["txOuts"] = txoutarr
        txdict["time"] = str(self.timestamp)
        return txdict
    def to_dict(self):
        txdict = self.dict_hash()
        txdict["txid"] = self.txid
        return txdict
    def to_json(self):
        return json.dumps(self.to_dict())
    def hash_tx(self):
        if self.txid == "":
            self.txid = hashlib.sha256(json.dumps(self.dict_hash())).hexdigest()
        return self.txid
    def __eq__(self, other): 
        return self.__dict__ == other.__dict__
    
class UTXO(object):
    def __init__(self,txoutid,txoutix):
        self.txoutid = txoutid
        self.txoutix = txoutix
    def __eq__(self, other): 
        return self.__dict__ == other.__dict__
    
    
class UTXOpool(object):
    
    def __init__(self):
        self.utxos = []
        self.txouts = []
        
        
    def add_to_pool(self,utxo,txout,txtype = 'normal'):
        if not self.is_utxo_in_pool(utxo):
            self.utxos.append(utxo)
            self.txouts.append(txout)
            
        
        
    def remove_from_pool(self,utxo,txout):
        if self.is_utxo_in_pool(utxo) and self.is_txout_in_pool(txout):
            self.blockidxs.remove(self.blockidxs[self.utxos.index(utxo)])
            self.utxos.remove(utxo)
            self.txouts.remove(txout)
        
    def remove_from_pool_utxo(self,utxo):
        if self.is_utxo_in_pool(utxo):
            ix = self.utxos.index(utxo)
            self.utxos.pop(ix)
            self.txouts.pop(ix)
            
        
    def remove_from_pool(self,index):
        if len(self.utxos) > index and len(self.txouts) > index:
            self.utxos.pop(index)
            self.txouts.pop(index)
            
    
    def get_txout_from_pool(self,utxo):
        if len(self.utxos) == len(self.txouts):
            return self.txouts[self.utxos.index(utxo)]
        else:
            return None
    
    def get_utxo_from_pool(self,txout):
        if len(self.utxos) == len(self.txouts):
            return self.utxos[self.txouts.index(txout)]
        else:
            return None
        
    
    
    
    def is_utxo_in_pool(self,utxo):
        try: 
            self.utxos.index(utxo)
            return True
        except: 
            return False
        
    def is_txout_in_pool(self,txout):
        try: 
            self.txouts.index(txout)
            return True
        except: 
            return False
        
    def __eq__(self, other): 
        return self.__dict__ == other.__dict__

    
class TxHandler:
    def __init__(self,utxopool,conf_utxopool,node_wallet_addr):
        self.utxopool = utxopool
        self.conf_utxopool = conf_utxopool
        self.COIN_BASE = 100
        self.MAX_TXS_TO_MINE = 20
        self.node_wallet_addr = node_wallet_addr
        
    def calc_tx_fee(self,tx):
        txinsum = 0
        txoutsum = 0
        for txin in tx.txIns:
            utxo = UTXO(txin.txoutid,txin.txoutix)
            txout = self.utxopool.get_txout_from_pool(utxo)
            if txout is not None:
                txinsum += self.utxopool.get_txout_from_pool(utxo).amount
        for txout in tx.txOuts:
            txoutsum += txout.amount
        return txinsum - txoutsum
            
    def is_tx_valid(self,tx,fee = 0,debug = True):
        uinq_utxopool = UTXOpool()
        txinsum = 0
        txoutsum = 0
        
        
        if tx.txtype == 'FEE':
            
            if len(tx.txOuts) != 1:
                if debug:
                    print("(Fee Tx Invalid) Multiple or No Tx Outputs!")
                return False
            if tx.txOuts[0].amount != fee:
                if debug:
                    print("(Fee Tx Invalid) Fee Amount Altered!")
                return False
            if len(tx.txIns) != 0:
                if debug:
                    print("(Fee Tx Invalid) There should not be any Tx Inputs!")
                return False
            return True
            
        
        if tx.txtype == 'COINBASE':
            if len(tx.txOuts) != 1:
                if debug:
                    print("(Coinbase Tx Invalid) Multiple or No Tx Outputs!")
                return False
            if tx.txOuts[0].amount != self.COIN_BASE:
                if debug:
                    print("(Coinbase Tx Invalid) Coinbase Amount Altered!")
                return False
            if len(tx.txIns) != 0:
                if debug:
                    print("(Coinbase Tx Invalid) There should not be any Tx Inputs!")
                return False
            return True
                
                
                
                
        for txin in tx.txIns:
            utxo = UTXO(txin.txoutid,txin.txoutix)
        
            #1. no UTXO is claimed multiple times by tx
            
            if utxo in uinq_utxopool.utxos:
                if debug:
                    print("(Tx Invalid) Unspent Coins Claimed Multiple Times!")
                return False
            
            
            
            #2. all outputs claimed by Tx are in the current UTXO pool
            
            if not self.utxopool.is_utxo_in_pool(utxo):
                if debug:
                    print("(Tx Invalid) Tx In is not in current UTXO pool!")
                return False
            
            #3. signatures of txin are valid
            if not Crypto.verify_signature(self.utxopool.get_txout_from_pool(utxo).address,tx.txin_to_sign(txin.txoutid,txin.txoutix),txin.sig):
                if debug:
                    print("(Tx Invalid) Signature Not Valid!")
                return False
            
            uinq_utxopool.add_to_pool(utxo,self.utxopool.get_txout_from_pool(utxo))
            
            txinsum += self.utxopool.get_txout_from_pool(utxo).amount
        
        for txout in tx.txOuts:
            #4. all amounts are not negative
            if txout.amount <= 0:
                if debug:
                    print("(Tx Invalid) Txout Amount is negative!")
                return False
            txoutsum += txout.amount
        
        #5. check if the txtinsum >= txtoutsum
        if txinsum < txoutsum:
            if debug:
                print("(Tx Invalid) txinput sum is less than txout sum!")
            return False
            
        return True 
            
    def handle_txs(self,txs,tx_pool = [],tx_fee_pool = [],test_validity = True):
        valid_txs = []
        fees = []
        total_fee = 0
        for tx in txs:
            valid = True
            if test_validity:
                valid = self.is_tx_valid(tx,fee = total_fee)
            if valid:
                
                valid_txs.append(tx)
                
                # calculate fee
                if tx.txtype == 'NORMAL':
                    f = self.calc_tx_fee(tx)
                    fees.append([f,tx.txid])
                    total_fee += f
                
                # remove txouts from pool
                for txin in tx.txIns:
                    self.utxopool.remove_from_pool_utxo(UTXO(txin.txoutid,txin.txoutix))
                    self.conf_utxopool.remove_from_pool_utxo(UTXO(txin.txoutid,txin.txoutix))
                
                # add new txouts to pool
                for i in range(len(tx.txOuts)):
                    self.utxopool.add_to_pool(UTXO(tx.hash_tx(),i),tx.txOuts[i])
            else:
                
                if tx in tx_pool:
                    #print "IN ELSE"
                    valid_txs.append(tx)
                    for txp in tx_fee_pool:
                        if txp[1] == tx.txid:
                            total_fee += txp[0]
                    continue
                
                #print "NOT IN ELSE"
                
                    
        return valid_txs,fees
    
    def org_txs_for_block(self,valid_txs,tx_fees):
        
        org_txs = []
        sorted_tx_fees = sorted(tx_fees,reverse = True)
        sorted_txs_by_fee = []
        total_fee = 0
        # can rearrange based on tx-fees
        if len(valid_txs) > 0:
            
            for txfee in sorted_tx_fees:
                for tx in valid_txs:
                    if txfee[1] == tx.txid:
                        sorted_txs_by_fee.append(tx)
                        total_fee += txfee[0]
            
            if len(valid_txs) > len(sorted_tx_fees):
                for tx in valid_txs:
                    if tx not in sorted_txs_by_fee:
                        sorted_txs_by_fee.append(tx)
                
            
            

            # end of rearrangement

            for i in range(len(sorted_txs_by_fee[:self.MAX_TXS_TO_MINE])):
                org_txs.append(sorted_txs_by_fee[i])
            if total_fee > 0:
                tx_fee = Transaction(txIns = [],txOuts = [TxOut(total_fee,self.node_wallet_addr.strip())],txtype = 'FEE')
                tx_fee.hash_tx()
                org_txs.append(tx_fee)
        
        # add a coinbase txs
        
        tx_coinbase = Transaction(txIns = [],txOuts = [TxOut(self.COIN_BASE,self.node_wallet_addr.strip())],txtype = 'COINBASE')
        tx_coinbase.hash_tx()
        org_txs.append(tx_coinbase)
        
        return org_txs
        

                    
    
    def cleanup_utxopool(self,txs):
        # remove utxos from utxopool if txouts are in the new added external block 
        for tx in txs:
            for txin in tx.txIns:
                self.utxopool.remove_from_pool(UTXO(txin.txoutid,txin.txoutix))
                
                
                

