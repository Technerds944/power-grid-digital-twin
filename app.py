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

    @staticmethod
    def analyze_home_iot(voltage: float, current: float) -> Tuple[str, str]:
        """
        Analyzes Smart Home telemetry for safety & efficiency.
        """
        # Preventive Logic: Surge Protection
        if voltage > 255.0:
            return "PROTECTION ACTIVE", "Surge Detected. Power Cut to Save Appliances."
        
        # Predictive Logic: Appliance Health
        # Normal voltage but high current indicates motor strain (e.g., AC compressor)
        if current > 15.0:
            return "WARNING", "High Current. Check AC Compressor Health."

        return "NORMAL", "Home System Nominal."

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

class SmartHomeModule:
    """Module for residential load logic."""
    @staticmethod
    def get_load_profile() -> float:
        """Simulates typical home usage (Amps)."""
        # Base: 5A (Lights, TV), Peak: 20A (AC, Kettle)
        return 8.0 + random.uniform(-1.0, 3.0)

def get_module_load(asset_type: str) -> float:
    """Factory function to get load based on asset type."""
    if asset_type == "Generation":
        return GenerationModule.get_load_profile()
    elif asset_type == "Transmission":
        return TransmissionModule.get_load_profile()
    elif asset_type == "Distribution":
        return DistributionModule.get_load_profile()
    elif asset_type == "Smart Home":
        return SmartHomeModule.get_load_profile()
    return 10.0 # Default

# ==========================================
# 2. BACKEND: DATABASE & SIMULATION
# ==========================================

# Global dictionary to hold current real-time sensor state in memory
# Key: asset_id (negative for homes to avoid collision or separate dict), Value: current_real_voltage
# Simplified: We'll use positive IDs for everything, assuming they don't overlap in DB seeding.
SENSOR_STATE: Dict[int, float] = {}

# Fault Injection State
# Key: asset_id, Value: dict { 'type': str, 'end_time': float }
FAULT_STATE: Dict[int, Dict[str, Any]] = {}

