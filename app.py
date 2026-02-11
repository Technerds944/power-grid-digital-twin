import sqlite3
import threading
import time
import random
import math
from typing import List, Dict, Any, Optional, Tuple
from flask import Flask, jsonify, render_template, request

# ==========================================
# CONFIGURATION & SETUP
# ==========================================
app = Flask(__name__)
DB_NAME = "infrastructure.db"

# ==========================================
# 1. CORE INNOVATION: DIGITAL TWIN LOGIC
# ==========================================

class DigitalTwinModel:
    """
    The core logic engine. Calculates Expected Behavior based on physics
    to compare against Real Sensor Data.
    """

    @staticmethod
    def calculate_expected_voltage(rated_voltage: float, current_load: float, impedance_factor: float) -> float:
        """
        Calculates the physics-based expected voltage.
        Formula: V_expected = V_rated - (I_load * Z)
        """
        # Ohm's Law / Voltage Drop approximation
        drop = current_load * impedance_factor
        return rated_voltage - drop

    @staticmethod
    def analyze_health(real_value: float, expected_value: float) -> str:
        """
        Compares Real vs Expected values to determine asset health.
        
        Thresholds:
        - Deviation > 10%: CRITICAL
        - Deviation > 5%: WARNING
        - Otherwise: NORMAL
        """
        if expected_value == 0:
            return "CRITICAL" # Avoid division by zero, treat as major error

        deviation_percent = abs((real_value - expected_value) / expected_value) * 100.0

        if deviation_percent > 10.0:
            return "CRITICAL"
        elif deviation_percent > 5.0:
            return "WARNING"
        else:
            return "NORMAL"

    @staticmethod
    def get_recommendation(real_value: float, expected_value: float, health_status: str) -> str:
        """
        Generates actionable engineering advice based on the fault signature.
        """
        if health_status == "NORMAL":
            return "System Optimal. No Action Required."
        
        if real_value < expected_value:
             # Voltage Sag / Undervoltage
            return "Possible Overload. Inspect Transformer Tap Changer."
        elif real_value > expected_value:
             # Voltage Swell / Overvoltage
             return "Load Rejection. Check for Capacitor Bank malfunction."
        
        return "Anomaly Detected. Manual Inspection Required."

# ==========================================
# MODULES (Generation, Transmission, Distribution)
# ==========================================

class GenerationModule:
    """Module for handling power generation assets."""
    @staticmethod
    def get_load_profile() -> float:
        """Simulates load on a generator (Amps)."""
        # Base load + random fluctuation
        return 50.0 + random.uniform(-5.0, 5.0)

class TransmissionModule:
    """Module for handling high-voltage transmission assets."""
    @staticmethod
    def get_load_profile() -> float:
        """Simulates load on a substation/line (Amps)."""
        return 120.0 + random.uniform(-10.0, 10.0)

class DistributionModule:
    """Module for handling local distribution feeds."""
    @staticmethod
    def get_load_profile() -> float:
        """Simulates load on a feeder (Amps)."""
        return 30.0 + random.uniform(-2.0, 2.0)

def get_module_load(asset_type: str) -> float:
    """Factory function to get load based on asset type."""
    if asset_type == "Generation":
        return GenerationModule.get_load_profile()
    elif asset_type == "Transmission":
        return TransmissionModule.get_load_profile()
    elif asset_type == "Distribution":
        return DistributionModule.get_load_profile()
    return 10.0 # Default

# ==========================================
# 2. BACKEND: DATABASE & SIMULATION
# ==========================================

# Global dictionary to hold current real-time sensor state in memory
# Key: asset_id, Value: current_real_voltage
SENSOR_STATE: Dict[int, float] = {}

# Fault Injection State
# Key: asset_id, Value: dict { 'type': str, 'end_time': float }
FAULT_STATE: Dict[int, Dict[str, Any]] = {}

