from configparser import ConfigParser
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
import os 


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



config:ConfigParser = ConfigParser()
config.read('../config/encryption-config.conf')

priv_key_str, pub_key_str = gen_rsa_keypairs(
    int(config['keys']['SIZE']),
    int(config['keys']['EXP'])
)


# Save the keys 
os.makedirs(os.path.join('../', os.path.dirname(config['paths']['PRIV_KEY_PATH'])), exist_ok=True)
os.makedirs(os.path.join('../', os.path.dirname(config['paths']['PUB_KEY_PATH'])), exist_ok=True)

with open(os.path.join('../', config['paths']['PRIV_KEY_PATH']), 'w+') as file:
    file.write(priv_key_str)

with open(os.path.join('../', config['paths']['PUB_KEY_PATH']), 'w+') as file: 
    file.write(pub_key_str)

# Done 
print('\n\033[92mDone generating keys\033[0m\n')
