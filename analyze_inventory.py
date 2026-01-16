#!/usr/bin/env python3
"""
Herramienta de análisis de inventario - Redsauce Agent
Muestra estadísticas y resumen del último inventario recopilado
"""

import json
import sys
from pathlib import Path
from datetime import datetime

INVENTORY_FILE = "/var/lib/rs-agent/inventories/inventory.json"

def load_inventory():
    """Carga el archivo de inventario"""
    if not Path(INVENTORY_FILE).exists():
        print(f"❌ No se encuentra el inventario en: {INVENTORY_FILE}")
        print("   Ejecuta primero: sudo python3 /opt/rs-agent/rs_agent.py")
        sys.exit(1)
    
    with open(INVENTORY_FILE, 'r') as f:
        return json.load(f)

def format_bytes(bytes_value):
    """Formatea bytes en formato legible"""
    try:
        bytes_value = int(bytes_value)
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if bytes_value < 1024.0:
                return f"{bytes_value:.2f} {unit}"
            bytes_value /= 1024.0
        return f"{bytes_value:.2f} PB"
    except (ValueError, TypeError):
        return "N/A"

def print_section(title):
    """Imprime encabezado de sección"""
    print(f"\n{'='*70}")
    print(f"  {title}")
    print(f"{'='*70}")

def analyze_system(inventory):
    """Analiza información del sistema"""
    print_section("📋 INFORMACIÓN DEL SISTEMA")
    
    system = inventory.get('system', {})
    os_info = system.get('os', {})
    
    print(f"Hostname:      {system.get('hostname', 'N/A')}")
    print(f"FQDN:          {system.get('fqdn', 'N/A')}")
    print(f"OS:            {os_info.get('name', 'N/A')} {os_info.get('version', 'N/A')}")
    print(f"Distribución:  {os_info.get('distro_id', 'N/A')}")
    print(f"Kernel:        {os_info.get('kernel', 'N/A')}")
    print(f"Arquitectura:  {os_info.get('architecture', 'N/A')}")
    print(f"Python:        {system.get('python_version', 'N/A')}")
    
    collected_at = system.get('collected_at', 'N/A')
    if collected_at != 'N/A':
        try:
            dt = datetime.fromisoformat(collected_at)
            print(f"Recopilado:    {dt.strftime('%d/%m/%Y %H:%M:%S')}")
        except:
            print(f"Recopilado:    {collected_at}")

def analyze_hardware(inventory):
    """Analiza información de hardware"""
    print_section("🖥️  HARDWARE")
    
    hardware = inventory.get('hardware', {})
    
    # CPU
    print(f"CPU:           {hardware.get('cpu_model', 'N/A')}")
    print(f"Cores:         {hardware.get('cpu_cores', 'N/A')}")
    
    # RAM
    ram_mb = hardware.get('ram_mb', 'N/A')
    if ram_mb != 'N/A':
        try:
            ram_gb = int(ram_mb) / 1024
            print(f"RAM:           {ram_gb:.2f} GB ({ram_mb} MB)")
        except:
            print(f"RAM:           {ram_mb} MB")
    else:
        print(f"RAM:           N/A")
    
    # Discos
    disks = hardware.get('disks', [])
    print(f"\nDiscos:        {len(disks)} dispositivo(s)")
    for disk in disks:
        size = format_bytes(disk.get('size_bytes', 0))
        model = disk.get('model', 'Unknown')
        print(f"  • {disk.get('device', 'N/A')}: {size} - {model}")
    
    # Interfaces de red
    interfaces = hardware.get('network_interfaces', [])
    print(f"\nRed:           {len(interfaces)} interfaz(es)")
    for iface in interfaces:
        print(f"  • {iface.get('name', 'N/A')}: {iface.get('ip', 'N/A')}")

def analyze_packages(inventory):
    """Analiza paquetes instalados"""
    print_section("📦 SOFTWARE INSTALADO")
    
    # Paquetes del sistema
    sys_packages = inventory.get('system_packages', [])
    print(f"Sistema:       {len(sys_packages)} paquetes")
    
    # Paquetes Python
    pip_packages = inventory.get('pip_packages', [])
    print(f"Python (pip):  {len(pip_packages)} paquetes")
    
    # Paquetes Node
    npm_packages = inventory.get('npm_packages', [])
    print(f"Node (npm):    {len(npm_packages)} paquetes")
    
    # Total
    total = len(sys_packages) + len(pip_packages) + len(npm_packages)
    print(f"\nTOTAL:         {total} paquetes")
    
    # Top 10 paquetes del sistema
    if sys_packages:
        print(f"\nTop 10 paquetes del sistema:")
        for pkg in sys_packages[:10]:
            print(f"  • {pkg['name']:30s} {pkg['version']}")

