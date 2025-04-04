import os 
import base64
import re 

from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend

from .general import now


def load_key_pem(filepath:str, type:str, passphrase:str=None) -> str:
    """Loads the RSA key from the given filepath, where type is 'public' or 'private'."""

    # Check that the filepath exists and is valid
    if not (os.path.exists(filepath) and filepath.endswith('.key')):
        print(f'\033[0m[{now()}] \033[91mERROR in load_key(): \033[0mThe given filepath "{filepath}" does not exist or is invalid.')
        return None

    # Read the key file
    with open(filepath, 'rb') as key_file:
        key_data = key_file.read()

        # Read RSA private key
        if type == 'private':
            
            # Make sure a passphrase is given 
            if not passphrase: 
                print(f'\033[0m[{now()}] \033[91mERROR in load_key(): \033[0mThe private key is not an RSA key.')
                return None
            
            # Read the key
            try:
                key = serialization.load_pem_private_key(
                    key_data,
                    password=passphrase.encode()
                )

                # Ensure it's an RSA key
                if not isinstance(key, rsa.RSAPrivateKey):
                    print(f'\033[0m[{now()}] \033[91mERROR in load_key(): \033[0mThe private key is not an RSA key.')
                    return None

                # Convert the key to a string and return
                return key.private_bytes(
                    encoding=serialization.Encoding.PEM,
                    format=serialization.PrivateFormat.TraditionalOpenSSL,
                    encryption_algorithm=serialization.NoEncryption(),
                ).decode()
            
            except Exception as e:
                print(f'\033[0m[{now()}] \033[91mERROR in load_key(): \033[0mFailed to load private key - {e}')
                return None

        # Read RSA public key
        elif type == 'public':
            try:
                key = serialization.load_pem_public_key(key_data)

                # Ensure it's an RSA key
                if not isinstance(key, rsa.RSAPublicKey):
                    print(f'\033[0m[{now()}] \033[91mERROR in load_key(): \033[0mThe public key is not an RSA key.')
                    return None

                # Convert the key to a string and return
                return key.public_bytes(
                        encoding=serialization.Encoding.PEM,
                        format=serialization.PublicFormat.SubjectPublicKeyInfo,
                    ).decode()

            except Exception as e:
                print(f'\033[0m[{now()}] \033[91mERROR in load_key(): \033[0mFailed to load public key - {e}')
                return None

        # Invalid type
        else:
            print(f'\033[0m[{now()}] \033[91mERROR in load_key(): \033[0mThe given type "{type}" is not valid.')
            return None

            
def gen_rsa_keypairs(size:int, exp:int, priv_passphrase:str) -> tuple[bytes, bytes]:
    """Generates a new private/public keypair using RSA and returns the bytes in the format (priv_bytes, pub_bytes)."""

    # Generate a new RSA private key
    private_key = rsa.generate_private_key(
        public_exponent=exp,
        key_size=size
    )
    
    # Serialize private key to PEM string (with the passphrase)
    private_pem:str = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.BestAvailableEncryption(priv_passphrase.encode())  
    )

    # Extract the public key
    public_key = private_key.public_key()

    # Serialize public key to PEM string
    public_pem:str = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    )

    # Return the two keys 
    return (private_pem, public_pem)


def generate_asymm_keys(keysize:int, exp:int, prv_save_path:str, pub_save_path:str, passphrase:str) -> None: 
    """Generates asymmetric keys using RSA and saves the private and public keys to the given 
    prv_save_path and pub_save_path respectively. Raises ValueError if no passphrase is given."""

    # Make sure a passphrase is given 
    if not passphrase: 
        raise ValueError('No passphrase given.')

    # Call gen keys func
    priv_key_str, pub_key_str = gen_rsa_keypairs(
        keysize,
        exp,
        passphrase
    )

    # Save the keys 
    os.makedirs(os.path.dirname(prv_save_path), exist_ok=True)
    os.makedirs(os.path.dirname(pub_save_path), exist_ok=True)

    with open(prv_save_path, 'rb+') as file:
        file.write(priv_key_str)

    with open(pub_save_path, 'rb+') as file: 
        file.write(pub_key_str)


def encrypt_message(public_key_pem:str, plaintext:str) -> dict:
    """Encrypts the given plaintext with the provided public key using hybrid encryption."""
    
    # Load the public key
    public_key = serialization.load_pem_public_key(public_key_pem.encode(), backend=default_backend())
    
    # Generate a random symmetric key (AES)
    symmetric_key = os.urandom(32)  # 256-bit key for AES-256
    
    # Encrypt the plaintext using AES
    iv = os.urandom(16)  # Initialization vector for AES
    cipher = Cipher(algorithms.AES(symmetric_key), modes.CFB(iv), backend=default_backend())
    encryptor = cipher.encryptor()
    ciphertext = encryptor.update(plaintext.encode()) + encryptor.finalize()
    
    # Encrypt the symmetric key using RSA
    encrypted_symmetric_key = public_key.encrypt(
        symmetric_key,
        padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None
        )
    )
    
    # Encode components to base64 for safe transmission
    encrypted_data = {
        'encrypted_symmetric_key': base64.b64encode(encrypted_symmetric_key).decode(),
        'iv': base64.b64encode(iv).decode(),
        'ciphertext': base64.b64encode(ciphertext).decode()
    }
    
    return encrypted_data


def decrypt_message(private_key_pem:str, encrypted_data:dict) -> str:
    """Decrypts the given encrypted data with the provided private key."""
    
    # Load the private key
    private_key = serialization.load_pem_private_key(private_key_pem.encode(), password=None, backend=default_backend())
    
    # Decode components from base64
    encrypted_symmetric_key = base64.b64decode(encrypted_data['encrypted_symmetric_key'])
    iv = base64.b64decode(encrypted_data['iv'])
    ciphertext = base64.b64decode(encrypted_data['ciphertext'])
    
    # Decrypt the symmetric key using RSA
    symmetric_key = private_key.decrypt(
        encrypted_symmetric_key,
        padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None
        )
    )
    
    # Decrypt the ciphertext using AES
    cipher = Cipher(algorithms.AES(symmetric_key), modes.CFB(iv), backend=default_backend())
    decryptor = cipher.decryptor()
    plaintext_bytes = decryptor.update(ciphertext) + decryptor.finalize()
    decoded_bytes = plaintext_bytes.decode()

    return decoded_bytes


def strip_pem_headers(pem_str:str) -> str:
    """Strips the leading and trailing "----- * KEY -----" from the given key PEM string."""
    return re.sub(r'-----.*?-----', '', pem_str).strip()


def sign_file(priv_key_pem_str:str, file_data:bytes) -> str:
    """Computes a digital signature for the given private key and file data."""

    # Convert the key pem str to a PrivateKeyPEM obj
    priv_key = serialization.load_pem_private_key(
        priv_key_pem_str.encode(),
        password=None
    )

    # Sign the file data
    return priv_key.sign(
        file_data,
        padding.PSS(
            mgf=padding.MGF1(hashes.SHA256()),
            salt_length=padding.PSS.MAX_LENGTH
        ),
        hashes.SHA256()
    )