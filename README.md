# Tu nube casera: archivos con Nextcloud y fotos con Immich

Ubuntu Server + Docker Compose + disco externo + acceso privado desde ordenador y móvil.

Guía paso a paso para una instalación nueva con Ubuntu Server 26.04 LTS, Nextcloud 35.0.2 e Immich 3.3.3. Los archivos usan versiones concretas: no las sustituyas por `latest`. Antes de actualizar una instalación existente, revisa las instrucciones de actualización de cada proyecto y crea una copia coherente.

## Qué vas a conseguir

- Nextcloud para sincronizar documentos y carpetas del ordenador.
- Immich para subir y consultar fotos y vídeos desde Android/iPhone.
- Acceso HTTPS privado mediante Tailscale, sin abrir puertos del router ni comprar un dominio.
- Arranque de ambos servicios cuando esté conectado el externo, también después de encender el equipo.
- SSD para bases y aplicaciones; externo para los archivos originales.

El paso 12 explica cómo extraer y reconectar el disco de forma segura. El [anexo de recuperación](anexos/recuperacion.md) permite guardar el estado de las aplicaciones y reconstruirlas si conservas el externo.

Los [anexos](anexos/README.md) incluyen recuperación Ubuntu/Windows, comparación USB y avisos de ocupación. Comienza con archivos de prueba y conserva otra copia independiente de tus originales: sincronización y recovery en el mismo disco no protegen frente a la pérdida de ese disco.

Para usar el equipo sin Ethernet, sigue [Wi-Fi por SSH](anexos/wifi.md). La protección por batería tiene su [propio anexo](anexos/bateria.md): un externo con enchufe requiere alimentación protegida antes de poder copiar durante un corte.

¿No tienes externo? Elige desde el principio la [variante solo SSD](anexos/solo-ssd.md), que indica qué pasos sustituir; no necesita formatear ni inventar un montaje USB.

¿Prefieres delegar la instalación? Usa el [prompt para un agente por SSH](PROMPT-AGENTE.md) una vez instalado Ubuntu y preparado el acceso. El agente necesita terminal, conectividad y autenticación propias; una sesión abierta en MobaXterm no le da acceso automático. Tendrás que intervenir para confirmar el disco, autorizar cuentas y probar los clientes.

## Archivos del repositorio

| Ruta | Para qué sirve |
| --- | --- |
| `README.md` | Recorrido manual, comandos y comprobaciones |
| [PROMPT-AGENTE.md](PROMPT-AGENTE.md) | Recorrido delegado desde SSH, datos de entrada e intervenciones humanas |
| [nextcloud/compose.yaml](nextcloud/compose.yaml) y [immich/compose.yaml](immich/compose.yaml) | Definición de aplicaciones e imágenes fijadas; no requieren Dockerfiles propios |
| `scripts/` y `systemd/` | Preparación, control de almacenamiento, supervisión, recuperación y avisos opcionales |
| [anexos/README.md](anexos/README.md) | Variantes y ampliaciones |
| `variantes/solo-ssd/` | Sustituciones para instalar sin disco externo |
| `tests/` | Comprobaciones de integridad y de restauración |

## Cómo seguir este paso a paso

Copia **un bloque completo cada vez**, incluidos sus delimitadores finales. Espera al prompt y verifica el resultado antes de seguir. Si falla un comando, detente en ese punto: no repitas el formateo ni las inicializaciones.

| Paso | Lo que introduces o haces tú |
| --- | --- |
| 1 | Nombre del equipo, usuario y contraseña de Ubuntu; IP local para SSH; huella de host verificada desde consola física |
| 3 | Sustituir DISCO por el enlace usb real y volver a escribirlo cuando pida confirmar el borrado |
| 5 | Arrastrar los archivos de este repositorio por SFTP |
| 6 | Abrir el enlace Tailscale y autorizar con tu cuenta; esperar confirmación; autorizar HTTPS sin Funnel |
| 9 | Escribir dos veces la contraseña de Nextcloud cuando pregunte y crear usuario normal en la web |
| 10 | Crear correo/contraseña de Immich en el asistente y elegir las fotos de prueba |
| 11–12 | Apagar/encender y conectar o retirar físicamente solo en el momento indicado |

Las contraseñas en terminal no muestran caracteres al teclear: es normal; pulsa Intro al terminar. Los secretos internos, UUID, dominio privado y gateways se generan u obtienen automáticamente. Tras reiniciar, vuelve a abrir SSH; los pasos posteriores leen la configuración del servidor y no requieren conservar variables de la sesión anterior.

