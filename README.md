# GPU Monitoring Script

This script monitors GPU status using `nvidia-smi` and sends alerts to a Slack channel when issues are detected.

## Features

- Monitors GPU utilization, memory usage, and temperature
- Sends alerts to Slack when thresholds are exceeded
- Prevents alert spam with rate limiting
- Easy configuration through environment variables
- Detailed error reporting

## Prerequisites

- Python 3.6+
- `nvidia-smi` command available in PATH
- `requests` Python package
- Slack incoming webhook URL

## Installation

1. Install the required Python package:
   ```bash
   pip install requests
   ```

2. Create a Slack incoming webhook:
   - Go to [Slack API](https://api.slack.com/apps)
   - Create a new app or select an existing one
   - Go to "Incoming Webhooks" and activate it
   - Add a new webhook to your workspace
   - Copy the webhook URL

## Configuration

Set the following environment variables:

```bash
# Required
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/...  # Your Slack webhook URL

# Optional (with default values)
GPU_ALERT_THRESHOLD=95    # GPU utilization threshold percentage (default: 95)
GPU_TEMP_THRESHOLD=85     # GPU temperature threshold in Celsius (default: 85)
```

## Running the Script

### Manual Run

```bash
# Make the script executable
chmod +x gpu_monitor.py

# Run the script
./gpu_monitor.py
```

### Running as a Service (Systemd)

1. Create a service file at `/etc/systemd/system/gpu-monitor.service`:

```ini
[Unit]
Description=GPU Monitoring Service
After=network.target

[Service]
User=your_username
Environment="SLACK_WEBHOOK_URL=your_webhook_url"
Environment="GPU_ALERT_THRESHOLD=95"
Environment="GPU_TEMP_THRESHOLD=85"
WorkingDirectory=/path/to/script/directory
ExecStart=/usr/bin/python3 /path/to/gpu_monitor.py
Restart=always

[Install]
WantedBy=multi-user.target
```

2. Reload systemd and start the service:

```bash
sudo systemctl daemon-reload
sudo systemctl enable gpu-monitor.service
sudo systemctl start gpu-monitor.service
```

### Running with Cron

Add this line to your crontab (edit with `crontab -e`):

```
# Run every 5 minutes
*/5 * * * * cd /path/to/script/directory && /usr/bin/python3 gpu_monitor.py
```

## Alert Examples

- High GPU utilization: `⚠️ High GPU utilization: 98%`
- High temperature: `⚠️ High temperature: 88°C`
- Command error: `❌ Error checking GPU status: nvidia-smi command failed`

## Logs

When not running in a terminal, logs are written to the system journal (if using systemd) or to the configured logging system. You can view logs with:

```bash
# If running as a service
journalctl -u gpu-monitor.service -f
```

## License

This script is provided as-is under the MIT License.
