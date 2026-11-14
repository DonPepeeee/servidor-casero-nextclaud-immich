# Copia y recuperación en Ubuntu

Este procedimiento conserva bases PostgreSQL detenidas, estado de Nextcloud, cola de Immich, configuración, secretos y referencias de imágenes por digest. No duplica la biblioteca dentro de recovery: los originales permanecen en el externo. Las miniaturas y modelos de Immich se regeneran.

Requiere Linux amd64, las mismas imágenes y un externo ext4 intacto. Una copia física de PostgreSQL no es un SQL portable entre versiones/arquitecturas. Si pierdes el externo, pierdes originales y recovery: necesitas otra copia independiente para cubrir ese fallo.

## 1. Crear un punto coherente

En Ubuntu por SSH, pausa las subidas de todos los clientes y espera a que terminen. No ejecutes otros despliegues o comandos Docker mientras se hace la copia. El paso 5 del tutorial instala el script; para actualizarlo desde la carpeta transferida:

```bash
python3 -m py_compile "$HOME/nube-instalacion/scripts/cloud-recovery"
sudo install -m 0755 "$HOME/nube-instalacion/scripts/cloud-recovery" /usr/local/sbin/cloud-recovery
sudo /usr/local/sbin/cloud-storage-check
sudo /usr/local/sbin/cloud-recovery backup
```

Espera a PUNTO COMPLETO y anota la ruta impresa. Puede tardar según el estado del SSD. La nube queda **detenida y bloqueada**, incluso tras reiniciar. Una carpeta terminada en .partial no es un punto completo. Si falla, conserva el error y los bloqueos; no continúes restaurando.

Solo para hacer una copia y seguir usando la instalación normal, sin iniciar una restauración:

```bash
sudo /usr/local/sbin/cloud-recovery backup-and-resume
```

Es una alternativa a backup, no el siguiente comando después de backup. Comprueba salud y acceso al terminar. Para reanudar después de un backup ya terminado, siempre que no hayas iniciado una restauración:

```bash
sudo /usr/local/sbin/cloud-recovery resume-source
```

El comando rechaza una restauración iniciada, puntos incompletos y otro disco. No borres el marcador manualmente para saltarlo.

El anexo de [copias y actualizaciones](copias-y-actualizaciones.md) explica `cloud-update`, sus comprobaciones y su retención, que puede borrar puntos antiguos. Consulta allí qué se ha probado y conserva una copia independiente.

## 2. Verificar el punto

Introduce la ruta completa que imprimió backup. Esta variable se usa en los siguientes bloques de esta misma sesión SSH; si vuelves a conectar, repite solo la selección, no la copia:

```bash
read -r -p 'Ruta completa del PUNTO COMPLETO: ' PUNTO
sudo /usr/local/sbin/cloud-recovery verify "$PUNTO"
```

Esperado: checksums e inventario OK. Esto comprueba el paquete, no que las aplicaciones puedan arrancar. El paquete contiene secretos; no lo subas a GitHub.

## 3. Elegir dónde restaurar

### Probar en el mismo Ubuntu

El origen debe seguir detenido y bloqueado desde backup. No reanudes clientes ni permitas nuevas escrituras entre copia y prueba:

```bash
sudo /usr/local/sbin/cloud-recovery prepare-restore "$PUNTO"
```

Extrae el estado a una carpeta SSD nueva /srv/cloud-restore.ID, conserva el estado anterior y crea redes/contenedores sin iniciarlos. Anota la ruta impresa. Los originales se reutilizan; no se duplican en recovery.

### Recuperar después de perder el SSD o el equipo

1. Instala Ubuntu, Docker y herramientas siguiendo solo los pasos 1 y 2 del tutorial. **No formatees el externo ni ejecutes la preparación de bases de una instalación nueva.**
2. Copia este repositorio a ~/nube-instalacion por SFTP como en el paso 5, sin ejecutar su bloque ARCHIVOS.
3. Conecta el externo y consulta sus identificadores:

```bash
lsblk -o NAME,MODEL,SIZE,TRAN,FSTYPE,LABEL,UUID,MOUNTPOINTS
```

Elige el UUID ext4 del externo intacto. El siguiente bloque pregunta por él y crea una entrada de montaje nueva; se detiene si ya existe /srv/storage en fstab, para no duplicarla:

```bash
sudo bash <<'MONTAR_RECUPERACION'
set -euo pipefail
printf 'UUID ext4 del externo intacto: ' > /dev/tty
read -r STORAGE_UUID < /dev/tty
test -b "/dev/disk/by-uuid/$STORAGE_UUID"
test "$(blkid -p -s TYPE -o value "/dev/disk/by-uuid/$STORAGE_UUID")" = ext4
if findmnt --fstab -rn -o TARGET | grep -Fxq /srv/storage; then
  printf 'Ya existe montaje; revisar y usar el existente sin duplicar.\n' >&2
  exit 1
fi
install -d -m 0755 /etc/homelab /srv/storage
printf 'STORAGE_UUID=%s\n' "$STORAGE_UUID" > /etc/homelab/storage.conf
cp -a /etc/fstab "/etc/fstab.backup.$(date +%Y%m%d-%H%M%S)"
printf '\nUUID=%s /srv/storage ext4 defaults,noatime,nofail,x-systemd.device-bound,x-systemd.device-timeout=10s 0 2\n' "$STORAGE_UUID" >> /etc/fstab
findmnt --verify
systemctl daemon-reload
mount /srv/storage
test "$(findmnt -rn -M /srv/storage -o UUID)" = "$STORAGE_UUID"
MONTAR_RECUPERACION
```

