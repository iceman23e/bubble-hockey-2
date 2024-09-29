#!/bin/bash

# Simplified check_updates.sh
# This script checks if updates are available in the Git repository.

cd /home/pi/bubble_hockey || exit

# Fetch updates from the remote repository
git fetch

# Check if the local branch is behind the remote branch
if git status -uno | grep -q 'Your branch is behind'; then
    touch update_available.flag
else
    rm -f update_available.flag
fi
