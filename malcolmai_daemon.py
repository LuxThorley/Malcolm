import psutil
import requests
import subprocess
import time
import json
import os
from datetime import datetime

MALCOLM_API_URL = "https://malcolmai.live"  # Malcolm AI endpoint
LOG_FILE = "malcolmai_daemon.log"

class MalcolmAIClient:
    def __init__(self, api_url=MALCOLM_API_URL):
        self.api_url = api_url

    def query(self, prompt, data=None):
        payload = {"input": prompt}
        if data:
            payload["data"] = data
        try:
            # Try POST first
            response = requests.post(self.api_url, json=payload, timeout=20)
            if response.status_code == 405:  # Method Not Allowed
                response = requests.get(self.api_url, params=payload, timeout=20)
            try:
                return response.json()
            except Exception:
                return {"error": f"Non-JSON response: {response.text[:200]}..."}
        except Exception as e:
            return {"error": str(e)}


class SystemMonitor:
    """Collects system performance metrics."""
    def get_metrics(self):
        return {
            "cpu_percent": psutil.cpu_percent(interval=1),
            "memory": psutil.virtual_memory()._asdict(),
            "disk": psutil.disk_usage('/')._asdict(),
            "network": psutil.net_io_counters()._asdict(),
            "process_count": len(psutil.pids())
        }

class Optimizer:
    """Executes safe system optimization actions suggested by Malcolm AI."""
    SAFE_COMMANDS = {
        "clear_cache": "sync; echo 3 > /proc/sys/vm/drop_caches",
        "restart_network": "systemctl restart NetworkManager",
        "cleanup_tmp": "rm -rf /tmp/*",
        "kill_high_cpu": None,  # Special handling
    }

    def execute(self, action, details=None):
        if action not in self.SAFE_COMMANDS and action != "kill_high_cpu":
            return f"[SKIPPED] Unsafe action: {action}"

        if action == "kill_high_cpu":
            if details and "pid" in details:
                try:
                    p = psutil.Process(details["pid"])
                    p.terminate()
                    return f"[DONE] Terminated high-CPU process PID {details['pid']}"
                except Exception as e:
                    return f"[ERROR] Failed to terminate PID {details['pid']}: {e}"
            return "[SKIPPED] No PID provided for high CPU process"

        cmd = self.SAFE_COMMANDS[action]
        if cmd:
            try:
                subprocess.run(cmd, shell=True, check=True)
                return f"[DONE] Executed {action}"
            except Exception as e:
                return f"[ERROR] Failed {action}: {e}"

        return f"[UNKNOWN] No command mapped for {action}"

class MalcolmAIDaemon:
    def __init__(self, interval=60):
        self.client = MalcolmAIClient()
        self.monitor = SystemMonitor()
        self.optimizer = Optimizer()
        self.interval = interval

    def log(self, message):
        with open(LOG_FILE, "a") as f:
            f.write(f"{datetime.now()} :: {message}\n")

    def run(self):
        self.log("=== Malcolm AI Daemon Started ===")
        while True:
            metrics = self.monitor.get_metrics()
            response = self.client.query("Optimize system performance", data=metrics)

            self.log(f"Metrics: {json.dumps(metrics)}")
            self.log(f"AI Response: {json.dumps(response)}")

            # Check if AI suggests optimizations
            if "actions" in response:
                for action in response["actions"]:
                    result = self.optimizer.execute(action.get("type"), action.get("details"))
                    self.log(f"Executed: {result}")

            time.sleep(self.interval)

if __name__ == "__main__":
    daemon = MalcolmAIDaemon(interval=120)  # Every 2 minutes
    daemon.run()
