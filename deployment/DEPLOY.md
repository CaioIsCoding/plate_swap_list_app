# Deployment Guide: AWS Lightsail

This guide assumes you have an AWS Lightsail instance (Ubuntu 22.04 or similar) and SSH access.

## 1. Prepare the Server
SSH into your instance:
```bash
# If using a key file (.pem):
chmod 400 your-key.pem
ssh -i path/to/your-key.pem ubuntu@<your-ip>
```

Update and install dependencies (Nginx for web server, Node.js for frontend build):
```bash
sudo apt update
sudo apt install -y nginx unzip
# Install Node.js (Latest/Current)
curl -fsSL https://deb.nodesource.com/setup_current.x | sudo -E bash -
sudo apt install -y nodejs
```

Install `uv` (Python package manager):
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
source $HOME/.local/bin/env
```

## 2. Upload the Application
From your local machine (parent directory of `plate_swap_list_app`), run:
# PRO TIP: Zip it first to save time! (node_modules has thousands of files)
# Run this locally:
rm -rf plate_swap_list_app/frontend/node_modules
rm -rf plate_swap_list_app/.venv
tar -czf swaplist.tar.gz plate_swap_list_app

# Send the single file
scp -i path/to/your-key.pem swaplist.tar.gz ubuntu@<your-ip>:~
```

### 2.1 Extract on Server
On the server:
```bash
tar -xzf swaplist.tar.gz
# Now you have the ~/plate_swap_list_app folder
mv plate_swap_list_app swaplist
```

## 3. Setup Application Directory
On the server:
```bash
# Move to /opt for persistence/convention (optional, but robust)
sudo mv ~/swaplist /opt/swaplist
sudo chown -R ubuntu:ubuntu /opt/swaplist
cd /opt/swaplist
```

## 4. Build Frontend
Build the static assets for production:
```bash
cd frontend
npm install
npm run build
# This creates /opt/swaplist/frontend/dist
cd ..
```

## 5. Setup Backend (Systemd)
Configure the backend to run automatically.

1.  Copy the service file:
    ```bash
    sudo cp deployment/swaplist.service /etc/systemd/system/
    ```
2.  Edit it if necessary (check paths/users):
    ```bash
    sudo nano /etc/systemd/system/swaplist.service
    # Verify ExecStart path for 'uv' (run 'which uv' to check path)
    ```
3.  Start the service:
    ```bash
    sudo systemctl daemon-reload
    sudo systemctl enable swaplist
    sudo systemctl start swaplist
    sudo systemctl status swaplist
    ```

## 6. Setup Nginx (Reverse Proxy)
Instead of editing files manually, we'll install our config.

1.  **Install the config:**
    ```bash
    # Copy our ready-made config
    sudo cp deployment/nginx.conf /etc/nginx/sites-available/swaplist
    ```

2.  **Enable it:**
    ```bash
    # Link it to sites-enabled
    sudo ln -s /etc/nginx/sites-available/swaplist /etc/nginx/sites-enabled/
    
    # (Optional) Disable the default "Welcome to Nginx" page
    sudo rm /etc/nginx/sites-enabled/default
    ```

3.  **Test and Restart:**
    ```bash
    sudo nginx -t
    sudo systemctl restart nginx
    ```

## 7. Verify
Visit **https://talktocaio.com/a1mini-swap/**
- You should see the UI.
- Dragging a file should upload correctly (check Network tab for calls to `/a1mini-swap/api/upload`).

## 8. DNS (Route53)
To make **talktocaio.com** resolve to your LightSail instance:

1.  **Get your Static IP:**
    *   In the Lightsail Console, go to **Networking**.
    *   Create a static IP and attach it to your instance.

2.  **Configure Route53:**
    *   Go to the Route53 Console -> **Hosted Zones**.
    *   Select `talktocaio.com`.
    *   Create a **Record**:
        *   **Record Name:** `talktocaio.com` (leave empty for root)
        *   **Record Type:** A - Routes traffic to an IPv4 address
        *   **Value:** <Your Lightsail Static IP>
    *   (Optional) Create a CNAME for `www`:
        *   **Name:** `www`
        *   **Type:** CNAME
        *   **Value:** `talktocaio.com`

## 9. Firewall (IMPORTANT)
If the site says "Took too long to respond":

1.  Go to **Lightsail Console** -> **Networking**.
2.  Under **IPv4 Firewall**, make sure you allow:
    *   **HTTP** (TCP 80)
    *   **HTTPS** (TCP 443)
3.  By default, only SSH (22) is open. **You must add HTTP/HTTPS rules.**

## 10. "Connection Refused" Error
If the site says "Refused to connect":
**This means the Firewall is OK, but Nginx is not running.**

