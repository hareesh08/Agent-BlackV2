import paramiko
import sys


# ─── CONFIGURE THESE ───────────────────────────────────────────────────────────
HOST = "139.59.2.234"
USER = "root"
PASSWORD = "Do12345@Do"

DOMAIN = "apiv5.hareeshworks.in"
EMAIL = "admin@apiv5.hareeshworks.in"

DOCKER_IMAGE = "diegosouzapw/omniroute:latest"
CONTAINER_NAME = "omniroute"
APP_PORT = 20128
DATA_VOLUME = "omniroute-data"
APP_DIR = "/opt/omniroute"
# ──────────────────────────────────────────────────────────────────────────────


def run(client, command, timeout=120):
    stdin, stdout, stderr = client.exec_command(command, timeout=timeout)
    out = stdout.read().decode("utf-8", errors="replace")
    err = stderr.read().decode("utf-8", errors="replace")
    code = stdout.channel.recv_exit_status()
    return code, out, err


def log(label, out, err, code):
    print(f"=== {label} ===")
    if out.strip():
        print(out.rstrip())
    if err.strip():
        print(err.rstrip())
    print(f"--- EXIT {code} ---")
    print()


def connect():
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(
        hostname=HOST,
        username=USER,
        password=PASSWORD,
        timeout=20,
        allow_agent=False,
        look_for_keys=False,
    )
    return client


def check_status(client):
    commands = [
        ("Packages", "dpkg -l docker-ce docker-ce-cli containerd.io docker-compose-plugin nginx certbot python3-certbot-nginx ufw 2>/dev/null | tail -n +6 || true"),
        ("Services", "systemctl is-active docker nginx ufw 2>/dev/null || true"),
        ("Containers", "docker ps --format '{{.Names}} {{.Status}} {{.Ports}}' 2>/dev/null || true"),
        ("Env File", "test -f /opt/omniroute/.env && echo env_exists || echo no_env"),
        ("Nginx Site", "test -f /etc/nginx/sites-enabled/omniroute && echo nginx_site || echo no_site"),
        ("Nginx Test", "nginx -t 2>&1 || true"),
        ("SSL Certs", "certbot certificates 2>/dev/null || true"),
        ("Nginx Logs", "journalctl -u nginx --no-pager -n 20 2>/dev/null || true"),
        ("Container Logs", f"docker logs {CONTAINER_NAME} --tail 20 2>/dev/null || true"),
        ("Docker Image", f"docker inspect --format='{{{{.Config.Image}}}} {{{{.Created}}}}' {CONTAINER_NAME} 2>/dev/null || true"),
    ]
    for label, cmd in commands:
        code, out, err = run(client, cmd, timeout=180)
        log(label, out, err, code)


