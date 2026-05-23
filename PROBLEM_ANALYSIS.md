# Análisis Técnico del Problema

## Hardware

- **Volante:** Serafim Racing Wheel R2+
- **Modo detectado:** Android GamePad
- **VID:PID:** `2563:0526` (ShenZhen ShanWan Technology Co., Ltd.)
- **Sistema:** Bazzite (Fedora Silverblue/SteamOS-based, Wayland, inmutable)

## Síntomas Reportados

1. El volante se detecta como "Android GamePad" en `lsusb`
2. `evtest` confirma eventos del kernel (BTN_TR, BTN_TL, MSC_SCAN, etc.)
3. Steam Input lo intercepta pero no mapea correctamente
4. Juegos Steam no reciben inputs

## Diagnóstico por Capas

### Capa 1: Kernel (evdev)

**Estado:** ✅ FUNCIONA

```
EV=1b  (EV_SYN + EV_KEY + EV_ABS + EV_MSC)
KEY=7fff000000000000 (15 botones)
ABS=30627 (8 ejes: X, Y, Z, RZ, GAS, BRAKE, HAT0X, HAT0Y)
```

El kernel detecta correctamente el dispositivo como joystick (`ID_INPUT_JOYSTICK=1`).

### Capa 2: Joystick API (/dev/input/js0)

**Estado:** ✅ EXISTE

El dispositivo crea `/dev/input/js0` con 8 ejes y 15 botones.

### Capa 3: SDL2

**Estado:** ❌ NO DETECTA

`sdl2-jstest --list` no muestra el dispositivo. Esto es clave: SDL2 rechaza el dispositivo a pesar de que existe `/dev/input/js0`.

**Hipótesis:** SDL2 tiene una lista interna de dispositivos conocidos o aplica heurísticas que descartan "Android GamePad" genéricos.

### Capa 4: Steam Input

**Estado:** ⚠️ PARCIAL

Steam Input detecta el volante pero:
- `mapping uses xinput: false`
- Aplica mapeo de "Android GamePad" que no coincide con la disposición física
- No expone el dispositivo como XInput a los juegos

**Evidencia de logs:**
```
Controller 0 mapping uses xinput : false
SDL Mapping for 2563/526: 0300f854632500002605000003016800,*,a:b0,b:b1,...
Controller using HIDAPI driver, vid=0x2563, pid=0x0526
```

### Capa 5: Juegos

**Estado:** ❌ FALLAN

Los juegos que esperan XInput (Forza, Assetto Corsa, F1) no ven el volante.

## Causa Raíz Identificada

El problema no es del kernel ni del hardware. Es un problema de **identidad del dispositivo** a nivel de SDL2/Steam Input:

1. El dispositivo se presenta como "Android GamePad" genérico
2. Steam Input no tiene un mapeo XInput predefinido para este VID:PID
3. El mapeo heurístico que aplica Steam no coincide con la disposición física del volante
4. Los juegos no reciben inputs porque no hay un gamepad XInput estándar presente

## Solución Aplicada

Crear un **dispositivo virtual** con:
- **VID:PID de Xbox 360 Controller** (`045E:028E`)
- **Nombre descriptivo:** "Serafim R2+ Virtual Wheel"
- **Mapeo de ejes/botones** 1:1 desde el dispositivo real

Esto aprovecha que Steam tiene mapeo nativo y optimizado para Xbox 360 Controller, eliminando cualquier heurística errónea.

## Lecciones Aprendidas

1. **No siempre es un problema de permisos:** Aunque el usuario no estaba en grupo `input`, las ACLs daban acceso. El problema era de identidad del dispositivo.

2. **VID:PID importa más de lo que parece:** No es solo identificación; determina qué drivers y mapeos aplica SDL2/Steam.

3. **Steam Input es la capa crítica:** Aunque SDL2 no detectaba el dispositivo, Steam Input sí. El problema era que Steam no lo exponía como XInput.

4. **Los dispositivos virtuales son poderosos:** Cuando el hardware no puede cambiar su identidad, un bridge virtual es la solución más limpia.