def init_db() -> None:
    """Initialize SQLite database with the schema and seed data."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # 1. Grid Assets Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS assets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            type TEXT NOT NULL,
            rated_voltage REAL NOT NULL,
            impedance REAL NOT NULL
        )
    ''')
    
    # 2. Smart Homes Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS smart_homes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            address TEXT NOT NULL,
            owner TEXT NOT NULL
        )
    ''')
    
    # Seed Grid Assets
    cursor.execute('SELECT count(*) FROM assets')
    if cursor.fetchone()[0] == 0:
        print("Seeding Grid Assets...")
        seed_data = [
            ("Kariba Hydro Gen", "Generation", 11000.0, 5.2),      # 11kV Generator
            ("Marvel Substation", "Transmission", 33000.0, 12.5),  # 33kV Substation
            ("Bulawayo Industry Feeder", "Distribution", 400.0, 1.1) # 400V Feeder
        ]
        cursor.executemany('INSERT INTO assets (name, type, rated_voltage, impedance) VALUES (?, ?, ?, ?)', seed_data)


    # Seed Smart Homes
    cursor.execute('SELECT count(*) FROM smart_homes')
    if cursor.fetchone()[0] == 0:
        print("Seeding Smart Homes...")
        # Start ID at 99 to distinct visually in logs, though AUTOINCREMENT handles it.
        # SQLite autoincrement is separate per table.
        # We'll just insert and let it be 1.
        cursor.execute('INSERT INTO smart_homes (address, owner) VALUES (?, ?)', 
                       ("14 Main St, Bulawayo", "Mr. Dube"))
        
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
            grid_assets = conn.execute('SELECT * FROM assets').fetchall()
            homes = conn.execute('SELECT * FROM smart_homes').fetchall()
            conn.close()

            current_time = time.time()

            # --- PROCESS GRID ASSETS ---
            for asset in grid_assets:
                sim_step(asset['id'], asset['rated_voltage'], asset['type'], current_time)

            # --- PROCESS SMART HOMES ---
            # Homes are 230V residential standard
            for home in homes:
                # We map home IDs to a safe range if needed, but here we'll use a string key prefix or just negative IDs? 
                # Let's use a composite key approach in memory or just assume IDs don't collide? 
                # Tables have separate IDs (1, 2, 3...). 
                # To avoid collision in SENSOR_STATE, we'll prefix keys: "grid_1", "home_1".
                # Refactor SENSOR_STATE to use string keys.
                pass 
            
            # REFACTOR: SENSOR_STATE keys will be strings: "grid_{id}" and "home_{id}"
            # This requires updating the sim_step function.

        except Exception as e:
            print(f"Simulation Error: {e}")
        
        time.sleep(1) # Update every second

def sim_step(db_id: int, rated_v: float, asset_type: str, current_time: float, is_home: bool = False):
    """Refactored simulation step for any asset."""
    global SENSOR_STATE, FAULT_STATE
    
    key = f"home_{db_id}" if is_home else f"grid_{db_id}"
    
    # 1. Normal Noise
    noise = random.uniform(-0.01, 0.01) * rated_v
    simulated_value = rated_v + noise

    # 2. Physics / Simulation Logic
    # Homes have different behavior? For now, similar voltage drop logic
    load = get_module_load(asset_type)
    
    # Voltage drop simulation
    simulated_value -= (load * 0.05) 

    # 3. FAULT INJECTION
    if key in FAULT_STATE:
        fault = FAULT_STATE[key]
        if current_time > fault['end_time']:
            del FAULT_STATE[key]
            print(f"Fault expired for {key}")
        else:
            f_type = fault['type']
            if f_type == "Voltage Dip":
                 simulated_value = simulated_value * 0.65
            elif f_type == "Voltage Spike":
                 simulated_value = simulated_value * 1.40
            elif f_type == "Zero Voltage":
                 simulated_value = 0.0
            
            # Specific Smart Home Faults
            elif f_type == "Grid Surge":
                simulated_value = 265.0 # Trigger Protection
            elif f_type == "Home Wear":
                # Voltage normal, but we need to trick the current.
                # Since this function only returns VOLTAGE, 
                # we need to store the Fake Load somewhere or calculate it.
                # Hack: We'll store a "Force Current" flag in SENSOR_STATE?
                # Better: SENSOR_STATE values become objects: { 'v': float, 'i': float }
                # For simplicity, we'll just handle voltage here since Current is derived in get_status 
                # UNLESS we override it.
                pass # Handled in get_status by checking FAULT_STATE directly

    # Store state
    # We now store just voltage in simple SENSOR_STATE for backward compat, 
    # but for homes we might need more. 
    # Let's stick to Voltage in SENSOR_STATE. 
    # We will handle "Current Injection" primarily in the read logic (get_status).
    SENSOR_STATE[key] = round(simulated_value, 2)

def simulation_worker_refactored() -> None:
    """
    Main loop for simulation.
    """
    print("Starting Main Simulation Loop...")
    while True:
        try:
            conn = get_db_connection()
            grid_assets = conn.execute('SELECT * FROM assets').fetchall()
            homes = conn.execute('SELECT * FROM smart_homes').fetchall()
            conn.close()

            t = time.time()

            # Grid
            for a in grid_assets:
                sim_step(a['id'], a['rated_voltage'], a['type'], t, is_home=False)
            
            # Homes (Standard 230V)
            for h in homes:
                sim_step(h['id'], 230.0, "Smart Home", t, is_home=True)
                
        except Exception as e:
            print(f"Sim Loop Error: {e}")
        time.sleep(1)

# ==========================================
# FLASK API ENDPOINTS
# ==========================================

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/status', methods=['GET'])
def get_status() -> Any:
    conn = get_db_connection()
    grid = conn.execute('SELECT * FROM assets').fetchall()
    homes = conn.execute('SELECT * FROM smart_homes').fetchall()
    conn.close()

    response_data: List[Dict[str, Any]] = []

    # 1. Process Grid Assets
    for asset in grid:
        key = f"grid_{asset['id']}"
        rated_v = asset['rated_voltage']
        
        # Get Sensor Data
        real_v = SENSOR_STATE.get(key, rated_v)
        current_load = get_module_load(asset['type'])

        # Analysis
        expected_v = DigitalTwinModel.calculate_expected_voltage(rated_v, current_load, asset['impedance'])
        health = DigitalTwinModel.analyze_health(real_v, expected_v)
        rec = DigitalTwinModel.get_recommendation(real_v, expected_v, health)

        response_data.append({
            "id": key, # Unique UI ID
            "name": asset['name'],
            "type": asset['type'],
            "real_value": real_v,
            "expected_value": round(expected_v, 2),
            "health_status": health,
            "load_amps": round(current_load, 2),
            "recommendation": rec
        })

    # 2. Process Smart Homes
    for home in homes:
        key = f"home_{home['id']}"
        rated_v = 230.0
        
        # Sensor Data
        real_v = SENSOR_STATE.get(key, rated_v)
        
        # Check for Current Injection (Fault Simulation)
        # If "Home Wear" fault is active, force Current to 18A
        # Otherwise normal 8A range
        fault_entry = FAULT_STATE.get(key)
        if fault_entry and fault_entry['type'] == 'Home Wear':
             current_load = 18.5 # High current
        else:
             current_load = SmartHomeModule.get_load_profile()

        # IoT Logic
        status, advisory = DigitalTwinModel.analyze_home_iot(real_v, current_load)
        
        # Determine Color/Health for UI based on status
        health_ui = "NORMAL"
        if status == "PROTECTION ACTIVE": health_ui = "CRITICAL"
        if status == "WARNING": health_ui = "WARNING"

        response_data.append({
            "id": key,
            "name": home['address'], # Display Address
            "owner": home['owner'],
            "type": "Smart Home",
            "real_value": real_v,
            "expected_value": 230.0, # Nominal
            "health_status": health_ui,
            "load_amps": round(current_load, 2),
            "recommendation": advisory # The IoT Message
        })

    return jsonify(response_data)

@app.route('/api/trigger_fault', methods=['POST'])
def trigger_fault() -> Any:
    data = request.json
    if not data:
        return jsonify({"error": "No data provided"}), 400

    # ID now comes in as integer from new admin console, 
    # BUT we need to know if it's grid or home.
    # New Admin Console will send target_type? Or we infer?
    # Let's update Admin Console to send "grid_1" or "home_1" as ID?
    # Or keep it simple: "asset_id" (int) and "is_home" (bool).
    
    # We'll support both for flexibility.
    raw_id = data.get('asset_id')
    fault_type = data.get('fault_type')
    duration = int(data.get('duration', 10))
    is_home = data.get('is_home', False)

    key = f"home_{raw_id}" if is_home else f"grid_{raw_id}"

    # Set fault state
    FAULT_STATE[key] = {
        "type": fault_type,
        "end_time": time.time() + duration
    }

    print(f"FAULT INJECTED: {key}, Type {fault_type}, Duration {duration}s")
    return jsonify({"status": "Fault Injected", "target": key, "message": "Command Sent."})

if __name__ == '__main__':
    init_db()
    sim_thread = threading.Thread(target=simulation_worker_refactored, daemon=True)
    sim_thread.start()
    print("System Online. IoT Layer Active.")
    app.run(host='0.0.0.0', port=5000, debug=True, use_reloader=False) 
