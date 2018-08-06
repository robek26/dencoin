import json
import hashlib
import time
import math
import pickle

"""
init :

index - index of this block in the block chain
version - the consensus protocol version (when changed is used to detect hard forks)
prev_hash - previous hash of the block that this block will append on
data - data to be kept in block
message - any message that the builder of the block want to send
nonce - number found from proof of work
difficulty - the difficulty of proof of work, adjusted every few blocks
coin_base - coin awarded if the block is accepted
send_addr - (optional) used incase the block contains create coin. in that case the send_addr is the addr to send the coin

methods:

prep_2_hash() - convert block information to json string format to convert it to hash
to_dict() - convert block information to dict
to_json() - convert block information to json string that contains the hash of the block

"""
class Block:
    def __init__(self,parent_block,version,data,message,nonce = 0,difficulty = 18,coin_base = 0,send_addr = None):
        self.parent_block = parent_block
        self.version = version
        self.index = 0
        self.prev_hash = "-"
        if self.parent_block is not None:
            self.index = parent_block.index + 1
            self.prev_hash = parent_block.get_hash()
        self.txs = data 
        self.message = message
        self.nonce = nonce
        self.difficulty = difficulty
        self.coin_base = coin_base
        self.send_addr = send_addr 
        self.timestamp = time.time()
        self.hash = hashlib.sha256(self.prep_2_hash()).hexdigest()
        
    def prep_2_hash(self):
        raw_data = {}
        data = ""
        raw_data["version"] = str(self.version)
        raw_data["index"] = str(self.index)
        raw_data["prev_hash"] = str(self.prev_hash)
        for tx in self.txs:
            data += tx.to_json()
        raw_data["data"] = str(data)
        raw_data["message"] = str(self.message)
        raw_data["nonce"] = str(self.nonce)
        raw_data["difficulty"] = str(self.difficulty)
        raw_data["timestamp"] = str(self.timestamp)
        jsdata = json.dumps(raw_data)
        return jsdata
    def to_dict(self):
        raw_data = {}
        data = ""
        raw_data["version"] = str(self.version)
        raw_data["index"] = str(self.index)
        raw_data["prev_hash"] = str(self.prev_hash)
        for tx in self.txs:
            data += tx.to_json()
        raw_data["data"] = data
        raw_data["message"] = str(self.message)
        raw_data["nonce"] = str(self.nonce)
        raw_data["difficulty"] = str(self.difficulty)
        raw_data["timestamp"] = str(self.timestamp)
        raw_data["hash"] = str(self.hash)
        return raw_data
    def to_json(self):
        raw_data = self.to_dict()
        jsdata = json.dumps(raw_data)
        return jsdata
    
    def get_hash(self):
        return self.hash
    
    
    
