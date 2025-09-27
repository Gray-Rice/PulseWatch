# File structure

.
├── agentd.service          //Service File
├── agent.yaml              //Config File
├── client.py               //Client Script
├── daemon.py               //Daemon Script (uses Watchdog for file monitor and net_mon.bin for network monitoring)
├── net_mon.bin             //Network Monitor Program Binary  
├── net-mon-libpcap 
│   └── network_monitor.c   //Network Monitor Program using libpcap
├── readme.md
└── requirements.txt        //For venv

Hidden dir - .dump // has previously created files which are not used in the agent

# Usage

- Daemon Script - Just execute the python script as it is in root (i think u must add yourself in specific group probably ig)

# Tasks Done

- File monitoring done with watchdog will only monitor file activity but need to do something for directory activities too
- Network monitoring done with libpcap in c will monitor the ports hardcoded and need to be changed arguments
- Daemonscript is tested and will be Storing the JSON objects in 2 files for Network and File events in **events** directory which will be created by the script if not there

# Tasks Todo

- Fixing file monitoring for Directory Monitoring
- Network monitoring - must add arguments to pass the ports to monitor
- At default the program will monitor all the open ports by checking for them (suggestion)
- config file - can pass selective ports explicitly for monitoring them or just leave it blank to scan all the open ports
- config file - ability add events and actions to be flagged when happened (suggestion)
- Daemon - ability to flag specific events as per the config file (suggestion)
- Testing the daemon as a proper service
- Client functions