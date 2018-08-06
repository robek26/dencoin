# dencoin

Install the following libraries and distribution to use Dencoin.

* **Anaconda** with python 2.7

* External Python Libraries

    * **Twisted** Communication library

    * **Pyqt5**   GUI library for the nodes 

    * **Ecdsa**   a library used to generate public, private key pair and is used to sign a text (contract)

To launch Dencoin

1. Go to the directory where the source code is kept
2. Activate anaconda environment `source activate <ENV NAME>`
3. To launch Dencoin, Use the following format

```
python dencoin.py <NODE NAME> <OPTIONS> <PORT 1> <PORT 2>

<NODE NAME> - Any suitable name for the node.

<OPTIONS> 
		-gen : Use it to launch the first (genesis) node in the network
		-ft  : Use it for launching a node for the first time.
		-nft : Use it for launching a node that has been shutdown.

<PORT 1> - the port where the node listens to incoming connections

<PORT 2> - the port of another node that this node will try to connect to. 
           Remember that if this node is a genesis node, then leave the port number.

```

Examples

```
Genesis Node - python dencoin.py Robel -gen 10000
First time Node - python dencoin.py Alice -ft 11000 10000
Waking a Node - python dencoin.py Mary -nft 11200 10000

```