def setup(client):
    bootstrap = f'''
set -euo pipefail
export DEBIAN_FRONTEND=noninteractive

# ── System packages ──
apt update
apt install -y ca-certificates curl gnupg lsb-release openssl

# ── Docker repo ──
install -m 0755 -d /etc/apt/keyrings
if [ ! -f /etc/apt/keyrings/docker.gpg ]; then
  curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
  chmod a+r /etc/apt/keyrings/docker.gpg
fi
cat >/etc/apt/sources.list.d/docker.list <<EOF
deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable
EOF
apt update
apt install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
systemctl enable --now docker

# ── App directory + secrets ──
mkdir -p {APP_DIR}
JWT_SECRET=$(openssl rand -hex 32)
API_KEY_SECRET=$(openssl rand -hex 32)
STORAGE_ENCRYPTION_KEY=$(openssl rand -hex 32)
MACHINE_ID_SALT=$(openssl rand -hex 32)
OMNIROUTE_WS_BRIDGE_SECRET=$(openssl rand -hex 32)
cat >{APP_DIR}/.env <<EOF
JWT_SECRET=$JWT_SECRET
INITIAL_PASSWORD=YourStrongPassword123!
API_KEY_SECRET=$API_KEY_SECRET
STORAGE_ENCRYPTION_KEY=$STORAGE_ENCRYPTION_KEY
STORAGE_ENCRYPTION_KEY_VERSION=v1
MACHINE_ID_SALT=$MACHINE_ID_SALT
OMNIROUTE_WS_BRIDGE_SECRET=$OMNIROUTE_WS_BRIDGE_SECRET
PORT={APP_PORT}
NODE_ENV=production
HOSTNAME=0.0.0.0
DATA_DIR=/app/data
APP_LOG_TO_FILE=true
AUTH_COOKIE_SECURE=true
REQUIRE_API_KEY=false
BASE_URL=https://{DOMAIN}
NEXT_PUBLIC_BASE_URL=https://{DOMAIN}
EOF
chmod 600 {APP_DIR}/.env

# ── Docker container ──
if docker ps -a --format '{{{{.Names}}}}' | grep -qx {CONTAINER_NAME}; then docker rm -f {CONTAINER_NAME}; fi
docker pull {DOCKER_IMAGE}
docker run -d --name {CONTAINER_NAME} --restart unless-stopped --env-file {APP_DIR}/.env -p 127.0.0.1:{APP_PORT}:{APP_PORT} -v {DATA_VOLUME}:/app/data {DOCKER_IMAGE}

# ── Nginx reverse proxy ──
cat >/etc/nginx/sites-available/omniroute <<NGINX
server {{
    listen 80;
    listen [::]:80;
    server_name {DOMAIN};

    location / {{
        proxy_pass http://127.0.0.1:{APP_PORT};
        proxy_set_header Host \\$host;
        proxy_set_header X-Real-IP \\$remote_addr;
        proxy_set_header X-Forwarded-For \\$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \\$scheme;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \\$http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_buffering off;
        proxy_cache off;
        proxy_read_timeout 600s;
        proxy_send_timeout 600s;
    }}
}}
NGINX
rm -f /etc/nginx/sites-enabled/default
ln -sf /etc/nginx/sites-available/omniroute /etc/nginx/sites-enabled/omniroute
nginx -t
systemctl enable --now nginx
systemctl reload nginx

# ── Firewall ──
ufw allow 22/tcp || true
ufw allow 80/tcp || true
ufw allow 443/tcp || true
ufw --force enable

# ── SSL certificate ──
certbot --nginx -d {DOMAIN} --email {EMAIL} --agree-tos --non-interactive || true
systemctl reload nginx

# ── Health check ──
curl -fsS http://127.0.0.1:{APP_PORT}/health || true
docker ps --format 'table {{{{.Names}}}}\\t{{{{.Status}}}}\\t{{{{.Ports}}}}'
certbot certificates 2>/dev/null || true
'''
    code, out, err = run(client, bootstrap, timeout=7200)
    log("SETUP COMPLETE", out, err, code)


def update_version(client):
    update_script = f'''
set -euo pipefail
echo ">>> Pulling latest image: {DOCKER_IMAGE}"
docker pull {DOCKER_IMAGE}

echo ">>> Stopping current container..."
docker stop {CONTAINER_NAME} || true
docker rm {CONTAINER_NAME} || true

echo ">>> Starting new container..."
docker run -d --name {CONTAINER_NAME} --restart unless-stopped --env-file {APP_DIR}/.env -p 127.0.0.1:{APP_PORT}:{APP_PORT} -v {DATA_VOLUME}:/app/data {DOCKER_IMAGE}

echo ">>> Waiting for container to be healthy..."
sleep 5

echo ">>> Container status:"
docker ps --filter name={CONTAINER_NAME} --format 'table {{{{.Names}}}}\\t{{{{.Status}}}}\\t{{{{.Ports}}}}'

echo ">>> Health check:"
curl -fsS http://127.0.0.1:{APP_PORT}/health || echo "Health check failed or endpoint not available"

echo ">>> Old images cleaned:"
docker image prune -f || true
'''
    code, out, err = run(client, update_script, timeout=3600)
    log("UPDATE COMPLETE", out, err, code)


