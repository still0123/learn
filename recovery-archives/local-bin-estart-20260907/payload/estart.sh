#!/bin/bash

app_path="/Applications/EasyStart.app"
executable_name="EasyStart"
executable_path="${app_path}/Contents/MacOS/${executable_name}"

# Wait up to 60 seconds for the application to appear
max_wait_seconds=60
waited=0

while [ ! -d "$app_path" ] && [ $waited -lt $max_wait_seconds ]; do
    echo "Waiting for application '${app_path}' to appear... (${waited}s)"
    sleep 1
    waited=$((waited + 1))
done

# Check if the application was found
if [ -d "$app_path" ]; then
    echo "Application '${app_path}' exists."

    # Check if the application is already running
    if pgrep -f "${executable_path}" > /dev/null; then
        echo "Application '${executable_name}' is already running."
    else
        echo "Application '${executable_name}' is not running."
        echo "Starting '${executable_name}'..."

        open "${app_path}"

        echo "'${executable_name}' has been started."
    fi
else
    echo "Application '${app_path}' was not found after waiting ${max_wait_seconds} seconds."
fi
