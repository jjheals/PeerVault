import sys
# import crypto.rsa
import rsa


def encrypt(pubkey, privkey):
    if(len(sys.argv) < 3):
        print("please call this code via this method: 'python3   encrypt.py   path/to/file.txt   path/to/output.txt'")

    file = sys.argv[1]
    data = open(file, "rb")
    data = data.read()

    # in 53 byte increments until the length of the data ends....
    encryptedData = []
    for n in range(0, len(data), 53):
        section = data[n:n+53]
        data = rsa.encrypt(section, pubkey)
        encryptedData.append(data)

    d = b"".join(encryptedData)
    
    encryptedImage = open(sys.argv[2], "wb")
    encryptedImage.write(d)

def decrypt(pubkey, privkey):
    print("called decrypt()")
    data = open(sys.argv[2], "rb")
    data = data.read()

    print(data)
    # plaintext = rsa.decrypt(data, privkey)

    encryptedData = []
    for n in range(0, len(data), 53):
        section = data[n:n+53]
        data = rsa.decrypt(section, privkey)
        encryptedData.append(data)

    d = b"".join(encryptedData)
    
#     encryptedImage = open("encryptedImage.jpg", "wb")



if __name__ == "__main__":
    (pubkey, privkey) = rsa.newkeys(512)

    encrypt(pubkey, privkey)
    decrypt(pubkey, privkey)