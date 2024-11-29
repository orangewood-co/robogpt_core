#!/usr/bin/expect

spawn pusher logout

# Check if the key argument is provided
if {[llength $argv] == 0} {
    puts "Usage: $argv0 <pusher_key>"
    exit 1
}

# Store the Pusher key from the argument
set PUSHER_KEY [lindex $argv 0]

# Start the pusher login process
spawn pusher login

# Expect the prompt asking for the API key and send the key
expect "What is your API key?*" {
    send "$PUSHER_KEY\r"
}

# Wait for the process to finish
expect eof
