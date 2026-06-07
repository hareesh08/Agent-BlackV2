import paramiko
import sys
import os
import tarfile
import io
import time

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# ─── CONFIGURE THESE ───────────────────────────────────────────────────────────
HOST = "64.227.177.219"
USER = "root"
PASSWORD = "Do12345@Do"

DOMAIN = "agentblack.hareeshworks.in"
EMAIL = "admin@agentblack.hareeshworks.in"

PROJECT_NAME = "agent-black"
APP_DIR = f"/opt/{PROJECT_NAME}"
CONTROL_PANEL_PORT = 8000
FRONTEND_PORT = 3000

LOCAL_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# ──────────────────────────────────────────────────────────────────────────────


def connect():
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(hostname=HOST, username=USER, password=PASSWORD, timeout=60,
                   allow_agent=False, look_for_keys=False)
    return client


def run(client, cmd, timeout=300):
    transport = client.get_transport()
    ch = transport.open_session()
    ch.settimeout(timeout)
    ch.exec_command(cmd)
    out_lines, err_lines = [], []
    while not ch.exit_status_ready():
        time.sleep(0.5)
    while ch.recv_ready():
        out_lines.append(ch.recv(65536).decode("utf-8", errors="replace"))
    while ch.recv_stderr_ready():
        err_lines.append(ch.recv_stderr(65536).decode("utf-8", errors="replace"))
    code = ch.recv_exit_status()
    ch.close()
    out = "".join(out_lines)
    err = "".join(err_lines)
    label = cmd.split("\n")[0][:80]
    print(f"--- {label} (exit {code}) ---")
    if out.strip(): print(out.rstrip())
    if err.strip(): print(err.rstrip())
    print()
    return code, out, err


def sftp_write(client, remote_path, content):
    sftp = client.open_sftp()
    with sftp.open(remote_path, "w") as f:
        f.write(content)
    sftp.close()


def upload_project(client):
    print(">>> Packaging project...")
    exclude_dirs = {".git", "node_modules", "__pycache__", ".idea", "data", "logs",
                    ".tanstack", "plans", "dist"}
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        for root, dirs, files in os.walk(LOCAL_PROJECT_ROOT):
            dirs[:] = [d for d in dirs if d not in exclude_dirs]
            rel = os.path.relpath(root, LOCAL_PROJECT_ROOT)
            if rel == ".":
                rel = ""
            for f in files:
                if any(f.endswith(e) for e in [".pyc", ".db", ".sqlite"]):
                    continue
                local = os.path.join(root, f)
                arc = os.path.join(rel, f).replace("\\", "/") if rel else f
                tar.add(local, arcname=arc)
    buf.seek(0)
    print(f"    Archive: {len(buf.getvalue()) / 1024 / 1024:.1f} MB")
    sftp = client.open_sftp()
    sftp.putfo(buf, f"/tmp/{PROJECT_NAME}.tar.gz")
    sftp.close()
    run(client, f"rm -rf {APP_DIR} && mkdir -p {APP_DIR}")
    run(client, f"tar -xzf /tmp/{PROJECT_NAME}.tar.gz -C {APP_DIR}/")
    run(client, "rm -f /tmp/agent-black.tar.gz")
    print(">>> Project uploaded.\n")


def setup_swap(client):
    print(">>> Setting up swap space...")
    run(client, """
set -euo pipefail
if [ ! -f /swapfile ]; then
  fallocate -l 1G /swapfile
  chmod 600 /swapfile
  mkswap /swapfile
  swapon /swapfile
  echo '/swapfile none swap sw 0 0' >> /etc/fstab
  echo ">>> 1GB swap created"
else
  echo ">>> Swap already exists"
fi
free -h
""", timeout=60)


def install_nodejs(client):
    run(client, """
set -euo pipefail
current_node=$(node -v 2>/dev/null || echo "none")
if [[ "$current_node" != v22* ]]; then
  echo ">>> Installing Node.js 22 (was $current_node)..."
  curl -fsSL https://deb.nodesource.com/setup_22.x | bash -
  apt install -y nodejs
else
  echo ">>> Node.js $current_node OK"
fi
""", timeout=120)


