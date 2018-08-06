import sys
from blockchain3 import Block,BlockChain
from xp2pv3 import xp2pv3
from xp2pv3.portal import Portal

from transaction import *
from utils import *
from wallets import *
from threading import Thread,Lock
import datetime
import time
import sys
from QT_UI import imgs_rc
from PyQt5 import QtCore, QtGui, uic , QtWidgets
from PyQt5.QtCore import QThread



#GUI

qtCreatorFile = "QT_UI/main_node_page.ui"
qtCreatorFile2 = "QT_UI/block_detail_dialog.ui"

 
Ui_MainWindow, QtBaseClass = uic.loadUiType(qtCreatorFile)
Ui_dialog, QtBaseClass2 = uic.loadUiType(qtCreatorFile2)

class BlockDetailDialog(QtWidgets.QDialog, Ui_dialog):
    def __init__(self,block,parent = None):
        QtWidgets.QDialog.__init__(self,parent)
        Ui_dialog.__init__(self)
        self.setupUi(self)
        
        self.display_info(block)
        
        
    def display_tx(self,block):

        curr_tx_ix = int(str(self.comb_txs.currentText()).split(" ")[1])
        
        tx = block.txs[curr_tx_ix - 1]
       
        txins = tx.txIns
        txouts = tx.txOuts
        
        row1 = len(txins)
        row2 = len(txouts)
        
        tb1cnter = 0
        tb2cnter = 0
        
        for i in range(self.tbl_blkd_consumed_coins.rowCount()):
            self.tbl_blkd_consumed_coins.removeRow(i)
        
        for i in range(self.tbl_blkd_created_coins.rowCount()):
            self.tbl_blkd_created_coins.removeRow(i)
        
        self.tbl_blkd_consumed_coins.setRowCount(3)
        self.tbl_blkd_created_coins.setRowCount(3)
        
        if row1 > 3:
            self.tbl_blkd_consumed_coins.setRowCount(row1)
        if row2 > 3:
            self.tbl_blkd_created_coins.setRowCount(row2)
            
        for txin in txins:
            self.tbl_blkd_consumed_coins.setItem(tb1cnter, 0, QtWidgets.QTableWidgetItem(txin.txoutid))
            self.tbl_blkd_consumed_coins.setItem(tb1cnter, 1, QtWidgets.QTableWidgetItem(str(txin.txoutix)))
            tb1cnter += 1
        
        for txout in txouts:
            self.tbl_blkd_created_coins.setItem(tb2cnter, 0, QtWidgets.QTableWidgetItem(str(txout.amount)))
            self.tbl_blkd_created_coins.setItem(tb2cnter, 1, QtWidgets.QTableWidgetItem(txout.address))
            tb2cnter += 1
        
    
    def display_info(self,block):
        
        conv = lambda s:"<html><head/><body><p><span style=' color:#186530;'>{}</span></p></body></html>".format(s)
       
        self.lbl_blkd_hash.setText(conv(block.hash))
        self.lbl_blkd_ix.setText(conv(block.index))
        self.lbl_blkd_diff.setText(conv(block.difficulty))
        self.lbl_blkd_nonce.setText(conv(block.nonce))
        self.lbl_blkd_prevhash.setText(conv(block.prev_hash))
        time = datetime.datetime.fromtimestamp(int(block.timestamp)).strftime('%Y-%m-%d %H:%M:%S')
        self.lbl_blkd_cdate.setText(conv(time))
        self.lbl_blkd_cbase.setText(conv(str(block.coin_base) + " DCN"))
        self.lbl_blkd_addr.setText(conv(block.txs[-1].txOuts[-1].address))
        
        # display txs
        
        self.tbl_blkd_consumed_coins.setRowCount(3)
        self.tbl_blkd_created_coins.setRowCount(3)
     
     
        
        
        txs = block.txs
        
        #display txs in combo box
        cnt = 1
        for tx in txs:
            self.comb_txs.addItem("Transaction {}".format(cnt))
            cnt += 1
        
        self.display_tx(block)
        
        self.comb_txs.currentIndexChanged.connect(lambda: self.display_tx(block))


