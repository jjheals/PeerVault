import cryptography as c
from cryptography.hazmat.primitives import serialization, hashes, padding
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
import os

def generate_keys(password):
    key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=4096)

    
    private_key = key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        encryption_algorithm= serialization.BestAvailableEncryption(password)
    )

    public_key = key.public_key().public_bytes(
        serialization.Encoding.PEM,
        serialization.PublicFormat.SubjectPublicKeyInfo
    )

    # generates a random 256 bit key... 
    key = os.urandom(32)
    iv = os.urandom(16)
    AES_doer = Cipher(algorithms.AES(key), modes.CBC(iv))
    
    return(public_key, private_key, AES_doer)

def save_key(private_key, public_key):
    
    with open("private.pem", "wb") as pem:
        pem.write(private_key)

    with open("public.pem", "wb") as pempub:
        pempub.write(public_key)

def recover_private_key(password):
    try:
        with open("private.pem", "rb") as key_file:
            private_key = serialization.load_pem_private_key(
                data=key_file.read(),
                password=password, 
                backend=default_backend
            )
        return private_key
    
    except Exception as e:
        print(f"Error opening PEM file: {e}")
        return None
    
def recover_public_key():
    try:
        with open("public.pem", "rb") as key_file:
            public_key = serialization.load_pem_public_key(
                data=key_file.read(),
                backend=default_backend
            )
        return public_key
    
    except Exception as e:
        print(f"Error opening PEM file: {e}")
        return None

def parse_data(file):
    with open(file, "rb") as data:
        parsed_data = data.read()  

    return parsed_data

def RSA_encrypt(data, key):
    cipher = key.encrypt(data,
                padding.OAEP(
                    mgf=padding.MGF1(algorithm=hashes.SHA256()),
                    algorithm=hashes.SHA256(),
                    label=None
                )
            )
    return cipher

def RSA_decrypt(data, key):
    message = key.decrypt(data,
                padding.OAEP(
                    mgf=padding.MGF1(algorithm=hashes.SHA256()),
                    algorithm=hashes.SHA256(),
                    label=None  
                )
            )

    return message

def AES_encrypt(data, doer):
    padder = c.hazmat.primitives.padding.PKCS7(128).padder()
    padded_data = padder.update(data)
    padded_data += padder.finalize()

    encryptor = doer.encryptor()
    cipher = encryptor.update(padded_data) + encryptor.finalize()
    return cipher

def AES_decrypt(data, doer):
    decryptor = doer.decryptor()
    text = decryptor.update(data) + decryptor.finalize() 

    unpadder = c.hazmat.primitives.padding.PKCS7(128).unpadder()
    unpadded_data = unpadder.update(text)
    unpadded_data += unpadder.finalize()
    return  unpadded_data

def hashMessage(data):
    digest = hashes.Hash(hashes.SHA256())
    digest.update(data)
    digest.finalize()
    return digest


def main():

    # select a "password" needed to get the private key 
    # TODO -- this should probably be stored a different way...
    password = b"pass"

    text = parse_data("../textfiles/plaintext.txt")
    image = parse_data("../textfiles/image.jpg")

    # generate the keys
    public_key, private_key, AES_doer = generate_keys(password)

    # save the keys to a pem file...
    save_key(public_key=public_key, private_key=private_key)

    # load the keys from the pem files!!!
    priv_key = recover_private_key(password = password)
    pub_key = recover_public_key()
    if priv_key is None or public_key is None:
        print("error loading keys")
        return
    
    cipher_AES = AES_encrypt(image, AES_doer)
    message_AES = AES_decrypt(cipher_AES, AES_doer)

    cipher = RSA_encrypt(text, pub_key)
    message = RSA_decrypt(cipher, priv_key)
# --------------------------------------------------------------------------


main()