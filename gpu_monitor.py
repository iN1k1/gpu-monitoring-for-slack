#!/usr/bin/env python3
"""
GPU Monitoring Script

This script monitors GPU status using nvidia-smi and sends alerts to Slack if any issues are detected.
It's designed to run periodically (e.g., via cron job).

Environment variables needed:
- SLACK_WEBHOOK_URL: Slack incoming webhook URL for notifications
- GPU_ALERT_THRESHOLD: (Optional) GPU utilization threshold percentage (default: 95)
- GPU_TEMP_THRESHOLD: (Optional) GPU temperature threshold in Celsius (default: 85)
"""

import os
import json
import subprocess
import time
import requests
from datetime import datetime
from typing import Dict, List, Optional, Tuple

# Configuration
GPU_CHECK_INTERVAL = int(os.getenv("GPU_CHECK_INTERVAL", "300"))  # 5 minutes
SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL")
GPU_ALERT_THRESHOLD = int(os.getenv("GPU_ALERT_THRESHOLD", "95"))
GPU_TEMP_THRESHOLD = int(os.getenv("GPU_TEMP_THRESHOLD", "85"))


def get_gpu_status() -> Tuple[bool, List[Dict]]:
    """
    Get GPU status using nvidia-smi
    Returns: (is_healthy, gpu_list)
    """
    try:
        # Run nvidia-smi and capture output
        result = subprocess.run(
            [
                "nvidia-smi",
                "--query-gpu=index,utilization.gpu,utilization.memory,temperature.gpu,memory.used,memory.total",
                "--format=csv,noheader,nounits",
            ],
            capture_output=True,
            text=True,
            check=True,
        )

        gpu_list = []
        is_healthy = True

        # Parse the output
        for line in result.stdout.strip().split("\n"):
            if not line.strip():
                continue

            # Parse the CSV output
            parts = [p.strip() for p in line.split(",")]
            if len(parts) < 6:
                continue

            gpu_info = {
                "id": int(parts[0]),
                "gpu_util": int(parts[1]),
                "mem_util": int(parts[2]),
                "temp": int(parts[3]),
                "mem_used": int(parts[4]),
                "mem_total": int(parts[5]),
                "issues": [],
            }

            # Check for issues
            if gpu_info["gpu_util"] > GPU_ALERT_THRESHOLD:
                gpu_info["issues"].append(
                    f"High GPU utilization: {gpu_info['gpu_util']}%"
                )
                is_healthy = False

            if gpu_info["temp"] > GPU_TEMP_THRESHOLD:
                gpu_info["issues"].append(
                    f"High temperature: {gpu_info['temp']}°C"
                )
                is_healthy = False

            gpu_list.append(gpu_info)

        return is_healthy, gpu_list

    except subprocess.CalledProcessError as e:
        error_msg = f"Error running nvidia-smi: {str(e)}\n{e.stderr}"
        return False, [{"error": error_msg}]
    except Exception as e:
        return False, [{"error": f"Unexpected error: {str(e)}"}]


def send_slack_alert(message: str, gpu_info: Optional[List[Dict]] = None):
    """Send alert to Slack"""
    if not SLACK_WEBHOOK_URL:
        print("SLACK_WEBHOOK_URL not set. Cannot send alert to Slack.")
        print(f"Alert message: {message}")
        if gpu_info:
            print("GPU Info:", json.dumps(gpu_info, indent=2))
        return

    # Prepare the message with markdown formatting
    blocks = [
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": f"*🚨 GPU Alert*\n{message}"},
        }
    ]

    # Add GPU details if available
    if gpu_info:
        gpu_details = []
        for gpu in gpu_info:
            gpu_text = f"*GPU {gpu.get('id', '?')}*"
            if "error" in gpu:
                gpu_text += f"\nError: {gpu['error']}"
            else:
                gpu_text += (
                    f"\n• ⚡ GPU: {gpu['gpu_util']}% | "
                    f"🧠 Mem: {gpu['mem_util']}% ({gpu['mem_used']}/{gpu['mem_total']} MiB) | "
                    f"🌡️ {gpu['temp']}°C"
                )
                if gpu.get("issues"):
                    gpu_text += "\n• " + " | ".join(
                        [f"⚠️ {issue}" for issue in gpu["issues"]]
                    )
            gpu_details.append(gpu_text)

        blocks.append(
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": "\n\n".join(gpu_details)},
            }
        )

    try:
        response = requests.post(
            SLACK_WEBHOOK_URL,
            json={
                "text": "GPU Alert",
                "blocks": blocks,
                "username": "GPU Monitor",
                "icon_emoji": ":desktop_computer:",
            },
            timeout=10,
        )
        response.raise_for_status()
    except Exception as e:
        print(f"Failed to send Slack notification: {str(e)}")


def main():
    print(
        f"Starting GPU monitor. Will check every {GPU_CHECK_INTERVAL} seconds."
    )
    print(
        f"Alert thresholds: GPU > {GPU_ALERT_THRESHOLD}%, Temp > {GPU_TEMP_THRESHOLD}°C"
    )

    if not SLACK_WEBHOOK_URL:
        print(
            "Warning: SLACK_WEBHOOK_URL environment variable not set. Alerts will be printed to console only."
        )

    last_alert_time = {}

    try:
        while True:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            is_healthy, gpu_info = get_gpu_status()

            if not is_healthy:
                alert_key = "_error_" if "error" in gpu_info[0] else "_gpu_"

                # Don't spam alerts - wait at least 1 hour before sending the same alert
                current_time = time.time()
                if (
                    alert_key not in last_alert_time
                    or (current_time - last_alert_time[alert_key]) > 3600
                ):
                    message = f"❌ GPU issues detected at {timestamp}"
                    if "error" in gpu_info[0]:
                        message = f"❌ Error checking GPU status at {timestamp}"

                    send_slack_alert(message, gpu_info)
                    last_alert_time[alert_key] = current_time
                else:
                    print(
                        f"[{timestamp}] Issues detected but alert was recently sent. Waiting before sending another one."
                    )
            else:
                print(f"[{timestamp}] All GPUs are healthy")
                # Reset alert timer if everything is fine
                last_alert_time.clear()

            time.sleep(GPU_CHECK_INTERVAL)

    except KeyboardInterrupt:
        print("\nStopping GPU monitor...")
    except Exception as e:
        error_msg = f"Unexpected error in GPU monitor: {str(e)}"
        print(error_msg)
        send_slack_alert(error_msg)


if __name__ == "__main__":
    main()
