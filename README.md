# SwapList App

A local web application for generating swapped 3MF files for 3D printing.

## 🚀 Quick Start (Local Dev)

**Mac/Linux:**
```bash
./start_app.sh
```
This launches the Backend (FastAPI) and Frontend (Vite) automatically.
Visit: **http://localhost:5173**

---

## 🛠 Project Structure

*   **`backend/`**: Python FastAPI app.
    *   Uses `uv` for dependency management.
    *   `app.py`: Entry point.
    *   `core.py`: Processing logic (3MF operations).
*   **`frontend/`**: React + Vite app.
    *   Uses `npm`.
    *   `src/`: Components and Logic.
*   **`deployment/`**: Configuration for Production.
    *   `nginx.conf`: Web Server config.
    *   `swaplist.service`: Systemd service.
    *   `DEPLOY.md`: **Use this for AWS Lightsail Deployment.**

## 📦 Requirements
*   **Node.js** (Latest/Current)
*   **uv** (Python tools)

## ☁️ Deployment
See **`deployment/DEPLOY.md`** for full instructions on setting up the AWS Lightsail server, Security, and Updates.
