# Deployment Guide: SwapList App
*Target: AWS Lightsail (Ubuntu)*

## 1. Quick Start (Maintenance)
**How to update the site after making code changes:**

1.  **Local Machine:** Push to GitHub.
    ```bash
    git add .
    git commit -m "update"
    git push
    ```
2.  **Server:** Run the update script.
    ```bash
    ssh -i your-key.pem ubuntu@talktocaio.com
    /opt/swaplist/deployment/update.sh
    ```

---

## 2. Initial Server Setup (One-Time)

### 2.1 Prepare System
```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y nginx unzip ufw fail2ban

# Install Node.js
curl -fsSL https://deb.nodesource.com/setup_current.x | sudo -E bash -
sudo apt install -y nodejs

# Install uv (Python)
curl -LsSf https://astral.sh/uv/install.sh | sh
source $HOME/.local/bin/env
```

### 2.2 Setup Secure Access (Git Deploy Keys)
Don't use personal passwords.
1.  **Generate Key:** `ssh-keygen -t ed25519 -C "deploy" -f ~/.ssh/github_deploy`
2.  **Add to GitHub:** Repo Settings -> Deploy Keys (Read Only).
3.  **Config SSH:** Add to `~/.ssh/config`:
    ```text
    Host github.com
      IdentityFile ~/.ssh/github_deploy
    ```
4.  **Clone Repo:**
    ```bash
    git clone git@github.com:youruser/your-repo.git /opt/swaplist
    # Fix permissions
    sudo chown -R ubuntu:ubuntu /opt/swaplist
    ```

### 2.3 Configure Nginx
Use the provided config.
```bash
# Install & Enable
sudo cp /opt/swaplist/deployment/nginx.conf /etc/nginx/sites-available/swaplist
sudo ln -s /etc/nginx/sites-available/swaplist /etc/nginx/sites-enabled/
sudo rm /etc/nginx/sites-enabled/default

# Test & Restart
sudo nginx -t
sudo systemctl restart nginx
```

### 2.4 Configure Systemd (Background Service)
Keep the backend running.
```bash
sudo cp /opt/swaplist/deployment/swaplist.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable swaplist
sudo systemctl start swaplist
```

### 2.5 Setup SSL (HTTPS)
Get the green lock.
```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d talktocaio.com -d www.talktocaio.com
```

---

## 3. Security Hardening (Best Practices)

### 3.1 Network Firewall (UFW)
Double-lock the connection (AWS + Host).
```bash
sudo ufw allow OpenSSH
sudo ufw allow "Nginx Full"
sudo ufw enable
```
*Note: Ensure AWS Lightsail Firewall also allows ports 80 (HTTP) and 443 (HTTPS).*

### 3.2 Nginx Security
Our `nginx.conf` includes:
*   Rate Limiting (10 req/s) - Prevents abuse.
*   Security Headers (X-Frame, XSS-Protection) - Prevents browser attacks.

### 3.3 Fail2Ban
Prevents brute-force SSH attacks automatically.
```bash
sudo systemctl enable fail2ban
sudo systemctl start fail2ban
```

---

## 4. Troubleshooting

### "Connection Refused"
*   **Meaning:** Nginx is down.
*   **Fix:** `sudo systemctl restart nginx` (Check logs if it fails: `sudo nginx -t`).

### "Took too long to respond"
*   **Meaning:** Firewall is blocking access.
*   **Fix:** Open Ports 80 and 443 in **AWS Lightsail Networking** console.

### "404 Not Found"
*   **Meaning:** Nginx works, but can't find files.
*   **Checks:**
    1.  Did you visit the correct path? `/a1mini-swap/`
    2.  Does the build exist? `ls /opt/swaplist/frontend/dist`
    3.  Permissions? `sudo chmod -R 755 /opt/swaplist`

### "500 Internal Server Error"
*   **Meaning:** Crash or Config Loop.
*   **Debug:** `sudo tail -n 20 /var/log/nginx/error.log`
