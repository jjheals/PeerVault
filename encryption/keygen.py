import rsa
import os

# generate the keys --> takes .1 sec? --> can be up to 4096 bytes (~72 seconds)
(pubkey,privkey) = rsa.newkeys(1024)

# cryptographically secure psuedo random number generation....32 bytes = 256 bits
symmetrickey = os.urandom(32)

print(pubkey, privkey, symmetrickey)