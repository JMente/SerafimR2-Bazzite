# Serafim R2+ Racing Wheel — Linux/Bazzite Fix

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Platform: Bazzite](https://img.shields.io/badge/Platform-Bazzite-blue.svg)](https://bazzite.gg/)
[![Hardware: Serafim R2+](https://img.shields.io/badge/Hardware-Serafim%20R2+-green.svg)]()

> **Solución completa para usar el volante Serafim Racing Wheel R2+ en Linux (Bazzite/Fedora Silverblue) con Steam.**

---

## 📋 Tabla de Contenidos

- [Problema](#-problema)
- [Causa Raíz](#-causa-raíz)
- [Solución](#-solución)
- [Instalación Rápida](#-instalación-rápida)
- [Documentación Técnica](#-documentación-técnica)
- [Soluciones Alternativas](#-soluciones-alternativas)
- [Compatibilidad de Juegos](#-compatibilidad-de-juegos)
- [Troubleshooting](#-troubleshooting)
- [Créditos](#-créditos)

---

## 🔴 Problema

El **Serafim Racing Wheel R2+** se detecta en Linux como un **"Android GamePad"** genérico (VID:PID `2563:0526` — ShenZhen ShanWan Technology). Aunque el kernel reconoce eventos correctamente (`evtest` funciona), los juegos de Steam **no reciben inputs**.

### Síntomas

| Capa | Estado | Detalle |
|------|--------|---------|
| Kernel (evdev) | ✅ Funciona | `evtest` detecta eventos EV_KEY y EV_ABS |
| Joystick API (`/dev/input/js0`) | ✅ Existe | Dispositivo `js0` presente |
| SDL2 / `sdl2-jstest` | ❌ No detecta | SDL rechaza el dispositivo |
| Steam Input | ⚠️ Parcial | Detecta pero `mapping uses xinput: false` |
| Juegos Steam/Proton | ❌ Fallan | No ven el volante |

### Sistema Afectado

- **Distro:** Bazzite (Fedora Silverblue/SteamOS-based, inmutable)
- **Display Server:** Wayland
- **Kernel:** 6.16.4-116.bazzite.fc42.x86_64
- **Steam:** Flatpak / nativo

---

## 🔍 Causa Raíz

### Diagnóstico Técnico

1. **El volante SÍ tiene ejes analógicos** (8 ejes ABS, 15 botones) — no es un dispositivo digital.
2. **Steam Input detecta el volante** pero lo trata como un gamepad genérico Android.
3. **El mapeo SDL de Steam** (`0300f854632500002605000003016800`) aplica configuración de "Android GamePad" que no coincide con la disposición física del volante.
4. **Steam no expone el dispositivo como XInput** (`mapping uses xinput: false`), por lo que los juegos que esperan un controlador Xbox no lo ven.
5. **El dispositivo real y virtual compartían VID:PID** en versiones anteriores del fix, causando que Steam aplicara el mismo mapeo erróneo a ambos.

### Logs de Steam (evidencia)

```
Controller 0 mapping uses xinput : false
SDL Mapping for 2563/526: 0300f854632500002605000003016800,*,a:b0,b:b1,...
Controller using HIDAPI driver, vid=0x2563, pid=0x0526
```

---

## ✅ Solución

### Arquitectura

La solución consiste en un **bridge de joystick virtual** que:

1. **Lee** eventos del volante real (`/dev/input/event4`)
2. **Crea** un dispositivo virtual con **VID:PID de Xbox 360 Controller** (`045E:028E`)
3. **Expone** ejes y botones con mapeo estándar XInput que Steam reconoce nativamente

```
┌─────────────────┐     ┌──────────────────────────┐     ┌─────────────────┐
│  Serafim R2+    │────▶│  serafim_virtual_joystick │────▶│  Steam / Juegos │
│  (Android       │     │  (Virtual Xbox 360 Pad)   │     │  (XInput)       │
│   GamePad)      │     │                           │     │                 │
│  2563:0526      │     │  VID:PID = 045E:028E      │     │  Detecta como   │
│                 │     │  Name: "Serafim R2+       │     │  Xbox Controller│
│                 │     │         Virtual Wheel"    │     │                 │
└─────────────────┘     └──────────────────────────┘     └─────────────────┘
```

### Archivos del Proyecto

| Archivo | Descripción |
|---------|-------------|
| `serafim_virtual_joystick.py` | Bridge principal en Python (evdev → uinput) |
| `99-serafim-r2.rules` | Reglas udev para permisos de dispositivos |
| `serafim-bridge.service` | Servicio systemd de usuario (auto-inicio) |
| `install.sh` | Script de instalación automatizado |

---

## 🚀 Instalación Rápida

### Requisitos

- Bazzite / Fedora Silverblue (o cualquier distro con `python3-evdev`)
- `systemd` (para el servicio de usuario)
- Acceso `sudo` (solo para udev rules y grupo `input`)

### Pasos

```bash
# 1. Clonar el repositorio
git clone https://github.com/JMente/SerafimR2-Bazzite.git
cd SerafimR2-Bazzite

# 2. Ejecutar instalador
bash install.sh

# 3. Reiniciar sesión (obligatorio para grupo 'input')
# Cierra sesión y vuelve a entrar

# 4. Iniciar el bridge
systemctl --user start serafim-bridge

# 5. Verificar
python3 serafim_virtual_joystick.py --list
```

### Post-instalación

1. **Reinicia Steam completamente** (cierra y vuelve a abrir)
2. Ve a **Steam → Configuración → Controlador**
3. Debe aparecer **"Serafim R2+ Virtual Wheel"** (o "Microsoft X-Box 360 pad")

---

## 📖 Documentación Técnica

### Estructura del Hardware

**Serafim R2+ en modo Android GamePad:**

| Característica | Valor |
|----------------|-------|
| Vendor ID | `0x2563` |
| Product ID | `0x0526` |
| Manufacturer | ShenZhen ShanWan Technology |
| Bus | USB (`0x03`) |
| Ejes ABS | 8 (X, Y, Z, RZ, GAS, BRAKE, HAT0X, HAT0Y) |
| Botones | 15 (A, B, C, X, Y, Z, TL, TR, TL2, TR2, SELECT, START, MODE, THUMBL, THUMBR) |

### Mapeo de Ejes

| Eje Real (Serafim) | Eje Virtual (Xbox 360) | Función |
|--------------------|------------------------|---------|
| `ABS_X` | `ABS_X` | Volante (Steering) |
| `ABS_GAS` | `ABS_GAS` | Acelerador |
| `ABS_BRAKE` | `ABS_BRAKE` | Freno |
| `ABS_Y` | `ABS_Y` | No usado |
| `ABS_HAT0X` | `ABS_HAT0X` | D-Pad X |
| `ABS_HAT0Y` | `ABS_HAT0Y` | D-Pad Y |

### Mapeo de Botones

| Botón Real | Botón Virtual | Función |
|------------|---------------|---------|
| `BTN_A` | `BTN_A` | A / Cruz abajo |
| `BTN_B` | `BTN_B` | B / Cruz derecha |
| `BTN_X` | `BTN_X` | X / Cruz izquierda |
| `BTN_Y` | `BTN_Y` | Y / Cruz arriba |
| `BTN_TL` | `BTN_TL` | L1 / Paddle izquierdo |
| `BTN_TR` | `BTN_TR` | R1 / Paddle derecho |
| `BTN_TL2` | `BTN_TL2` | L2 |
| `BTN_TR2` | `BTN_TR2` | R2 |
| `BTN_SELECT` | `BTN_SELECT` | Select / Share |
| `BTN_START` | `BTN_START` | Start / Options |
| `BTN_MODE` | `BTN_MODE` | Home / Mode |

### Por qué Xbox 360 VID:PID

El cambio crítico en la solución fue usar **VID:PID de Microsoft Xbox 360 Controller** (`045E:028E`) en el dispositivo virtual. Esto asegura que:

1. **Steam tiene mapeo nativo** para este dispositivo (no aplica heurísticas de "Android GamePad")
2. **Los juegos detectan XInput** automáticamente
3. **No hay conflicto** con el dispositivo real (`2563:0526`)

---

## 🔄 Soluciones Alternativas

### Opción A: Cambiar Modo del Volante (Hardware)

El Serafim R2+ tiene modos seleccionables por combinación de botones:

| Modo | Combinación | LED | Notas |
|------|-------------|-----|-------|
| Android (default) | — | Azul | Modo actual, requiere bridge |
| **PC / XInput** | `Home + X` (3 seg) | **Verde** | **Recomendado — puede funcionar sin bridge** |
| Nintendo Switch | `Home + B` (3 seg) | Rojo | — |
| D-Input | `Home + Y` (3 seg) | Amarillo | — |

> **Nota:** En modo PC/XInput el VID:PID puede cambiar. Si cambia a un ID conocido por Linux, el volante podría funcionar sin necesidad de este bridge.

### Opción B: SDL_GAMECONTROLLERCONFIG Manual

Si el dispositivo aparece en SDL pero sin mapeo correcto:

```bash
export SDL_GAMECONTROLLERCONFIG="0300f854632500002605000003016800,Serafim R2+,a:b0,b:b1,back:b4,dpdown:h0.4,dpleft:h0.8,dpright:h0.2,dpup:h0.1,guide:b5,leftshoulder:b9,leftstick:b7,lefttrigger:a4,leftx:a0,lefty:a1,rightshoulder:b10,rightstick:b8,righttrigger:a5,rightx:a2,righty:a3,start:b6,x:b2,y:b3,platform:Linux,"
```

### Opción C: xboxdrv en DistroBox

Para distros inmutables donde no se puede instalar `python3-evdev`:

```bash
distrobox create --name xbox --image fedora:latest
distrobox enter xbox
sudo dnf install -y xboxdrv
# Mapeo específico requiere calibración manual
```

---

## 🎮 Compatibilidad de Juegos

| Juego | Estado | Notas |
|-------|--------|-------|
| **Assetto Corsa** | ✅ Funciona | Desactivar Steam Input si hay conflictos |
| **Assetto Corsa Competizione** | ✅ Funciona | Modo XInput nativo |
| **F1 23/24** | ✅ Funciona | — |
| **Dirt Rally 2.0** | ✅ Funciona | — |
| **Euro Truck Simulator 2** | ✅ Funciona | — |
| **BeamNG.drive** | ✅ Funciona | — |
| **SuperTuxKart** | ✅ Funciona | Confirmado nativo |
| **Forza Horizon 5** | ⚠️ Parcial | Easy Anti-Cheat puede bloquear input virtual |
| **iRacing** | ❌ No compatible | Requiere drivers oficiales de volante |

---

## 🔧 Troubleshooting

### "Permission denied" al ejecutar el bridge

```bash
# Agregar usuario al grupo input
sudo usermod -aG input $USER
# Cerrar sesión y volver a entrar
```

### El dispositivo virtual no aparece

```bash
# Verificar que uinput esté disponible
ls -la /dev/uinput

# Verificar que el servicio esté corriendo
systemctl --user status serafim-bridge

# Ver logs
journalctl --user -u serafim-bridge -f
```

### Steam no detecta el volante

1. Reinicia Steam completamente (cierra tray icon también)
2. Verifica que el bridge esté activo: `systemctl --user is-active serafim-bridge`
3. Verifica dispositivos: `python3 serafim_virtual_joystick.py --list`

### Drift o botones fantasmas

Este problema ocurría en versiones anteriores donde el dispositivo virtual usaba VID:PID similar al real (`2563:0527`). La solución actual usa **VID:PID de Xbox 360** (`045E:028E`) para evitar que Steam Input aplique mapeos incorrectos del "Android GamePad".

Si persisten problemas:
1. Verifica que estés usando la última versión del script
2. Borra configuraciones de Steam Input antiguas:
   ```bash
   rm ~/.local/share/Steam/steamapps/common/Steam\ Controller\ Configs/*/config/configset_2563-*.vdf
   ```
3. Reinicia Steam

---

## 📝 Changelog

### v1.1 (2025-05-23)
- **Fix:** Cambiado VID:PID del dispositivo virtual a Xbox 360 Controller (`045E:028E`)
- **Fix:** Resuelto problema de drift y botones fantasmas causado por mapeo conflictivo de Steam Input
- **Mejora:** Documentación expandida con arquitectura y mapeos detallados

### v1.0 (2025-05-23)
- Release inicial
- Bridge Python con evdev/uinput
- Servicio systemd de usuario
- Script de instalación automatizado

---

## 📄 Licencia

MIT License — Ver [LICENSE](LICENSE) para detalles.

---

## 🙏 Créditos

- **Autor:** [JMente](https://github.com/JMente) (Josué Mente)
- **Asistente:** Kira (IA assistant)
- **Hardware:** Serafim R2+ Racing Wheel
- **Plataforma:** [Bazzite](https://bazzite.gg/) — Fedora Silverblue para gaming

---

## 🔗 Links Relacionados

- [Serafim Official](https://www.serafim.com/)
- [Bazzite Documentation](https://docs.bazzite.gg/)
- [evdev Python Library](https://python-evdev.readthedocs.io/)
- [SDL GameControllerDB](https://github.com/mdqinc/SDL_GameControllerDB)