No hay que sustituir cada aparición de cloud ni homelab: son nombres públicos del proyecto y rutas comunes. Tu nombre solo se introduce al crear el usuario Ubuntu y al conectar por SSH. El administrador web Nextcloud se llama admin para todos; no es el usuario de Ubuntu.

Sigue los pasos en orden. Los anexos son opcionales y explican sus propios requisitos.

## Antes de empezar

- Equipo dedicado compatible con Ubuntu Server de 64 bits, SSD y un disco USB que puedas borrar.
- Referencia práctica: 8 GB de RAM para empezar con ambos servicios y bibliotecas pequeñas; medir consumo al importar. Immich recomienda 8 GB para sí mismo y necesita CPU compatible con su versión: [requisitos oficiales](https://docs.immich.app/install/requirements/).
- Ubuntu Server 26.04 LTS en el recorrido de referencia. Un Windows con MobaXterm para SSH/SFTP y un móvil para comprobar el resultado.
- Cuenta Tailscale; conexión a Internet y alimentación estable durante instalación/formateo.

Los comandos son **para Ubuntu por SSH**, salvo indicación. Los scripts de preparación son de **primera instalación**, no actualizadores: las rutas de aplicaciones y bases deben estar vacías. Para recuperar datos usa el anexo correspondiente, sin volver a inicializarlos.

Solo tendrás que elegir tu equipo/usuario/IP, el identificador de tu disco y tus contraseñas web. El UUID, el dominio Tailscale y las IP de las redes Docker se obtienen automáticamente.

## 1. Instalar Ubuntu Server y conectar desde Windows

1. Descargar Ubuntu Server desde su web oficial y grabar el USB de instalación.
2. Desconectar el externo para evitar seleccionarlo como destino. En el instalador: elegir idioma/teclado, instalación Ubuntu Server estándar y red por DHCP. Dejar proxy vacío si tu red no usa uno y conservar el mirror ofrecido. Seleccionar el **SSD interno** para el sistema; confirmar que sus datos se pueden borrar. Crear nombre, usuario, contraseña y nombre del equipo, por ejemplo `nube`. Omitir Ubuntu Pro si no lo necesitas; seleccionar **OpenSSH server**. No es obligatorio importar claves de GitHub para este recorrido con contraseña. No seleccionar paquetes Snap de servidor adicionales. Finalizar, reiniciar y retirar el USB de instalación. Mantener el equipo accesible físicamente durante esta fase.
3. Reservar en el router la IP local mediante DHCP para ese equipo; ejemplo `192.168.1.50`. Es una reserva del router, no otra configuración estática simultánea en Ubuntu.
4. En MobaXterm: Session → SSH → IP local → usuario creado → puerto 22. Comparar la huella inicial con la consola del servidor:

```bash
sudo ssh-keygen -lf /etc/ssh/ssh_host_ed25519_key.pub
```

Este comando **no genera claves**: `-l` muestra la huella de la clave pública de host ya creada por OpenSSH; `-f` indica el archivo. Compararla verifica que conectas al equipo esperado. No es el par de claves personal de tu usuario, ni obliga a configurar acceso sin contraseña.

La reserva facilita el SSH local. Tailscale tendrá su propia dirección y nombre estables; no depende de esa IP local para acceder a la nube. No configurar redirecciones de puertos en el router.

Actualizar Ubuntu e instalar herramientas:

```bash
sudo apt update
sudo apt upgrade
sudo apt install ca-certificates curl openssl python3 parted e2fsprogs
```

Si existe el archivo siguiente, reinicia y vuelve a conectar antes de continuar:

```bash
test ! -e /var/run/reboot-required || cat /var/run/reboot-required
```

```bash
sudo systemctl reboot
```

## 2. Instalar Docker y Compose

Añadir el repositorio oficial para la versión y arquitectura de Ubuntu instaladas. Estos pasos parten de una instalación limpia sin otros paquetes Docker:

```bash
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc
sudo bash <<'DOCKER_REPO'
set -eu
. /etc/os-release
cat > /etc/apt/sources.list.d/docker.sources <<EOF
Types: deb
URIs: https://download.docker.com/linux/ubuntu
Suites: ${UBUNTU_CODENAME:-$VERSION_CODENAME}
Components: stable
Architectures: $(dpkg --print-architecture)
Signed-By: /etc/apt/keyrings/docker.asc
EOF
DOCKER_REPO
sudo apt update
sudo apt install docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
sudo systemctl enable --now docker
sudo docker run --rm hello-world
sudo docker compose version
```

Esperado: `Hello from Docker!` y versión de Compose. Usaremos `sudo docker`; no necesitas dar a tu usuario permisos sobre el socket.

## 3. Identificar y preparar el externo

Conecta el disco y consulta sus identificadores:

```bash
lsblk -o NAME,MODEL,SIZE,TRAN,FSTYPE,LABEL,UUID,MOUNTPOINTS
ls -l /dev/disk/by-id/
```

**Solo para un disco que hayas decidido borrar por completo.** Elige el enlace `usb-...` de la unidad entera, sin `-part1`. Contrasta modelo/tamaño: no debe ser el SSD donde instalaste Ubuntu. El tipo de conector no garantiza la velocidad; la comparación exhaustiva de puertos queda fuera de este recorrido.

Sustituye **únicamente la primera línea** con tu identificador real. La confirmación pide volver a escribirlo antes de borrar:

```bash
DISCO='/dev/disk/by-id/usb-SUSTITUYE_POR_TU_DISCO'
sudo -v
export DISCO
bash <<'FORMATEAR'
set -euo pipefail
test -b "$DISCO"
test "$(lsblk -dn -o TRAN "$DISCO")" = usb
test -z "$(lsblk -nr -o MOUNTPOINTS "$DISCO" | tr -d '[:space:]')"
lsblk -o NAME,MODEL,SIZE,TRAN,FSTYPE,MOUNTPOINTS "$DISCO"
printf 'BORRADO TOTAL. Escribe el identificador completo del disco para confirmar: ' > /dev/tty
read -r confirmacion < /dev/tty
if [ "$confirmacion" != "$DISCO" ]; then
  printf 'CANCELADO: la confirmacion no coincide. No se ha ejecutado el formateo.\n' >&2
  printf 'Debias introducir la ruta completa: %s\n' "$DISCO" >&2
  exit 1
fi
sudo parted --script "$DISCO" mklabel gpt
sudo parted --script --align optimal "$DISCO" mkpart primary ext4 1MiB 100%
sudo partprobe "$DISCO"
sudo udevadm settle
test -b "${DISCO}-part1"
sudo mkfs.ext4 -m 0 -L nube-datos "${DISCO}-part1"
sudo parted "$DISCO" align-check minimal 1
STORAGE_UUID=$(sudo blkid -p -s UUID -o value "${DISCO}-part1")
test -n "$STORAGE_UUID"
sudo install -d -m 0755 /etc/homelab
printf 'STORAGE_UUID=%s\n' "$STORAGE_UUID" | sudo tee /etc/homelab/storage.conf
sudo chmod 0644 /etc/homelab/storage.conf
printf 'FORMATO COMPLETADO: ext4, UUID=%s, configuracion en /etc/homelab/storage.conf\n' "$STORAGE_UUID"
FORMATEAR
```

Cuando se solicite confirmar, introduce la ruta completa de DISCO, incluyendo /dev/disk/by-id/, sin comillas. No basta con escribir usb-... ni el final del identificador. Esperado al terminar: FORMATO COMPLETADO, ext4 y UUID nuevo. Si vuelves al prompt sin ese mensaje, no continúes al montaje: revisa la salida del bloque. No repitas el bloque si ya terminó correctamente. Si aparece una advertencia de alineación, revisa la topología del dispositivo antes de continuar; no reformatees por ensayo/error.

## 4. Montar siempre por UUID y comprobar escritura

El UUID identifica el disco aunque cambie de puerto o de nombre `/dev/sdX`. `nofail` permite encender el servidor sin él; `device-bound` vincula el montaje a la presencia del dispositivo.

```bash
sudo bash <<'MONTAR'
set -euo pipefail
. /etc/homelab/storage.conf
if findmnt --fstab -rn -o TARGET | grep -Fxq /srv/storage; then
  printf 'Ya existe entrada para /srv/storage; revisar, no duplicar.\n' >&2
  exit 1
fi
install -d -m 0755 /srv/storage
cp -a /etc/fstab "/etc/fstab.backup.$(date +%Y%m%d-%H%M%S)"
printf '\nUUID=%s /srv/storage ext4 defaults,noatime,nofail,x-systemd.device-bound,x-systemd.device-timeout=10s 0 2\n' "$STORAGE_UUID" >> /etc/fstab
findmnt --verify
systemctl daemon-reload
mount /srv/storage
test "$(findmnt -rn -M /srv/storage -o UUID)" = "$STORAGE_UUID"
findmnt -M /srv/storage -o SOURCE,TARGET,FSTYPE,UUID,OPTIONS
MONTAR
```

Comprobar 8 MiB de escritura y lectura tras desmontar/remontar. No hay aplicaciones usando el disco todavía:

```bash
sudo bash <<'PRUEBA_DISCO'
set -euo pipefail
. /etc/homelab/storage.conf
test "$(findmnt -rn -M /srv/storage -o UUID)" = "$STORAGE_UUID"
prueba=$(mktemp -d /srv/storage/.prueba.XXXXXX)
dd if=/dev/urandom of="$prueba/datos.bin" bs=1M count=8 conv=fsync status=none
suma=$(sha256sum "$prueba/datos.bin" | cut -d ' ' -f 1)
cd /
umount /srv/storage
mount /srv/storage
test "$(findmnt -rn -M /srv/storage -o UUID)" = "$STORAGE_UUID"
printf '%s  %s\n' "$suma" "$prueba/datos.bin" | sha256sum -c -
rm -- "$prueba/datos.bin"
rmdir -- "$prueba"
PRUEBA_DISCO
```

Esperado: checksum `OK`. Esto comprueba funcionalidad, no certifica la vida útil ni toda la capacidad del disco.

## 5. Copiar los archivos de este repositorio

En Ubuntu crea la carpeta de llegada:

```bash
mkdir -p "$HOME/nube-instalacion"
```

Desde el explorador SFTP de MobaXterm entra en esa ruta de tu usuario y arrastra **el contenido de esta carpeta del repositorio**. Deben quedar `nextcloud/`, `immich/`, `scripts/` y `systemd/` dentro de `~/nube-instalacion`. No mezcles ambos `compose.yaml` ni copies secretos desde otro servidor.

Instalar los scripts y unidades; todavía no arrancan servicios:

```bash
sudo -v
bash <<'ARCHIVOS'
set -euo pipefail
cd "$HOME/nube-instalacion"
for archivo in scripts/cloud-* systemd/*; do sed -i 's/\r$//' "$archivo"; done
for archivo in scripts/cloud-storage-check scripts/cloud-nextcloud-prepare scripts/cloud-immich-prepare; do bash -n "$archivo"; done
python3 -m py_compile scripts/cloud-recovery
sudo install -m 0755 scripts/cloud-* /usr/local/sbin/
sudo install -m 0644 systemd/cloud@.service systemd/cloud.target /etc/systemd/system/
sudo /usr/local/sbin/cloud-storage-check
sudo bash <<'PRUEBA_GUARDIA'
set -euo pipefail
cd /
umount /srv/storage
if /usr/local/sbin/cloud-storage-check; then
  printf 'ERROR: se acepto ausencia de montaje; no continuar.\n' >&2
  exit 1
else
  printf 'PRUEBA CORRECTA: el comprobador rechaza la ausencia de montaje.\n'
fi
mount /srv/storage
/usr/local/sbin/cloud-storage-check
PRUEBA_GUARDIA
sudo bash <<'CARPETAS'
set -eu
cd /srv/storage
/usr/local/sbin/cloud-storage-check
install -d -m 0755 nextcloud immich /srv/appdata/nextcloud /srv/appdata/immich /opt/homelab
install -d -m 0700 recovery
CARPETAS
sudo /usr/local/sbin/cloud-nextcloud-prepare
sudo /usr/local/sbin/cloud-immich-prepare
sudo install -m 0644 nextcloud/compose.yaml /opt/homelab/nextcloud/compose.yaml
sudo install -m 0644 immich/compose.yaml /opt/homelab/immich/compose.yaml
sudo systemctl daemon-reload
sudo systemd-analyze --generators --recursive-errors=no verify /etc/systemd/system/cloud@.service /etc/systemd/system/cloud.target
printf 'ARCHIVOS COMPLETADOS: preparadores, Compose y unidades instalados y verificados.\n'
ARCHIVOS
```

Esperado: disco correcto y preparaciones completadas. `install -d` crea carpetas, no instala aplicaciones. Los scripts generan contraseñas internas en `.env` root/0600; no subir esos archivos a GitHub.

Durante PRUEBA_GUARDIA es esperado ver «Disco no disponible» entre dos comprobaciones correctas: se desmonta deliberadamente para verificar el rechazo y después se vuelve a montar. La verificación systemd puede mostrar avisos de generadores o unidades del sistema ajenas a cloud, por ejemplo opciones CPUAccounting ignoradas de xfs_scrub. No vuelvas a ejecutar los preparadores por esos avisos: si falta el mensaje final, repite únicamente la verificación de unidades y consulta su código de salida. Los preparadores rechazan secretos ya existentes.

| Ubicación | Contenido |
| --- | --- |
| SSD: `/opt/homelab` | Compose y ajustes secretos locales |
| SSD: `/srv/appdata/nextcloud` | PostgreSQL, aplicación y configuración |
| SSD: `/srv/appdata/immich` | PostgreSQL, miniaturas, modelos y cola |
| Externo: `/srv/storage/nextcloud/data` | Archivos, versiones y previews Nextcloud |
| Externo: `/srv/storage/immich/media` | Originales y vídeos convertidos Immich |
| Externo: `/srv/storage/recovery` | Puntos fríos de estado SSD; consultar anexo antes de ejecutarlos |

Cada aplicación tiene su Compose y su PostgreSQL. Así se actualizan y recuperan por separado; Immich necesita además extensiones vectoriales. Redis/Valkey gestionan bloqueos o colas; el cron de Nextcloud ejecuta tareas periódicas. Los ocho contenedores comparten el equipo, no las bases.

## 6. Configurar Tailscale y HTTPS

Instalar Tailscale en Ubuntu y autorizar el servidor en el enlace que muestre:

```bash
curl -fsSL https://tailscale.com/install.sh -o "$HOME/tailscale-install.sh"
sudo sh "$HOME/tailscale-install.sh"
sudo tailscale up
tailscale status
```

Instala Tailscale también en Windows y en el móvil, entra en la misma red privada y conéctalo. Para otra persona invita su propia cuenta; no compartas tu acceso administrador.

Crear dos proxies HTTPS privados hacia las aplicaciones, todavía sin iniciar:

```bash
sudo tailscale serve --bg --https=443 http://127.0.0.1:8080
sudo tailscale serve --bg --https=8443 http://127.0.0.1:2283
sudo tailscale serve status
```

Si aparece una autorización web, habilita **HTTPS certificates** y deja **Funnel desmarcado**. Los certificados publican el nombre del equipo en registros públicos, pero Serve mantiene el acceso dentro de la red privada. Un error de conexión al destino es esperable hasta arrancar las aplicaciones. No usar `serve reset`.

## 7. Preparar y descargar ambos proyectos

Este bloque prepara los dos Compose y obtiene sus gateways reales. No inicia las aplicaciones ni fija IP de red a mano:

```bash
sudo bash <<'PROYECTOS'
set -euo pipefail
/usr/local/sbin/cloud-storage-check
DOMINIO=$(tailscale status --json | python3 -c 'import json,sys; print(json.load(sys.stdin)["Self"]["DNSName"].rstrip("."))')
test -n "$DOMINIO"
for app in nextcloud immich; do
  cd "/opt/homelab/$app"
  docker compose --project-name "cloud-$app" config --quiet
  docker compose --project-name "cloud-$app" pull
  docker compose --project-name "cloud-$app" create
  gateway=$(docker network inspect "cloud-${app}_default" --format '{{range .IPAM.Config}}{{println .Gateway}}{{end}}')
  test -n "$gateway"
  if [ "$app" = nextcloud ]; then
    printf '\nNEXTCLOUD_URL=https://%s\nNEXTCLOUD_PROTOCOL=https\nNEXTCLOUD_TRUSTED_PROXIES="127.0.0.1 %s"\nNEXTCLOUD_EXTRA_TRUSTED_DOMAIN=%s\n' "$DOMINIO" "$gateway" "$DOMINIO" >> .env
  else
    sed -i "s/^IMMICH_TRUSTED_PROXIES=.*/IMMICH_TRUSTED_PROXIES=127.0.0.1,$gateway/" .env
  fi
  docker compose --project-name "cloud-$app" config --quiet
done
printf 'Nextcloud: https://%s/\nImmich: https://%s:8443/\n' "$DOMINIO" "$DOMINIO"
PROYECTOS
```

Esperado: imágenes descargadas, contenedores creados y dos URLs propias. Este bloque modifica ajustes de primera instalación; no repetirlo como procedimiento de actualización. No hace falta puente SSH, Caddy ni dominio propio para abrir estas URLs desde clientes Tailscale.

## 8. Arrancar y automatizar la nube

systemd supervisa ambos proyectos y comprueba el disco antes de arrancar. La regla udev solicita el grupo cuando aparece su UUID. Los contenedores no usan `restart: always`: evita que Docker los arranque saltándose este control.

```bash
sudo bash <<'AUTOMATIZAR'
set -euo pipefail
. /etc/homelab/storage.conf
/usr/local/sbin/cloud-storage-check
printf 'ACTION=="add|change", SUBSYSTEM=="block", ENV{DEVTYPE}=="partition", ENV{ID_FS_UUID}=="%s", TAG+="systemd", ENV{SYSTEMD_WANTS}+="cloud.target"\n' "$STORAGE_UUID" > /etc/udev/rules.d/99-cloud.rules
udevadm verify /etc/udev/rules.d/99-cloud.rules
udevadm control --reload-rules
systemctl daemon-reload
systemctl enable cloud@nextcloud.service cloud@immich.service
systemctl start cloud.target
AUTOMATIZAR
sudo docker ps
```

Espera unos minutos y repite `sudo docker ps`: **ocho contenedores, siete healthy y cron Up**. Arrancan los dos proyectos en el mismo paso; después comprobaremos cada aplicación. En equipos modestos el primer inicio puede tardar más. `cloud.target` puede aparecer disabled: lo activa el dispositivo, no se habilita directamente en multi-user.

Si faltan contenedores o hay reinicios, conserva el disco conectado y revisa antes de continuar:

```bash
sudo systemctl status cloud@nextcloud.service cloud@immich.service --no-pager --full
sudo journalctl -b -u cloud@nextcloud.service -u cloud@immich.service -n 100 --no-pager
free -h
sudo docker stats --no-stream
```

## 9. Probar Nextcloud

Activar tareas periódicas y elegir contraseña para el usuario `admin`. El segundo comando pregunta interactivamente; no necesitas leer la contraseña aleatoria inicial ni editar el secreto de PostgreSQL:

```bash
sudo docker compose --project-name cloud-nextcloud --project-directory /opt/homelab/nextcloud exec -T --user www-data app php occ background:cron
sudo docker compose --project-name cloud-nextcloud --project-directory /opt/homelab/nextcloud exec --user www-data app php occ user:resetpassword admin
```

Abre la URL sin `:8443`, entra como `admin` y crea un usuario normal para tus archivos. Elige contraseñas robustas que puedas manejar con un gestor.

1. Crea una carpeta, sube un archivo pequeño y descárgalo.
2. Instala el cliente oficial Nextcloud en Windows y en el móvil.
3. Introduce la misma URL HTTPS y autoriza tu usuario normal. En Windows prueba una carpeta pequeña, no todo tu PC.

La sincronización puede propagar borrados: no equivale a una copia versionada independiente.

## 10. Probar Immich

Abre la segunda URL, **con `:8443`**, y crea la cuenta administradora desde el asistente. Elige tu contraseña; la clave de PostgreSQL es independiente. Puedes dejar la estructura de carpetas predeterminada o elegir año/mes/día; no modifica quién puede ver tus fotos.

1. Revisa el asistente. La pantalla sobre backups es informativa, no configura una copia completa.
2. Crea cuentas individuales para cada persona; no compartir el administrador.
3. Instala la app oficial Immich en Android/iPhone e introduce la URL completa con `:8443` y tu cuenta.
4. Sube unas pocas fotos y un vídeo. Comprueba que se ven en web y que puedes descargar un original.
5. Elige qué álbumes respaldará el móvil y permite los accesos necesarios. La subida en segundo plano depende también del sistema operativo: no prometemos el mismo comportamiento que iCloud.

Para la demostración remota desactiva el Wi-Fi del móvil, mantén Tailscale conectado y comprueba ambos servicios por datos móviles. Las URLs no cambian al salir de casa.

## 11. Demostrar el arranque automático

**Prueba A: disco conectado.** Reinicia y vuelve por SSH sin ejecutar mount/start manualmente:

```bash
sudo systemctl reboot
```

```bash
sudo /usr/local/sbin/cloud-storage-check
sudo docker ps
sudo tailscale serve status
```

Esperado: montaje correcto, ocho contenedores saludables tras inicializar y las dos URLs privadas conservadas.

**Prueba B: conectar el disco después.** Apaga, espera al apagado completo, retira el USB y enciende:

```bash
sudo systemctl poweroff
```

Sin externo, SSH/Docker/Tailscale deben funcionar y ambos proyectos permanecer parados. Conecta ahora el externo, espera y repite las tres comprobaciones anteriores **sin montar ni arrancar a mano**. No desconectes el disco en uso para hacer esta prueba.

Si falla, consulta también:

```bash
sudo journalctl -b -u srv-storage.mount -u cloud@nextcloud.service -u cloud@immich.service -n 100 --no-pager
systemctl --failed --no-pager
```

## 12. Extracción segura y uso diario

Esperar a que terminen las subidas antes de apagar:

```bash
sudo systemctl poweroff
```

Espera al apagado completo antes de retirar el externo. No es necesario parar cada contenedor a mano. El apagado ordenado no crea un backup.

### Extraer y volver a conectar el disco

Pausa primero subidas y sincronizaciones en los clientes y espera a que terminen. Ejecuta el comando de apagado anterior. La desconexión de SSH por sí sola no acredita que el equipo esté apagado: compruébalo físicamente antes de quitar el cable.

1. Espera al apagado completo; entonces retira el USB.
2. Para usar de nuevo la nube, conecta el mismo externo y enciende Ubuntu.
3. Vuelve a SSH y comprueba sin arrancar servicios a mano:

```bash
sudo /usr/local/sbin/cloud-storage-check
sudo docker ps
sudo tailscale serve status
```

Espera a siete healthy y cron Up; abre ambas URLs y descarga tus archivos de muestra. También puedes encender sin disco y conectarlo después como en el paso 11.

No desenchufes el USB mientras Ubuntu y las aplicaciones estén usando el disco.

Consultar espacio y carga:

```bash
sudo /usr/local/sbin/cloud-storage-check && df -hT / /srv/storage
sudo docker stats --no-stream
```

**Resultado del tutorial:** documentos y fotos accesibles desde dispositivos autorizados, originales en disco externo y arranque condicionado a su presencia. El SSD sigue conteniendo bases y configuración imprescindibles: conectar solo el externo a otro ordenador no reconstruye automáticamente las aplicaciones.

Antes de convertirlo en tu almacenamiento definitivo, completa la [copia y prueba de recuperación](anexos/recuperacion.md) y conserva una copia independiente de originales. El punto frío debe renovarse mientras utilizas la nube: una única copia inicial no conserva las nuevas cuentas, referencias a archivos, álbumes y cambios posteriores. Actualizar exige revisar versiones y migraciones; no basta cambiar `latest`. Mantén Ubuntu al día. Los avisos se configuran por separado en su anexo.

## Comprobación final de la instalación

- [ ] Montaje ext4 por UUID; escritura/lectura con checksum OK.
- [ ] Ocho contenedores: siete healthy y cron Up.
- [ ] Nextcloud: usuario normal, archivo subido y descargado; clientes Windows/móvil.
- [ ] Immich: cuentas, fotos y vídeo visibles; descarga de original.
- [ ] Las dos URLs funcionan por datos móviles con Tailscale.
- [ ] Reinicio con disco y conexión del disco tras el arranque comprobados.
- [ ] Extracción tras apagado completo y reconexión comprobadas.
- [ ] Recuperación tratada con datos de muestra según su anexo, sin anunciar automatización diaria ni protección ante pérdida del externo.

Si falla una comprobación de arranque automático, conserva la salida y corrige el problema antes de continuar.

## Referencias y ampliaciones

- [Docker en Ubuntu](https://docs.docker.com/engine/install/ubuntu/).
- [Imagen oficial Nextcloud](https://github.com/nextcloud/docker) y [copias Nextcloud](https://docs.nextcloud.com/server/stable/admin_manual/maintenance/backup.html).
- [Compose oficial Immich de referencia](https://github.com/immich-app/immich/blob/v3.3.3/docker/docker-compose.yml), [ubicaciones](https://docs.immich.app/guides/custom-locations/) y [copias](https://docs.immich.app/administration/backup-and-restore/).
- [Tailscale Serve](https://tailscale.com/docs/reference/tailscale-cli/serve).
- [Índice de anexos](anexos/README.md): comandos disponibles y alcance de cada procedimiento.
