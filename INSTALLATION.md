# Guía de Instalación - Módulo Recurrente para Odoo 18

## Resumen del Módulo

El módulo `payment_recurrente` es una integración completa de la pasarela de pagos Recurrente para Odoo 18, desarrollado específicamente para el mercado guatemalteco. Incluye todas las funcionalidades necesarias para procesar pagos seguros, manejar suscripciones, procesar reembolsos y gestionar facturación electrónica.

## Estructura del Módulo

```
payment_recurrente/
├── __manifest__.py                 # Configuración del módulo
├── __init__.py                     # Inicialización del módulo
├── README.md                       # Documentación completa
├── INSTALLATION.md                 # Esta guía de instalación
├── validate_module.py              # Script de validación
├── .gitignore                      # Archivos a ignorar en Git
├── models/                         # Modelos de datos
│   ├── __init__.py
│   ├── payment_acquirer.py         # Configuración del proveedor
│   └── payment_transaction.py      # Gestión de transacciones
├── controllers/                    # Controladores web
│   ├── __init__.py
│   └── main.py                     # Endpoints y webhooks
├── views/                          # Interfaces de usuario
│   ├── payment_recurrente_views.xml    # Vistas de administración
│   └── payment_recurrente_templates.xml # Templates de pago
├── security/                       # Configuración de seguridad
│   ├── ir.model.access.csv         # Permisos de acceso
│   └── payment_recurrente_security.xml # Reglas de seguridad
├── data/                          # Datos iniciales
│   └── payment_acquirer_data.xml   # Configuración del proveedor
├── static/                        # Archivos estáticos
│   ├── description/
│   │   ├── index.html             # Descripción del módulo
│   │   └── icon.png               # Icono del módulo
│   └── src/
│       ├── js/
│       │   └── payment_form.js    # JavaScript del frontend
│       └── css/
│           └── payment_form.css   # Estilos CSS
└── tests/                         # Pruebas unitarias
    ├── __init__.py
    └── test_recurrente.py         # Tests del módulo
```

## Requisitos Previos

### Sistema
- **Odoo 18.0** o superior
- **Python 3.8+**
- **PostgreSQL 12+**
- Acceso a internet para comunicación con API de Recurrente

