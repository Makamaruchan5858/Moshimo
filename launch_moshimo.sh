#!/bin/bash

# Kill processes using target ports
if lsof -t -i:5005 > /dev/null; then
    echo "Port 5005 is in use. Attempting to kill process..."
    kill $(lsof -t -i:5005) || echo "Failed to kill process on port 5005, or port was already free."
    sleep 1
else
    echo "Port 5005 is free."
fi

if lsof -t -i:5006 > /dev/null; then
    echo "Port 5006 is in use. Attempting to kill process..."
    kill $(lsof -t -i:5006) || echo "Failed to kill process on port 5006, or port was already free."
    sleep 1
else
    echo "Port 5006 is free."
fi

# Assume Python environment already activated
echo "Assuming Python environment is already activated or scripts are directly executable."

# Install/update dependencies
echo "Installing dependencies from requirements.txt..."
pip install -r requirements.txt
if [ $? -ne 0 ]; then
    echo "Failed to install dependencies. Exiting."
    exit 1
fi

# Create required directories
mkdir -p models
mkdir -p models/wizardcoder
mkdir -p models/swallow
mkdir -p logs

# Download WizardCoder model if it doesn't exist
WIZARDCODER_URL="https://www.dropbox.com/scl/fi/gop0dewzds99friqmir6g/wizardcoder-python-34b-v1.0.Q4_K_M.gguf?rlkey=lmsv797dcb95upq83l15c5fmy&dl=1"
WIZARDCODER_PATH="models/wizardcoder/wizardcoder-python-34b-v1.0.Q4_K_M.gguf"
if [ ! -f "$WIZARDCODER_PATH" ]; then
    echo "Downloading WizardCoder model..."
    curl -L "$WIZARDCODER_URL" -o "$WIZARDCODER_PATH"
    if [ $? -ne 0 ]; then
        echo "Failed to download WizardCoder model. Exiting."
        exit 1
    fi
    echo "WizardCoder model downloaded."
else
    echo "WizardCoder model already exists at $WIZARDCODER_PATH."
fi

# Download Swallow model if it doesn't exist
SWALLOW_URL="https://www.dropbox.com/scl/fi/8cbfmd567t8e33nfrsys1/swallow-70b-instruct.Q4_K_M.gguf?rlkey=c6qt4nigiwkguhxcmobjbenkb&dl=1"
SWALLOW_PATH="models/swallow/swallow-70b-instruct.Q4_K_M.gguf"
if [ ! -f "$SWALLOW_PATH" ]; then
    echo "Downloading Swallow model..."
    curl -L "$SWALLOW_URL" -o "$SWALLOW_PATH"
    if [ $? -ne 0 ]; then
        echo "Failed to download Swallow model. Exiting."
        exit 1
    fi
    echo "Swallow model downloaded."
else
    echo "Swallow model already exists at $SWALLOW_PATH."
fi

echo "Starting WizardCoder server..."
python wizardcoder_server.py > logs/wizardcoder_server.log 2>&1 &
WIZARDCODER_PID=$!
echo "WizardCoder server PID: $WIZARDCODER_PID"

echo "Starting Swallow server..."
python swallow_server.py > logs/swallow_server.log 2>&1 &
SWALLOW_PID=$!
echo "Swallow server PID: $SWALLOW_PID"

echo "Waiting for servers to start (giving 30 seconds)..."
sleep 30

# Test WizardCoder server
echo "Sending test prompt to WizardCoder server (Port 5005)..."
curl -s -X POST http://localhost:5005/v1/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "wizardcoder",
    "prompt": "フィボナッチ数を計算するPythonコードを書いてください。",
    "max_tokens": 512,
    "temperature": 0.7,
    "stop": ["```"]
  }' > logs/wizardcoder_response.log
echo "WizardCoder response saved to logs/wizardcoder_response.log"

# Test Swallow server
echo "Sending test prompt to Swallow server (Port 5006)..."
curl -s -X POST http://localhost:5006/v1/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "swallow",
    "prompt": "日本の首都はどこですか？",
    "max_tokens": 512,
    "temperature": 0.7
  }' > logs/swallow_response.log
echo "Swallow response saved to logs/swallow_response.log"

echo ""
echo "MOSHIMO launch script finished."
echo "Server logs: logs/wizardcoder_server.log, logs/swallow_server.log"
echo "Response logs: logs/wizardcoder_response.log, logs/swallow_response.log"
echo ""
echo "To stop the servers, run:"
echo "kill $WIZARDCODER_PID"
echo "kill $SWALLOW_PID"
echo "(Or use 'pkill -f wizardcoder_server.py' and 'pkill -f swallow_server.py')"
