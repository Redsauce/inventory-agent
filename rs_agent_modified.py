#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Redsauce Inventory Agent - Recopilador de inventario de sistemas Linux
Versión: 0.1.0 (con detección de cambios y auto-actualización)
Requiere: Permisos de root/sudo
"""

import json
import subprocess
import platform
import socket
import os
import sys
import hashlib
from datetime import datetime
from pathlib import Path

try:
    import requests
except ImportError:
    requests = None

# ============ CONFIGURACIÓN ============

# Versión actual del agente
AGENT_VERSION = "0.1.0"

# URLs de GitHub para auto-actualización
GITHUB_API_URL = "https://api.github.com/repos/redsauce/inventory-agent/releases/latest"
GITHUB_AGENT_URL = "https://raw.githubusercontent.com/redsauce/inventory-agent/main/rs_agent.py"

# Directorio donde se guardará el inventario
OUTPUT_DIR = "/var/lib/rs-agent"

# Archivos de salida
OUTPUT_FILE = "inventory.json"
HASH_FILE = ".inventory.hash"

# Configuración RSM (modificar según cliente)
RSM_API_URL = "https://rsm1.redsauce.net/AppController/commands_RSM/api/api.php"
RSM_TOKEN = "429bd269e5c88dc73c14c69bf0e87717"  # ⚠️ CAMBIAR POR CLIENTE
SERVER_ID = "1"  # ⚠️ CAMBIAR POR CLIENTE

# ============ UTILIDADES ============

def run_command(cmd, shell=True, ignore_errors=False):
    """
    Ejecuta un comando y retorna su salida
    """
    try:
        result = subprocess.run(
            cmd,
            shell=shell,
            capture_output=True,
            text=True,
            timeout=30
        )
        if result.returncode != 0 and not ignore_errors:
            return None
        return result.stdout.strip()
    except subprocess.TimeoutExpired:
        print(f"⚠️ Timeout ejecutando: {cmd}")
        return None
    except Exception as e:
        if not ignore_errors:
            print(f"⚠️ Error ejecutando {cmd}: {e}")
        return None

def detect_distro():
    """
    Detecta la distribución Linux
    """
    # Intentar con /etc/os-release (método moderno)
    if os.path.exists("/etc/os-release"):
        os_release = {}
        with open("/etc/os-release", "r") as f:
            for line in f:
                if "=" in line:
                    key, value = line.strip().split("=", 1)
                    os_release[key] = value.strip('"')
        
        return {
            "name": os_release.get("NAME", "Unknown"),
            "version": os_release.get("VERSION", "Unknown"),
            "id": os_release.get("ID", "unknown"),
            "version_id": os_release.get("VERSION_ID", "Unknown")
        }
    
    # Fallback para sistemas antiguos
    if os.path.exists("/etc/redhat-release"):
        with open("/etc/redhat-release", "r") as f:
            content = f.read().strip()
            return {"name": content, "version": "Unknown", "id": "rhel-based", "version_id": "Unknown"}
    
    if os.path.exists("/etc/debian_version"):
        with open("/etc/debian_version", "r") as f:
            version = f.read().strip()
            return {"name": "Debian", "version": version, "id": "debian", "version_id": version}
    
    return {"name": "Unknown", "version": "Unknown", "id": "unknown", "version_id": "Unknown"}

def get_package_manager():
    """
    Detecta el gestor de paquetes disponible
    """
    managers = {
        "dpkg": "dpkg -l",
        "rpm": "rpm -qa",
        "apt": "apt list --installed",
        "yum": "yum list installed",
        "dnf": "dnf list installed"
    }
    
    for manager, cmd in managers.items():
        if run_command(f"which {manager}", ignore_errors=True):
            return manager
    
    return None

# ============ RECOPILADORES ============

def collect_system_info():
    """
    Información básica del sistema
    """
    distro = detect_distro()
    
    return {
        "hostname": socket.gethostname(),
        "fqdn": socket.getfqdn(),
        "os": {
            "name": distro["name"],
            "version": distro["version"],
            "distro_id": distro["id"],
            "distro_version": distro["version_id"],
            "kernel": platform.release(),
            "architecture": platform.machine()
        },
        "python_version": platform.python_version(),
        "collected_at": datetime.now().isoformat()
    }

def collect_hardware():
    """
    Información de hardware
    """
    hardware = {}
    
    # CPU
    cpu_info = run_command("lscpu")
    if cpu_info:
        for line in cpu_info.split('\n'):
            if "Model name:" in line:
                hardware["cpu_model"] = line.split(":", 1)[1].strip()
            elif "CPU(s):" in line and "NUMA" not in line:
                hardware["cpu_cores"] = line.split(":", 1)[1].strip()
    
    # RAM
    mem_info = run_command("free -m")
    if mem_info:
        lines = mem_info.split('\n')
        if len(lines) > 1:
            mem_parts = lines[1].split()
            if len(mem_parts) > 1:
                hardware["ram_mb"] = mem_parts[1]
    
    # Discos
    disks = []
    disk_info = run_command("lsblk -b -d -o NAME,SIZE,TYPE,MODEL -n")
    if disk_info:
        for line in disk_info.split('\n'):
            parts = line.split()
            if len(parts) >= 3 and parts[2] == "disk":
                disks.append({
                    "device": f"/dev/{parts[0]}",
                    "size_bytes": parts[1],
                    "model": " ".join(parts[3:]) if len(parts) > 3 else "Unknown"
                })
    hardware["disks"] = disks
    
    # Interfaces de red
    interfaces = []
    ip_info = run_command("ip -o addr show")
    if ip_info:
        for line in ip_info.split('\n'):
            parts = line.split()
            if len(parts) >= 4:
                interface = parts[1]
                ip = parts[3].split('/')[0]
                if interface != "lo":  # Ignorar loopback
                    interfaces.append({
                        "name": interface,
                        "ip": ip
                    })
    hardware["network_interfaces"] = interfaces
    
    return hardware

def collect_packages_dpkg():
    """
    Recopila paquetes instalados vía dpkg (Debian/Ubuntu)
    """
    packages = []
    output = run_command("dpkg-query -W -f='${Package}\t${Version}\t${Status}\n'")
    
    if output:
        for line in output.split('\n'):
            parts = line.split('\t')
            if len(parts) >= 3 and "installed" in parts[2]:
                packages.append({
                    "name": parts[0],
                    "version": parts[1],
                    "manager": "dpkg"
                })
    
    return packages

def collect_packages_rpm():
    """
    Recopila paquetes instalados vía rpm (RHEL/CentOS/Fedora)
    """
    packages = []
    output = run_command("rpm -qa --queryformat '%{NAME}\t%{VERSION}-%{RELEASE}\n'")
    
    if output:
        for line in output.split('\n'):
            parts = line.split('\t')
            if len(parts) >= 2:
                packages.append({
                    "name": parts[0],
                    "version": parts[1],
                    "manager": "rpm"
                })
    
    return packages

def collect_packages():
    """
    Recopila todos los paquetes del sistema
    """
    pkg_manager = get_package_manager()
    
    if pkg_manager in ["dpkg", "apt"]:
        return collect_packages_dpkg()
    elif pkg_manager in ["rpm", "yum", "dnf"]:
        return collect_packages_rpm()
    else:
        print("⚠️ No se detectó un gestor de paquetes compatible")
        return []

def collect_pip_packages():
    """
    Recopila paquetes Python instalados
    """
    packages = []
    
    # Intentar con pip3
    for pip_cmd in ["pip3", "pip"]:
        output = run_command(f"{pip_cmd} list --format=json", ignore_errors=True)
        if output:
            try:
                pip_list = json.loads(output)
                for pkg in pip_list:
                    packages.append({
                        "name": pkg["name"],
                        "version": pkg["version"],
                        "manager": "pip"
                    })
                break  # Si funcionó, no intentar el otro
            except json.JSONDecodeError:
                continue
    
    return packages

def collect_npm_packages():
    """
    Recopila paquetes Node.js globales
    """
    packages = []
    output = run_command("npm list -g --depth=0 --json", ignore_errors=True)
    
    if output:
        try:
            npm_data = json.loads(output)
            deps = npm_data.get("dependencies", {})
            for name, info in deps.items():
                packages.append({
                    "name": name,
                    "version": info.get("version", "unknown"),
                    "manager": "npm"
                })
        except json.JSONDecodeError:
            pass
    
    return packages

def collect_services():
    """
    Recopila servicios systemd activos
    """
    services = []
    output = run_command("systemctl list-units --type=service --state=running --no-pager --no-legend")
    
    if output:
        for line in output.split('\n'):
            parts = line.split()
            if parts:
                service_name = parts[0].replace(".service", "")
                services.append({
                    "name": service_name,
                    "status": "running"
                })
    
    return services

def collect_critical_software():
    """
    Detecta versiones de software crítico común
    """
    software = {}
    
    # Lista de software a detectar
    checks = {
        "apache2": "apache2 -v",
        "httpd": "httpd -v",
        "nginx": "nginx -v",
        "mysql": "mysql --version",
        "mysqld": "mysqld --version",
        "postgresql": "psql --version",
        "postgres": "postgres --version",
        "docker": "docker --version",
        "php": "php --version",
        "node": "node --version",
        "java": "java -version",
        "python3": "python3 --version",
        "openssh": "ssh -V",
        "openssl": "openssl version",
        "git": "git --version"
    }
    
    for name, cmd in checks.items():
        version = run_command(cmd, ignore_errors=True)
        if version:
            # Extraer solo la primera línea (suele tener la versión)
            version = version.split('\n')[0]
            software[name] = version
    
    return software

# ============ DETECCIÓN DE CAMBIOS ============

def calculate_hash(data):
    """
    Calcula hash SHA256 del inventario (sin timestamp)
    """
    # Crear copia sin el timestamp para comparar contenido real
    data_copy = json.loads(json.dumps(data))
    if 'system' in data_copy and 'collected_at' in data_copy['system']:
        del data_copy['system']['collected_at']
    
    # Serializar de forma determinista
    json_str = json.dumps(data_copy, sort_keys=True)
    return hashlib.sha256(json_str.encode()).hexdigest()

def load_previous_hash():
    """
    Carga el hash del inventario anterior
    """
    hash_path = os.path.join(OUTPUT_DIR, HASH_FILE)
    if os.path.exists(hash_path):
        with open(hash_path, 'r') as f:
            return f.read().strip()
    return None

def save_hash(hash_value):
    """
    Guarda el hash del inventario actual
    """
    hash_path = os.path.join(OUTPUT_DIR, HASH_FILE)
    with open(hash_path, 'w') as f:
        f.write(hash_value)

# ============ ENVÍO A RSM ============

def send_to_rsm(inventory):
    """
    Envía los system_packages a RSM mediante curl
    Retorna True si el envío fue exitoso, False en caso contrario
    """
    print("\n📤 Enviando datos a RSM...")
    
    system_packages = inventory.get('system_packages', [])
    
    if not system_packages:
        print("⚠️ No hay paquetes del sistema para enviar")
        return True
    
    # Transformar al formato RSM
    rsm_data = []
    for pkg in system_packages:
        rsm_data.append({
            "77": pkg["name"],
            "78": pkg["version"],
            "79": SERVER_ID
        })
    
    # 🔍 DEBUG 1: Mostrar muestra de datos
    print(f"\n🔍 DEBUG - Total paquetes a enviar: {len(rsm_data)}")
    print(f"🔍 DEBUG - Muestra de los primeros 3 paquetes:")
    for i, pkg in enumerate(rsm_data[:3]):
        print(f"   [{i+1}] {pkg}")
    
    # Convertir a JSON string
    rsm_json = json.dumps(rsm_data, ensure_ascii=False)
    
    # 🔍 DEBUG 2: Mostrar JSON (primeros 500 caracteres)
    print(f"\n🔍 DEBUG - JSON generado (primeros 500 chars):")
    print(f"   {rsm_json[:500]}...")
    print(f"🔍 DEBUG - Longitud total del JSON: {len(rsm_json)} caracteres")
    
    # 🔍 DEBUG 3: Guardar JSON en archivo temporal para inspección
    debug_json_path = "/tmp/rsm_debug_payload.json"
    with open(debug_json_path, 'w') as f:
        f.write(rsm_json)
    print(f"🔍 DEBUG - JSON completo guardado en: {debug_json_path}")
    
    # Construir comando curl (SIN --silent para ver respuesta completa)
    curl_cmd = [
        'curl',
        '--location', RSM_API_URL,
        '--form', 'RStrigger=newServerData',
        '--form', f'RSdata={rsm_json}',
        '--form', f'RStoken={RSM_TOKEN}',
        '--max-time', '30',
        '--show-error',
        '--verbose'  # 🔍 Añadir verbose para ver más detalles
    ]
    
    # 🔍 DEBUG 4: Mostrar comando curl exacto
    print(f"\n🔍 DEBUG - Comando curl a ejecutar:")
    print(f"   {' '.join(curl_cmd[:6])}...")  # Mostrar primeros argumentos
    print(f"🔍 DEBUG - Configuración:")
    print(f"   • URL: {RSM_API_URL}")
    print(f"   • Token: {RSM_TOKEN}")
    print(f"   • Server ID: {SERVER_ID}")
    
    try:
        print(f"\n🔄 Ejecutando petición a RSM...")
        
        # Ejecutar curl
        result = subprocess.run(
            curl_cmd,
            capture_output=True,
            text=True,
            timeout=35
        )
        
        # 🔍 DEBUG 5: Mostrar respuesta completa
        print(f"\n🔍 DEBUG - Código de salida: {result.returncode}")
        
        if result.stdout:
            print(f"🔍 DEBUG - STDOUT del servidor:")
            print(f"   {result.stdout}")
        
        if result.stderr:
            print(f"🔍 DEBUG - STDERR (info de curl):")
            print(f"   {result.stderr[:500]}...")  # Primeros 500 caracteres
        
        if result.returncode == 0:
            print(f"\n✅ Datos enviados correctamente ({len(system_packages)} paquetes)")
            return True
        else:
            print(f"\n❌ ERROR: Fallo al enviar datos a RSM")
            return False
            
    except subprocess.TimeoutExpired:
        print("❌ ERROR: Timeout al enviar datos a RSM (>30s)")
        return False
    except Exception as e:
        print(f"❌ ERROR: Excepción al enviar datos a RSM: {e}")
        import traceback
        traceback.print_exc()
        return False

# ============ AUTO-ACTUALIZACIÓN ============

def check_for_updates():
    """Comprueba si hay nueva versión en GitHub Releases"""
    if not requests:
        return False  # Si no hay requests, no puede actualizar
    
    try:
        response = requests.get(GITHUB_API_URL, timeout=5)
        if response.status_code == 200:
            data = response.json()
            latest_version = data['tag_name'].lstrip('v')  # Por si usa v0.1.0
            
            if latest_version > AGENT_VERSION:
                print(f"🔄 Nueva versión disponible: {latest_version} (actual: {AGENT_VERSION})")
                return download_update()
    except Exception as e:
        # Falla silenciosamente para no interrumpir el inventario
        pass
    
    return False

def download_update():
    """Descarga e instala la nueva versión"""
    try:
        print("📥 Descargando actualización...")
        response = requests.get(GITHUB_AGENT_URL, timeout=10)
        
        if response.status_code == 200:
            script_path = "/opt/rs-agent/rs_agent.py"
            
            # Guardar backup
            backup_path = script_path + ".backup"
            if os.path.exists(script_path):
                os.rename(script_path, backup_path)
            
            # Escribir nueva versión
            with open(script_path, 'w') as f:
                f.write(response.text)
            os.chmod(script_path, 0o755)
            
            print("✅ Actualización completada. Reiniciando agente...")
            
            # Re-ejecutar el script actualizado
            os.execv(sys.executable, [sys.executable] + sys.argv)
            
        return True
        
    except Exception as e:
        print(f"⚠️ Error actualizando: {e}")
        # Restaurar backup si existe
        if os.path.exists(backup_path):
            os.rename(backup_path, script_path)
        return False

# ============ MAIN ============

def check_root():
    """
    Verifica que el script se ejecute como root
    """
    if os.geteuid() != 0:
        print("❌ ERROR: Este script requiere permisos de root")
        print("   Ejecuta con: sudo python3 rs_agent.py")
        sys.exit(1)

def ensure_output_dir():
    """
    Crea el directorio de salida si no existe
    """
    Path(OUTPUT_DIR).mkdir(parents=True, exist_ok=True)

def main():
    print("\n" + "="*60)
    print("🔍 Redsauce Inventory Agent - Recopilando información")
    print("="*60 + "\n")
    
    # Verificar permisos
    check_root()
    
    # Comprobar actualizaciones (antes de recopilar inventario)
    if check_for_updates():
        return  # Si se actualizó, el script se re-ejecuta automáticamente
    
    # Crear directorio de salida
    ensure_output_dir()
    
    # Recopilar información
    inventory = {}
    
    print("📋 Recopilando información del sistema...")
    inventory["system"] = collect_system_info()
    
    print("🖥️ Recopilando información de hardware...")
    inventory["hardware"] = collect_hardware()
    
    print("📦 Recopilando paquetes del sistema...")
    inventory["system_packages"] = collect_packages()
    print(f"   → {len(inventory['system_packages'])} paquetes encontrados")
    
    print("🐍 Recopilando paquetes Python...")
    inventory["pip_packages"] = collect_pip_packages()
    print(f"   → {len(inventory['pip_packages'])} paquetes pip encontrados")
    
    print("🔗 Recopilando paquetes Node.js...")
    inventory["npm_packages"] = collect_npm_packages()
    print(f"   → {len(inventory['npm_packages'])} paquetes npm encontrados")
    
    print("⚙️ Recopilando servicios activos...")
    inventory["services"] = collect_services()
    print(f"   → {len(inventory['services'])} servicios activos")
    
    print("🔧 Detectando software crítico...")
    inventory["critical_software"] = collect_critical_software()
    print(f"   → {len(inventory['critical_software'])} aplicaciones detectadas")
    
    # Calcular hash del nuevo inventario
    new_hash = calculate_hash(inventory)
    previous_hash = load_previous_hash()
    
    output_path = os.path.join(OUTPUT_DIR, OUTPUT_FILE)
    
    # Comparar con hash anterior
    if previous_hash and new_hash == previous_hash:
        print("\n" + "="*60)
        print("✓ No hay cambios en el sistema")
        print("="*60)
        print(f"\n📄 Inventario actual: {output_path}")
        print(f"🕐 Última actualización: {inventory['system']['collected_at']}")
        print()
        return
    
    # Hay cambios o es primera ejecución
    print(f"\n💾 Guardando inventario en {output_path}...")
    
    with open(output_path, 'w') as f:
        json.dump(inventory, f, indent=2)
    
    # Guardar nuevo hash
    save_hash(new_hash)
    
    # Enviar datos a RSM (solo cuando hay cambios)
    if not send_to_rsm(inventory):
        print("\n" + "="*60)
        print("❌ ERROR CRÍTICO: No se pudo enviar el inventario a RSM")
        print("="*60)
        print("\n⚠️ Verifica:")
        print(f"   • Token RSM: {RSM_TOKEN}")
        print(f"   • Server ID: {SERVER_ID}")
        print(f"   • URL: {RSM_API_URL}")
        print(f"   • Conectividad de red")
        print()
        sys.exit(1)
    
    # Estadísticas finales
    total_packages = (len(inventory['system_packages']) + 
                     len(inventory['pip_packages']) + 
                     len(inventory['npm_packages']))
    
    print("\n" + "="*60)
    if previous_hash:
        print("✅ Inventario actualizado (detectados cambios)")
    else:
        print("✅ Inventario creado (primera ejecución)")
    print("="*60)
    print(f"\n📊 Resumen:")
    print(f"   • Sistema: {inventory['system']['os']['name']} {inventory['system']['os']['version']}")
    print(f"   • Hostname: {inventory['system']['hostname']}")
    print(f"   • Total paquetes: {total_packages}")
    print(f"   • Servicios activos: {len(inventory['services'])}")
    print(f"   • Archivo: {output_path}")
    print(f"   • Tamaño: {os.path.getsize(output_path) / 1024:.2f} KB")
    print()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️ Proceso interrumpido por el usuario")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error inesperado: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
