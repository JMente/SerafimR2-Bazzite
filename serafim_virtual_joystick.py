#!/usr/bin/env python3
"""
Serafim R2+ Virtual Joystick Bridge
====================================
Lee eventos del volante ShanWan (2563:0526) y crea un joystick virtual
con ejes estándar que SDL2 y juegos reconocen correctamente.

Hardware: Serafim Racing Wheel R2+ en modo Android GamePad
Sistema: Bazzite (Fedora Silverblue, inmutable)
Autor: Kira (JA Mente)
"""

import sys
import os
import signal
import argparse
import threading
import time

# Asegurar que usamos el python del sistema con evdev
if not os.path.exists('/usr/lib64/python3.13/site-packages/evdev'):
    print("ERROR: python-evdev no está instalado. Instalar con: rpm-ostree install python3-evdev")
    sys.exit(1)

sys.path.insert(0, '/usr/lib64/python3.13/site-packages')

try:
    from evdev import InputDevice, UInput, ecodes, list_devices, AbsInfo
except ImportError as e:
    print(f"ERROR importando evdev: {e}")
    print("Asegúrate de que python3-evdev esté instalado en el sistema base.")
    sys.exit(1)

# ============================================================================
# CONFIGURACIÓN DEL HARDWARE SERAFIM R2+
# ============================================================================

# VID:PID del volante en modo Android GamePad
TARGET_VENDOR = 0x2563
TARGET_PRODUCT = 0x0526

# Mapeo de botones del ShanWan Android GamePad a botones estándar de joystick
BUTTON_MAP = {
    ecodes.BTN_A:      ecodes.BTN_A,        # Botón A (cruz abajo)
    ecodes.BTN_B:      ecodes.BTN_B,        # Botón B (cruz derecha)
    ecodes.BTN_C:      ecodes.BTN_C,        # Botón C (extra)
    ecodes.BTN_X:      ecodes.BTN_X,        # Botón X (cruz izquierda)
    ecodes.BTN_Y:      ecodes.BTN_Y,        # Botón Y (cruz arriba)
    ecodes.BTN_Z:      ecodes.BTN_Z,        # Botón Z (extra)
    ecodes.BTN_TL:     ecodes.BTN_TL,       # L1 / Paddle izquierdo
    ecodes.BTN_TR:     ecodes.BTN_TR,       # R1 / Paddle derecho
    ecodes.BTN_TL2:    ecodes.BTN_TL2,      # L2
    ecodes.BTN_TR2:    ecodes.BTN_TR2,      # R2
    ecodes.BTN_SELECT: ecodes.BTN_SELECT,   # Select / Share
    ecodes.BTN_START:  ecodes.BTN_START,    # Start / Options
    ecodes.BTN_MODE:   ecodes.BTN_MODE,     # Home / Mode
    ecodes.BTN_THUMBL: ecodes.BTN_THUMBL,   # L3
    ecodes.BTN_THUMBR: ecodes.BTN_THUMBR,   # R3
}

# Mapeo de ejes ABS del ShanWan a ejes estándar de volante
AXIS_MAP = {
    # ShanWan axis -> Virtual axis
    ecodes.ABS_X:     ecodes.ABS_X,      # Volante ( steering ) -> ABS_X
    ecodes.ABS_Y:     ecodes.ABS_Y,      # No usado / Pedal aux
    ecodes.ABS_Z:     ecodes.ABS_Z,      # No usado
    ecodes.ABS_RZ:    ecodes.ABS_RZ,     # No usado
    ecodes.ABS_GAS:   ecodes.ABS_GAS,    # Acelerador -> ABS_GAS
    ecodes.ABS_BRAKE: ecodes.ABS_BRAKE,  # Freno -> ABS_BRAKE
    ecodes.ABS_HAT0X: ecodes.ABS_HAT0X,  # D-Pad X
    ecodes.ABS_HAT0Y: ecodes.ABS_HAT0Y,  # D-Pad Y
}

# Configuración de ejes del dispositivo virtual
VIRTUAL_AXES = {
    ecodes.ABS_X:     (0, 255, 0, 15),    # Volante: min=0, max=255, fuzz=0, flat=15
    ecodes.ABS_Y:     (0, 255, 0, 15),
    ecodes.ABS_Z:     (0, 255, 0, 15),
    ecodes.ABS_RZ:    (0, 255, 0, 15),
    ecodes.ABS_GAS:   (0, 255, 0, 15),    # Acelerador
    ecodes.ABS_BRAKE: (0, 255, 0, 15),    # Freno
    ecodes.ABS_HAT0X: (-1, 1, 0, 0),      # D-Pad
    ecodes.ABS_HAT0Y: (-1, 1, 0, 0),
}

VIRTUAL_BUTTONS = list(BUTTON_MAP.values())

# ============================================================================
# FUNCIONES AUXILIARES
# ============================================================================

def find_serafim_device():
    """Encuentra el dispositivo Serafim R2+ por VID:PID."""
    for path in list_devices():
        try:
            dev = InputDevice(path)
            if dev.info.vendor == TARGET_VENDOR and dev.info.product == TARGET_PRODUCT:
                return dev
        except (OSError, PermissionError):
            continue
    return None

