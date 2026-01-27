# Redsauce Inventory Agent

Agente de inventario automático para sistemas Linux con **auto-actualización** desde GitHub Releases.

## Instalación

```bash
curl -fsSL https://raw.githubusercontent.com/redsauce/inventory-agent/main/install.sh | sudo bash
```

## Funcionalidades

-  Recopila hardware (CPU, RAM, discos, red) y software instalado (dpkg/rpm/pip/npm)
-  Detecta software crítico (Apache, MySQL, PHP, Docker...) y servicios activos
-  **Solo actualiza si detecta cambios** en el sistema
-  **Auto-actualización automática** desde GitHub Releases
-  Ejecución diaria programada (3:00 AM)

##  Uso básico

```bash
# Ejecución manual
sudo python3 /opt/rs-agent/rs_agent.py

# Ver inventario
cat /var/lib/rs-agent/inventory.json | python3 -m json.tool

# Desinstalar
sudo bash /opt/rs-agent/uninstall.sh
```

**Ubicaciones:**
- Agente: `/opt/rs-agent/rs_agent.py`
- Inventario: `/var/lib/rs-agent/inventory.json`
- Logs: `/var/log/rs-agent.log`

---

## Sistema de Auto-actualización

El agente comprueba GitHub Releases cada vez que se ejecuta. Si detecta una versión nueva, se actualiza automáticamente.

### Publicar nueva versión

1. **Editar versión en el código:**
```bash
# Cambiar línea 23 en rs_agent.py: AGENT_VERSION = "0.2.0"
git add rs_agent.py
git commit -m "Update to v0.2.0: [descripción]"
git push
```

2. **Crear Release en GitHub:**
   - https://github.com/redsauce/inventory-agent/releases/new
   - Tag: `0.2.0` (sin `v`)
   - Title: `v0.2.0`
   - Publish release

3. **Los clientes se actualizan automáticamente** en las próximas 24h.

### Versionado Semántico

```
MAJOR.MINOR.PATCH
  0  .  1  .  0
  │     │     └─ Bug fixes
  │     └─────── Nuevas funcionalidades
  └───────────── Cambios incompatibles
```

### Ver versión instalada

```bash
grep "AGENT_VERSION" /opt/rs-agent/rs_agent.py
```

---

## Requisitos

- Linux (Ubuntu, Debian, RHEL, CentOS, Fedora)
- Python 3.6+ con `requests`
- Permisos root

## Seguridad

- Solo lectura (no modifica el sistema)
- No recopila contraseñas ni claves
- Open source y auditable

---

**Redsauce** © 2026 | [redsauce.net](https://redsauce.net)
