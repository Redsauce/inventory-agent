# 🤖 Redsauce Inventory Agent

Agente de inventario automático para sistemas Linux. Recopila hardware, software y servicios cada día.

## 🚀 Instalación (un comando)

```bash
curl -fsSL https://raw.githubusercontent.com/redsauce/inventory-agent/main/install.sh | sudo bash
```

## 📋 ¿Qué hace?

- ✅ Detecta hardware (CPU, RAM, discos, red)
- ✅ Lista paquetes instalados (dpkg/rpm/pip/npm)
- ✅ Identifica software crítico (Apache, MySQL, PHP, Docker...)
- ✅ Monitoriza servicios activos
- ✅ **Solo actualiza si detecta cambios**
- ✅ Ejecución automática diaria (3:00 AM)

## 📂 Ubicaciones

```
/opt/rs-agent/rs_agent.py          # El agente
/var/lib/rs-agent/inventory.json   # Inventario actual
/var/log/rs-agent.log              # Logs
```

## 💻 Uso

```bash
# Ejecutar manualmente
sudo python3 /opt/rs-agent/rs_agent.py

# Ver inventario
cat /var/lib/rs-agent/inventory.json | python3 -m json.tool

# Ver logs
tail -f /var/log/rs-agent.log

# Desinstalar
sudo bash /opt/rs-agent/uninstall.sh
```

## 🔧 Requisitos

- Linux (Ubuntu, Debian, RHEL, CentOS, Fedora)
- Python 3.6+
- Permisos root

## 🛡️ Seguridad

- Solo lectura (no modifica el sistema)
- No recopila contraseñas ni claves
- No se conecta a internet (por ahora)
- Open source y auditable

---

**Redsauce** © 2026 | [Documentación completa](https://www.redsauce.net)