def init_db() -> None:
    """Initialize SQLite database with the schema and seed data."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # Create table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS assets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            type TEXT NOT NULL,
            rated_voltage REAL NOT NULL,
            impedance REAL NOT NULL
        )
    ''')
    
    # Check if empty, then seed
    cursor.execute('SELECT count(*) FROM assets')
    if cursor.fetchone()[0] == 0:
        print("Seeding database...")
        seed_data = [
            ("Kariba Hydro Gen", "Generation", 11000.0, 5.2),      # 11kV Generator
            ("Marvel Substation", "Transmission", 33000.0, 12.5),  # 33kV Substation
            ("Bulawayo Industry Feeder", "Distribution", 400.0, 1.1) # 400V Feeder
        ]
        cursor.executemany('INSERT INTO assets (name, type, rated_voltage, impedance) VALUES (?, ?, ?, ?)', seed_data)
        conn.commit()
    
    conn.close()

def get_db_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def simulation_worker() -> None:
    """
    Background thread to simulate sensor data.
    Updates SENSOR_STATE with realistic noise or injected faults.
    """
    print("Starting simulation worker...")
    while True:
        try:
            conn = get_db_connection()
            assets = conn.execute('SELECT * FROM assets').fetchall()
            conn.close()

            current_time = time.time()

            for asset in assets:
                asset_id = asset['id']
                rated_v = asset['rated_voltage']
                
                # 1. Normal Noise Generation
                # Fluctuate around Rated Voltage +/- 1%
                noise = random.uniform(-0.01, 0.01) * rated_v
                simulated_value = rated_v + noise

                # 2. Apply Load Effect (Physics Lite)
                load = get_module_load(asset['type'])
                simulated_value -= (load * 0.05) # Small drop

                # 3. FAULT INJECTION
                if asset_id in FAULT_STATE:
                    fault = FAULT_STATE[asset_id]
                    
                    # Check if fault has expired
                    if current_time > fault['end_time']:
                        del FAULT_STATE[asset_id]
                        print(f"Fault expired for asset {asset_id}")
                    else:
                        f_type = fault['type']
                        if f_type == "Voltage Dip":
                             simulated_value = simulated_value * 0.65 # 35% drop
                        elif f_type == "Voltage Spike":
                             simulated_value = simulated_value * 1.40 # 40% spike
                        elif f_type == "Zero Voltage":
                             simulated_value = 0.0

                SENSOR_STATE[asset_id] = round(simulated_value, 2)
            
        except Exception as e:
            print(f"Simulation Error: {e}")
        
        time.sleep(1) # Update every second

# ==========================================
# FLASK API ENDPOINTS
# ==========================================

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/status', methods=['GET'])
def get_status() -> Any:
    """
    Returns the Digital Twin analysis for all assets.
    """
    conn = get_db_connection()
    assets = conn.execute('SELECT * FROM assets').fetchall()
    conn.close()

    response_data: List[Dict[str, Any]] = []

    for asset in assets:
        asset_id = asset['id']
        name = asset['name']
        a_type = asset['type']
        rated_v = asset['rated_voltage']
        impedance = asset['impedance']

        # Get Real Sensor Value (Simulated)
        real_value = SENSOR_STATE.get(asset_id, rated_v)

        # Get Current Load Assumption
        current_load = get_module_load(a_type)

        # --- DIGITAL TWIN CALCULATION ---
        expected_value = DigitalTwinModel.calculate_expected_voltage(rated_v, current_load, impedance)
        
        # --- HEALTH ANALYSIS ---
        health = DigitalTwinModel.analyze_health(real_value, expected_value)
        
        # --- RECOMMENDATION ENGINE ---
        recommendation = DigitalTwinModel.get_recommendation(real_value, expected_value, health)

        response_data.append({
            "id": asset_id,
            "name": name,
            "type": a_type,
            "real_value": real_value,
            "expected_value": round(expected_value, 2),
            "health_status": health,
            "load_amps": round(current_load, 2),
            "recommendation": recommendation
        })

    return jsonify(response_data)

@app.route('/api/trigger_fault', methods=['POST'])
def trigger_fault() -> Any:
    """
    Admin Endpoint for Fault Injection.
    Payload: { "asset_id": int, "fault_type": str, "duration": int }
    """
    data = request.json
    if not data:
        return jsonify({"error": "No data provided"}), 400

    asset_id = int(data.get('asset_id'))
    fault_type = data.get('fault_type', 'Voltage Dip')
    duration = int(data.get('duration', 10))

    valid_faults = ["Voltage Dip", "Voltage Spike", "Zero Voltage"]
    if fault_type not in valid_faults:
        return jsonify({"error": f"Invalid fault type. Must be one of {valid_faults}"}), 400

    # Set fault state
    FAULT_STATE[asset_id] = {
        "type": fault_type,
        "end_time": time.time() + duration
    }

    print(f"FAULT INJECTED: Asset {asset_id}, Type {fault_type}, Duration {duration}s")
    return jsonify({
        "status": "Fault Injected", 
        "asset_id": asset_id, 
        "type": fault_type, 
        "duration": duration,
        "message": "Sabotage protocol initiated."
    })

# ==========================================
# MAIN ENTRY POINT
# ==========================================

if __name__ == '__main__':
    # Initialize DB (run once)
    init_db()

    # Start Simulation Thread
    sim_thread = threading.Thread(target=simulation_worker, daemon=True)
    sim_thread.start()

    # Determine port (default 5000)
    print("System Online. Digital Twin Engine Active.")
    app.run(host='0.0.0.0', port=5000, debug=True, use_reloader=False) 
