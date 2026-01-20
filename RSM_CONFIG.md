# Configuración de Envío a RSM

## Cambios Realizados

Se ha modificado `rs_agent.py` para enviar automáticamente los `system_packages` a RSM cuando se detectan cambios en el sistema.

## Configuración Requerida

Antes de desplegar en un cliente, debes modificar estas líneas en `rs_agent.py` (líneas 39-41):

```python
# Configuración RSM (modificar según cliente)
RSM_API_URL = "https://rsm1.redsauce.net/AppController/commands_RSM/api/api.php"
RSM_TOKEN = "429bd269e5c88dc73c14c69bf0e87717"  # ⚠️ CAMBIAR POR CLIENTE
RSM_CLIENT_ID = "1"  # ⚠️ CAMBIAR POR CLIENTE
```

### Parámetros:
- **RSM_TOKEN**: Token único del cliente en RSM
- **RSM_CLIENT_ID**: ID numérico del cliente en RSM

## Funcionamiento

### Cuándo se envían los datos:
- ✅ Solo cuando detecta **cambios** en el sistema
- ✅ NO se envía si no hay cambios (optimización de red)
- ✅ En primera ejecución siempre envía

### Formato de envío:

El agente transforma los paquetes del sistema al formato RSM:

```python
[
    {"77": "nombre_paquete", "78": "version", "79": "cliente_id"},
    {"77": "zlib", "78": "1.4", "79": "1"},
    {"77": "canvas", "78": "1.5", "79": "1"}
]
```

Donde:
- **77**: Nombre del paquete
- **78**: Versión del paquete  
- **79**: ID del cliente (RSM_CLIENT_ID)

### Petición curl generada:

```bash
curl --location 'https://rsm1.redsauce.net/AppController/commands_RSM/api/api.php' \
  --form 'RStrigger="newServerData"' \
  --form 'RSdata=[{...}]' \
  --form 'RStoken="TOKEN_CLIENTE"'
```

## Manejo de Errores

Si el envío a RSM **falla**:
- ❌ El script muestra **ERROR CRÍTICO**
- ❌ Sale con código de error `1`
- ❌ Muestra información de diagnóstico:
  - Token configurado
  - Cliente ID
  - URL del API
  - Sugerencia de verificar conectividad

### Ejemplo de error:

```
❌ ERROR CRÍTICO: No se pudo enviar el inventario a RSM
============================================================

⚠️  Verifica:
   • Token RSM: 429bd269e5c88dc73c14c69bf0e87717
   • Cliente ID: 1
   • URL: https://rsm1.redsauce.net/...
   • Conectividad de red
```

## Testing

### 1. Prueba local (cambiar token/cliente antes):

```bash
sudo python3 rs_agent.py
```

### 2. Verificar en salida:

```
📤 Enviando datos a RSM...
✅ Datos enviados correctamente (324 paquetes)
   Respuesta: OK
```

### 3. Si hay error de conectividad:

```
❌ ERROR: Fallo al enviar datos a RSM
   Código de salida: 7
   Error: Could not resolve host
```

## Próximos Pasos

Actualmente solo se envían `system_packages`. En futuras iteraciones se añadirán:
- `pip_packages`
- `npm_packages`
- `hardware`
- `services`
- `critical_software`

## Notas Importantes

⚠️ **Cada cliente debe tener su propia configuración**
⚠️ **El token y cliente ID son obligatorios**
⚠️ **Sin conexión a RSM el script fallará de forma controlada**
