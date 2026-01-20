#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de prueba para verificar el envío a RSM
Simula el envío de paquetes sin ejecutar todo el agente
"""

import json
import subprocess
import sys

# CONFIGURAR ESTOS VALORES
RSM_API_URL = "https://rsm1.redsauce.net/AppController/commands_RSM/api/api.php"
RSM_TOKEN = "429bd269e5c88dc73c14c69bf0e87717"  # ⚠️ CAMBIAR
RSM_CLIENT_ID = "1"  # ⚠️ CAMBIAR

def test_rsm_connection():
    """Prueba el envío a RSM con datos de ejemplo"""
    
    print("="*60)
    print("🧪 Test de Conexión a RSM")
    print("="*60)
    print(f"\n📍 Configuración:")
    print(f"   URL: {RSM_API_URL}")
    print(f"   Token: {RSM_TOKEN}")
    print(f"   Cliente ID: {RSM_CLIENT_ID}")
    
    # Datos de prueba
    test_packages = [
        {"77": "test-package-1", "78": "1.0.0", "79": RSM_CLIENT_ID},
        {"77": "test-package-2", "78": "2.5.3", "79": RSM_CLIENT_ID},
        {"77": "test-package-3", "78": "0.9.1", "79": RSM_CLIENT_ID},
    ]
    
    print(f"\n📦 Paquetes de prueba: {len(test_packages)}")
    for pkg in test_packages:
        print(f"   • {pkg['77']} v{pkg['78']}")
    
    # Convertir a JSON
    rsm_json = json.dumps(test_packages, ensure_ascii=False)
    
    # Comando curl
    curl_cmd = [
    'curl',
    '--location', RSM_API_URL,
    '--form', 'RStrigger=newServerData',      
    '--form', f'RSdata={rsm_json}',
    '--form', f'RStoken={RSM_TOKEN}',         
    '--max-time', '30',
    '--verbose'
]
    
    print("\n🔄 Enviando datos...")
    print(f"   Comando: curl --location '{RSM_API_URL}' ...")
    
    try:
        result = subprocess.run(
            curl_cmd,
            capture_output=True,
            text=True,
            timeout=35
        )
        
        print("\n" + "="*60)
        if result.returncode == 0:
            print("✅ ÉXITO: Conexión establecida")
            print("="*60)
            if result.stdout:
                print(f"\n📥 Respuesta del servidor:")
                print(result.stdout)
        else:
            print("❌ ERROR: Fallo en la conexión")
            print("="*60)
            print(f"\n   Código de salida: {result.returncode}")
            if result.stderr:
                print(f"\n📛 Error:")
                print(result.stderr)
        
        print()
        return result.returncode == 0
        
    except subprocess.TimeoutExpired:
        print("\n❌ ERROR: Timeout (>30s)")
        return False
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        return False


if __name__ == "__main__":
    print("\n⚠️  NOTA: Este script usa datos de PRUEBA")
    print("   Los paquetes 'test-package-X' se enviarán a RSM\n")
    
    input("Presiona ENTER para continuar...")
    
    success = test_rsm_connection()
    
    if success:
        print("\n✅ La configuración es correcta")
        print("   Puedes usar estos valores en rs_agent.py")
        sys.exit(0)
    else:
        print("\n❌ Hay problemas con la configuración")
        print("   Verifica token, cliente ID y conectividad")
        sys.exit(1)