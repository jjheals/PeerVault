# setup-scripts

The scripts in this directory set up the required firewall rules for the P2P connections to work properly.

To run each of the scripts, open an *elevated command prompt* and type: 

```bash
powershell -ExecutionPolicy Bypass <script-filename>
```

Example with the [firewall_allow.ps1](./firewall_allow.ps1) script: 

```bash
powershell -ExecutionPolicy Bypass firewall_allow.ps1
```