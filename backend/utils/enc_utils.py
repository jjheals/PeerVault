import os 
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
import base64

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


def encrypt_message(public_key_pem:str, plaintext:str) -> str:
    """Encrypts the given data with the given public key and returns the ciphertext as a string."""
    
    # Convert the pub key pem to a PublicKeyTypes 
    public_key = serialization.load_pem_public_key(public_key_pem.encode())

    # Enrcypt the given plaintext 
    ciphertext:str = public_key.encrypt(
        plaintext.encode(),
        padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None
        )
    )

    # Convert the ciphertext to a string and return
    return base64.b64encode(ciphertext).decode()


def decrypt_message(private_key_pem:str, ciphertext_message:str) -> str:
    """Decrypts the given message with the given key and returns the plaintext as a string."""

    # Convert the private key pem to a PrivateKeyTypes
    private_key = serialization.load_pem_private_key(private_key_pem.encode(), password=None)

    # Decrypt the given ciphertext
    plaintext_bytes:bytes = private_key.decrypt(
        base64.b64decode(ciphertext_message),
        padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None
        )
    )

    # Decode the decrypted ciphertext and return
    return plaintext_bytes.decode()