Instala solo herramientas y unidades, sin inicializar aplicaciones:

```bash
cd "$HOME/nube-instalacion"
sed -i 's/\r$//' scripts/cloud-* systemd/*
sudo install -m 0755 scripts/cloud-* /usr/local/sbin/
sudo install -m 0644 systemd/cloud@.service systemd/cloud.target /etc/systemd/system/
sudo systemctl daemon-reload
sudo /usr/local/sbin/cloud-storage-check
sudo ls -1 /srv/storage/recovery/state-points
read -r -p 'Ruta completa del punto que quieres recuperar: ' PUNTO
sudo /usr/local/sbin/cloud-recovery verify "$PUNTO"
sudo /usr/local/sbin/cloud-recovery prepare-restore "$PUNTO" --new-host
```

--new-host solo admite un equipo sin bases ni .env previos; no es una forma de sustituir una nube existente. Necesitas Internet para descargar las imágenes exactas. No ejecutes simultáneamente el equipo anterior con el mismo externo.

## 4. Iniciar y validar las aplicaciones recuperadas

Introduce la carpeta /srv/cloud-restore.ID impresa por prepare-restore:

```bash
read -r -p 'Carpeta SSD de restauracion (/srv/cloud-restore.ID): ' RESTAURACION
sudo python3 "$HOME/nube-instalacion/tests/recovery_acceptance.py" "$RESTAURACION"
```

El test registra hashes de una muestra de originales, inicia solo los proyectos recuperados, espera salud y comprueba montajes/cuentas/recuentos. No lo repitas si ya hay un resultado parcial: conserva su salida y revisa el fallo. Después:

```bash
sudo docker ps
sudo systemctl status cloud-restore@nextcloud.service cloud-restore@immich.service --no-pager
```

Debes ver siete healthy y cron Up. Si has cambiado de equipo, completa primero el paso 5 para adaptar sus URLs. Comprueba además desde navegador: cuentas, permisos, comparticiones, álbumes y descarga de un original de cada aplicación. Si faltan miniaturas en Immich, usa Administración → Colas de trabajo → Generar Miniaturas → Todos. No vuelvas a subir originales para corregir miniaturas.

**Desde que arranca la restauración puede haber escrituras en los originales.** Conserva bloqueada la instalación anterior. Volver a sus bases antiguas puede perder referencias y cambios aunque los archivos sigan en disco.

## 5. Acceso en el equipo recuperado

En el mismo equipo se conservan los puertos y la identidad Tailscale. En otro equipo, instala y autoriza Tailscale con el paso 6 del tutorial: tendrá su propio dominio. Ajusta la URL y los proxies de la configuración recuperada antes de reanudar clientes.

Para un equipo nuevo, pausa ambos servicios y actualiza únicamente el JSON de configuración resuelto, sin mostrar secretos:

```bash
sudo systemctl stop cloud-restore@nextcloud.service cloud-restore@immich.service
sudo python3 - "$RESTAURACION" <<'URL_RECUPERADA'
import json, pathlib, subprocess, sys
p = pathlib.Path(sys.argv[1]).resolve(strict=True)
assert p.parent == pathlib.Path('/srv') and p.name.startswith('cloud-restore.')
domain = json.loads(subprocess.check_output(['tailscale', 'status', '--json']))['Self']['DNSName'].rstrip('.')
assert domain
file = p / 'nextcloud.compose.json'
cfg = json.loads(file.read_text())
for service in ('app', 'cron'):
    cfg['services'][service]['environment']['OVERWRITECLIURL'] = 'https://' + domain
    cfg['services'][service]['environment']['OVERWRITEPROTOCOL'] = 'https'
file.write_text(json.dumps(cfg, indent=2) + '\n')
print('Nextcloud: https://' + domain + '/\nImmich: https://' + domain + ':8443/')
URL_RECUPERADA
sudo systemctl start cloud-restore@nextcloud.service cloud-restore@immich.service
DOMINIO=$(tailscale status --json | python3 -c 'import json,sys; print(json.load(sys.stdin)["Self"]["DNSName"].rstrip("."))')
sudo docker compose --project-name cloud-restore-nextcloud --file "$RESTAURACION/nextcloud.compose.json" exec -T --user www-data app php occ config:system:set trusted_domains 10 --value="$DOMINIO"
```

