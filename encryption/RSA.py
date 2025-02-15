# https://stuvel.eu/python-rsa-doc/usage.html#generating-keys 

import rsa
from Cryptodome.Cipher import AES
from Crypto.PublicKey import RSA
from Crypto.Cipher import PKCS1_OAEP



def main():
    # generate the keys --> may take a long time... only run this 1x...
    (mypubkey, myprivkey) = rsa.newkeys(512)
    (theirpubkey, theirprivkey) = rsa.newkeys(512)


    # read a file as a binary (RSA requires bytestream...) 
    plaintextfile = open("textfiles/plaintext.txt", "rb")
    encodedplaintext = plaintextfile.read()

    # encrypt (for authentication)
    cipher_auth = rsa.encrypt(encodedplaintext, mypubkey)

    # encrypt (for storage?)
    cipher_store = rsa.encrypt(encodedplaintext, myprivkey)

    # encrypt (for secure sending?)
    cipher_send = rsa.encrypt(encodedplaintext, theirpubkey)



    # store the 3 cipher texts in an output file (aka make an encrypted file...)
    ciphertextfile = open("textfiles/cipherBinary.txt", "wb")
    cipherPlaintextfile = open("textfiles/cipherPlain.txt", "w")

    ciphertextfile.write(cipher_auth)

    cipherPlaintextfile.write(str(cipher_auth))


    encodedimagefile = open("image.jpg", "rb")
    image = encodedimagefile.read()
    encodedimagefile.close()

    image = bytearray(image)
    encryptedBinary = []

    # can only encrypt 53 bytes at a time so this must be done by chunks!!!
    for n in range(0, len(image), 53):
        part = image[n:n+53]
        encryptedBinary.append(rsa.encrypt(part, theirpubkey))


    cipherimagefile = open("cipherimage.jpg", "wb")
    cipherimagefile.write(b"".join(encryptedBinary))
    cipherimagefile.close()

    cipherimagefile = open("cipherimage.jpg", "rb")
    decryptedcipherfile= open("decryptedimage.jpg", "wb")
    encryptedContent = cipherimagefile.read()


# TODO --> issues with decryption???!!!

    # unencrypted = []
    # for n in range (0, len(encryptedContent), 256):
    #     part = encryptedContent[n:n+256]
    #     unencrypted.append(rsa.decrypt(part, theirprivkey))
    # decryptedcipherfile.close()
    # cipherimagefile.close()



main();
