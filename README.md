# Recurrente Payment Provider for Odoo 18

Este módulo integra la pasarela de pagos **Recurrente** con Odoo 18, proporcionando una solución completa para procesar pagos en Guatemala y la región.

## Características

### 🔒 Pagos Seguros
- Páginas de pago hospedadas con cumplimiento PCI
- Autenticación 3D Secure
- Encriptación de nivel bancario

### 💳 Múltiples Métodos de Pago
- Tarjetas Visa y Mastercard
- Soporte para múltiples monedas: GTQ, USD, USDT, USDC
- Pagos con dólares digitales

### 🔄 Pagos Recurrentes
- Integración completa con el módulo de suscripciones de Odoo
- Pagos automáticos programados
- Gestión de planes de suscripción

### 📊 Webhooks en Tiempo Real
- Actualizaciones automáticas del estado de transacciones
- Verificación segura de webhooks con HMAC-SHA256
- Manejo de eventos de pago, cancelación y reembolso

### 💰 Gestión de Reembolsos
- Reembolsos completos y parciales
- Procesamiento directo desde Odoo
- Seguimiento automático del estado

### 📄 Facturación Electrónica
- Integración con facturación electrónica guatemalteca
- Vinculación automática de facturas a transacciones
- Cumplimiento con regulaciones locales

## Instalación

