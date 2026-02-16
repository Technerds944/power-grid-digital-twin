import requests
import time
import sys

API_URL = "http://localhost:5000/api/trigger_fault"

def clear_screen():
    print("\033c", end="")

def print_header():
    clear_screen()
    print("==================================================")
    print("   POWER GRID SIMULATION - ADMIN CONTROL PANEL    ")
    print("==================================================")
    print("WARNING: AUTHORIZED PERSONNEL ONLY")
    print("--------------------------------------------------")

def main():
    while True:
        print_header()
        print("\nSELECT TARGET ASSET:")
        print("1. Kariba Hydro Gen")
        print("2. Marvel Substation")
        print("3. Bulawayo Industry Feeder")
        print("4. Simulate Smart Home Faults (NEW)")
        print("q. Quit")
        
        choice = input("\n> ")
        
        if choice.lower() == 'q':
            sys.exit()
            
        # Logic branch: Grid vs Home
        if choice == '4':
             handle_smart_home_menu()
             continue

        asset_map = {'1': 1, '2': 2, '3': 3}
        if choice not in asset_map:
            print("Invalid selection.")
            time.sleep(1)
            continue
            
        asset_id = asset_map[choice]
        handle_grid_fault_menu(asset_id)

def handle_grid_fault_menu(asset_id):
    print("\nSELECT FAULT TYPE:")
    print("1. Voltage Dip (Sag)")
    print("2. Voltage Spike (Swell)")
    print("3. Zero Voltage (Trip)")
    
    f_choice = input("\n> ")
    fault_map = {'1': "Voltage Dip", '2': "Voltage Spike", '3': "Zero Voltage"}
    if f_choice not in fault_map:
            print("Invalid selection.")
            time.sleep(1)
            return
            
    fault_type = fault_map[f_choice]
    send_fault(asset_id, fault_type, is_home=False)

def handle_smart_home_menu():
    print("\n--- SMART HOME SIMULATION (ID: 14 Main St) ---")
    print("[A] Simulate Grid Surge (265V) -> Trigger Protection")
    print("[B] Simulate Appliance Wear (18A) -> Trigger Warning")
    print("[C] Cancel")

    sub_choice = input("\n> ").upper()
    
    if sub_choice == 'A':
        send_fault(1, "Grid Surge", is_home=True) # Home ID 1
    elif sub_choice == 'B':
        send_fault(1, "Home Wear", is_home=True) # Home ID 1
    elif sub_choice == 'C':
        return
    else:
        print("Invalid selection.")
        time.sleep(1)

def send_fault(asset_id, fault_type, is_home=False):
    print("\nSELECT DURATION:")
    print("1. 10 Seconds")
    print("2. 30 Seconds")
    print("3. 60 Seconds")
    
    d_choice = input("\n> ")
    duration_map = {'1': 10, '2': 30, '3': 60}
    duration = duration_map.get(d_choice, 10)
            
    # Send Request
    payload = {
        "asset_id": asset_id,
        "fault_type": fault_type,
        "duration": duration,
        "is_home": is_home
    }
    
    try:
        target_str = f"Home {asset_id}" if is_home else f"Grid Asset {asset_id}"
        print(f"\nSending command: {fault_type} -> {target_str} ({duration}s)...")
        res = requests.post(API_URL, json=payload)
        if res.status_code == 200:
            print("\n[SUCCESS] FAULT INJECTED SUCCESSFULLY.")
            print(f"Server Response: {res.json().get('message', 'OK')}")
        else:
            print(f"\n[ERROR] Server returned {res.status_code}: {res.text}")
    except Exception as e:
        print(f"\n[ERROR] Connection failed: {e}")
        print("Ensure app.py is running.")
        
    input("\nPress ENTER to continue...")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nExiting...")
        sys.exit()