def build_frontend(client):
    print(">>> Building frontend on VPS...")
    run(client, f"""
set -euo pipefail
cd {APP_DIR}/ui
export NODE_OPTIONS="--max-old-space-size=768"
npm install --legacy-peer-deps
npm run build
""", timeout=600)


def setup_python(client):
    print(">>> Setting up Python environment...")
    run(client, f"""
set -euo pipefail
cd {APP_DIR}
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
pip install uvicorn[standard]
""", timeout=300)


def write_frontend_wrapper(client):
    sftp_write(client, f"{APP_DIR}/ui/server-wrapper.mjs", r"""
import { createServer } from 'node:http';
import { readFile } from 'node:fs/promises';
import { join, extname } from 'node:path';

const PORT = process.env.PORT || 3000;
const PUBLIC_DIR = join(import.meta.dirname, 'dist', 'client');

const MIME = {
  '.html': 'text/html; charset=utf-8',
  '.js': 'application/javascript',
  '.css': 'text/css',
  '.json': 'application/json',
  '.png': 'image/png',
  '.jpg': 'image/jpeg',
  '.svg': 'image/svg+xml',
  '.ico': 'image/x-icon',
  '.woff': 'font/woff',
  '.woff2': 'font/woff2',
};

let ssrHandler;
async function getSSRHandler() {
  if (!ssrHandler) {
    const mod = await import(join(import.meta.dirname, 'dist', 'server', 'server.js'));
    const entry = mod.default || mod;
    ssrHandler = entry.fetch ? entry : { fetch: entry };
  }
  return ssrHandler;
}

const server = createServer(async (req, res) => {
  try {
    const url = new URL(req.url, `http://localhost:${PORT}`);
    if (url.pathname !== '/' || !req.headers.accept?.includes('text/html')) {
      let filePath = join(PUBLIC_DIR, url.pathname);
      try {
        const content = await readFile(filePath);
        const ext = extname(filePath);
        res.writeHead(200, {
          'Content-Type': MIME[ext] || 'application/octet-stream',
          'Cache-Control': ext !== '.html' ? 'public, max-age=31536000, immutable' : 'no-cache',
        });
        res.end(content);
        return;
      } catch {}
    }
    const handler = await getSSRHandler();
    const headers = new Headers();
    for (const [key, value] of Object.entries(req.headers)) {
      if (value) headers.set(key, Array.isArray(value) ? value.join(', ') : value);
    }
    let body = undefined;
    if (['POST', 'PUT', 'PATCH'].includes(req.method)) {
      const chunks = [];
      for await (const chunk of req) chunks.push(chunk);
      body = Buffer.concat(chunks);
    }
    const response = await handler.fetch(new Request(url.href, { method: req.method, headers, body }));
    const resHeaders = {};
    response.headers.forEach((v, k) => { resHeaders[k] = v; });
    res.writeHead(response.status, resHeaders);
    if (response.body) {
      const reader = response.body.getReader();
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        res.write(value);
      }
    }
    res.end();
  } catch (error) {
    console.error('SSR error:', error.message);
    res.writeHead(500, { 'Content-Type': 'text/html; charset=utf-8' });
    res.end('<!DOCTYPE html><html><body><h1>500</h1></body></html>');
  }
});

server.listen(PORT, '0.0.0.0', () => {
  console.log(`Agent Black Frontend running on http://0.0.0.0:${PORT}`);
});
""")


def write_env(client):
    sftp_write(client, f"{APP_DIR}/.env", f"""HOST=0.0.0.0
PORT={CONTROL_PANEL_PORT}
DOMAIN={DOMAIN}
BASE_URL=https://{DOMAIN}
VITE_API_URL=https://{DOMAIN}/api
RESEARCH_AGENT_HOST=127.0.0.1
RESEARCH_AGENT_PORT=8001
SOLUTION_AGENT_HOST=127.0.0.1
SOLUTION_AGENT_PORT=8002
EXPERIMENT_AGENT_HOST=127.0.0.1
EXPERIMENT_AGENT_PORT=8003
""")