Espera salud, usa las URLs impresas y cambia los clientes al dominio nuevo. La identidad de red no se traslada automáticamente con las bases.

## 6. Mantener la instalación recuperada y su arranque automático

Tras validar las aplicaciones, puedes conservar sus rutas SSD nuevas como instalación activa. El origen anterior continúa bloqueado; no se mueve ni se borra. Este bloque configura conexión/arranque automático **solo de la restauración**:

```bash
sudo bash <<'ACTIVAR_RECUPERADA'
set -euo pipefail
. /etc/homelab/storage.conf
/usr/local/sbin/cloud-storage-check
test -e /etc/homelab/recovery-maintenance
test -e /etc/systemd/system/cloud-restore@.service
test ! -e /etc/homelab/recovery-freeze-restored
systemctl disable --now cloud@nextcloud.service cloud@immich.service
cat > /etc/systemd/system/cloud-restored.target <<'TARGET'
[Unit]
Description=Nube recuperada
RequiresMountsFor=/srv/storage
BindsTo=srv-storage.mount
After=srv-storage.mount
TARGET
install -d /etc/systemd/system/cloud-restore@.service.d
cat > /etc/systemd/system/cloud-restore@.service.d/60-supervision.conf <<'SUPERVISION'
[Unit]
PartOf=cloud-restored.target
[Service]
ExecStartPre=/usr/local/sbin/cloud-storage-check
Restart=on-failure
RestartSec=15
SUPERVISION
printf 'ACTION=="add|change", SUBSYSTEM=="block", ENV{DEVTYPE}=="partition", ENV{ID_FS_UUID}=="%s", TAG+="systemd", ENV{SYSTEMD_WANTS}+="cloud-restored.target"\n' "$STORAGE_UUID" > /etc/udev/rules.d/99-cloud.rules
udevadm verify /etc/udev/rules.d/99-cloud.rules
systemctl daemon-reload
systemctl add-wants cloud-restored.target cloud-restore@nextcloud.service cloud-restore@immich.service
udevadm control --reload-rules
systemctl start cloud-restored.target
ACTIVAR_RECUPERADA
```

Reinicia con el externo conectado y comprueba que arrancan los ocho contenedores, que los montajes SSD apuntan a la carpeta recuperada y que funcionan las URLs/descargas. Después prueba apagado completo, arranque sin disco y conexión posterior. Usa el paso 12 del tutorial para retirarlo.

## 7. Guardar el estado recuperado antes de trasladarlo

Para trasladar esta instalación a Windows u otro Ubuntu no uses una copia antigua del origen. Pausa clientes y guarda las bases que están activas ahora:

```bash
sudo /usr/local/sbin/cloud-recovery backup-restored "$RESTAURACION"
```

Espera PUNTO COMPLETO. Queda detenido y congelado para el traslado. Verifica el punto, apaga y espera antes de retirar. Esta operación no reanuda la restauración; su finalidad es sellar el estado que se va a mover. El siguiente destino debe restaurar ese punto final.

## Coherencia, espacio y copias periódicas

Una sola copia inicial no basta para mantener recuperable el estado de una nube en uso. Aunque los originales se guarden aparte, las nuevas subidas, cuentas, álbumes, comparticiones y cambios actualizan las bases del SSD. Renovar el punto no es necesario solo cuando cambia el software.

Crea una copia antes de actualizar aplicaciones o bases y conserva ese punto. Después de comprobar que la actualización funciona, crea otro con las versiones nuevas. Durante el uso normal, elige una frecuencia según los cambios que aceptas perder: una copia diaria limita aproximadamente la antigüedad del estado guardado si la tarea funciona, pero no garantiza coherencia con originales que se modifiquen después.

El apagado del tutorial no ejecuta recovery. Hacer una copia antes de apagar ayuda en un traslado previsto, pero no protege los cambios acumulados si el equipo funciona durante semanas o falla antes del siguiente apagado. Estos comandos no instalan copias periódicas ni un gancho de apagado.

`cloud-recovery backup` y `backup-and-resume` no eliminan puntos automáticamente. El uso de `cloud-update` puede aplicar la retención descrita en su anexo. Revisa df y du antes de copiar y conserva varios puntos completos. backup-and-resume sirve para una copia puntual de la instalación normal; no lo programes sobre cloud-restore ni sobre la variante solo SSD. Los puntos completos guardan solo estado SSD, pero aún requieren espacio y E/S.

Una base guardada ayer y unos originales que han seguido cambiando no garantizan el estado idéntico de hoy. Para volver a fechas anteriores con garantía necesitas también originales versionados/snapshots coherentes. Este formato no contiene esos snapshots. Nextcloud puede escanear archivos, pero eso no reconstruye todas sus comparticiones; Immich no reconstruye su base escaneando su biblioteca interna.

Referencias: [Nextcloud](https://docs.nextcloud.com/server/stable/admin_manual/maintenance/backup.html), [Immich](https://docs.immich.app/administration/backup-and-restore/). [Volver al índice](README.md).
