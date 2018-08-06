import json
import hashlib
import time
import math
import pickle
import os

from ecdsa import SigningKey,VerifyingKey,SECP256k1,BadSignatureError
from base58 import b58encode_check,b58encode,b58decode_check,b58decode
import binascii


#NOT USEFUL NOW
def pubkey_to_address(pubkey):
    if 'ripemd160' not in hashlib.algorithms_available:
        raise RuntimeError('missing ripemd160 hash algorithm')

    sha = hashlib.sha256(hashlib.sha256(pubkey).digest()).hexdigest()
    print sha 
    ripe = hashlib.new('ripemd160', sha).digest()
    return b58encode_check(b'\x00' + ripe)


class Crypto:
    
    @staticmethod
    def uncompress_pubkey(c_pub_key):
        p_hex = 'FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEFFFFFC2F'
        p = int(p_hex, 16)
        compressed_key_hex = c_pub_key
        x_hex = compressed_key_hex[2:66]
        x = int(x_hex, 16)
        prefix = compressed_key_hex[0:2]

        y_square = (pow(x, 3, p)  + 7) % p
        y_square_square_root = pow(y_square, (p+1)/4, p)
        if (prefix == "02" and y_square_square_root & 1) or (prefix == "03" and not y_square_square_root & 1):
            y = (-y_square_square_root) % p
        else:
            y = y_square_square_root

        computed_y_hex = format(y, '064x')
        computed_uncompressed_key = "04" + x_hex + computed_y_hex

        return computed_uncompressed_key
    
    @staticmethod
    def generate_priv_pub_key_pair():
        sk = SigningKey.generate(curve=SECP256k1,hashfunc=hashlib.sha256)
        vk = sk.get_verifying_key().to_string()
        compressed_vk = chr((ord(vk[63]) & 1) + 2) + vk[0:32]
        return binascii.hexlify(sk.to_string()),binascii.hexlify(compressed_vk)
    
    @staticmethod
    def sign_document(priv_key,data_to_sign):
        return binascii.hexlify(SigningKey.from_string(binascii.unhexlify(priv_key),curve=SECP256k1,hashfunc=hashlib.sha256).sign(bytes(data_to_sign)))
    
    @staticmethod
    def verify_signature(pubkey,origdata,sig):
        vk = VerifyingKey.from_string(bytes(bytearray.fromhex(Crypto.uncompress_pubkey(pubkey)[2:])), curve=SECP256k1,hashfunc=hashlib.sha256)
        try:
            return vk.verify(bytes(bytearray.fromhex(sig)), bytes(origdata))
        except:
            return False
    
    @staticmethod
    def is_pubkey_valid(compressed_pubkey):
        try:
            VerifyingKey.from_string(bytes(bytearray.fromhex(Crypto.uncompress_pubkey(compressed_pubkey)[2:])),curve=SECP256k1,hashfunc=hashlib.sha256)
            return True
        except:
            return False
        
        
class Settings:
    def __init__(self,name,init_sets = None):
        self.name = name
        if not os.path.isfile('{}.setgs'.format(self.name)):
            self.update_settings(init_sets)
    # sets is a dictionary {'txfee' : 0.05}
    def update_settings(self,sets):
        with open('{}.setgs'.format(self.name),"w") as hnd:
            hnd.write(json.dumps(sets))
    def load_settings(self):
        settings = ""
        with open('{}.setgs'.format(self.name),"r") as hnd:
            for line in hnd:
                settings += line
        settings = json.loads(settings)
        return settings
    