# https://stuvel.eu/python-rsa-doc/usage.html#generating-keys 

import rsa
from Cryptodome.Cipher import AES

def main():
    # generate the keys --> may take a long time... only run this 1x...
    (mypubkey, myprivkey) = rsa.newkeys(512)

    # simulate a recipient... should NEVER have their priv key...
    (theirpubkey, theirprivkey) = rsa.newkeys(512)


    # read a file as a binary (RSA requires bytestream...) 
    plaintextfile = open("plaintext.txt", "rb")
    print(plaintextfile.read())
    encodedplaintext = plaintextfile.read()

    # encrypt (for authentication)
    cipher_auth = rsa.encrypt(encodedplaintext, mypubkey)

    # encrypt (for storage?)
    cipher_store = rsa.encrypt(encodedplaintext, myprivkey)

    # encrypt (for secure sending?)
    cipher_send = rsa.encrypt(encodedplaintext, theirpubkey)

    # store the 3 cipher texts in an output file (aka make an encrypted file...)
    ciphertextfile = open("cipher.txt", "wb")

    ciphertextfile.write(cipher_auth)
    ciphertextfile.write(cipher_store)
    ciphertextfile.write(cipher_send)


    encodedimagefile = open("image.jpg", "rb")
    # none of this works
    # cipher_image = rsa.encrypt(encodedimagefile, theirpubkey)
    # cipherimagefile = open("cipherimage.jpg", "rb")
    # cipherimagefile.write(cipher_image)
    

# encrypting and decrypting 

    print(dir(AES))
    AEScipherobj = AES.new(myprivkey, AES.MODE_CCM)
    # key = get_random_bytes(16)
    # c = AES.new(key, AES.MODE_GCM)
    # # AEScipherobj.encrypt(encodedimagefile)
    # AEScipher = AEScipherobj.encrypt(encodedplaintext)

    # ciphertextfile = open("AEScipher.txt", "wb")
    # ciphertextfile.write(AEScipher)

main();
