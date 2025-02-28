Asymmetric Cryptography:
* RSA can only encrypt reliably up to 256 Bytes of data given a key that is 2048 bits. Encrypting files larger than this with RSA is not recommended
    * requires larger sized keys to encrypt the same amount of data
    * can be derrived by providing specific inputs to be encrypted
    * slower than symmetric encryption.

Symmetric Cryptography:
* It is difficult to share symmetric keys securely...

Suggested Encryption methodology (Hybrid):
* RSA should be used to send a randomly generated symmetric key and the symmetric key should be used to encrypt the data which will be sent. 
* In storage situations the symmetric key will NOT be sent, but in sharing situations it will be!

Sending symmetric key with RSA:

    Encrypt with the RECIPIENTS public key. Ensures that only the person we intend to send this message to can open the message (aka our symmetric key)

Signing a message RSA:

    Encrypt the hashed value of the message with the SENDERS private key
    This ensures that we are who we say we are (they verify w our public key) AND that the message has NOT been interfered with...

Sending a message AES:

    Encrypt the message with the generated symmetric key... This ensures that only people WITH the symmetric key can read the message