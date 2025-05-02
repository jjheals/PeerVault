
import os
from configparser import ConfigParser
from shutil import rmtree


# Define vars to replace config w/
IP:str = '192.168.4.4'  # Appears in network conf as IFACE and MCAST IFACE, and in identity conf as LOCAL IP


# Remove current log files
print('\033[93mRemoving log files.\033[0m\n')

for log_file in os.listdir('logs/'): 
    os.remove(os.path.join('logs/', log_file))
    
# Remove database files 
print(f'\033[93mRemoving DB files.\033[0m')

for db_file in os.listdir('data/'): 
    if not db_file.endswith('.db'): continue 
    os.remove(os.path.join('data/', db_file))

# Remove keys
print('\033[93mRemoving keys.\033[0m')

for key_file in os.listdir('keys/'): 
    os.remove(os.path.join('keys/', key_file))
    
# Reset identity file 
print(f'\033[93mResetting identity config.\033[0m')
identity_config:ConfigParser = ConfigParser() 
identity_config.read('config/identity.conf') 

identity_config['IDENTITY']['common_name'] = ''
identity_config['IDENTITY']['mac'] = ''
identity_config['IDENTITY']['ip'] = IP 
identity_config['SETTINGS']['allocated_storage'] = ''
identity_config['PATHS']['peer_storage_path'] = ''

with open('config/identity.conf', 'w') as file: 
    identity_config.write(file)

# Reset network file
print(f'\033[93mResetting network config.\033[0m')
network_config:ConfigParser = ConfigParser() 
network_config.read('config/network.conf')

network_config['network']['IFACE'] = IP
network_config['multicast']['LOCAL_IP'] = IP 

with open('config/network.conf', 'w') as file: 
    network_config.write(file)

# Reset encryption config 
print(f'\033[93mResetting encryption config.\033[0m')
enc_config:ConfigParser = ConfigParser() 
enc_config.read('config/encryption.conf')

enc_config['misc']['pass_hash'] = ''


with open('config/encryption.conf', 'w') as file:     
    enc_config.write(file)

# Reset the tmp dir
print('\033[93mRemoving temp files.\033[0m')

rmtree('.tmp/', ignore_errors=True)


# Create the app
from setup_scripts.create_db import main as create_db

create_db()
