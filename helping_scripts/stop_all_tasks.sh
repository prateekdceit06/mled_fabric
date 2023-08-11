#!/bin/bash

# List of Python scripts to stop
scripts_to_stop=(
    "/home/prateek/Documents/FABRIC/mled_fabric/server/start.py"
    "/home/prateek/Documents/FABRIC/mled_fabric/3-1/start.py"
    "/home/prateek/Documents/FABRIC/mled_fabric/2-1/start.py"
    "/home/prateek/Documents/FABRIC/mled_fabric/1-1/start.py"
    "/home/prateek/Documents/FABRIC/mled_fabric/1-2/start.py"
    "/home/prateek/Documents/FABRIC/mled_fabric/1-3/start.py"
    "/home/prateek/Documents/FABRIC/mled_fabric/2-3/start.py"
    "/home/prateek/Documents/FABRIC/mled_fabric/1-4/start.py"
    "/home/prateek/Documents/FABRIC/mled_fabric/1-5/start.py"
    "/home/prateek/Documents/FABRIC/mled_fabric/2-5/start.py"
    "/home/prateek/Documents/FABRIC/mled_fabric/3-5/start.py"
)

for script in "${scripts_to_stop[@]}"; do
    pkill -f $script
done
