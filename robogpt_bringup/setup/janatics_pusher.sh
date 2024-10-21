#!/usr/bin/expect

# Logout the old key
echo "Logging out from Old Key"
spawn pusher logout

# Hardcoded Pusher API key
set PUSHER_KEY "JD5g-_Uf1u2lu0W9T52kZm812NqEiHe3AIHqLn9ELxI"

# Start the pusher login process
spawn pusher login

# Expect the prompt asking for the API key and send the key
expect "What is your API key?*" {
    send "$PUSHER_KEY\r"
}

# Wait for the process to finish
expect eof
