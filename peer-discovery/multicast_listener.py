
import configparser as cpr
import logging 


from utils.listener_utils import join_multicast
from utils.general import now


# --- Define local vars --- #
DEBUG:bool = True
LOG_FILE:str = '../logs/peer_discovery.log'
LOGGING_LEVEL:any = logging.INFO

# --- Init configparser --- #
config:cpr.ConfigParser = cpr.ConfigParser()
config.read('config/multicast-config.conf')

# --- Init logger --- #
logging.basicConfig(
    filename=LOG_FILE,  
    level=logging.INFO,   # Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    format="%(asctime)s - %(levelname)s - %(message)s",  # Log format
)

# --- Start listener --- #
print(f'\n\033[0m[{now()}] \033[94mStarting multicast listener.\033[0m')
logging.info('Starting multicast listener.')

print(config['multicast-config']['MCAST_GROUP'])

# Join the multicast group
join_multicast(
    config['multicast-config']['MCAST_GROUP'],
    int(config['multicast-config']['MCAST_PORT']),
    config['multicast-config']['LOCAL_IP']
)

