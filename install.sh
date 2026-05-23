#!/bin/bash
# ============================================================================
# Instalador de Serafim R2+ Virtual Joystick Bridge para Bazzite
# ============================================================================
# Ejecutar con: bash install.sh
# Requiere: sudo (para udev rules y grupos)

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
USER_NAME="$(whoami)"

echo "============================================"
echo "  Serafim R2+ Bridge Installer"
echo "  Bazzite / Fedora Silverblue"
echo "============================================"
echo ""

# ----------------------------------------------------------------------------
# 1. Verificar dependencias
# ----------------------------------------------------------------------------
echo "[1/5] Verificando dependencias..."

if ! python3 -c "import evdev" 2>/dev/null; then
    echo "      python3-evdev NO está instalado."
    echo "      Instalando via rpm-ostree (requiere reboot)..."
    rpm-ostree install python3-evdev || {
        echo "[ERROR] No se pudo instalar python3-evdev."
        echo "[ERROR] Intenta manualmente: rpm-ostree install python3-evdev"
        exit 1
    }
    echo "      Instalación programada. Reinicia y vuelve a ejecutar este script."
    exit 0
else
    echo "      python3-evdev: OK"
fi

# ----------------------------------------------------------------------------
# 2. Agregar usuario al grupo input
# ----------------------------------------------------------------------------
echo ""
echo "[2/5] Configurando grupo 'input'..."

if groups | grep -q '\binput\b'; then
    echo "      Usuario ya está en grupo input: OK"
else
    echo "      Agregando usuario al grupo input..."
    sudo usermod -aG input "$USER_NAME"
    echo "      ¡IMPORTANTE! Cierra sesión y vuelve a entrar para aplicar cambios."
    NEED_RELOGIN=1
fi

# ----------------------------------------------------------------------------
# 3. Instalar udev rules
# ----------------------------------------------------------------------------
echo ""
echo "[3/5] Instalando udev rules..."

sudo cp "$SCRIPT_DIR/99-serafim-r2.rules" /etc/udev/rules.d/
sudo chmod 644 /etc/udev/rules.d/99-serafim-r2.rules
sudo udevadm control --reload-rules
sudo udevadm trigger --subsystem-match=input --attr-match=idVendor=2563

echo "      udev rules instaladas: OK"

# ----------------------------------------------------------------------------
# 4. Instalar servicio systemd de usuario
# ----------------------------------------------------------------------------
echo ""
echo "[4/5] Instalando servicio systemd..."

mkdir -p ~/.config/systemd/user
cp "$SCRIPT_DIR/serafim-bridge.service" ~/.config/systemd/user/

# Ajustar path en el servicio si es necesario
sed -i "s|/var/home/mente|$HOME|g" ~/.config/systemd/user/serafim-bridge.service

systemctl --user daemon-reload
systemctl --user enable serafim-bridge.service

echo "      Servicio instalado: OK"

# ----------------------------------------------------------------------------
# 5. Instrucciones finales
# ----------------------------------------------------------------------------
echo ""
echo "============================================"
echo "  Instalación completada"
echo "============================================"
echo ""

if [ -n "$NEED_RELOGIN" ]; then
    echo "⚠️  ACCIÓN REQUERIDA: Cierra sesión y vuelve a entrar"
    echo "   para que el grupo 'input' se aplique."
    echo ""
fi

echo "Para iniciar el bridge ahora:"
echo "   systemctl --user start serafim-bridge"
echo ""
echo "Para verificar que funciona:"
echo "   python3 ~/.config/serafim-r2/serafim_virtual_joystick.py --list"
echo "   sdl2-jstest --list  (instalar con: distrobox + dnf install SDL2_joystick)")
echo ""
echo "Para probar en Steam:"
echo "   1. Inicia el bridge"
echo "   2. Abre Steam → Configuración → Controlador"
echo "   3. El 'Serafim R2+ Virtual Wheel' debe aparecer"
echo ""
echo "Para desinstalar:"
echo "   systemctl --user stop serafim-bridge"
echo "   systemctl --user disable serafim-bridge"
echo "   rm ~/.config/systemd/user/serafim-bridge.service"
echo "   sudo rm /etc/udev/rules.d/99-serafim-r2.rules"
echo ""