def create_virtual_joystick():
    """Crea un dispositivo joystick virtual con las capacidades correctas."""
    
    # Construir diccionario de capacidades para UInput
    capabilities = {
        ecodes.EV_SYN: [],
        ecodes.EV_KEY: VIRTUAL_BUTTONS,
        ecodes.EV_ABS: [(axis, AbsInfo(value=params[0], min=params[0], max=params[1], fuzz=params[2], flat=params[3], resolution=0)) for axis, params in VIRTUAL_AXES.items()],
    }
    
    # Crear dispositivo virtual
    # NOTA: Usamos VID/PID completamente diferentes al original para evitar
    # que Steam Input aplique el mismo mapeo de "Android GamePad"
    virtual = UInput(
        capabilities,
        name="Serafim R2+ Virtual Wheel",
        vendor=0x045E,  # Microsoft (XInput compatible)
        product=0x028E,  # Xbox 360 Controller
        version=0x0110,
        bustype=0x03,  # USB
    )
    
    return virtual

def read_events(source_dev, virtual_dev, running):
    """Lee eventos del dispositivo real y los reenvía al virtual."""
    
    print(f"[BRIDGE] Leyendo de: {source_dev.path} ({source_dev.name})")
    print(f"[BRIDGE] Escribiendo a: {virtual_dev.device}")
    print("[BRIDGE] Presiona Ctrl+C para detener.\n")
    
    try:
        for event in source_dev.read_loop():
            if not running[0]:
                break
            
            if event.type == ecodes.EV_SYN:
                virtual_dev.syn()
                continue
            
            if event.type == ecodes.EV_KEY:
                if event.code in BUTTON_MAP:
                    virtual_dev.write(ecodes.EV_KEY, BUTTON_MAP[event.code], event.value)
            
            elif event.type == ecodes.EV_ABS:
                if event.code in AXIS_MAP:
                    virtual_dev.write(ecodes.EV_ABS, AXIS_MAP[event.code], event.value)
            
            # EV_MSC lo ignoramos (MSC_SCAN no es necesario para juegos)
    
    except OSError as e:
        print(f"[ERROR] Dispositivo desconectado: {e}")
    
    print("[BRIDGE] Hilo de lectura terminado.")

# ============================================================================
# MAIN
# ============================================================================

def main():
    parser = argparse.ArgumentParser(description='Serafim R2+ Virtual Joystick Bridge')
    parser.add_argument('--daemon', '-d', action='store_true', help='Ejecutar en modo daemon')
    parser.add_argument('--list', '-l', action='store_true', help='Listar dispositivos de input')
    args = parser.parse_args()
    
    if args.list:
        print("Dispositivos de input disponibles:")
        for path in list_devices():
            dev = InputDevice(path)
            print(f"  {path}: {dev.name} (vid=0x{dev.info.vendor:04x}, pid=0x{dev.info.product:04x})")
        return
    
    # Buscar dispositivo Serafim
    print("[INIT] Buscando Serafim R2+...")
    source_dev = find_serafim_device()
    
    if source_dev is None:
        print("[ERROR] No se encontró el dispositivo Serafim R2+ (2563:0526).")
        print("[ERROR] Verifica que el volante esté conectado.")
        sys.exit(1)
    
    print(f"[INIT] Dispositivo encontrado: {source_dev.name}")
    print(f"[INIT] Path: {source_dev.path}")
    print(f"[INIT] VID:PID = 0x{source_dev.info.vendor:04x}:0x{source_dev.info.product:04x}")
    
    # Mostrar capacidades
    caps = source_dev.capabilities(verbose=True)
    print("[INIT] Capacidades detectadas:")
    for cap_type, cap_list in caps.items():
        if "EV_SYN" in str(cap_type):
            continue
        print(f"       {cap_type}: {len(cap_list)} items")
    
    # Crear joystick virtual
    print("\n[INIT] Creando joystick virtual...")
    try:
        virtual_dev = create_virtual_joystick()
    except PermissionError:
        print("[ERROR] Permiso denegado para crear dispositivo virtual.")
        print("[ERROR] Asegúrate de estar en el grupo 'input' o tener permisos udev.")
        sys.exit(1)
    
    print(f"[INIT] Joystick virtual creado: {virtual_dev.device}")
    print(f"[INIT] Nombre: {virtual_dev.name}")
    print(f"[INIT] Path: {virtual_dev.device}")
    
    # Variable de control para el hilo
    running = [True]
    
    # Manejar señales
    def signal_handler(sig, frame):
        print("\n[SIGNAL] Cerrando...")
        running[0] = False
        source_dev.close()
        virtual_dev.close()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Iniciar hilo de lectura
    reader_thread = threading.Thread(target=read_events, args=(source_dev, virtual_dev, running))
    reader_thread.daemon = True
    reader_thread.start()
    
    # Mantener vivo el proceso principal
    try:
        while running[0]:
            time.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        running[0] = False
        source_dev.close()
        virtual_dev.close()
        print("[INIT] Cerrado.")

if __name__ == "__main__":
    main()