def write_nginx_config(client, ssl=False):
    if ssl:
        sftp_write(client, "/etc/nginx/sites-available/agentblack", f"""server {{
    listen 80;
    listen [::]:80;
    server_name {DOMAIN};
    return 301 https://$host$request_uri;
}}

server {{
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name {DOMAIN};

    ssl_certificate /etc/letsencrypt/live/{DOMAIN}/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/{DOMAIN}/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;

    location / {{
        proxy_pass http://127.0.0.1:{FRONTEND_PORT};
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_http_version 1.1;
        proxy_buffering off;
        proxy_cache off;
        proxy_read_timeout 600s;
        proxy_send_timeout 600s;
    }}

    location /api/query/stream/ {{
        proxy_pass http://127.0.0.1:{CONTROL_PANEL_PORT}/api/query/stream/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_http_version 1.1;
        proxy_buffering off;
        proxy_cache off;
        proxy_read_timeout 600s;
        proxy_send_timeout 600s;
        chunked_transfer_encoding on;
    }}

    location /api/ {{
        proxy_pass http://127.0.0.1:{CONTROL_PANEL_PORT}/api/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_http_version 1.1;
        proxy_buffering off;
        proxy_cache off;
        proxy_read_timeout 600s;
        proxy_send_timeout 600s;
    }}

    location /assets/ {{
        proxy_pass http://127.0.0.1:{FRONTEND_PORT}/assets/;
        proxy_set_header Host $host;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }}
}}
""")
    else:
        sftp_write(client, "/etc/nginx/sites-available/agentblack", f"""server {{
    listen 80;
    listen [::]:80;
    server_name {DOMAIN};

    location / {{
        proxy_pass http://127.0.0.1:{FRONTEND_PORT};
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_http_version 1.1;
        proxy_buffering off;
        proxy_cache off;
        proxy_read_timeout 600s;
        proxy_send_timeout 600s;
    }}

    location /api/query/stream/ {{
        proxy_pass http://127.0.0.1:{CONTROL_PANEL_PORT}/api/query/stream/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_http_version 1.1;
        proxy_buffering off;
        proxy_cache off;
        proxy_read_timeout 600s;
        proxy_send_timeout 600s;
        chunked_transfer_encoding on;
    }}

    location /api/ {{
        proxy_pass http://127.0.0.1:{CONTROL_PANEL_PORT}/api/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_http_version 1.1;
        proxy_buffering off;
        proxy_cache off;
        proxy_read_timeout 600s;
        proxy_send_timeout 600s;
    }}

    location /assets/ {{
        proxy_pass http://127.0.0.1:{FRONTEND_PORT}/assets/;
        proxy_set_header Host $host;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }}
}}
""")