### Cuenta Recurrente
- Cuenta activa en [Recurrente](https://www.recurrente.com)
- Claves API obtenidas del dashboard:
  - Clave Pública (pk_live_... o pk_test_...)
  - Clave Secreta (sk_live_... o sk_test_...)
  - Webhook Secret (whsec_...)

### Dependencias de Odoo
El módulo requiere los siguientes módulos de Odoo:
- `payment` (módulo base de pagos)
- `website_sale` (ecommerce)
- `sale_subscription` (suscripciones)

## Instalación Paso a Paso

### 1. Preparación del Entorno

```bash
# Detener Odoo si está ejecutándose
sudo systemctl stop odoo

# Navegar al directorio de addons
cd /opt/odoo/addons/
# O tu directorio personalizado de addons
```

### 2. Instalación del Módulo

```bash
# Copiar el módulo al directorio de addons
sudo cp -r ~/payment_recurrente /opt/odoo/addons/

# Cambiar permisos
sudo chown -R odoo:odoo /opt/odoo/addons/payment_recurrente
sudo chmod -R 755 /opt/odoo/addons/payment_recurrente
```

### 3. Actualización de la Lista de Addons

```bash
# Reiniciar Odoo con actualización de lista de addons
sudo systemctl start odoo

# O si usas línea de comandos:
./odoo-bin -d tu_base_de_datos --addons-path=/opt/odoo/addons -u base --stop-after-init
```

### 4. Instalación desde la Interfaz Web

1. **Acceder a Odoo**
   - Ir a tu instancia de Odoo
   - Iniciar sesión como administrador

2. **Activar Modo Desarrollador**
   - Ir a Configuración → Activar modo desarrollador

3. **Instalar el Módulo**
   - Ir a Apps
   - Buscar "Recurrente"
   - Hacer clic en "Instalar"

### 5. Configuración Inicial

#### 5.1 Configurar el Proveedor de Pagos

1. **Navegar a Configuración**
   ```
   Contabilidad → Configuración → Proveedores de Pago
   ```

2. **Buscar Recurrente**
   - Encontrar "Recurrente" en la lista
   - Hacer clic en "Configurar"

3. **Completar Configuración**
   ```
   Nombre: Recurrente
   Estado: Modo de Prueba (para desarrollo)
   Clave Pública: pk_test_tu_clave_publica
   Clave Secreta: sk_test_tu_clave_secreta
   Webhook Secret: whsec_tu_webhook_secret
   ```

#### 5.2 Configurar Webhooks en Recurrente

1. **Acceder al Dashboard de Recurrente**
   - Ir a [dashboard.recurrente.com](https://dashboard.recurrente.com)
   - Iniciar sesión con tu cuenta

2. **Configurar Webhook**
   ```
   Sección: Developers and API → Webhooks
   URL: https://tu-dominio.com/payment/recurrente/webhook
   Eventos a seleccionar:
   ✓ payment_intent.succeeded
   ✓ payment_intent.payment_failed
   ✓ payment_intent.canceled
   ✓ checkout.session.completed
   ✓ checkout.session.expired
   ✓ refund.succeeded
   ✓ refund.failed
   ```

3. **Obtener Webhook Secret**
   - Copiar el webhook secret generado
   - Pegarlo en la configuración de Odoo

### 6. Configuración de Monedas

1. **Activar Monedas Soportadas**
   ```
   Contabilidad → Configuración → Monedas
   ```

2. **Activar las siguientes monedas:**
   - GTQ (Quetzal Guatemalteco)
   - USD (Dólar Estadounidense)
   - USDT (Tether USD) - si se requiere
   - USDC (USD Coin) - si se requiere

### 7. Configuración de Ecommerce (Opcional)

Si planeas usar el módulo con el ecommerce de Odoo:

1. **Instalar Website Sale**
   ```
   Apps → Buscar "Website Sale" → Instalar
   ```

2. **Configurar Métodos de Pago**
   ```
   Website → Configuración → Métodos de Pago
   Activar: Recurrente
   ```

### 8. Configuración de Suscripciones (Opcional)

Para pagos recurrentes:

1. **Instalar Sale Subscription**
   ```
   Apps → Buscar "Subscriptions" → Instalar
   ```

2. **Configurar Productos de Suscripción**
   ```
   Ventas → Productos → Crear producto
   Tipo: Servicio
   Política de Facturación: Recurrente
   ```

## Verificación de la Instalación

### 1. Ejecutar Script de Validación

```bash
cd /opt/odoo/addons/payment_recurrente
python3 validate_module.py
```

### 2. Verificar en la Interfaz

1. **Verificar Proveedor de Pagos**
   ```
   Contabilidad → Configuración → Proveedores de Pago
   Debe aparecer "Recurrente" en la lista
   ```

2. **Verificar en Checkout**
   ```
   Website → Shop → Agregar producto al carrito → Checkout
   Debe aparecer "Recurrente" como opción de pago
   ```

### 3. Prueba de Pago de Prueba

1. **Usar Tarjetas de Prueba**
   ```
   Número: 4242424242424242
   Fecha: Cualquier fecha futura
   CVC: Cualquier 3 dígitos
   ```

2. **Verificar Flujo Completo**
   - Crear orden de prueba
   - Seleccionar Recurrente como método de pago
   - Completar pago en página de Recurrente
   - Verificar confirmación en Odoo

## Configuración de Producción

### 1. Cambiar a Claves de Producción

```
Clave Pública: pk_live_tu_clave_publica_live
Clave Secreta: sk_live_tu_clave_secreta_live
Estado: Habilitado
```

### 2. Configurar HTTPS

Asegúrate de que tu sitio Odoo esté configurado con HTTPS para producción.

### 3. Configurar Webhook de Producción

Actualizar la URL del webhook en el dashboard de Recurrente con la URL de producción.

## Solución de Problemas Comunes

### Error: "Módulo no encontrado"
```bash
# Verificar que el módulo esté en el addons-path
./odoo-bin --addons-path=/ruta/a/addons --list-db
```

### Error: "Dependencias no satisfechas"
```bash
# Instalar dependencias faltantes
Apps → Buscar "payment" → Instalar
Apps → Buscar "website_sale" → Instalar
Apps → Buscar "sale_subscription" → Instalar
```

### Error: "Webhook no funciona"
1. Verificar que la URL sea accesible desde internet
2. Verificar que el webhook secret sea correcto
3. Revisar logs de Odoo para errores de verificación

### Error: "Pagos no se confirman"
1. Verificar configuración de webhooks en Recurrente
2. Verificar que todos los eventos estén seleccionados
3. Revisar logs de transacciones en Odoo

## Logs y Debugging

### Ubicación de Logs
```bash
# Logs de Odoo
tail -f /var/log/odoo/odoo.log

# Filtrar logs de Recurrente
tail -f /var/log/odoo/odoo.log | grep -i recurrente
```

### Activar Modo Debug
```python
# En el archivo de configuración de Odoo
log_level = debug
```

## Soporte y Documentación

### Documentación Oficial
- [Documentación de Recurrente](https://ayuda.recurrente.com)
- [API de Recurrente](https://documenter.getpostman.com/view/10340859/2sA2rFQf5R)
- [Documentación de Odoo Payment](https://www.odoo.com/documentation/18.0/developer/reference/addons/payment.html)

### Contacto de Soporte
- Soporte Recurrente: [ayuda.recurrente.com](https://ayuda.recurrente.com)
- Documentación del módulo: Ver README.md

## Mantenimiento

### Actualizaciones del Módulo
```bash
# Actualizar módulo
./odoo-bin -d tu_base_de_datos -u payment_recurrente
```

### Backup de Configuración
Asegúrate de hacer backup de:
- Configuración del proveedor de pagos
- Claves API
- Configuración de webhooks

### Monitoreo
- Revisar logs regularmente
- Monitorear transacciones fallidas
- Verificar estado de webhooks

---

¡El módulo Recurrente para Odoo 18 está ahora completamente instalado y configurado! 🎉