"""
init:

genesis_block - if new block chain, build a genesis block(new block)
chain - import existing blockchain 

methods:

get_max_height_block() - finds the max height  block in the chain (one with max index)
generate_block() - generates a new block given data and message
mine_block() - solve puzzle to find nonce, that makes hash of the block proportional to its difficulty level
add_block_to_chain() - if block is valid, it's added to chain
is_block_valid() - compares curr block with prev block and decides if curr block is valid
get_latest_block() - gets the most recent block
hash_block_data() - hash json string of block info
is_blockchain_valid() - validates the entire or part of it(index - last) blockchain by checking individual blocks
to_dict() - converts the whole blockchain to dictionary object.
to_json() - converts the whole blockchain to json string.
replace_block_chain() - incase there is a chain conflict from other nodes and need to replace with a new one.
append_block_chain() - adds new blocks to blockchain
fetch_blocks_from_chain() - fetches blocks from chain starting from index i
calc_difficulty() - calculates the difficulty of the next mined block
adjust_difficulty() - adjusts the difficulty of the next mined block based on time and number of blocks
timestamp_valid() - given a new block's timestamp, compare it to prev block and check if it's in optimum range, else it's edited to manipulate
                    mining difficulty
choose_chain_wrt_difficulty() - Given a new blockchain, calculate the cummulative difficulties of each blocks and the chain with higher difficulty 
                                will replace the existing one.

"""
class BlockChain:
    def __init__(self,txhandler,genesis_block = None,chain = []):
        self.MAX_CUT_HEIGHT = 10 # the max far back index parent block goes from latest to append a new block.
        self.CONSENSUS_PROTOCOL_VERSION = "1.0"
        
        self.DIFFICULTY = 18
        self.block_gen_interval = 20 #seconds
        self.diffculty_adj_interval = 20 #block
        self.timestamp_validator = 60 # seconds, to check if the miners changed their block timestamp to manipulate difficulty
        
        self.char_2_bin = {
                '0': '0000', '1': '0001', '2': '0010', '3': '0011', '4': '0100',
                '5': '0101', '6': '0110', '7': '0111', '8': '1000', '9': '1001',
                'a': '1010', 'b': '1011', 'c': '1100', 'd': '1101',
                'e': '1110', 'f': '1111'
            }
        
        
        self.chain = chain
        self.genesis_block = genesis_block
        self.max_height_block = None
        self.txhandler = txhandler
        if self.genesis_block is not None:
            self.chain.append(genesis_block)
            self.max_height_block = genesis_block
        elif len(self.chain) > 0:
            self.max_height_block = self.get_max_height_block()
            
    def get_max_height_block(self):
        max_height = 0
        max_block = None
        for block in self.chain:
            if block.index >= max_height:
                max_block = block
                max_height = block.index
        return max_block
    
    def mine_block(self,data,message,coin_base = 100,send_addr = None):
        nonce = 0
        difficulty = self.calc_difficulty()
        block = None
        while True:
            block = self.generate_block(data,message,nonce,difficulty,coin_base,send_addr)
            hashfnd = block.get_hash()
            bytes = ''.join(self.char_2_bin[x] for x in hashfnd)
            if bytes[:difficulty] == '0' * difficulty:
                
                print 'Mining complete.'
                
                break
            nonce += 1
        return block
    
    def generate_block(self,data,message,nonce,difficulty,coin_base,send_addr):
        parent_block = self.max_height_block
        block  = Block(parent_block,self.CONSENSUS_PROTOCOL_VERSION,data,message,nonce = nonce,difficulty = difficulty,coin_base = coin_base,send_addr = send_addr)
        return block
       
    def add_block_to_chain(self,new_block):
        parent_block = new_block.parent_block
        for block in self.chain:
            if block.get_hash() == new_block.get_hash():
                return False
            
        if self.is_block_valid(new_block,parent_block):
            new_height = new_block.index
            if self.max_height_block is not None and new_height <= self.max_height_block.index - self.MAX_CUT_HEIGHT:
                print("Unable to add block to chain since block is too far back from max height block.")
                return False
            self.chain.append(new_block)
            if self.max_height_block is None or new_height > self.max_height_block.index:
                self.max_height_block = new_block
            return True
        return False
            
       
    def is_block_valid(self,new_block,parent_block):
        if parent_block is None and new_block.index == 0 and self.hash_block_data(new_block) == new_block.get_hash():
            #it's a genesis block
            return True
        
        if parent_block.get_hash() != new_block.prev_hash:
            print("previous hash doesn't match...")
            return False
        if new_block.index != parent_block.index + 1:
            print("index mismatch...")
            return False
        if self.hash_block_data(new_block) != new_block.get_hash():
            print("new block hash doesn't match with hash of raw data. data is corrupted or tampered with...")
            return False
        if ''.join(self.char_2_bin[x] for x in new_block.get_hash())[:new_block.difficulty] != '0' * new_block.difficulty:
            print("new block hash is not mined properly..")
            return False
     
        
        return True
        
    def get_latest_block(self):
        return self.max_height_block
        
    
    def hash_block_data(self,block):
        return hashlib.sha256(block.prep_2_hash()).hexdigest()
    
    def is_blockchain_valid(self,chain,index = 0):
        print("Checking blockchain validity from block...")
        
        if index >= len(chain):
            print("Index out of bounds!!!")
            return False
        elif index < 0:
            print("Index can't be less than zero!!!")
            return False
        
        
        # check the genesis block
        if index == 0:
            index += 1
            if self.hash_block_data(chain[0]) != chain[0].get_hash():
                print("Genesis block hash doesn't match with hash of raw data. data is corrupted or tampered with...")
                print("\nBlockchain Invalid...")
                return False
            #print("Block Valid...")
          
      
        
        for i in range(index,len(chain)):
            if not self.is_block_valid(chain[i],chain[i].parent_block):
                print("invalid block found at index {}".format(i))
                print(chain[i].to_json())
                print("\nBlockchain Invalid...")
                return False
        print("BlockChain Succesfully Validated!!!")
        return True
    
    
        
    
    def replace_block_chain(self,new_chain = []):
        if self.is_blockchain_valid(chain = new_chain) and len(new_chain) > len(self.chain):
            new_chain = self.choose_chain_wrt_difficulty(new_chain,self.chain)
            self.chain.clear()
            self.chain = new_chain
            print("New BlockChain Added!!!!!")
            return True
        return False
    
    def append_block_chain(self,new_blocks = []):
        look_back = 0
        max_index = 0
        if len(self.chain) > self.MAX_CUT_HEIGHT:
            look_back = self.MAX_CUT_HEIGHT
        last_existing_chain = self.chain[-look_back:]
        appended_sub_chain = last_existing_chain + new_blocks
        if self.is_blockchain_valid(appended_sub_chain,index = 0):
            self.chain = self.chain + new_blocks
            for block in new_blocks:
                if max_index < block.index:
                    self.max_height_block = block
            print("New blocks added to the existing blockchain!")
            return True
        else:
            print("The new blocks aren't compatable with the existing blockchain!")
            return False
    
    def fetch_blocks_from_chain(self,index = 0):
        return self.chain[index:]
        
    
    def calc_difficulty(self):
        latest_block = self.max_height_block
        if latest_block is None:
            return self.DIFFICULTY
        if latest_block.index % self.diffculty_adj_interval == 0 and latest_block.index > 0:
            return self.adjust_difficulty(latest_block,self.chain)
        else:
            return latest_block.difficulty

    def adjust_difficulty(self,latest_block,chain):
        prev_adj_block = chain[len(chain) - self.diffculty_adj_interval]
        time_expected = self.block_gen_interval * self.diffculty_adj_interval
        time_spent = latest_block.timestamp - prev_adj_block.timestamp
        if time_spent > 2 * time_expected:
            return latest_block.difficulty - 1
        elif time_spent < time_expected / 2.:
            return latest_block.difficulty + 1
        else:
            return latest_block.difficulty

    # new block valid if its timestamp at most timestamp_validator seconds from timestamp of prev block
    def timestamp_valid(self,new_block,prev_block):
        return new_block.timestamp - prev_block.timestamp < self.timestamp_validator


    # chain validity
    def choose_chain_wrt_difficulty(self,chain1,chain2):
        chain1_cumm_diff = 0
        chain2_cumm_diff = 0
        for i in range(len(chain1)):
            chain1_cumm_diff += 2 ** chain1[i].difficulty
        for i in range(len(lenchain2)):
            chain2_cumm_diff += 2 ** chain2[i].difficulty
        if chain2_cumm_diff > chain1_cumm_diff:
            return chain2
        else:
            return chain1
    
    def to_dict(self):
        blocks_json = []
        for block in self.chain:
            blocks_json.append(block.to_dict())
        block_chain = {"block_chain" : blocks_json}
        return block_chain
    
    def to_json(self):
        return json.dumps(self.to_dict())

   