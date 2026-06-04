"""
=============================================================================
Proiect: Sistem Ciber-Fizic (CPS) pentru Monitorizare AMR Pharma
Modul:   Core Engine (FSM, MQTT, Edge SQLite Logging)
=============================================================================
"""

import time
import random
import sqlite3
import ssl
import os
from datetime import datetime
import paho.mqtt.client as mqtt

os.chdir(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = "pharma_data.db"

MQTT_BROKER = "a66111aa5df847cba675dddc5d9ecc65.s1.eu.hivemq.cloud"
MQTT_PORT = 8883
TOPIC_TELEMETRY = "amr_pharma/telemetry"
TOPIC_COMMANDS = "amr_pharma/commands"

# Fix pentru DeprecationWarning cerut de paho-mqtt v2.0+
client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
comanda_curenta = "STOP"
dim_x_max, dim_y_max = 0.0, 0.0

def setup_database():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("DROP TABLE IF EXISTS telemetry")
    conn.execute("""
    CREATE TABLE telemetry (
        id INTEGER PRIMARY KEY AUTOINCREMENT, 
        timestamp TEXT, pos_x REAL, pos_y REAL, pos_z REAL,
        temperature REAL, humidity REAL, status TEXT, battery REAL, current_state TEXT
    )
    """)
    conn.commit()
    conn.close()
    print(f"[SYSTEM] Baza de date generată la: {os.path.abspath(DB_PATH)}")

def log_state(ts, x, y, z, temp, hum, status, bat, state_name):
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        INSERT INTO telemetry (timestamp, pos_x, pos_y, pos_z, temperature, humidity, status, battery, current_state)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (ts, round(x,1), round(y,1), round(z,1), round(temp,1), round(hum,1), status, round(bat,1), state_name))
    conn.commit()
    conn.close()

def on_message(client, userdata, msg):
    global comanda_curenta, dim_x_max, dim_y_max
    payload = msg.payload.decode()
    if payload == "STOP":
        comanda_curenta = "STOP"
        print("[MQTT] Comandă recepționată: STOP")
    elif payload.startswith("START"):
        date = payload.split(",")
        comanda_curenta = "START"
        dim_x_max, dim_y_max = float(date[1]), float(date[2])
        print(f"[MQTT] Comandă recepționată: START ({dim_x_max}m x {dim_y_max}m)")

client.on_message = on_message

def connect_mqtt():
    client.username_pw_set("test-dafi", "Test_Dafi_Ana_Miu1")
    client.tls_set(cert_reqs=ssl.CERT_REQUIRED, tls_version=ssl.PROTOCOL_TLSv1_2)
    client.connect(MQTT_BROKER, MQTT_PORT, 60)
    client.subscribe(TOPIC_COMMANDS)
    client.loop_start()

def run_state_machine():
    global comanda_curenta
    state = "INIT" 
    pos_x, pos_y = 0.0, 0.0
    battery = 100.0
    inaltimi_z = [0.2, 1.5, 3.0]

    setup_database()
    connect_mqtt()
    print("[SYSTEM] Robot pornit. Inițializare sisteme hardware (INIT)...")

    while True:
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        if comanda_curenta == "STOP" and state not in ["INIT", "IDLE", "SAFE_STOP"]:
            state = "IDLE"

        if state == "INIT":
            print("[HARDWARE] Auto-diagnostic... BMS: OK | LiDAR: OK | Motoare: OK")
            log_state(ts, pos_x, pos_y, 0.0, 20.0, 45.0, 'SYSTEM_OK', battery, 'INIT')
            time.sleep(4)
            state = "IDLE"
            print("[SYSTEM] Diagnostic complet. Trecere în starea IDLE. Așteptare misiune.")

        elif state == "IDLE":
            log_state(ts, pos_x, pos_y, 0.0, 20.0, 45.0, 'VALID', battery, 'IDLE')
            if comanda_curenta == "START":
                pos_x, pos_y, battery = 0.0, 0.0, 100.0
                state = "NAVIGATE"
            else:
                time.sleep(2)

        elif state == "NAVIGATE":
            battery -= random.uniform(1.5, 3.0)
            log_state(ts, pos_x, pos_y, 0.0, 20.0, 45.0, 'VALID', battery, 'NAVIGATE')
            time.sleep(2)
            state = "SAFE_STOP" if battery <= 15.0 else "SCAN_HEIGHTS"

        elif state == "SCAN_HEIGHTS":
            battery -= 0.5
            log_state(ts, pos_x, pos_y, 0.0, 20.0, 45.0, 'VALID', battery, 'SCAN_HEIGHTS')
            
            pachet_scanari = []
            for z in inaltimi_z:
                temp = round(random.uniform(19.0, 21.5) + (z * 1.5), 1)
                hum = round(random.uniform(41.0, 49.0), 1)
                pachet_scanari.append((z, temp, hum))
                time.sleep(0.6)
            state = "EDGE_SAVE_AND_SYNC"

        elif state == "EDGE_SAVE_AND_SYNC":
            for scanare in pachet_scanari:
                z, temp, hum = scanare
                status = "ALARM" if temp > 25.0 else "VALID"
                log_state(ts, pos_x, pos_y, z, temp, hum, status, battery, 'EDGE_SAVE_AND_SYNC')
            
            pos_x += 2.0
            if pos_x > dim_x_max: 
                pos_x = 0.0
                pos_y += 2.0
            
            if battery <= 15.0: state = "SAFE_STOP"
            elif pos_y > dim_y_max: comanda_curenta, state = "STOP", "IDLE"
            else: state = "NAVIGATE"
            time.sleep(1)

        elif state == "SAFE_STOP":
            battery = min(battery + 25.0, 100.0)
            log_state(ts, pos_x, pos_y, 0.0, 20.0, 45.0, 'INCARCARE', battery, 'SAFE_STOP')
            time.sleep(2)
            if battery >= 100.0: comanda_curenta, state = "STOP", "IDLE"

if __name__ == "__main__":
    run_state_machine()