def renew_ssl(client):
    renew_script = f'''
set -euo pipefail
echo ">>> Current certificates:"
certbot certificates 2>/dev/null || true

echo ">>> Attempting certificate renewal..."
certbot renew --non-interactive || true

echo ">>> Reloading nginx..."
nginx -t && systemctl reload nginx

echo ">>> Certificates after renewal:"
certbot certificates 2>/dev/null || true
'''
    code, out, err = run(client, renew_script, timeout=600)
    log("SSL RENEW COMPLETE", out, err, code)


def full_update(client):
    update_script = f'''
set -euo pipefail
export DEBIAN_FRONTEND=noninteractive

echo ">>> Updating system packages..."
apt update && apt upgrade -y || true

echo ">>> Updating Docker..."
apt install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin || true

echo ">>> Pulling latest image: {DOCKER_IMAGE}"
docker pull {DOCKER_IMAGE}

echo ">>> Stopping current container..."
docker stop {CONTAINER_NAME} || true
docker rm {CONTAINER_NAME} || true

echo ">>> Starting new container..."
docker run -d --name {CONTAINER_NAME} --restart unless-stopped --env-file {APP_DIR}/.env -p 127.0.0.1:{APP_PORT}:{APP_PORT} -v {DATA_VOLUME}:/app/data {DOCKER_IMAGE}

echo ">>> Waiting for container..."
sleep 5

echo ">>> Updating certbot..."
apt install -y certbot python3-certbot-nginx || true

echo ">>> Attempting SSL renewal..."
certbot renew --non-interactive || true
nginx -t && systemctl reload nginx

echo ">>> Cleaning old Docker images..."
docker image prune -f || true

echo ">>> Final status:"
docker ps --filter name={CONTAINER_NAME} --format 'table {{{{.Names}}}}\\t{{{{.Status}}}}\\t{{{{.Ports}}}}'
curl -fsS http://127.0.0.1:{APP_PORT}/health || echo "Health check endpoint not available"
certbot certificates 2>/dev/null || true
'''
    code, out, err = run(client, update_script, timeout=7200)
    log("FULL UPDATE COMPLETE", out, err, code)


def restart_services(client):
    restart_script = f'''
set -euo pipefail
echo ">>> Restarting Docker container..."
docker restart {CONTAINER_NAME}

echo ">>> Restarting Nginx..."
systemctl restart nginx

echo ">>> Service status:"
systemctl is-active docker nginx
docker ps --filter name={CONTAINER_NAME} --format 'table {{{{.Names}}}}\\t{{{{.Status}}}}\\t{{{{.Ports}}}}'

echo ">>> Health check:"
curl -fsS http://127.0.0.1:{APP_PORT}/health || echo "Health check failed"
'''
    code, out, err = run(client, restart_script, timeout=300)
    log("RESTART COMPLETE", out, err, code)


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

    print("=" * 50)
    print("  OMNIROUTE REMOTE SERVER MANAGER V2")
    print("=" * 50)
    print(f"  Server : {USER}@{HOST}")
    print(f"  Domain : {DOMAIN}")
    print(f"  Email  : {EMAIL}")
    print("=" * 50)
    print()
    print("  1) setup        - Fresh install (Docker, Nginx, SSL, Omniroute)")
    print("  2) status       - Check server & container status")
    print("  3) update       - Pull latest image & restart container")
    print("  4) ssl-renew    - Renew SSL certificate & reload Nginx")
    print("  5) full-update  - System packages + Docker image + SSL renewal")
    print("  6) restart      - Restart Docker container & Nginx")
    print()

    choice = input("  Enter choice (1-6): ").strip()

    actions = {
        "1": ("setup", setup),
        "2": ("status", check_status),
        "3": ("update", update_version),
        "4": ("ssl-renew", renew_ssl),
        "5": ("full-update", full_update),
        "6": ("restart", restart_services),
    }

    if choice not in actions:
        print("  Invalid choice.")
        return

    action_name, action_fn = actions[choice]
    print(f"\n  Running: {action_name} ...\n")

    client = connect()
    action_fn(client)
    client.close()
    print("Done.")


if __name__ == "__main__":
    main()
