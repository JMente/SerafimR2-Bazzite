# Serafim R2+ Racing Wheel — Linux/Bazzite Fix

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Platform: Bazzite](https://img.shields.io/badge/Platform-Bazzite-blue.svg)](https://bazzite.gg/)
[![Hardware: Serafim R2+](https://img.shields.io/badge/Hardware-Serafim%20R2+-green.svg)]()

> **Complete solution to use the Serafim Racing Wheel R2+ on Linux (Bazzite/Fedora Silverblue) with Steam.**

[Leer en Español](README.md)

---

## 📋 Table of Contents

- [Problem](#-problem)
- [Root Cause](#-root-cause)
- [Solution](#-solution)
- [Quick Install](#-quick-install)
- [Technical Documentation](#-technical-documentation)
- [Alternative Solutions](#-alternative-solutions)
- [Game Compatibility](#-game-compatibility)
- [Troubleshooting](#-troubleshooting)
- [Credits](#-credits)

---

## 🔴 Problem

The **Serafim Racing Wheel R2+** is detected on Linux as a generic **"Android GamePad"** (VID:PID `2563:0526` — ShenZhen ShanWan Technology). Although the kernel recognizes events correctly (`evtest` works), Steam games **do not receive inputs**.

### Symptoms

| Layer | Status | Detail |
|-------|--------|--------|
| Kernel (evdev) | ✅ Works | `evtest` detects EV_KEY and EV_ABS events |
| Joystick API (`/dev/input/js0`) | ✅ Exists | `js0` device present |
| SDL2 / `sdl2-jstest` | ❌ Not detected | SDL rejects the device |
| Steam Input | ⚠️ Partial | Detects but `mapping uses xinput: false` |
| Steam/Proton Games | ❌ Fails | Games don't see the wheel |

### Affected System

- **Distro:** Bazzite (Fedora Silverblue/SteamOS-based, immutable)
- **Display Server:** Wayland
- **Kernel:** 6.16.4-116.bazzite.fc42.x86_64
- **Steam:** Flatpak / native

---

## 🔍 Root Cause

### Technical Diagnosis

1. **The wheel DOES have analog axes** (8 ABS axes, 15 buttons) — it's not a digital device.
2. **Steam Input detects the wheel** but treats it as a generic Android gamepad.
3. **Steam's SDL mapping** (`0300f854632500002605000003016800`) applies an "Android GamePad" configuration that doesn't match the physical wheel layout.
4. **Steam does not expose the device as XInput** (`mapping uses xinput: false`), so games expecting an Xbox controller don't see it.
5. **The real and virtual devices shared VID:PID** in earlier versions of the fix, causing Steam to apply the same wrong mapping to both.

### Steam Logs (evidence)

```
Controller 0 mapping uses xinput : false
SDL Mapping for 2563/526: 0300f854632500002605000003016800,*,a:b0,b:b1,...
Controller using HIDAPI driver, vid=0x2563, pid=0x0526
```

---

## ✅ Solution

### Architecture

The solution consists of a **virtual joystick bridge** that:

1. **Reads** events from the real wheel (`/dev/input/event4`)
2. **Creates** a virtual device with **Xbox 360 Controller VID:PID** (`045E:028E`)
3. **Exposes** axes and buttons with standard XInput mapping that Steam recognizes natively

```
┌─────────────────┐     ┌──────────────────────────┐     ┌─────────────────┐
│  Serafim R2+    │────▶│  serafim_virtual_joystick │────▶│  Steam / Games  │
│  (Android       │     │  (Virtual Xbox 360 Pad)   │     │  (XInput)       │
│   GamePad)      │     │                           │     │                 │
│  2563:0526      │     │  VID:PID = 045E:028E      │     │  Detects as     │
│                 │     │  Name: "Serafim R2+       │     │  Xbox Controller│
│                 │     │         Virtual Wheel"    │     │                 │
└─────────────────┘     └──────────────────────────┘     └─────────────────┘
```

### Project Files

| File | Description |
|------|-------------|
| `serafim_virtual_joystick.py` | Main Python bridge (evdev → uinput) |
| `99-serafim-r2.rules` | udev rules for device permissions |
| `serafim-bridge.service` | systemd user service (auto-start) |
| `install.sh` | Automated installation script |

---

## 🚀 Quick Install

### Requirements

- Bazzite / Fedora Silverblue (or any distro with `python3-evdev`)
- `systemd` (for the user service)
- `sudo` access (only for udev rules and `input` group)

### Steps

```bash
# 1. Clone the repository
git clone https://github.com/JMente/SerafimR2-Bazzite.git
cd SerafimR2-Bazzite

# 2. Run installer
bash install.sh

# 3. Restart session (required for 'input' group)
# Log out and log back in

# 4. Start the bridge
systemctl --user start serafim-bridge

# 5. Verify
python3 serafim_virtual_joystick.py --list
```

### Post-installation

1. **Restart Steam completely** (close and reopen)
2. Go to **Steam → Settings → Controller**
3. **"Serafim R2+ Virtual Wheel"** (or "Microsoft X-Box 360 pad") should appear

---

## 📖 Technical Documentation

### Hardware Structure

**Serafim R2+ in Android GamePad mode:**

| Feature | Value |
|---------|-------|
| Vendor ID | `0x2563` |
| Product ID | `0x0526` |
| Manufacturer | ShenZhen ShanWan Technology |
| Bus | USB (`0x03`) |
| ABS Axes | 8 (X, Y, Z, RZ, GAS, BRAKE, HAT0X, HAT0Y) |
| Buttons | 15 (A, B, C, X, Y, Z, TL, TR, TL2, TR2, SELECT, START, MODE, THUMBL, THUMBR) |

### Axis Mapping

| Real Axis (Serafim) | Virtual Axis (Xbox 360) | Function |
|---------------------|------------------------|----------|
| `ABS_X` | `ABS_X` | Steering Wheel |
| `ABS_GAS` | `ABS_GAS` | Accelerator |
| `ABS_BRAKE` | `ABS_BRAKE` | Brake |
| `ABS_Y` | `ABS_Y` | Unused |
| `ABS_HAT0X` | `ABS_HAT0X` | D-Pad X |
| `ABS_HAT0Y` | `ABS_HAT0Y` | D-Pad Y |

### Button Mapping

| Real Button | Virtual Button | Function |
|-------------|----------------|----------|
| `BTN_A` | `BTN_A` | A / Cross down |
| `BTN_B` | `BTN_B` | B / Cross right |
| `BTN_X` | `BTN_X` | X / Cross left |
| `BTN_Y` | `BTN_Y` | Y / Cross up |
| `BTN_TL` | `BTN_TL` | L1 / Left paddle |
| `BTN_TR` | `BTN_TR` | R1 / Right paddle |
| `BTN_TL2` | `BTN_TL2` | L2 |
| `BTN_TR2` | `BTN_TR2` | R2 |
| `BTN_SELECT` | `BTN_SELECT` | Select / Share |
| `BTN_START` | `BTN_START` | Start / Options |
| `BTN_MODE` | `BTN_MODE` | Home / Mode |

### Why Xbox 360 VID:PID

The critical change in the solution was using **Microsoft Xbox 360 Controller VID:PID** (`045E:028E`) on the virtual device. This ensures that:

1. **Steam has native mapping** for this device (no "Android GamePad" heuristics)
2. **Games detect XInput** automatically
3. **No conflict** with the real device (`2563:0526`)

---

## 🔄 Alternative Solutions

### Option A: Change Wheel Mode (Hardware)

The Serafim R2+ has selectable modes via button combination:

| Mode | Combination | LED | Notes |
|------|-------------|-----|-------|
| Android (default) | — | Blue | Current mode, requires bridge |
| **PC / XInput** | `Home + X` (3 sec) | **Green** | **Recommended — may work without bridge** |
| Nintendo Switch | `Home + B` (3 sec) | Red | — |
| D-Input | `Home + Y` (3 sec) | Yellow | — |

> **Note:** In PC/XInput mode the VID:PID may change. If it changes to a Linux-known ID, the wheel might work without this bridge.

### Option B: Manual SDL_GAMECONTROLLERCONFIG

If the device appears in SDL but without correct mapping:

```bash
export SDL_GAMECONTROLLERCONFIG="0300f854632500002605000003016800,Serafim R2+,a:b0,b:b1,back:b4,dpdown:h0.4,dpleft:h0.8,dpright:h0.2,dpup:h0.1,guide:b5,leftshoulder:b9,leftstick:b7,lefttrigger:a4,leftx:a0,lefty:a1,rightshoulder:b10,rightstick:b8,righttrigger:a5,rightx:a2,righty:a3,start:b6,x:b2,y:b3,platform:Linux,"
```

### Option C: xboxdrv in DistroBox

For immutable distros where `python3-evdev` cannot be installed:

```bash
distrobox create --name xbox --image fedora:latest
distrobox enter xbox
sudo dnf install -y xboxdrv
# Specific mapping requires manual calibration
```

---

## 🎮 Game Compatibility

| Game | Status | Notes |
|------|--------|-------|
| **Assetto Corsa** | ✅ Works | Disable Steam Input if conflicts |
| **Assetto Corsa Competizione** | ✅ Works | Native XInput mode |
| **F1 23/24** | ✅ Works | — |
| **Dirt Rally 2.0** | ✅ Works | — |
| **Euro Truck Simulator 2** | ✅ Works | — |
| **BeamNG.drive** | ✅ Works | — |
| **SuperTuxKart** | ✅ Works | Confirmed native |
| **Forza Horizon 5** | ⚠️ Partial | Easy Anti-Cheat may block virtual input |
| **iRacing** | ❌ Not compatible | Requires official wheel drivers |

---

## 🔧 Troubleshooting

### "Permission denied" when running the bridge

```bash
# Add user to input group
sudo usermod -aG input $USER
# Log out and log back in
```

### Virtual device does not appear

```bash
# Verify uinput is available
ls -la /dev/uinput

# Verify service is running
systemctl --user status serafim-bridge

# Check logs
journalctl --user -u serafim-bridge -f
```

### Steam does not detect the wheel

1. Restart Steam completely (close tray icon too)
2. Verify bridge is active: `systemctl --user is-active serafim-bridge`
3. Verify devices: `python3 serafim_virtual_joystick.py --list`

### Drift or phantom buttons

This problem occurs when **Steam Input applies an incorrect mapping** (e.g. PS3) instead of the native Xbox 360 mapping. This usually happens if there were old configurations from the real device (`2563:0526`) or the previous virtual device (`2563:0527`).

**Symptoms:**
- Wheel moves by itself (drift)
- Buttons activate without pressing them
- Game shows PS3 icons (△○×□) instead of Xbox (ABXY)

**Solution:**

```bash
# 1. Stop the bridge
systemctl --user stop serafim-bridge

# 2. Delete old Steam Input configurations
rm -f ~/.local/share/Steam/steamapps/common/Steam\ Controller\ Configs/*/config/configset_2563-*.vdf
rm -f ~/.local/share/Steam/steamapps/common/Steam\ Controller\ Configs/*/config/preferences_2563-*.vdf
rm -rf ~/.local/share/Steam/steamapps/common/Steam\ Controller\ Configs/*/config/[0-9]*/

# 3. Restart the bridge
systemctl --user start serafim-bridge

# 4. Restart Steam completely
# 5. In the game, select "Gamepad" or "Xbox Controller" profile
#    DO NOT select "PS3" or "Generic"
```

> **Note:** The current bridge uses Xbox 360 Controller VID:PID (`045E:028E`) so Steam applies the correct mapping automatically. If you used an earlier version of the bridge with VID:PID `2563:0527`, Steam likely has old configs that cause conflict.

### Forza Horizon 5 does not detect the wheel

Forza Horizon 5 uses **Easy Anti-Cheat** which may block virtual input devices.

**Solution:** Disable Steam Input only for Forza 5:
```
Right-click Forza 5 → Properties → Controller → "Disable Steam Input"
```

Then add to Launch Options:
```
SDL_JOYSTICK_DEVICE=/dev/input/js1 %command%
```

(Replace `js1` with your virtual device joystick)

---

## 📝 Changelog

### v1.2 (2025-05-23)
- **Fix:** Expanded documentation with solution for drift/phantom buttons caused by old Steam Input configs
- **Fix:** Troubleshooting section for Forza Horizon 5 (Easy Anti-Cheat)
- **Improvement:** Detailed instructions for cleaning Steam Input configurations
- **New:** English README (README_EN.md)

### v1.1 (2025-05-23)
- **Fix:** Changed virtual device VID:PID to Xbox 360 Controller (`045E:028E`)
- **Fix:** Resolved drift and phantom buttons caused by conflicting Steam Input mapping
- **Improvement:** Expanded documentation with architecture and detailed mappings

### v1.0 (2025-05-23)
- Initial release
- Python bridge with evdev/uinput
- systemd user service
- Automated installation script

---

## 📄 License

MIT License — See [LICENSE](LICENSE) for details.

---

## 🙏 Credits

- **Author:** [JMente](https://github.com/JMente) (Josué Mente)
- **Assistant:** Kira (AI assistant)
- **Hardware:** Serafim R2+ Racing Wheel
- **Platform:** [Bazzite](https://bazzite.gg/) — Fedora Silverblue for gaming

---

## 🔗 Related Links

- [Serafim Official](https://www.serafim.com/)
- [Bazzite Documentation](https://docs.bazzite.gg/)
- [evdev Python Library](https://python-evdev.readthedocs.io/)
- [SDL GameControllerDB](https://github.com/mdqinc/SDL_GameControllerDB)
