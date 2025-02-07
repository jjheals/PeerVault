import os
import pyaes 

# Generate random 256 bit key!!
key_256 = os.random(32)

initialization = "InitializationVe"

aes = pyaes.AESModeOfOperationCTR(key_256)

plaintext = open("plaintext.txt", "r")
print(plaintext.read())

