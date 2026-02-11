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
        print("q. Quit")
        
        choice = input("\n> ")
        
        if choice.lower() == 'q':
            sys.exit()
            
        asset_map = {'1': 1, '2': 2, '3': 3}
        if choice not in asset_map:
            print("Invalid selection.")
            time.sleep(1)
            continue
            
        asset_id = asset_map[choice]
        
        print("\nSELECT FAULT TYPE:")
        print("1. Voltage Dip (Sag)")
        print("2. Voltage Spike (Swell)")
        print("3. Zero Voltage (Trip)")
        
        f_choice = input("\n> ")
        fault_map = {'1': "Voltage Dip", '2': "Voltage Spike", '3': "Zero Voltage"}
        if f_choice not in fault_map:
             print("Invalid selection.")
             time.sleep(1)
             continue
             
        fault_type = fault_map[f_choice]
        
        print("\nSELECT DURATION:")
        print("1. 10 Seconds")
        print("2. 30 Seconds")
        print("3. 60 Seconds")
        
        d_choice = input("\n> ")
        duration_map = {'1': 10, '2': 30, '3': 60}
        if d_choice not in duration_map:
             duration = 10
        else:
             duration = duration_map[d_choice]
             
        # Send Request
        payload = {
            "asset_id": asset_id,
            "fault_type": fault_type,
            "duration": duration
        }
        
        try:
            print(f"\nSending command: {fault_type} -> Asset {asset_id} ({duration}s)...")
            res = requests.post(API_URL, json=payload)
            if res.status_code == 200:
                print("\n[SUCCESS] FAULT INJECTED SUCCESSFULLY.")
                print(f"Server Response: {res.json()['message']}")
            else:
                print(f"\n[ERROR] Server returned {res.status_code}: {res.text}")
        except Exception as e:
            print(f"\n[ERROR] Connection failed: {e}")
            
        input("\nPress ENTER to continue...")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nExiting...")
        sys.exit()