class MyApp(QtWidgets.QMainWindow, Ui_MainWindow):
    def __init__(self):
        QtWidgets.QMainWindow.__init__(self)
        Ui_MainWindow.__init__(self)
        self.setupUi(self)
        
        
        #self.tbl_tx_hist.setSortingEnabled(True)
        self.tbl_tx_hist.sortItems(0, order = QtCore.Qt.DescendingOrder)
        
        #transaction page wallets management
        self.wal_2_tx = {}
        
        self.lbl_blk1_details.mousePressEvent = self.details_click1
        self.lbl_blk2_details.mousePressEvent = self.details_click2
        self.lbl_blk3_details.mousePressEvent = self.details_click3
        self.btn_blk_srch.mousePressEvent = self.show_blk_dialog_srch
        self.btn_send_money.mousePressEvent = self.send_money
        self.btn_create_wal.mousePressEvent = self.add_wallet
        self.btn_update_sets.mousePressEvent = self.save_txfee_settings
        self.lst_wallets.itemPressed.connect(self.wallet_item_pressed)
        self.txt_recepts.textChanged.connect(self.txtrecept_txtchanged)
        
        
    def txtrecept_txtchanged(self):
        wal_name = str(self.lst_wallets.currentItem().text()).split(" ")[0]
        self.wal_2_tx[wal_name] = str(self.txt_recepts.toPlainText())
        
    def wallet_item_pressed(self):
        wal_name = str(self.lst_wallets.currentItem().text()).split(" ")[0]
        try:
            txs = self.wal_2_tx[wal_name]
            self.txt_recepts.setPlainText(txs)
        except:
            self.txt_recepts.clear()
            return
            
    def build_txsheet(self):
        #build transaction sheet by accessing the lists and tables
        node = Portal.node
        txsheet = {}
        checked_wallets = []
        check_wallets_pubk = []
        
        #sample {str(node2.master_wallet.public_addr) : [[str(node1.master_wallet.public_addr),30]]}
        for index in range(self.lst_wallets.count()):
            if self.lst_wallets.item(index).checkState() == QtCore.Qt.Checked:
                wal_name = str(self.lst_wallets.item(index).text()).split(" ")[0]
                checked_wallets.append(wal_name)
                for wallet in node.wallet_manager.wallets:
                    if wallet.wallet_name == wal_name:
                        check_wallets_pubk.append(wallet.public_addr)
                        break
                
                
        ix = 0                
        for cwallet in checked_wallets:
            try:
                reps = self.wal_2_tx[cwallet]
                try:
                    reps_lines = reps.split("\n")
                    reps_arged = []
                    for rep_line in reps_lines:
                        addr,amnt = rep_line.split(" ")
                        reps_arged.append([addr,float(amnt)])
                except:
                    return None
                txsheet[check_wallets_pubk[ix]] = reps_arged
                ix += 1
            except:
                ix += 1
                continue
            
        
        
        
        
           
        
        
        
        return txsheet
    
    def send_money(self,event):
        node = Portal.node
        node.wallet_manager.utxopool = node.utxopool
        node.wallet_manager.update_utxopool_on_wallet()
        tx_sheet = self.build_txsheet()
        print tx_sheet
        if tx_sheet is None:
            self.display_msg_box(QtWidgets.QMessageBox.Critical,"Transaction Input Error","Please check the recepients addresses and amount you typed.")
            return
        #return
        new_tx,msg,total_2_pay = node.wallet_manager.create_transaction(json.dumps(tx_sheet))
        if msg == "SUCCESS":
            node.tx_handler.utxopool = node.utxopool
            valid_txs,fees = node.tx_handler.handle_txs([new_tx])
            node.tx_fee_pool += fees
            node.block_chain.txhandler.utxopool = node.tx_handler.utxopool
            node.wallet_manager.utxopool = node.tx_handler.utxopool
            node.utxopool = node.tx_handler.utxopool
            node.confirmed_utxopool = node.tx_handler.conf_utxopool
            node.wallet_manager.conf_utxopool = node.tx_handler.conf_utxopool
            node.wallet_manager.update_utxopool_on_wallet()
            node.wallet_manager.update_all_wallets_account_balance()
            node.add_to_tx_pool(valid_txs)
            node.add_to_permanent_tx_pool(valid_txs)
            
            if len(valid_txs) > 0:
                xp2pv3.reactor.callFromThread(node.send_tx_via_clients,valid_txs[0])
            
            date = datetime.datetime.fromtimestamp(int(time.time())).strftime('%Y-%m-%d %H:%M:%S')
            node.wallet_manager.set_tx_history(date,-total_2_pay)
            
            
            #clear text areas and lists
            self.wal_2_tx = {}
            self.txt_recepts.clear()
            for index in range(self.lst_wallets.count()):
                self.lst_wallets.item(index).setCheckState(QtCore.Qt.PartiallyChecked)
            #display success message
            self.display_msg_box(QtWidgets.QMessageBox.Information,"Money Sent Successfully!","It takes about 1 minute to confirm the payment.")
        else:
            #display error message
            self.display_msg_box(QtWidgets.QMessageBox.Critical,"Create Transaction Error",msg)
            
            
             
    def save_txfee_settings(self,event):
        node = Portal.node
        try:
            new_fee = float(self.txt_tx_fee.toPlainText())
            node.settings.update_settings({'txfee' : new_fee})
            Portal.load_settings(node.settings,node.wallet_manager)
            self.display_msg_box(QtWidgets.QMessageBox.Information,"Settings updated!","Settings updatesd successfully")
        except:
            self.display_msg_box(QtWidgets.QMessageBox.Critical,"Settings Error","Transaction fee should be a number")
            return
        
        
    def display_msg_box(self,icon,message,details):
        msg = QtWidgets.QMessageBox()
        msg.setIcon(icon)
        msg.setText(message)
        #msg.setWindowTitle("Error")
        msg.setInformativeText(details)
        msg.setStandardButtons(QtWidgets.QMessageBox.Ok)
        retval = msg.exec_()
    
    
        
    def find_block_from_ix(self,blk_index):
        node = Portal.node
        #find the block and display the hash
        block = None
        try:
            blk_index = int(blk_index)
            block = node.block_chain.chain[blk_index]
            if block.index == blk_index:
                #start displaying the block info
                return block
            else:
                for i in range(self.blk_index,len(node.block_chain.chain)):
                    block = node.block_chain.chain[i]
                    if block.index == blk_index:
                        #dispay block info
                        return block
                     
        except:
            print "No block found"
            return block
       
    def fetch_ix_and_display(self,ix):
        
        block = self.find_block_from_ix(ix)
        
        if block is None:
            self.display_msg_box(QtWidgets.QMessageBox.Critical,"Block doesn't exist!","Use valid block indices.")
        else:
            bld = BlockDetailDialog(block)
            bld.show()
            bld.exec_()
        
 
    def details_click1(self,event):
        ix = self.lbl_blk1_ix.text()
        self.fetch_ix_and_display(ix)
    
    def details_click2(self,event):
        ix = self.lbl_blk2_ix.text()
        self.fetch_ix_and_display(ix)
    
    def details_click3(self,event):
        ix = self.lbl_blk3_ix.text()
        self.fetch_ix_and_display(ix)
        
    def add_wallet(self,event):
        node = Portal.node
        wallets = node.wallet_manager.wallets
        new_wal_name = str(self.txt_wal_name.toPlainText())
        
        if new_wal_name == "":
            self.display_msg_box(QtWidgets.QMessageBox.Critical,"Wallet name can't be string or empty","Please Use valid name.")
            return
        
        for wallet in wallets:
            if wallet.wallet_name == new_wal_name:
                self.display_msg_box(QtWidgets.QMessageBox.Critical,"Wallet name exists","Please Use another name.")
                return
        
        node.wallet_manager.create_wallet(new_wal_name)
        
        Portal.display_wallet(node.wallet_manager)
        Portal.display_wallet_table(node.wallet_manager)
        
        self.display_msg_box(QtWidgets.QMessageBox.Information,"Wallet Created","Use the public address to accept money.")
        self.txt_wal_name.clear()
 

        
    def show_blk_dialog_srch(self,event):
        try:
            blk_index = int(self.txt_blk_ix.toPlainText())
            self.fetch_ix_and_display(blk_index)
        except:
            self.display_msg_box(QtWidgets.QMessageBox.Critical,"block index can't be string or empty","Use valid block indices.")
            
        
        
