#!/bin/bash
# ============================================================================
# Redsauce Inventory Agent - Instalador One-Liner
# ============================================================================
#
# Uso:
#   curl -fsSL https://raw.githubusercontent.com/redsauce/inventory-agent/main/install.sh | sudo bash
#

set -e

# ============================================================================
# CONFIGURACIÓN
# ============================================================================

# URL de GitHub donde está el agente
GITHUB_RAW_URL="https://raw.githubusercontent.com/redsauce/inventory-agent/main"

# Directorios de instalación
INSTALL_DIR="/opt/rs-agent"
DATA_DIR="/var/lib/rs-agent"
LOG_FILE="/var/log/rs-agent.log"

# ============================================================================
# COLORES
# ============================================================================

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# ============================================================================
# FUNCIONES
# ============================================================================

log() {
    echo -e "${GREEN}✓${NC} $1"
}

error() {
    echo -e "${RED}✗${NC} $1"
}

info() {
    echo -e "${BLUE}ℹ${NC} $1"
}

warn() {
    echo -e "${YELLOW}⚠${NC} $1"
}

banner() {
    echo ""
    echo "============================================================================"
    echo "  🤖 Redsauce Inventory Agent - Instalador"
    echo "============================================================================"
    echo ""
}

check_root() {
    if [ "$EUID" -ne 0 ]; then 
        error "Este script debe ejecutarse como root"
        echo ""
        echo "Ejecuta:"
        echo "  curl -fsSL https://raw.githubusercontent.com/redsauce/inventory-agent/main/install.sh | sudo bash"
        echo ""
        exit 1
    fi
}

detect_distro() {
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        DISTRO=$ID
        VERSION=$VERSION_ID
    elif [ -f /etc/redhat-release ]; then
        DISTRO="rhel"
        VERSION=$(cat /etc/redhat-release | grep -oE '[0-9]+\.[0-9]+' | head -1)
    else
        DISTRO="unknown"
        VERSION="unknown"
    fi
    
    info "Distribución: $DISTRO $VERSION"
}

check_dependencies() {
    info "Verificando dependencias..."
    
    # Verificar curl (debería estar si llegamos aquí)
    if ! command -v curl &> /dev/null; then
        error "curl no está instalado"
        exit 1
    fi
    
    # Verificar Python 3
    if ! command -v python3 &> /dev/null; then
        warn "Python 3 no está instalado, instalando..."
        install_python
    else
        log "Python 3 encontrado: $(python3 --version)"
    fi
}

install_python() {
    case $DISTRO in
        ubuntu|debian)
            apt-get update -qq
            apt-get install -y python3 python3-pip lsb-release util-linux iproute2 > /dev/null 2>&1
            ;;
        rhel|centos|fedora|rocky|almalinux)
            if command -v dnf &> /dev/null; then
                dnf install -y python3 python3-pip util-linux iproute > /dev/null 2>&1
            else
                yum install -y python3 python3-pip util-linux iproute > /dev/null 2>&1
            fi
            ;;
        *)
            error "Distribución no soportada: $DISTRO"
            exit 1
            ;;
    esac
    log "Dependencias instaladas"
}

create_directories() {
    info "Creando directorios..."
    
    mkdir -p "$INSTALL_DIR"
    mkdir -p "$DATA_DIR"
    touch "$LOG_FILE"
    chmod 644 "$LOG_FILE"
    
    log "Directorios creados"
}

download_agent() {
    info "Descargando agente desde GitHub..."
    
    AGENT_URL="${GITHUB_RAW_URL}/rs_agent.py"
    
    # Descargar con curl
    if curl -fsSL "$AGENT_URL" -o "$INSTALL_DIR/rs_agent.py"; then
        chmod +x "$INSTALL_DIR/rs_agent.py"
        log "Agente descargado: $INSTALL_DIR/rs_agent.py"
    else
        error "No se pudo descargar el agente desde GitHub"
        error ""
        error "URL intentada: $AGENT_URL"
        error ""
        error "Verifica que:"
        error "  • Tienes conexión a internet"
        error "  • GitHub es accesible desde este servidor"
        exit 1
    fi
}

