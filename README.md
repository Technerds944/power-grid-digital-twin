# Power Grid Digital Twin - Smart Home Edition

## Prerequisites
- Python 3.8+
- Flask

## Installation
Ensure you have the virtual environment set up (if not already):
```bash
python3 -m venv venv
source venv/bin/activate
pip install flask
```

## Running the System

### 1. Start the Dashboard (Backend)
This runs the Digital Twin Engine and Web Server.
```bash
./venv/bin/python app.py
```
*Access the Dashboard at:* [http://localhost:5000](http://localhost:5000)

### 2. Start the Admin Console
This allows you to inject faults (Grid Surges, Home Wear, etc.).
Open a new terminal window:
```bash
./venv/bin/python admin_console.py
```

## Usage
1.  **Monitor**: Watch the Dashboard for real-time Voltage/Current data.
2.  **Simulate**: Use the Admin Console to trigger events.
    *   Select **Option 4** for Smart Home Faults.
    *   **[A] Grid Surge**: Triggers "PROTECTION ACTIVE" (Red).
    *   **[B] Appliance Wear**: Triggers "WARNING" (Orange).