### Requisitos Previos
- Odoo 18.0+
- Cuenta activa en [Recurrente](https://www.recurrente.com)
- Claves API de Recurrente (pública, secreta y webhook secret)

### Pasos de Instalación

1. **Instalar el módulo**
   ```bash
   # Copiar el módulo al directorio de addons
   cp -r payment_recurrente /path/to/odoo/addons/
   
   # Reiniciar Odoo con el nuevo addon path
   ./odoo-bin -u payment_recurrente -d your_database
   ```

2. **Activar el módulo**
   - Ve a Apps → Buscar "Recurrente"
   - Instala el módulo "Recurrente Payment Acquirer"

3. **Configurar el proveedor de pagos**
   - Ve a Contabilidad → Configuración → Proveedores de Pago
   - Busca "Recurrente" y haz clic en "Configurar"
   - Completa los campos requeridos:
     - **Clave Pública**: Tu clave pública de Recurrente (pk_live_... o pk_test_...)
     - **Clave Secreta**: Tu clave secreta de Recurrente (sk_live_... o sk_test_...)
     - **Webhook Secret**: El secreto para verificar webhooks

4. **Configurar webhooks en Recurrente**
   - Inicia sesión en tu dashboard de Recurrente
   - Ve a "Developers and API" → "Webhooks"
   - Agrega un nuevo webhook con la URL: `https://tu-dominio.com/payment/recurrente/webhook`
   - Selecciona los siguientes eventos:
     - `payment_intent.succeeded`
     - `payment_intent.payment_failed`
     - `payment_intent.canceled`
     - `checkout.session.completed`
     - `checkout.session.expired`
     - `refund.succeeded`
     - `refund.failed`

5. **Activar el proveedor**
   - Cambia el estado del proveedor a "Habilitado" para producción
   - O "Modo de Prueba" para desarrollo

## Configuración

### Variables de Entorno (Recomendado)
Para mayor seguridad, puedes configurar las claves como variables de entorno:

```bash
export RECURRENTE_PUBLIC_KEY="pk_live_your_public_key"
export RECURRENTE_SECRET_KEY="sk_live_your_secret_key"
export RECURRENTE_WEBHOOK_SECRET="whsec_your_webhook_secret"
```

### Configuración de Monedas
El módulo soporta las siguientes monedas:
- **GTQ** (Quetzal Guatemalteco)
- **USD** (Dólar Estadounidense)
- **USDT** (Tether USD)
- **USDC** (USD Coin)

### Configuración de Suscripciones
Para habilitar pagos recurrentes:
1. Instala el módulo `sale_subscription`
2. Ve a la configuración de Recurrente
3. Activa "Enable Subscriptions"

## Uso

### Pagos Únicos
1. El cliente selecciona productos y procede al checkout
2. Selecciona "Recurrente" como método de pago
3. Es redirigido a la página segura de Recurrente
4. Completa el pago con su tarjeta
5. Es redirigido de vuelta a Odoo con confirmación

### Pagos Recurrentes
1. Crea un producto de suscripción en Odoo
2. El cliente se suscribe al servicio
3. Los pagos se procesan automáticamente según el plan
4. Las facturas se generan automáticamente

### Reembolsos
1. Ve a la transacción en Contabilidad → Pagos
2. Haz clic en "Refund" en la transacción completada
3. Especifica el monto (completo o parcial)
4. El reembolso se procesa automáticamente

## API y Webhooks

### Endpoints del Módulo
- `GET /payment/recurrente/return` - Manejo de retorno de pagos
- `POST /payment/recurrente/webhook` - Recepción de webhooks
- `GET /payment/recurrente/test` - Endpoint de prueba (solo administradores)

### Eventos de Webhook Soportados
- `payment_intent.succeeded` - Pago exitoso
- `payment_intent.payment_failed` - Pago fallido
- `payment_intent.canceled` - Pago cancelado
- `checkout.session.completed` - Sesión de checkout completada
- `checkout.session.expired` - Sesión de checkout expirada
- `refund.succeeded` - Reembolso exitoso
- `refund.failed` - Reembolso fallido

## Desarrollo y Pruebas

### Modo de Prueba
Para desarrollo, usa las claves de prueba de Recurrente:
- Clave pública: `pk_test_...`
- Clave secreta: `sk_test_...`
- Configura el proveedor en "Modo de Prueba"

### Tarjetas de Prueba
Usa las tarjetas de prueba proporcionadas por Recurrente para simular diferentes escenarios.

### Ejecutar Pruebas
```bash
# Ejecutar todas las pruebas del módulo
./odoo-bin -d test_db --test-tags payment_recurrente

# Ejecutar pruebas específicas
./odoo-bin -d test_db --test-tags payment_recurrente.test_recurrente
```

## Seguridad

### Mejores Prácticas
- **Nunca** hardcodees las claves API en el código
- Usa HTTPS en producción
- Configura correctamente los webhooks con verificación de firma
- Mantén las claves seguras y rótalas periódicamente
- Usa el modo de prueba durante el desarrollo

### Verificación de Webhooks
El módulo verifica automáticamente la autenticidad de los webhooks usando:
- Firma HMAC-SHA256
- Timestamp para prevenir ataques de replay
- Comparación de tiempo constante para prevenir ataques de timing

## Solución de Problemas

### Problemas Comunes

1. **Webhook no funciona**
   - Verifica que la URL del webhook esté correctamente configurada
   - Asegúrate de que el webhook secret sea correcto
   - Revisa los logs de Odoo para errores de verificación

2. **Pagos no se confirman**
   - Verifica la configuración de webhooks en Recurrente
   - Revisa que los eventos estén seleccionados correctamente
   - Verifica la conectividad de red

3. **Error de autenticación API**
   - Verifica que las claves API sean correctas
   - Asegúrate de usar las claves del entorno correcto (test/live)
   - Verifica que las claves no hayan expirado

### Logs y Debugging
Los logs del módulo se encuentran en:
- Nivel INFO: Operaciones normales
- Nivel ERROR: Errores de API y webhooks
- Nivel DEBUG: Información detallada de debugging

## Soporte

### Documentación
- [Documentación oficial de Recurrente](https://ayuda.recurrente.com)
- [API de Recurrente](https://documenter.getpostman.com/view/10340859/2sA2rFQf5R)
- [Documentación de Odoo Payment](https://www.odoo.com/documentation/18.0/developer/reference/addons/payment.html)

### Contacto
Para soporte técnico específico del módulo, contacta al equipo de desarrollo o consulta la documentación oficial de Recurrente.

## Licencia

Este módulo está licenciado bajo LGPL-3. Ver el archivo LICENSE para más detalles.

## Contribuciones

Las contribuciones son bienvenidas. Por favor:
1. Fork el repositorio
2. Crea una rama para tu feature
3. Commit tus cambios
4. Push a la rama
5. Crea un Pull Request

## Changelog

### v18.0.1.0.0
- **MIGRACIÓN A ODOO 18**: Actualización completa para compatibilidad con Odoo 18
- **Cambios de API**: Migración de `payment.acquirer` a `payment.provider`
- **Campos actualizados**: Cambio de `acquirer_id` a `provider_id` y `acquirer_reference` a `provider_reference`
- **Modelos renombrados**: Actualización de todos los modelos, vistas y referencias
- Soporte completo para pagos únicos y recurrentes
- Integración con webhooks
- Soporte para reembolsos
- Integración con facturación electrónica guatemalteca
- Soporte para múltiples monedas
- Pruebas unitarias completas

## Migración desde versiones anteriores

### Cambios importantes en Odoo 18

En Odoo 18, el modelo principal para proveedores de pago cambió de `payment.acquirer` a `payment.provider`. Este módulo ha sido completamente actualizado para reflejar estos cambios:

#### Cambios en modelos:
- `payment.acquirer` → `payment.provider`
- `payment.acquirer.recurrente` → `payment.provider.recurrente`

#### Cambios en campos:
- `acquirer_id` → `provider_id`
- `acquirer_reference` → `provider_reference`

#### Cambios en métodos:
- `_get_compatible_acquirers()` → `_get_compatible_providers()`

### Migración automática
El módulo incluye scripts de migración que se ejecutan automáticamente durante la actualización para:
- Actualizar referencias de modelos
- Migrar datos existentes
- Mantener la compatibilidad con transacciones anteriores

### Verificación post-migración
Después de la migración, verifica:
1. Configuración del proveedor de pago en Configuración > Contabilidad > Proveedores de Pago
2. Transacciones existentes en Contabilidad > Pagos > Transacciones
3. Configuración de webhooks en el dashboard de Recurrente
