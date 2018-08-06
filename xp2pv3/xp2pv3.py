from twisted.internet.endpoints import TCP4ServerEndpoint
from twisted.internet.protocol import Protocol, Factory
from twisted.internet.endpoints import TCP4ClientEndpoint, connectProtocol
from twisted.internet.task import LoopingCall
from twisted.internet import reactor
from uuid import uuid4
import time,json
from threading import Thread,Lock
import enum
from blockchain3 import Block,BlockChain
from transaction import *
from utils import *
from wallets import *
import pickle
import random as rd
from portal import Portal
import os


class PeerType(enum.Enum):
    SERVER = 1
    CLIENT = 2

node_2_id_lookup = {}

def append_to_node_dict(name,node_id):
    hand = open("node_dicts.dit","a")
    hand.write("{},{}\n".format(name,node_id))
    hand.close()

def reload_node_dict():
    hand = open("node_dicts.dit","r")
    for line in hand:
        line = line.strip()
        splt = line.split(",")
        node_2_id_lookup[splt[1]] = splt[0]
    hand.close()

    

class XpeerFactory(Factory):
    def __init__(self,node,protocol_mode):
        self.node = node
        self.protocol_mode = protocol_mode
    def startFactory(self):
        self.peers = {}
        generate_nodeid = lambda: str(uuid4())
        self.nodeid = generate_nodeid()

    def buildProtocol(self, addr):
        return XpeerServerProtocol(self,self.node)
    

