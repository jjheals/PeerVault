import rsa


# generate the keys --> takes .1 sec? --> can be up to 4096 bytes (~72 seconds)

(pubkey,privkey) = rsa.newkeys(512)