def write_systemd_services(client):
    sftp_write(client, "/etc/systemd/system/agent-black-frontend.service", f"""[Unit]
Description=Agent Black Frontend (TanStack Start)
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory={APP_DIR}/ui
Environment=NODE_ENV=production
Environment=PORT={FRONTEND_PORT}
Environment=NODE_OPTIONS=--max-old-space-size=384
ExecStart=/usr/bin/node server-wrapper.mjs
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
""")
    sftp_write(client, "/etc/systemd/system/agent-black-panel.service", f"""[Unit]
Description=Agent Black Control Panel
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory={APP_DIR}
Environment=PATH={APP_DIR}/venv/bin:/usr/local/bin:/usr/bin:/bin
ExecStart={APP_DIR}/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port {CONTROL_PANEL_PORT} --log-level info
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
""")
    sftp_write(client, "/etc/systemd/system/agent-black-research.service", f"""[Unit]
Description=Agent Black Research Agent
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory={APP_DIR}/agents/research-agent
Environment=PATH={APP_DIR}/venv/bin:/usr/local/bin:/usr/bin:/bin
ExecStart={APP_DIR}/venv/bin/uvicorn main:app --host 127.0.0.1 --port 8001 --log-level info
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
""")
    sftp_write(client, "/etc/systemd/system/agent-black-solution.service", f"""[Unit]
Description=Agent Black Solution Agent
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory={APP_DIR}/agents/solution-agent
Environment=PATH={APP_DIR}/venv/bin:/usr/local/bin:/usr/bin:/bin
ExecStart={APP_DIR}/venv/bin/uvicorn main:app --host 127.0.0.1 --port 8002 --log-level info
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
""")
    sftp_write(client, "/etc/systemd/system/agent-black-experiment.service", f"""[Unit]
Description=Agent Black Experiment Agent
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory={APP_DIR}/agents/experiment-agent
Environment=PATH={APP_DIR}/venv/bin:/usr/local/bin:/usr/bin:/bin
ExecStart={APP_DIR}/venv/bin/uvicorn main:app --host 127.0.0.1 --port 8003 --log-level info
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
""")


def setup(client):
    upload_project(client)
    setup_swap(client)

    print(">>> Installing system packages...")
    run(client, """
set -euo pipefail
export DEBIAN_FRONTEND=noninteractive
apt update
apt install -y ca-certificates curl gnupg lsb-release openssl git ufw \
    python3 python3-venv python3-pip \
    nginx certbot python3-certbot-nginx
""", timeout=300)

    install_nodejs(client)
    build_frontend(client)
    setup_python(client)

    write_frontend_wrapper(client)
    write_env(client)

    write_systemd_services(client)
    write_nginx_config(client, ssl=False)

    print(">>> Configuring firewall...")
    run(client, "ufw allow 22/tcp || true; ufw allow 80/tcp || true; ufw allow 443/tcp || true; ufw --force enable", timeout=30)

    print(">>> Starting services...")
    run(client, """
set -euo pipefail
rm -f /etc/nginx/sites-enabled/default
ln -sf /etc/nginx/sites-available/agentblack /etc/nginx/sites-enabled/agentblack
nginx -t
systemctl enable --now nginx
systemctl reload nginx
systemctl daemon-reload
systemctl enable --now agent-black-frontend
systemctl enable --now agent-black-research
systemctl enable --now agent-black-solution
systemctl enable --now agent-black-experiment
systemctl enable --now agent-black-panel
sleep 5
""", timeout=60)

    print(">>> Obtaining SSL certificate...")
    run(client, f"certbot --nginx -d {DOMAIN} --email {EMAIL} --agree-tos --non-interactive 2>&1 || true", timeout=300)

    write_nginx_config(client, ssl=True)
    run(client, "nginx -t && systemctl reload nginx")

    time.sleep(2)
    print(">>> Final verification...")
    run(client, f"""
echo "=== Services ==="
systemctl is-active agent-black-frontend agent-black-panel agent-black-research agent-black-solution agent-black-experiment nginx

echo ""
echo "=== Health ==="
curl -s -o /dev/null -w "HTTPS: %{{http_code}}" https://{DOMAIN}/
echo ""
curl -s -o /dev/null -w "Frontend: %{{http_code}}" http://127.0.0.1:{FRONTEND_PORT}/
echo ""
curl -s http://127.0.0.1:{CONTROL_PANEL_PORT}/ | head -1
echo ""
free -h
""", timeout=30)

    print("\n" + "=" * 60)
    print("  DEPLOYMENT COMPLETE!")
    print(f"  Site : https://{DOMAIN}")
    print(f"  API  : https://{DOMAIN}/api/")
    print("=" * 60)