setup_cron() {
    info "Configurando ejecución automática..."
    
    CRON_JOB="0 3 * * * /usr/bin/python3 $INSTALL_DIR/rs_agent.py >> $LOG_FILE 2>&1"
    
    # Añadir a crontab de root (evitar duplicados)
    (crontab -l 2>/dev/null | grep -v "$INSTALL_DIR/rs_agent.py"; echo "$CRON_JOB") | crontab -
    
    log "Cron configurado (ejecución diaria a las 3:00 AM)"
}

test_agent() {
    info "Ejecutando primera recopilación..."
    
    if /usr/bin/python3 "$INSTALL_DIR/rs_agent.py" >> "$LOG_FILE" 2>&1; then
        if [ -f "$DATA_DIR/inventory.json" ]; then
            INVENTORY_SIZE=$(stat -f%z "$DATA_DIR/inventory.json" 2>/dev/null || stat -c%s "$DATA_DIR/inventory.json" 2>/dev/null)
            log "Inventario generado correctamente (${INVENTORY_SIZE} bytes)"
            return 0
        fi
    fi
    
    warn "No se pudo generar el inventario en la primera ejecución"
    info "Revisa el log: tail -f $LOG_FILE"
    return 1
}

create_uninstaller() {
    cat > "$INSTALL_DIR/uninstall.sh" << 'UNINSTALL_EOF'
#!/bin/bash
echo "🗑️  Desinstalando Redsauce Inventory Agent..."

# Eliminar cron
crontab -l 2>/dev/null | grep -v "/opt/rs-agent/rs_agent.py" | crontab -
echo "✓ Entrada de cron eliminada"

# Preguntar antes de borrar datos
read -p "¿Eliminar datos de inventario? (s/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Ss]$ ]]; then
    rm -rf /var/lib/rs-agent
    echo "✓ Datos eliminados"
fi

rm -rf /opt/rs-agent
rm -f /var/log/rs-agent.log

echo "✓ Agente desinstalado"
UNINSTALL_EOF
    
    chmod +x "$INSTALL_DIR/uninstall.sh"
}

print_summary() {
    echo ""
    echo "============================================================================"
    echo "  ✅ INSTALACIÓN COMPLETADA"
    echo "============================================================================"
    echo ""
    echo "📁 Ubicaciones:"
    echo "   • Agente:      $INSTALL_DIR/rs_agent.py"
    echo "   • Inventario:  $DATA_DIR/inventory.json"
    echo "   • Logs:        $LOG_FILE"
    echo ""
    echo "⏰ Ejecución:"
    echo "   • Automática:  Diariamente a las 3:00 AM"
    echo "   • Manual:      sudo python3 $INSTALL_DIR/rs_agent.py"
    echo ""
    echo "📊 Ver inventario:"
    echo "   cat $DATA_DIR/inventory.json | python3 -m json.tool"
    echo ""
    echo "🔄 Funcionamiento:"
    echo "   • Solo actualiza si detecta cambios en el sistema"
    echo "   • Ahorra espacio y logs innecesarios"
    echo ""
    echo "🗑️  Desinstalar:"
    echo "   sudo bash $INSTALL_DIR/uninstall.sh"
    echo ""
    echo "============================================================================"
    echo ""
}

# ============================================================================
# MAIN
# ============================================================================

main() {
    banner
    
    # Verificaciones
    check_root
    detect_distro
    check_dependencies
    
    # Instalación
    create_directories
    download_agent
    setup_cron
    create_uninstaller
    
    # Prueba
    echo ""
    test_agent
    
    # Resumen
    print_summary
    
    log "Instalación exitosa"
}

# Ejecutar
main "$@"