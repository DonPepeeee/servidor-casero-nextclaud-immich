# Copias con retención y actualización supervisada

[`cloud-update`](../scripts/cloud-update) reúne dos operaciones distintas: crear una copia fría del estado y actualizar manualmente parches de Nextcloud o Immich tras hacer una copia. En ambos casos intenta aplicar una retención de puntos antiguos. Está pensado para la instalación normal `cloud` del tutorial en Ubuntu con disco externo; no para `cloud-restore` ni la variante solo SSD.

## Qué se ha comprobado

- En el servidor utilizado para desarrollar el proyecto se realizaron copias frías reales con `cloud-recovery`, incluida su verificación y la reanudación de los servicios, durante pruebas de corriente y cortes. También se confirmó el arranque de ambos servicios después. Esto no equivale a una restauración completa demostrada para todas las instalaciones.
- La lógica de retención de `cloud-update` está presente en el script instalado en ese servidor y cuenta con pruebas automatizadas aisladas. En la revisión más reciente no se ejecutó `cloud-update` ni se probó en el servidor el borrado de puntos antiguos; tampoco se comprobó ahí una actualización de aplicación de extremo a extremo. No asumir que esos pasos están validados en producción por las pruebas de la copia fría.
- Las pruebas automatizadas están en [`tests/update.py`](../tests/update.py); emplean simulaciones y no sustituyen una prueba de restauración con tus datos.

## Preparación

Revisa el script y conserva una copia independiente antes de usarlo: **la retención puede borrar puntos de recuperación** y el estado guardado en el mismo disco que los originales no protege frente a la pérdida de ese disco. Comprueba espacio libre y documenta el estado de tu instalación. Haz primero ensayos con datos prescindibles; una copia verificada no garantiza por sí sola que puedas restaurarla.

Una vez transferido el repositorio a `~/nube-instalacion`, comprueba e instala el script revisado:

```bash
python3 -m py_compile "$HOME/nube-instalacion/scripts/cloud-update"
sudo install -m 0755 "$HOME/nube-instalacion/scripts/cloud-update" /usr/local/sbin/cloud-update
```

## Crear una copia

```bash
sudo /usr/local/sbin/cloud-update backup
```

Comprueba la salud de Nextcloud e Immich antes y después de invocar `cloud-recovery backup-and-resume`, identifica el punto nuevo y verifica su contenido. Los servicios se detienen durante la copia; el punto guarda estado de SSD, no duplica los originales del disco externo. Si la copia y las comprobaciones terminan correctamente, intenta aplicar la retención descrita más abajo. Comprueba también el acceso, los archivos y las subidas desde los clientes.

Para realizar la copia y restauración sin este wrapper, consulta el [anexo de recuperación](recuperacion.md). Ejecutar `cloud-recovery` directamente no activa la retención de `cloud-update`.

## Retención

Tras una copia o actualización satisfactoria, `cloud-update` intenta conservar los cuatro puntos completos reconocidos más recientes. Antes de borrar verifica los puntos y comprueba que el inventario no haya cambiado y que no existan ciertos marcadores de mantenimiento, restauraciones preparadas o puntos parciales. Si una comprobación falla, emite un aviso y puede omitir la limpieza; pueden permanecer más de cuatro puntos. Las copias creadas mediante `cloud-recovery` u otros procesos no activan por sí solas esta limpieza, aunque un uso posterior de `cloud-update` puede tenerlas en cuenta.

No se configura aquí ninguna ejecución periódica. La retención no sustituye copias independientes ni versiones de los originales.

## Actualización supervisada

Antes de elegir una versión, consulta las instrucciones oficiales de la aplicación y comprueba las compatibilidades. El script solo acepta una versión de parche superior dentro de la misma rama, con tres números; no automatiza saltos de versión menor o mayor ni actualiza PostgreSQL, Redis o Valkey.

```bash
sudo /usr/local/sbin/cloud-update immich VERSION
sudo /usr/local/sbin/cloud-update nextcloud VERSION
```

Sustituye `VERSION` por una versión exacta existente y revisada; usa solo el comando de la aplicación que quieras actualizar. El script crea primero una copia, modifica las imágenes de Compose, descarga y reinicia el servicio, y comprueba salud e imágenes. Si fallan la validación o la descarga antes del reinicio, restaura el Compose anterior. **Después de iniciar el reinicio no hace rollback automático:** las migraciones pueden haber cambiado datos. Si falla, conserva el punto previo y revisa el estado antes de intervenir.