class XpeerServerProtocol(Protocol):
    def __init__(self, factory,node,conn_debug = False):
        self.PROTOCOL_VERSION = "1"
        self.node = node
        self.conn_debug = conn_debug
        self.nodename = self.node.node_name + "_server"
        self.factory = factory
        self.state = "HELLO"
        self.generate_nodeid = lambda: str(uuid4())
        self.remote_nodeid = None
        self.nodeid = self.factory.nodeid
        
        

    def connectionMade(self):
        remote_ip = self.transport.getPeer()
        host_ip = self.transport.getHost()
        self.remote_ip = remote_ip.host + ":" + str(remote_ip.port)
        self.host_ip = host_ip.host + ":" + str(host_ip.port)
   
        """
        print("==============================================")
        print("remote addr {}".format(self.remote_ip))
        print("host addr {}".format(self.host_ip))
        print "Connection from", self.transport.getPeer()
        print("==============================================")
        """
        if self.conn_debug:
            print "Connection from", self.transport.getPeer()

    def connectionLost(self, reason):
        if self.remote_nodeid in self.factory.peers:
            self.factory.peers.pop(self.remote_nodeid)
            self.node.curr_incoming_conns -= 1
            self.node.Portal.update_connections_count(self.node.curr_outgoing_conns,self.node.curr_incoming_conns)
        if self.conn_debug:
            reload_node_dict()
            print node_2_id_lookup[self.remote_nodeid], "disconnected"

    def dataReceived(self, data):
        #print "DATA IS SERVER " + data
        for line in data.splitlines():
            line = line.strip()
            msgtype = json.loads(line)['msgtype']
            if self.state == "HELLO" and msgtype == "hello":
                self.handle_hello(line)
                self.state = "READY"
            elif msgtype == "helloback":
                self.handle_hello_back(line)
            elif msgtype == "ping":
                self.handle_ping(line)
            
            elif msgtype == "getmoreaddr":
                self.handle_getaddr()
            elif msgtype == "addr":
                self.handle_addr(json.loads(line)['peers'])
            elif msgtype == "finalize":
                self.sync_with_node(line)
                
            elif msgtype == "new_block":
                self.add_block_to_chain(json.loads(line)['block'],json.loads(line)['owner'])
            elif msgtype == "init_bc_request":
                self.send_latest_blockchain(json.loads(line)['myname'])
            elif msgtype == "latest_blocks_request":
                self.send_blocks_to_client(json.loads(line)['index'],json.loads(line)['myname'])
                
            elif msgtype == "rqst_tx_pool":
                self.send_tx_pool_to_client(json.loads(line)['myname'])
            elif msgtype == "new_tx":
                self.handle_new_tx(json.loads(line)['tx'])
    
    def handle_hello(self, hello):
        hello = json.loads(hello)
        self.remote_nodeid = hello["nodeid"]
        sender_server_ip,sender_server_id = hello["myserveraddr"]
        if sender_server_id == self.nodeid:
            if self.remote_nodeid is not None and self.conn_debug:
                reload_node_dict()
                print("{} RECEIVED HELLO FROM {}".format(self.nodename,node_2_id_lookup[self.remote_nodeid]))
            if self.conn_debug:
                print "Connected to myself {}".format(self.nodename)
            self.transport.loseConnection()
            self.node.curr_outgoing_conns -= 1
        else:
            if self.remote_nodeid is not None and str(self.remote_nodeid) not in self.factory.peers:
                if self.conn_debug:
                    reload_node_dict()
                    print("{} RECEIVED HELLO FROM {}".format(self.nodename,node_2_id_lookup[self.remote_nodeid]))
                reload_node_dict()
                print("New Remote Node {} Added in {}'s Node!!".format(node_2_id_lookup[self.remote_nodeid],self.nodename))
                self.node.curr_incoming_conns += 1
                self.node.Portal.update_connections_count(self.node.curr_outgoing_conns,self.node.curr_incoming_conns)
             
            if str(self.remote_nodeid) not in self.factory.peers:
                self.factory.peers[str(self.remote_nodeid)] = self
                self.send_hello_back()
                
            
            
    def sync_with_node(self,finalize):
        
        finalize = json.loads(finalize)
        sender_server_ip,sender_server_id = finalize["myserveraddr"]
        if self.node.curr_outgoing_conns < self.node.MAX_OUTGOING_CONN and (sender_server_ip,sender_server_id) not in self.node.connected_servers:
            host,port = sender_server_ip.split(":")
            point = TCP4ClientEndpoint(reactor, str(host), int(port))
            xpr = XpeerClientProtocol(None,self.node)
            self.node.xpeerprotocols.append(xpr)
            d = connectProtocol(point,xpr)
            d.addCallback(self.node.gotProtocol)
            self.node.curr_outgoing_conns += 1
            self.node.Portal.update_connections_count(self.node.curr_outgoing_conns,self.node.curr_incoming_conns)
        elif self.node.curr_outgoing_conns >= self.node.MAX_OUTGOING_CONN:
            reload_node_dict()
            print("{} REACHED MAX OUTGOING CONNECTION.".format(self.nodename))
        

    def send_hello_back(self):
        if self.remote_nodeid is not None and self.conn_debug:
            reload_node_dict()
            print("{} SENDING HELLO BACK TO {}".format(self.nodename,node_2_id_lookup[self.remote_nodeid]))
        hello = json.dumps({'nodeid': str(self.nodeid),'serverip': str(self.host_ip),'msgtype': 'helloback'})
        self.transport.write(hello + "\n")
    
    def handle_getaddr(self):
        self.send_addr()
        
    def send_addr(self):
        if self.remote_nodeid is not None and self.conn_debug:
            reload_node_dict()
            print("{} SENDING MORE ADDR TO {}".format(self.nodename,node_2_id_lookup[self.remote_nodeid]))
        now = time.time()
        peers = self.node.connected_servers
        addr = json.dumps({'msgtype': 'addr', 'peers': peers})
        self.transport.write(addr + "\n")
        
    
    def send_pong(self):
        pong = json.dumps({'msgtype': 'pong'})
        self.transport.write(pong + "\n")

    def handle_ping(self, ping):
        self.send_pong()
    
    
    def close_connection(self):
        self.transport.loseConnection()

    
    def send_latest_blockchain(self,name):
        print("Sending Block chain to {}...".format(name))
        bc_serial = pickle.dumps(self.node.block_chain)
        data = json.dumps({'msgtype' : 'bc_response','data' : bc_serial})
        self.transport.write(data + "\n")
    def send_blocks_to_client(self,index,name):
        print("Sending Latest Blocks to {}...".format(name))
        if self.node.block_chain is not None:
            blocks = self.node.block_chain.fetch_blocks_from_chain(index = index)
            bc_serial = pickle.dumps(blocks)
            data = json.dumps({'msgtype' : 'lb_response','data' : bc_serial})
            self.transport.write(data + "\n")
        
        
        
        
    def add_block_to_chain(self,block,owner):
        block = pickle.loads(block)
        if owner != self.node.node_name:
            print("New block Received...")
            self.node.Portal.update_debugger("New block Received...")
            
            #validate the txs in block
             
       
            valid_txs,fees = self.node.tx_handler.handle_txs(block.txs,self.node.transaction_pool,tx_fee_pool = self.node.tx_fee_pool)
            
        
        
            if len(valid_txs) != len(block.txs):
                print("Block Contains Invalid Transactions. Block rejected!!")
                return
            
         
        
        
            if self.node.block_chain.add_block_to_chain(block):
                with open("{}_blockchain.bc".format(self.node.node_name),"wb") as handle:
                    pickle.dump(self.node.block_chain,handle)
                print("Block Added To Blockchain...")
                print("Forwarding Block To Peers...")
                self.node.Portal.update_debugger("Block Added To Blockchain...")
                self.node.Portal.update_debugger("Forwarding Block To Peers...")
                
                #print "block chain txhandler utxopool len " + str(len(self.node.block_chain.txhandler.utxopool.utxos))
                #print "Node utxopool len " + str(len(self.node.utxopool.utxos))
                #print "TX id is " + valid_txs[0].txid
                
                
               
                self.node.utxopool = self.node.tx_handler.utxopool
                self.node.wallet_manager.utxopool = self.node.utxopool
                self.node.confirmed_utxopool = self.node.tx_handler.conf_utxopool
                self.node.add_to_conf_utxopool(block)
                
                chain_len = len(self.node.block_chain.chain)
                size = os.path.getsize("{}_blockchain.bc".format(self.node.node_name))
                num_utxos = len(self.node.utxopool.utxos)
                self.node.num_txs += len(block.txs)
                self.node.Portal.update_blockchain_info(chain_len,int(size),self.node.num_txs,num_utxos,self.node.num_blk_mined)
                self.node.Portal.update_blockchain_gui(block.index,block.hash)
                
                
                self.node.wallet_manager.conf_utxopool = self.node.confirmed_utxopool
                self.node.new_block_received = True
                self.node.wallet_manager.update_utxopool_on_wallet()
                self.node.wallet_manager.update_all_wallets_account_balance()
                for t in block.txs:    
                    try:
                        self.node.transaction_pool.remove(t)
                    except:
                        continue
                        
                reactor.callFromThread(self.node.send_block_via_clients,block)
               
        else:
            print("The Block Received is Owned By This Node!!")
        
    
    
  
    
    def send_tx_pool_to_client(self,name):
        print("sending tx pools to {}".format(name))
        self.node.Portal.update_debugger("sending tx pools to {}".format(name))
        txpool = pickle.dumps(self.node.transaction_pool)
        data = json.dumps({'msgtype' : 'tx_pool_response','data' : txpool})
        self.transport.write(data + "\n")
        
    def handle_new_tx(self,tx):
        tx_unloaded = pickle.loads(tx)
        print "handling new tx\n"
        
        self.node.tx_handler.utxopool = self.node.utxopool
        self.node.tx_handler.conf_utxopool = self.node.confirmed_utxopool
        valid_txs,fees = self.node.tx_handler.handle_txs([tx_unloaded],self.node.transaction_pool)
        
        self.node.utxopool = self.node.tx_handler.utxopool
        self.node.confirmed_utxopool = self.node.tx_handler.conf_utxopool
        if len(valid_txs) > 0:
            if valid_txs[0] not in self.node.transaction_pool:
                self.node.add_to_permanent_tx_pool(valid_txs)
                self.node.tx_fee_pool += fees
                self.node.wallet_manager.utxopool = self.node.tx_handler.utxopool
                self.node.wallet_manager.update_utxopool_on_wallet()
                self.node.wallet_manager.update_all_wallets_account_balance()
                

                self.node.transaction_pool.append(valid_txs[0])
                
                total = 0
                #if tx holds this nodes public key 
                for txout in valid_txs[0].txOuts:
                    for wallet in self.node.wallet_manager.wallets:
                        if wallet.public_addr == txout.address:
                            total += txout.amount
                            break
               
                if total > 0:
                    date = datetime.datetime.fromtimestamp(int(time.time())).strftime('%Y-%m-%d %H:%M:%S')
                    self.node.wallet_manager.set_tx_history(date,total)
                
                
                print("New Tx Added Sucessfully!!!")
                self.node.Portal.update_debugger("New Tx Added Sucessfully!!!")
                reactor.callFromThread(self.node.send_tx_via_clients,tx_unloaded)
            

        else:
            print("Invalid Tx Imported!")
            self.node.Portal.update_debugger("Invalid Tx Imported!")
            
            
