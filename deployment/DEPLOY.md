# Deployment Guide: AWS Lightsail

This guide assumes you have an AWS Lightsail instance (Ubuntu 22.04 or similar) and SSH access.

## 1. Prepare the Server
SSH into your instance:
```bash
ssh ubuntu@<your-ip>
```

Update and install dependencies (Nginx for web server, Node.js for frontend build):
```bash
sudo apt update
sudo apt install -y nginx unzip
# Install Node.js (v18+)
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt install -y nodejs
```

Install `uv` (Python package manager):
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
source $HOME/.local/bin/env
```

## 2. Upload the Application
From your local machine (parent directory of `plate_swap_list_app`), run:
```bash
# E.g. using scp
scp -r plate_swap_list_app ubuntu@<your-ip>:~/swaplist
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
Configure Nginx to serve the frontend and proxy the API.

1.  Edit your Nginx config (e.g., default site):
    ```bash
    sudo nano /etc/nginx/sites-available/default
    ```
2.  Insert the blocks from `deployment/nginx.conf` inside your `server { ... }` block (the one handling talktocaio.com).
    *   Make sure `server_name` matches your domain.
    *   Ensure the paths (`/opt/swaplist/...`) match where you put the files.

3.  Test and restart Nginx:
    ```bash
    sudo nginx -t
    sudo systemctl restart nginx
    ```

## 7. Verify
Visit **https://talktocaio.com/a1mini-swap/**
- You should see the UI.
- Dragging a file should upload correctly (check Network tab for calls to `/a1mini-swap/api/upload`).