def build_node(name,first_time,myport,port_lsts):
    print "Starting {}'s Node....".format(name)
    node1 = xp2pv3.Node(name,first_time = first_time)
    node1.start_node(myport,port_lsts)
    xp2pv3.reactor.run(installSignalHandlers=False)

def main():
    # print command line arguments
    name = sys.argv[1:][0]
    first_time = False  # used when the node is lauched for the first time on a new machine
    isgenesis = False   # if true the node is launched for the first time and also is a genesis node.
    
    if sys.argv[1:][1] == '-ft':
        first_time = True
    elif sys.argv[1:][1] == '-gen':
        isgenesis = True
    
    myport = int(sys.argv[1:][2])
    if len(sys.argv[1:]) <= 3:
        port_lsts = []
    else:
        port_lsts = map(int,sys.argv[1:][3].split(","))
    
    
    app = QtWidgets.QApplication(sys.argv)
    window = MyApp()
    Portal.init(window)
    node = xp2pv3.Node(name,first_time = first_time,genesis = isgenesis,Portal = Portal)
    node.start_node(myport,port_lsts)
    Portal.port_node(node)
    
    print "Starting {}'s Node....".format(name)
   
    Thread(target=xp2pv3.reactor.run, args=(False,)).start()

    # call the GUI
    
    window.show()
    sys.exit(app.exec_())
    
   
   
    

    
if __name__ == "__main__":
    
    main()