1.  SSH into the server.
2.  Check Nginx status:
    ```bash
    sudo systemctl status nginx
    ```
    (If it says "inactive" or "failed", it's not running)
3.  Check for config errors:
    ```bash
    sudo nginx -t
    ```
4.  Restart it:
    ```bash
    sudo systemctl restart nginx
    ```

## 11. Enable HTTPS (SSL)
"Connection Refused" on **https://** happens if you haven't set up SSL yet.

1.  Install Certbot:
    ```bash
    sudo apt install -y certbot python3-certbot-nginx
    ```
2.  Run it:
    ```bash
    sudo certbot --nginx -d talktocaio.com -d www.talktocaio.com
    ```
    (Follow the prompts. It will automatically update your Nginx config to support HTTPS.)

## 12. "404 Not Found" Error
If you see a white page with "404 Not Found":

1.  **Check the URL:**
    You must visit **https://talktocaio.com/a1mini-swap/**
    (If you go to just talktocaio.com, it will 404 because we only configured the /a1mini-swap path).

2.  **Check the Build:**
    Ensure the files actually exist on the server:
    ```bash
    ls /opt/swaplist/frontend/dist
    ```
    (You should see `index.html` and an `assets` folder).
    *   **If empty:** Go to `/opt/swaplist/frontend` and run `npm run build` again.

3.  **Check Permissions:**
    Nginx needs to read the files.
    ```bash
    sudo chmod -R 755 /opt/swaplist
    ```

## 13. "500 Internal Server Error"
This usually means a configuration error in Nginx or a permission issue.

1.  **Check Nginx Logs (The Truth):**
    ```bash
    sudo tail -n 20 /var/log/nginx/error.log
    ```
    *   If it says "rewrite or internal redirection cycle", check your `try_files` config.
    *   If it says "permission denied", run the chmod command above.
    *   If it says "directory index of ... is forbidden", ensure `index.html` exists in the `alias` folder.

## 14. Security Hardening (Recommended)
Now that it works, let's lock it down.

### 14.1 Update Nginx Security
Update your `default` config with the new security headers and rate limiting (already in `deployment/nginx.conf`).
```bash
# 1. Edit the file
sudo nano /etc/nginx/sites-available/default
# 2. Add the "limit_req_zone" line at the very top (outside server block)
# 3. Add the "limit_req" and "add_header" lines inside server/location blocks
# 4. Restart
sudo systemctl restart nginx
```

### 14.2 Auto-Updates
Keep the OS patched automatically.
```bash
sudo apt install -y unattended-upgrades
sudo dpkg-reconfigure --priority=low unattended-upgrades
```

### 14.3 Block Brute Force (Fail2Ban)
Ban IPs that try to guess your SSH password.
```bash
sudo apt install -y fail2ban
sudo systemctl enable fail2ban
sudo systemctl start fail2ban
```

### 14.4 Disable Password Login (SSH)
Ensure only your Key File (.pem) works.
```bash
sudo nano /etc/ssh/sshd_config
# Find and set:
# PasswordAuthentication no
# PubkeyAuthentication yes

# Restart SSH
sudo systemctl restart ssh
```

## 15. Continuous Updates (The "Git" Way)
Instead of SCPing files manually every time, use Git.

### 15.1 Secure Setup (Deploy Keys)
**Crucial:** Do NOT use your personal GitHub password or main SSH key. Use a **Deploy Key**.

1.  **On the Server:** Generate a new key.
    ```bash
    ssh-keygen -t ed25519 -C "lightsail-deploy" -f ~/.ssh/github_deploy
    # Press Enter for empty passphrase
    cat ~/.ssh/github_deploy.pub
    ```

2.  **On GitHub:**
    *   Go to your Repository -> **Settings** -> **Deploy keys**.
    *   Click **Add deploy key**.
    *   Paste the key you copied.
    *   **Do NOT** check "Allow write access" (Read-only is safer).

3.  **Configure Server:**
    Tell SSH to use this key for GitHub.
    ```bash
    nano ~/.ssh/config
    ```
    Add this:
    ```text
    Host github.com
      IdentityFile ~/.ssh/github_deploy
    ```
    Now `git checkout` / `git pull` will work securely without your personal credentials.

### 15.2 The Workflow
1.  **Local Machine:** Push changes (`git push`).
2.  **Server:** Authenticate and clone (first time):
    ```bash
    git clone git@github.com:youruser/your-repo.git /opt/swaplist
    ```
3.  **Update:**
    Run the script:
    ```bash
    chmod +x /opt/swaplist/deployment/update.sh
    /opt/swaplist/deployment/update.sh
    ```
