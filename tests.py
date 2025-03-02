# lilys encryption module
import backend.objects.encryption.enc as enc
import pytest
from cryptography.hazmat.primitives import serialization, hashes, padding


def test_saveKeys():
    enc.save_keys_test(b"h1", b"h2", "privateTest.pem", "publicTest.pem")
    with open("privateTest.pem") as priv:
        priv_equal = priv.read() == "h1"
        assert priv_equal
        
    with open("publicTest.pem") as pub:
        pub_equal = pub.read() == "h2"
        assert pub_equal


# Unique keys are generated even when using the same password!!!
def test_process():
    p1 = b"password"
    aes_doer1 = enc.generate_keys(p1)
    pub1 = enc.get_public_key("public.pem").public_bytes(serialization.Encoding.PEM,serialization.PublicFormat.SubjectPublicKeyInfo)
    priv1 = enc.get_private_key(p1, "private.pem")


    aes_doer2 = enc.generate_keys(p1)
    pub2 = enc.get_public_key("public.pem").public_bytes(serialization.Encoding.PEM,serialization.PublicFormat.SubjectPublicKeyInfo)
    priv2 = enc.get_private_key(p1, "private.pem")


    assert aes_doer1 != aes_doer2
    assert pub1 != pub2
    assert priv1 != priv2

# Testing the RSA encryption
    message = b"hello"
    cipher = enc.RSA_encrypt(message, enc.get_public_key("public.pem"))
    m2 = enc.RSA_decrypt(cipher, enc.get_private_key(p1, "private.pem"))

    assert message != cipher
    assert message == m2


    # Testing the AES encryption
    message_AES = b"hello"
    cipher_AES = enc.AES_encrypt(message_AES , aes_doer1)
    m2_AES = enc.AES_decrypt(cipher_AES, aes_doer1)

    assert message_AES != cipher_AES
    assert message_AES  == m2_AES 

def test_hashing():
    message = b"hello"
    hashed_message = enc.hashMessage(message)
    print(hashed_message)
    assert message != hashed_message


test_saveKeys()
test_process()
test_hashing()