# SwapList App

A local web application for generating swapped 3MF files for 3D printing.

## Requirements
- Python 3.9+
- Node.js (Latest)
- NPM
- [uv](https://docs.astral.sh/uv/) (Python package manager)

## Installation
(If you received this folder as a standalone package)

1.  Ensure you have `uv` and Node.js installed.
2.  Install Python dependencies:
    ```bash
    # This happens automatically when running with 'uv run',
    # or explicitly:
    uv sync
    ```
3.  Install Frontend dependencies (if not already present):
    ```bash
    cd frontend
    npm install
    cd ..
    ```

## Usage

### Simple Start (Mac/Linux)
Run the provided startup script:
```bash
./start_app.sh
```
This will launch both the backend (via `uv`) and frontend servers.
Open **http://localhost:5173** in your browser.

### Manual Start
1.  **Backend**:
    ```bash
    uv run -m uvicorn backend.app:app --reload --port 8000
    ```
2.  **Frontend**:
    ```bash
    cd frontend
    npm run dev
    ```

## Features
- Drag & Drop `.3mf` files.
- Reorder plates.
- Set copy counts.
- Generate unified Swap `.3mf`.

## Notes
- Generated files are saved in `backend/static/` temporarily.
