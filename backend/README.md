This document is the documentation for the server 

Codes - each packet sent to eachother will have a code for the first 3 bytes execpt when exchangeing public keys 

Message layout 
    code        -all
    public key  -all
    





000 - 099 these codes have to do with discoverablities and handshake 
    010 - is the hello messages sent form the server. this will happen at start up and in response from reciving a hello message 
        Handshake message: 
            3 bytes 010
            6 bytes mac address 
            256 public key 
            rest common name of user 


