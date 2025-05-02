# !!! RUN AS ADMIN !!! 

netsh advfirewall firewall add rule name="Allow UDP 5001" dir=in action=allow protocol=UDP localport=5001