class XpeerClientProtocol(Protocol):
    
    def __init__(self, factory,node,conn_debug = False):
        self.PROTOCOL_VERSION = "1"
        self.node = node
        self.conn_debug = conn_debug
        self.nodename = self.node.node_name + "_client"
        self.factory = factory
        generate_nodeid = lambda: str(uuid4())
        self.nodeid = generate_nodeid()
        node_2_id_lookup[self.nodeid] = self.nodename + "_client"
        append_to_node_dict(self.nodename + "_client",self.nodeid)
        self.remote_nodeid = None
        self.lc_ping = LoopingCall(self.send_ping)
        self.last_successful_ping = None
        
    
    def dataReceived(self, data):
        #print "DATA IS " + data
        for line in data.splitlines():
            line = line.strip()
            msgtype = json.loads(line)['msgtype']
            if msgtype == "helloback":
                self.handle_hello_back(line)
            elif msgtype == "ping":
                self.handle_ping(line)
            elif msgtype == "pong":
                self.handle_pong(line)
            elif msgtype == "addr":
                self.handle_addr(json.loads(line)['peers'])
                
            elif msgtype == "bc_response":
                self.handle_blockchain_download(json.loads(line)['data'])
            elif msgtype == "lb_response":
                self.handle_latestblocks_download(json.loads(line)['data'])
                
            elif msgtype == "tx_pool_response":
                self.handle_tx_pool_download(json.loads(line)['data'])
    
    def send_hello(self):
        if self.conn_debug:
            reload_node_dict()
            print("{} SENDING HELLO".format(self.nodename))
        hello = json.dumps({'nodeid': str(self.nodeid),'myserveraddr' : [self.node.node_server_ip,self.node.node_server_id],'myname' : self.nodename, 'msgtype': 'hello'})
        self.transport.write(hello + "\n")
        
    def handle_hello_back(self,hello):
        hello = json.loads(hello)
        self.remote_nodeid = hello["nodeid"]
        self.remote_ip = hello["serverip"]
        
        if self.remote_nodeid is not None and self.conn_debug:
            reload_node_dict()
            print("{} RECEIVED HELLO BACK FROM {}".format(self.nodename,node_2_id_lookup[self.remote_nodeid]))
            
        
        if (self.remote_ip,self.remote_nodeid) not in self.node.connected_servers:
            self.node.connected_servers.append((self.remote_ip,self.remote_nodeid))

        if (self.remote_ip,self.remote_nodeid) not in self.node.all_servers:
            self.node.all_servers.append((self.remote_ip,self.remote_nodeid))
            
        
        self.send_getaddr()
            
    
                
    def send_getaddr(self):
        if self.remote_nodeid is not None and self.conn_debug:
            reload_node_dict()
            print("{} REQUESTING MORE ADDR FROM {}".format(self.nodename,node_2_id_lookup[self.remote_nodeid]))
        moreaddr = json.dumps({'msgtype': 'getmoreaddr'})
        self.transport.write(moreaddr + "\n")
    
    def handle_addr(self,peers):
        if self.remote_nodeid is not None and self.conn_debug:
            reload_node_dict()
            print("{} EXTRACTING ADDR FROM {}".format(self.nodename,node_2_id_lookup[self.remote_nodeid]))
        
        
        if peers is not None:
            for remote_ip, remote_nodeid in peers:
                if (remote_ip, remote_nodeid) not in self.node.connected_servers and str(remote_nodeid) != self.node.node_server_id and self.node.curr_outgoing_conns < self.node.MAX_OUTGOING_CONN:
                    
                    host, port = str(remote_ip).split(":")
                    point = TCP4ClientEndpoint(reactor, str(host), int(port))
                    xpr = XpeerClientProtocol(None,self.node)
                    self.node.xpeerprotocols.append(xpr)
                    d = connectProtocol(point,xpr)
                    d.addCallback(self.node.gotProtocol)
                    self.node.curr_outgoing_conns += 1
                    self.node.Portal.update_connections_count(self.node.curr_outgoing_conns,self.node.curr_incoming_conns)
      
                elif self.node.curr_outgoing_conns >= self.node.MAX_OUTGOING_CONN:
                    reload_node_dict()
                    print("{} REACHED MAX OUTGOING CONNECTION.".format(self.nodename))
                    
        
        #after conn is complete send my server info to server i'm connected to so it can connect to my server
        finalize = json.dumps({'myserveraddr' : [self.node.node_server_ip,self.node.node_server_id],'myname' : self.nodename, 'msgtype': 'finalize'})
        self.transport.write(finalize + "\n")
        
        self.lc_ping.start(60 * 3)
        
        
        self.send_init_blockchain_request()
     
    
    
        
    def send_ping(self):
        if self.last_successful_ping is not None and time.time() - self.last_successful_ping > 60 * 60:
            self.lc_ping.stop()
            self.node.curr_outgoing_conns -= 1
            return
        ping = json.dumps({'msgtype': 'ping'})
        if self.remote_nodeid is not None and self.conn_debug:
            reload_node_dict()
            print self.nodename,"Pinging", node_2_id_lookup[self.remote_nodeid]
        self.transport.write(ping + "\n")
   
    def handle_pong(self, pong):
        if self.remote_nodeid is not None and self.conn_debug:
            reload_node_dict()
            print self.nodename,"got pong from", node_2_id_lookup[self.remote_nodeid]
        self.last_successful_ping = time.time()
        
    def close_connection(self):
        self.transport.loseConnection()
        
    #new code
    
    def send_init_blockchain_request(self):
        if self.node.first_time and not self.node.requesting_bc:
            print("Requesting BlockChain From Peers...")
            self.node.Portal.update_debugger("Requesting BlockChain From Peers...")
            self.node.Portal.set_status_text("Init Blockchain Sync...")
            mess_bc = json.dumps({'msgtype' : 'init_bc_request','myname' : self.nodename})
            self.transport.write(mess_bc  + "\n")
            self.node.requesting_bc = True
        elif not self.node.first_time and not self.node.requesting_bc:
            print("Requesting latest Blocks From Peers...")
            self.node.Portal.update_debugger("Requesting latest Blocks From Peers...")
            mess_bc = json.dumps({'msgtype' : 'latest_blocks_request','index' : len(self.node.block_chain.chain),'myname' : self.nodename})
            self.transport.write(mess_bc  + "\n")
            self.node.requesting_bc = True
            
    def handle_latestblocks_download(self,serial_blocks):
        
        blocks = pickle.loads(serial_blocks)
        if len(blocks) > 0:
            print("Download Complete!!!")
            self.node.Portal.update_debugger("Download Complete!!!")
            if self.node.block_chain.append_block_chain(blocks):
                print("Blocks Added to the blockchain Successfully!!")
                self.node.Portal.update_debugger("Blocks Added to the blockchain Successfully!!")
                self.node.Portal.set_status_text("Blockchain Synchronized Sucessfully!!")
                self.node.requesting_bc = False
                self.node.block_chain_uptodate = True
                with open("{}_blockchain.bc".format(self.node.node_name),"wb") as handle:
                    pickle.dump(self.node.block_chain,handle)
                
                self.node.update_display_on_bc_update(blocks)
            
                
                # display the last three blockchain
                self.node.Portal.reset_blockchain_gui()
                last_blocks = self.node.block_chain.chain[-3:]
                for blk in last_blocks:
                    self.node.Portal.update_blockchain_gui(blk.index,blk.hash)
                
                
                
            else:
                self.node.requesting_bc = False
                # select another client to send request
                print("Invalid Blocks Found. Trying From Other Peers...")
                self.node.Portal.update_debugger("Invalid Blocks Found. Trying From Other Peers...")
                self.node.Portal.update_debugger("BlockChain Validated!!")
                peers = self.node.xpeerprotocols
                while True:
                    if len(peers) <= 1:
                        break
                    ix = int(rd.random() * len(peers))
                    client = peers[ix]
                    if client.nodename != self.nodename:
                        self.send_init_blockchain_request()
                    break
        else:
            print("No New Blocks Available!!!")
            self.node.Portal.update_debugger("No New Blocks Available!!!")
            self.node.block_chain_uptodate = True
            
        
        
        
    def handle_blockchain_download(self,serial_bc):
        print("Download Complete!!!")
        self.node.Portal.update_debugger("Download Complete!!!")
        temp_bc = pickle.loads(serial_bc)
        
            
        block_chain = BlockChain(self.node.tx_handler,chain = temp_bc.chain)
        print("Checking BlockChain Integrity...")
        self.node.Portal.update_debugger("Checking BlockChain Integrity...")
        if block_chain.is_blockchain_valid(block_chain.chain,index = 0):
            print("BlockChain Validated!!")
            self.node.Portal.update_debugger("BlockChain Validated!!")
            self.node.block_chain = block_chain
            self.node.first_time = False
            self.node.requesting_bc = False
            self.node.block_chain_uptodate = True
            with open("{}_blockchain.bc".format(self.node.node_name),"wb") as handle:
                pickle.dump(block_chain,handle)
            self.node.Portal.set_status_text("Blockchain Synchronized Sucessfully!!")
            self.node.update_display_on_bc_update(self.node.block_chain.chain)
            
            #display the last three blockchain
            last_blocks = self.node.block_chain.chain[-3:]
            for blk in last_blocks:
                self.node.Portal.update_blockchain_gui(blk.index,blk.hash)
            
            
            
            
            
        else:
            self.node.requesting_bc = False
            # select another client to send request
            print("BlockChain Invalid!!")
            self.node.Portal.update_debugger("BlockChain Invalid!!")
            peers = self.node.xpeerprotocols
            while True:
                if len(peers) <= 1:
                    break
                ix = int(rd.random() * len(peers))
                client = peers[ix]
                if client.nodename != self.nodename:
                    self.send_init_blockchain_request()
                break
                
    def broadcast_block(self,block):
        blk_serial = pickle.dumps(block)
        msg = json.dumps({"msgtype" : "new_block" ,"owner" : self.node.node_name, "block" : blk_serial})
        self.transport.write(msg + "\n")
        
    
    def send_tx_pool_request(self):
        msg = json.dumps({"msgtype" : "rqst_tx_pool" ,"myname" : self.nodename})
        self.transport.write(msg + "\n")
        
    def broadcast_new_tx(self,tx):
        tx_serial = pickle.dumps(tx)
        msg = json.dumps({"msgtype" : "new_tx", "tx" : tx_serial,"myname" : self.nodename})
        self.transport.write(msg + "\n")
        
    def handle_tx_pool_download(self,serial_tx):
        tx_pool = pickle.loads(serial_tx_pool)
        valid_txs,fees = self.node.tx_handler.handle_txs(tx_pool)
        self.node.wallet_manager.update_utxopool_on_wallet()
        self.node.wallet_manager.update_all_wallets_account_balance()
        if len(valid_txs) > 0:
            self.node.transaction_pool = valid_txs
            self.node.requesting_tx_pool = True
            print("Transaction pool imported Successfully!!!")
            self.node.Portal.update_debugger("Transaction pool imported Successfully!!!")
            
        else:
            self.node.requesting_tx_pool = False
            print("Transaction pool import failed!! trying again...")
            self.node.Portal.update_debugger("Transaction pool import failed!! trying again...")
            peers = self.node.xpeerprotocols
            while True:
                if len(peers) <= 1:
                    break
                ix = int(rd.random() * len(peers))
                client = peers[ix]
                if client.nodename != self.nodename:
                    self.send_tx_pool_request()
                break
                

                
                
                
                
