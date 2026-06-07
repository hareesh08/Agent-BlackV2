import paramiko
import sys

HOST = "64.227.177.219"
USER = "root"
PASSWORD = "Do12345@Do"
APP_DIR = "/opt/agent-black"
CONTROL_PANEL_PORT = 8000

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(hostname=HOST, username=USER, password=PASSWORD, timeout=20, allow_agent=False, look_for_keys=False)

def run(cmd, timeout=60):
    stdin, stdout, stderr = client.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode("utf-8", errors="replace")
    err = stderr.read().decode("utf-8", errors="replace")
    code = stdout.channel.recv_exit_status()
    return code, out, err

checks = [
    ("Docker Containers", "docker ps -a --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'"),
    ("Docker Compose", f"cd {APP_DIR} && docker compose ps 2>&1"),
    ("Control Panel", f"curl -s http://127.0.0.1:{CONTROL_PANEL_PORT}/api/status 2>&1"),
    ("Control Panel Port", f"curl -s http://127.0.0.1:{CONTROL_PANEL_PORT}/ 2>&1"),
    ("Frontend Port", "curl -s http://127.0.0.1:8080/ 2>&1 || echo 'frontend not responding'"),
    ("Nginx Config", "nginx -t 2>&1"),
    ("Nginx Site", "cat /etc/nginx/sites-available/agentblack 2>&1"),
    ("Compose Logs", f"cd {APP_DIR} && docker compose logs --tail 30 2>&1"),
]

for label, cmd in checks:
    code, out, err = run(cmd, timeout=120)
    print(f"=== {label} (exit {code}) ===")
    if out.strip():
        print(out.rstrip())
    if err.strip():
        print(err.rstrip())
    print()

client.close()