def update_version(client):
    upload_project(client)
    setup_swap(client)
    install_nodejs(client)
    build_frontend(client)
    setup_python(client)

    write_frontend_wrapper(client)
    write_env(client)

    # Check if SSL cert exists
    _, cert_check, _ = run(client, f"certbot certificates 2>/dev/null | grep -c '{DOMAIN}' || echo 0", timeout=10)
    has_ssl = "1" in cert_check

    write_nginx_config(client, ssl=has_ssl)
    write_systemd_services(client)

    print(">>> Restarting services...")
    run(client, """
set -euo pipefail
systemctl daemon-reload
nginx -t && systemctl reload nginx
systemctl restart agent-black-frontend
systemctl restart agent-black-research
systemctl restart agent-black-solution
systemctl restart agent-black-experiment
systemctl restart agent-black-panel
sleep 5
""", timeout=120)

    time.sleep(2)
    run(client, f"""
echo "=== Services ==="
systemctl is-active agent-black-frontend agent-black-panel agent-black-research agent-black-solution agent-black-experiment nginx
echo ""
curl -s -o /dev/null -w "HTTPS: %{{http_code}}" https://{DOMAIN}/ || echo "HTTPS failed"
echo ""
curl -s -o /dev/null -w "Frontend: %{{http_code}}" http://127.0.0.1:{FRONTEND_PORT}/
echo ""
free -h
""", timeout=30)


def restart_services(client):
    run(client, """
systemctl daemon-reload
systemctl restart agent-black-frontend agent-black-research agent-black-solution agent-black-experiment agent-black-panel
systemctl reload nginx
sleep 3
systemctl is-active agent-black-frontend agent-black-panel agent-black-research agent-black-solution agent-black-experiment nginx
""", timeout=60)


def view_logs(client):
    run(client, """
echo "=== Frontend ==="
journalctl -u agent-black-frontend --no-pager -n 20
echo ""
echo "=== Control Panel ==="
journalctl -u agent-black-panel --no-pager -n 20
echo ""
echo "=== Nginx ==="
tail -10 /var/log/nginx/error.log 2>/dev/null || true
""", timeout=30)


def check_status(client):
    run(client, """
echo "=== Services ==="
systemctl is-active agent-black-frontend agent-black-panel agent-black-research agent-black-solution agent-black-experiment nginx 2>/dev/null
echo ""
echo "=== Health ==="
curl -s -o /dev/null -w "HTTPS: %{http_code}\n" https://agentblack.hareeshworks.in/ 2>/dev/null || echo "HTTPS: failed"
curl -s -o /dev/null -w "Frontend: %{http_code}\n" http://127.0.0.1:3000/ || echo "Frontend: failed"
curl -s http://127.0.0.1:8000/ | head -1 || echo "Panel: failed"
echo ""
free -h
""", timeout=30)


def renew_ssl(client):
    run(client, "certbot renew --non-interactive || true; nginx -t && systemctl reload nginx", timeout=300)


def main():
    print("=" * 60)
    print("  AGENT BLACK - SERVER DEPLOYER (No Docker)")
    print("=" * 60)
    print(f"  Server : {USER}@{HOST}")
    print(f"  Domain : {DOMAIN}")
    print("=" * 60)
    print()
    print("  1) setup      - Full deploy")
    print("  2) status     - Check status")
    print("  3) update     - Upload code & restart")
    print("  4) restart    - Restart services")
    print("  5) logs       - View logs")
    print("  6) ssl-renew  - Renew SSL")
    print()

    if len(sys.argv) > 1:
        choice = sys.argv[1].strip()
    else:
        choice = input("  Enter choice (1-6): ").strip()

    actions = {
        "1": ("setup", setup),
        "2": ("status", check_status),
        "3": ("update", update_version),
        "4": ("restart", restart_services),
        "5": ("logs", view_logs),
        "6": ("ssl-renew", renew_ssl),
    }
    if choice not in actions:
        print("  Invalid choice.")
        return

    name, fn = actions[choice]
    print(f"\n  Running: {name} ...\n")
    client = connect()
    fn(client)
    client.close()
    print("\nDone.")


if __name__ == "__main__":
    main()