"""
parameters

MAX_INCOMING_CONN - maximum number of peers can connect to this node (-1 is infinite)
MAX_OUTGOING_CONN - maximum number of peers this node can connect to. (-1 is infinite)

"""
class Node:
    
    def __init__(self,node_name,first_time = False,genesis = False,Portal = None):
        
       
        
        self.first_time = first_time
        self.genesis = genesis
        self.requesting_bc = False
        self.block_chain = None
        self.block_chain_uptodate = False
        self.Portal = Portal
        
        
        if not first_time and not genesis:
            with open("{}_blockchain.bc".format(node_name),"rb") as handle:
                self.block_chain = pickle.load(handle)
            
            
        Thread(target=self.mine_block, args=()).start() 
            
        
        self.xpeerprotocols = []
        self.connected_servers = []
        self.all_servers = []
        self.MAX_INCOMING_CONN = -1 
        self.MAX_OUTGOING_CONN = 10
        self.curr_incoming_conns = 0
        self.curr_outgoing_conns = 0
        self.node_server_ip = ""
        self.node_server_id = ""
        self.node_name = node_name
        
        
      
        self.NUM_BLK_CONFIRM = 1 # how many blocks should extend to current block that contains utxo, so that it can be spent
        self.lock = Lock()
        self.new_block_received = False # used to stop current mining process if new block is received
        self.settings = Settings(self.node_name,init_sets = {'txfee' : 0.05})
        self.utxopool = UTXOpool()
        self.confirmed_utxopool = UTXOpool()
        self.wallet_manager = WalletManager(self.utxopool,self.confirmed_utxopool,self.node_name,self.Portal)
        self.wallet_manager.MAX_TX_FEE = self.settings.load_settings()['txfee']
        self.master_wallet = None
        self.wallet_manager.load_wallets()
        
        if len(self.wallet_manager.wallets) == 0:
            self.master_wallet = self.wallet_manager.create_wallet("master_wallet")
        else:
            self.master_wallet = self.wallet_manager.wallets[0]
            
        self.tx_handler = TxHandler(self.utxopool,self.confirmed_utxopool,self.master_wallet.public_addr)
        self.transaction_pool = []
        self.permanent_tx_pool = []
        self.tx_fee_pool = []
        self.requesting_tx_pool = False
        
        self.Portal.write_node_name(self.node_name)
        self.Portal.set_status_text("")
        self.Portal.update_connections_count(self.curr_outgoing_conns,self.curr_incoming_conns)
        self.Portal.display_wallet(self.wallet_manager)
        self.Portal.display_wallet_table(self.wallet_manager)
        self.Portal.load_settings(self.settings,self.wallet_manager)
        
        self.num_txs = 0
        self.num_blk_mined = 0
        
        # update all data
        if not first_time and not genesis:
            self.update_display_on_bc_update(self.block_chain.chain)
            self.Portal.display_wallet(self.wallet_manager)
            self.Portal.display_wallet_table(self.wallet_manager)
            
        if genesis:
            self.block_chain = BlockChain(self.tx_handler)
            
        
       
    
   
    def update_display_on_bc_update(self,blks):
        size = os.path.getsize("{}_blockchain.bc".format(self.node_name))
        self.num_txs = 0
        self.num_blk_mined = 0

        wals_num = len(self.wallet_manager.wallets)

        for blk in blks:
            self.num_txs += len(blk.txs)

            last_tx = blk.txs[-1]
            if wals_num > 0:
                if last_tx.txtype == 'COINBASE':
                    if last_tx.txOuts[0].address == self.wallet_manager.wallets[0].public_addr:
                        self.num_blk_mined += 1
                    self.tx_handler.handle_txs(blk.txs,test_validity = False)         


        self.utxopool = self.tx_handler.utxopool
        
        #update conf utxopool
        for blk in blks:
            self.add_to_conf_utxopool(blk)
        
        num_utxos = len(self.utxopool.utxos)
        chain_len = len(self.block_chain.chain)

        self.Portal.update_blockchain_info(chain_len,int(size),self.num_txs,num_utxos,self.num_blk_mined)
        last_blocks = self.block_chain.chain[-3:]
        for blk in last_blocks:
            self.Portal.update_blockchain_gui(blk.index,blk.hash)
        self.wallet_manager.utxopool = self.utxopool
        self.wallet_manager.conf_utxopool = self.confirmed_utxopool
        self.wallet_manager.update_utxopool_on_wallet()
        self.wallet_manager.update_all_wallets_account_balance()
        self.wallet_manager.load_tx_history_local()
        
    
    
    def add_to_tx_pool(self,txs):
        for tx in txs:
            self.transaction_pool.append(tx)
    def add_to_permanent_tx_pool(self,txs):
        for tx in txs:
            self.permanent_tx_pool.append(tx)
    def send_tx_via_clients(self,tx):
        print("Broadcasting Tx to Peers")
        for client in self.xpeerprotocols:
            client.broadcast_new_tx(tx)
            
    def add_to_conf_utxopool(self,new_block):
        block = new_block
        for i in range(self.NUM_BLK_CONFIRM):
            block = block.parent_block
            
        if block is not None:
            txs = block.txs
            for tx in txs:
                for i in range(len(tx.txOuts)):
                    utxo = UTXO(tx.txid,i)
                    if self.utxopool.is_utxo_in_pool(utxo):
                        self.confirmed_utxopool.add_to_pool(utxo,tx.txOuts[i])
                       
            
                
    
    
    def send_block_via_clients(self,block):
        print("Broadcasting Block To Peers...")
        self.Portal.update_debugger("Broadcasting Block To Peers...")
        for client in self.xpeerprotocols:
            client.broadcast_block(block)
            
    def mine_block(self):
        while True:
            if self.block_chain_uptodate or self.genesis:
                # mine block
                if self.block_chain is not None:
                    
                    txs = self.tx_handler.org_txs_for_block(self.transaction_pool,self.tx_fee_pool)
                   
                    
                    block = self.block_chain.mine_block(txs,self.node_name + "'s message",coin_base = 100,send_addr = None)
                    
                    
                    # if new block received before mining this then. start over
                    if self.new_block_received:
                        self.new_block_received = False
                        continue
                        
                    
                    if self.block_chain.add_block_to_chain(block):
                        
                        with self.lock:
                            tx_coinbase = txs[-1]
                            self.utxopool.add_to_pool(UTXO(tx_coinbase.txid,0),tx_coinbase.txOuts[0],txtype = 'coinbase')
                            #chk if there is any fee tx
                            for tx in txs:
                                if tx.txtype == "FEE":
                                    self.utxopool.add_to_pool(UTXO(tx.txid,0),tx.txOuts[0],txtype = 'fee')
                                    print 
                            self.add_to_conf_utxopool(block)
                            
                            self.wallet_manager.utxopool = self.utxopool
                            self.wallet_manager.conf_utxopool = self.confirmed_utxopool
                            self.wallet_manager.update_utxopool_on_wallet()
                            self.wallet_manager.update_all_wallets_account_balance()

                            for t in txs[:-1]:
                                try: 
                                    
                                    self.transaction_pool.remove(t)
                                    
                                except:
                                    continue
                        
                        
                        
                        print("Block Mined...")
                        self.Portal.update_debugger("Block Mined...")
                        reactor.callFromThread(self.send_block_via_clients,block)
                        with open("{}_blockchain.bc".format(self.node_name),"wb") as handle:
                            pickle.dump(self.block_chain,handle)
                        
                        chain_len = len(self.block_chain.chain)
                        size = os.path.getsize("{}_blockchain.bc".format(self.node_name))
                        num_utxos = len(self.utxopool.utxos)
                        self.num_blk_mined += 1
                        self.num_txs += len(txs)
                        self.Portal.update_blockchain_info(chain_len,int(size),self.num_txs,num_utxos,self.num_blk_mined)
                        self.Portal.update_blockchain_gui(block.index,block.hash)
                        
                        
                        time.sleep(10)
                
        
    
    def close_all_connections(self):
        if len(self.xpeerprotocols) > 0:
            for protocol in self.xpeerprotocols:
                protocol.close_connection()
    def gotProtocol(self,p):
        """The callback to start the protocol exchange. We let connecting
        nodes start the hello handshake""" 
        p.send_hello()
    def start_node(self,port,other_ports):
        # node server
        endpoint = TCP4ServerEndpoint(reactor, port)
        xps = XpeerFactory(self,PeerType.SERVER)
        endpoint.listen(xps)
        self.node_server_ip = "127.0.0.1:{}".format(port)
        self.node_server_id = xps.nodeid
        self.all_servers.append((self.node_server_ip,self.node_server_id))
        node_2_id_lookup[xps.nodeid] = self.node_name+"_server"
        # node client
        # bootstraping
        
        for prt in other_ports:
            point = TCP4ClientEndpoint(reactor, "localhost", prt)
            xppr = XpeerClientProtocol(None,self)
            self.xpeerprotocols.append(xppr)
            d = connectProtocol(point, xppr)
            d.addCallback(self.gotProtocol)
            self.curr_outgoing_conns += 1
            self.Portal.update_connections_count(self.curr_outgoing_conns,self.curr_incoming_conns)
    def get_curr_in_conn(self):
        return self.curr_incoming_conns
    def get_curr_out_conn(self):
        return self.curr_outgoing_conns
        
    
    
    