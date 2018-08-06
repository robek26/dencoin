"""

Portal is used to connect the Node to GUI


"""
from PyQt5 import QtCore, QtGui, uic , QtWidgets
class Portal:
    gui = None
    node = None
    curr_row_tx = 0
    @staticmethod
    def init(gui):
        Portal.gui = gui
    @staticmethod
    def port_node(node):
        Portal.node = node
    @staticmethod
    def write_node_name(txt):
        Portal.gui.lbl_node_name.setText("<html><head/><body><p><span style=' color:#114fcd;'>{}</span></p></body></html>".format(txt))
        
    @staticmethod
    def update_balance(total,conf):
        Portal.gui.lbl_total_balance.setText("<html><head/><body><p><span style=' color:#098700;'>{} DCN</span></p></body></html>".format(total))
        Portal.gui.lbl_confirmed.setText("<html><head/><body><p><span style=' color:#098700;'>{} DCN</span></p></body></html>".format(conf))
        Portal.gui.lbl_unconfirmed.setText("<html><head/><body><p><span style=' color:#098700;'>{} DCN</span></p></body></html>".format(total - conf))
    
    @staticmethod
    def update_wallet_num(num):
        Portal.gui.lbl_num_wallets.setText("<html><head/><body><p><span style=' color:#098700;'>{}</span></p></body></html>".format(num))
    
    @staticmethod
    def update_connections_count(cpn,ccn):
        Portal.gui.lbl_cpn.setText("<html><head/><body><p><span style=' color:#098700;'>{}</span></p></body></html>".format(cpn))
        Portal.gui.lbl_ccn.setText("<html><head/><body><p><span style=' color:#098700;'>{}</span></p></body></html>".format(ccn))
    
    @staticmethod
    def set_status_text(txt):
        Portal.gui.lbl_sync.setText(txt)
        
        
    
    @staticmethod
    def update_blockchain_info(num_blks,bc_size,num_txs,num_utxos,num_mined_blks):
        
        # calculate the bc_size 
        
        bcs = float(bc_size)
        size = "0 bytes"
        if bcs < 1000:
            size = "{} bytes".format(int(bcs))
        elif bcs < 1000000:
            size = "{} KB".format(int(bcs / 1000))
        elif bcs < 1000000000:
            size = "{} MB".format(int(bcs / 1000000))
        else:
            size = "{} GB".format(int(bcs / 1000000000))

        # display 
        
        Portal.gui.lbl_num_blocks.setText("<html><head/><body><p><span style=' color:#186530;'>{}</span></p></body></html>".format(num_blks))
        Portal.gui.lbl_blk_size.setText("<html><head/><body><p><span style=' color:#186530;'>{}</span></p></body></html>".format(size))
        Portal.gui.lbl_num_txs.setText("<html><head/><body><p><span style=' color:#186530;'>{}</span></p></body></html>".format(num_txs))
        Portal.gui.lbl_num_utxos.setText("<html><head/><body><p><span style=' color:#186530;'>{}</span></p></body></html>".format(num_utxos))
        Portal.gui.lbl_num_blk_mined.setText("<html><head/><body><p><span style=' color:#186530;'>{}</span></p></body></html>".format(num_mined_blks))
        
        
    @staticmethod
    def update_debugger(txt,max_lines = 150):
        lines = Portal.gui.txt_debugger.document().blockCount()
        if lines > max_lines:
            txts = Portal.gui.txt_debugger.toPlainText().split("\n")
            Portal.gui.txt_debugger.clear()
            Portal.gui.txt_debugger.appendPlainText('\n'.join(txts[int(max_lines / 2):]))
            Portal.gui.txt_debugger.appendPlainText(txt)
        else:
            Portal.gui.txt_debugger.appendPlainText(txt)
            
    
    
    @staticmethod
    def reset_blockchain_gui():
        Portal.gui.lbl_blk1_ix.setText("-")
        Portal.gui.lbl_blk1_hash.setText("-")
        Portal.gui.lbl_blk2_ix.setText("-")
        Portal.gui.lbl_blk2_hash.setText("-")
        Portal.gui.lbl_blk3_ix.setText("-")
        Portal.gui.lbl_blk3_hash.setText("-")
        
    @staticmethod
    def update_blockchain_gui(blk_index,blk_hash):
        if Portal.gui.lbl_blk1_ix.text() == "-":
            Portal.gui.lbl_blk1_ix.setText(str(blk_index))
            Portal.gui.lbl_blk1_hash.setText(blk_hash[:8] + "...")
        elif Portal.gui.lbl_blk2_ix.text() == "-":
            Portal.gui.lbl_blk2_ix.setText(str(blk_index))
            Portal.gui.lbl_blk2_hash.setText(blk_hash[:8] + "...")
        elif Portal.gui.lbl_blk3_ix.text() == "-":
            Portal.gui.lbl_blk3_ix.setText(str(blk_index))
            Portal.gui.lbl_blk3_hash.setText(blk_hash[:8] + "...")
        else:
            Portal.gui.lbl_blk1_ix.setText(Portal.gui.lbl_blk2_ix.text())
            Portal.gui.lbl_blk1_hash.setText(Portal.gui.lbl_blk2_hash.text())
            Portal.gui.lbl_blk2_ix.setText(Portal.gui.lbl_blk3_ix.text())
            Portal.gui.lbl_blk2_hash.setText(Portal.gui.lbl_blk3_hash.text())
            Portal.gui.lbl_blk3_ix.setText(str(blk_index))
            Portal.gui.lbl_blk3_hash.setText(blk_hash[:8] + "...")
            
        
    @staticmethod
    def display_wallet(wallet_manager):
        #node = Portal.node
        Portal.gui.lst_wallets.clear()
        wallets = wallet_manager.wallets
        for wallet in wallets:
            wal = wallet.wallet_name + " (" + str(round(wallet.conf_acc_balance,2)) + " DCN)"
            item = QtWidgets.QListWidgetItem()
            item.setText(wal)
            item.setCheckState(QtCore.Qt.PartiallyChecked)
            Portal.gui.lst_wallets.addItem(item)
    
    @staticmethod
    def update_lst_wallet(wallet_manager):
        #node = Portal.node
        for i in range(Portal.gui.lst_wallets.count()):
            item = Portal.gui.lst_wallets.item(i)
            for wallet in wallet_manager.wallets:
                txts = item.text().split(" ")
                if " ".join(txts[:-2]) == wallet.wallet_name:
                    item.setText(wallet.wallet_name + " (" + str(round(wallet.conf_acc_balance,2)) + " DCN)")
                    break
            
    @staticmethod
    def display_wallet_table(wallet_manager):
        wallets = wallet_manager.wallets
        if len(wallets) > 11:
            Portal.gui.tbl_wallets.setRowCount(len(wallets))
        tb1cnter = 0
        for wallet in wallets:
            Portal.gui.tbl_wallets.setItem(tb1cnter, 0, QtWidgets.QTableWidgetItem(wallet.wallet_name))
            Portal.gui.tbl_wallets.setItem(tb1cnter, 1, QtWidgets.QTableWidgetItem(wallet.public_addr))
            Portal.gui.tbl_wallets.setItem(tb1cnter, 2, QtWidgets.QTableWidgetItem(wallet.private_key))
            Portal.gui.tbl_wallets.setItem(tb1cnter, 3, QtWidgets.QTableWidgetItem(str(wallet.conf_acc_balance) + " DCN"))
            tb1cnter += 1
        
    @staticmethod
    def load_settings(settings,wallet_manager):
        sets = settings.load_settings()
        Portal.gui.txt_tx_fee.setPlainText(str(sets["txfee"]))
        wallet_manager.MAX_TX_FEE = float(sets["txfee"])
        
        
    @staticmethod
    def add_row_2_txhist(date,amnt):
        Portal.gui.tbl_tx_hist.setSortingEnabled(False) 
        Portal.gui.tbl_tx_hist.setItem(Portal.curr_row_tx, 0, QtWidgets.QTableWidgetItem(date))
        Portal.gui.tbl_tx_hist.setItem(Portal.curr_row_tx, 1, QtWidgets.QTableWidgetItem(str(amnt)))
        Portal.gui.tbl_tx_hist.setSortingEnabled(True) 
        Portal.curr_row_tx += 1
        
        