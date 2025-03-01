import os 
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from .general import now


def load_key(filepath:str, type:str) -> str:
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
            try:
                key = serialization.load_pem_private_key(key_data)

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

            
def gen_rsa_keypairs(size:int, exp:int) -> tuple[str, str]:
    """Generates a new private/public keypair using RSA."""

    # Generate a new RSA private key
    private_key = rsa.generate_private_key(
        public_exponent=exp,
        key_size=size
    )

    # Serialize private key to PEM string
    private_pem:str = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()
    ).decode()

    # Extract the public key
    public_key = private_key.public_key()

    # Serialize public key to PEM string
    public_pem:str = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    ).decode()

    # Return the two keys 
    return (private_pem, public_pem)


def generate_asymm_keys(keysize:int, exp:int, prv_save_path:str, pub_save_path:str) -> None: 
    """Generates asymmetric keys using RSA and saves the private and public keys to the given 
    prv_save_path and pub_save_path respectively."""

    # Call gen keys func
    priv_key_str, pub_key_str = gen_rsa_keypairs(
        keysize,
        exp
    )

    # Save the keys 
    os.makedirs(os.path.dirname(prv_save_path), exist_ok=True)
    os.makedirs(os.path.dirname(pub_save_path), exist_ok=True)

    with open(prv_save_path, 'w+') as file:
        file.write(priv_key_str)

    with open(pub_save_path, 'w+') as file: 
        file.write(pub_key_str)