def analyze_services(inventory):
    """Analiza servicios activos"""
    print_section("⚙️  SERVICIOS ACTIVOS")
    
    services = inventory.get('services', [])
    print(f"Total:         {len(services)} servicios corriendo")
    
    if services:
        # Agrupar por categoría (heurística simple)
        web_services = [s for s in services if any(k in s['name'].lower() 
                       for k in ['apache', 'nginx', 'httpd', 'lighttpd'])]
        db_services = [s for s in services if any(k in s['name'].lower() 
                      for k in ['mysql', 'postgres', 'mariadb', 'mongodb', 'redis'])]
        
        print(f"\nCategorías:")
        print(f"  • Servidores web:  {len(web_services)}")
        print(f"  • Bases de datos:  {len(db_services)}")
        
        # Listar algunos importantes
        print(f"\nServicios destacados:")
        important = ['ssh', 'sshd', 'cron', 'systemd', 'docker', 'apache2', 
                    'nginx', 'mysql', 'postgresql']
        
        for service in services:
            if any(imp in service['name'].lower() for imp in important):
                print(f"  • {service['name']}")

def analyze_critical_software(inventory):
    """Analiza software crítico detectado"""
    print_section("🔧 SOFTWARE CRÍTICO DETECTADO")
    
    software = inventory.get('critical_software', {})
    
    if not software:
        print("No se detectó software crítico")
        return
    
    print(f"Total:         {len(software)} aplicaciones\n")
    
    # Categorizar
    categories = {
        'Servidores Web': ['apache2', 'httpd', 'nginx'],
        'Bases de Datos': ['mysql', 'mysqld', 'postgresql', 'postgres'],
        'Lenguajes': ['python3', 'php', 'node', 'java'],
        'Herramientas': ['docker', 'git', 'openssh', 'openssl']
    }
    
    for category, keywords in categories.items():
        found = {k: v for k, v in software.items() if k in keywords}
        if found:
            print(f"{category}:")
            for name, version in found.items():
                # Limpiar salida de versión
                version_clean = version.split('\n')[0][:60]
                print(f"  • {name:12s} → {version_clean}")
            print()

def generate_summary(inventory):
    """Genera resumen ejecutivo"""
    print_section("📊 RESUMEN EJECUTIVO")
    
    sys_packages = len(inventory.get('system_packages', []))
    pip_packages = len(inventory.get('pip_packages', []))
    npm_packages = len(inventory.get('npm_packages', []))
    services = len(inventory.get('services', []))
    critical = len(inventory.get('critical_software', {}))
    disks = len(inventory.get('hardware', {}).get('disks', []))
    
    print(f"Este sistema tiene:")
    print(f"  • {sys_packages + pip_packages + npm_packages} paquetes instalados en total")
    print(f"  • {services} servicios activos")
    print(f"  • {critical} aplicaciones críticas detectadas")
    print(f"  • {disks} discos físicos")
    
    # Calcular tamaño del inventario
    try:
        size = Path(INVENTORY_FILE).stat().st_size / 1024
        print(f"\nTamaño del inventario: {size:.2f} KB")
    except:
        pass

def main():
    print("\n" + "="*70)
    print("  🔍 Análisis de Inventario - Redsauce Agent")
    print("="*70)
    
    # Cargar inventario
    try:
        inventory = load_inventory()
    except Exception as e:
        print(f"❌ Error al cargar inventario: {e}")
        sys.exit(1)
    
    # Analizar cada sección
    analyze_system(inventory)
    analyze_hardware(inventory)
    analyze_packages(inventory)
    analyze_services(inventory)
    analyze_critical_software(inventory)
    generate_summary(inventory)
    
    print("\n" + "="*70)
    print(f"  Inventario completo disponible en: {INVENTORY_FILE}")
    print("="*70 + "\n")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Análisis interrumpido")
        sys.exit(0)
