# Instalar sin disco externo: todo en el SSD

Variante de primera instalación. Elige esta variante **o** la del externo; no las mezcles ni la apliques como migración de servicios existentes.

Nextcloud e Immich conservan sus Compose y rutas. `/srv/storage` será una carpeta del SSD, no un montaje USB. Archivos, bases y miniaturas competirán por el mismo espacio. No se instala regla de conexión USB ni se impide arrancar por ausencia de un externo.

## 1. Ubuntu y Docker

Sigue los pasos 1 y 2 del [tutorial principal](../README.md). **Omite sus pasos 3 y 4 completos:** no identificar, particionar, formatear ni modificar fstab para un externo.

## 2. Preparar carpeta y comprobación del SSD

Este recorrido utiliza ext4 en el filesystem raíz. Si tienes otro filesystem o quieres un segundo disco interno dedicado, no apliques esta variante sin adaptarla.

```bash
sudo bash <<'SSD'
set -euo pipefail
test "$(findmnt -rn -M / -o FSTYPE)" = ext4
if mountpoint -q /srv/storage; then
  printf '/srv/storage ya es un montaje; no mezclar instalaciones.\n' >&2
  exit 1
fi
test ! -L /srv/storage
install -d -m 0755 /srv/storage /etc/homelab
uuid=$(findmnt -rn -M / -o UUID)
test -n "$uuid"
test "$(findmnt -rn -T /srv/storage -o UUID)" = "$uuid"
printf 'STORAGE_UUID=%s\n' "$uuid" > /etc/homelab/storage.conf
chmod 0644 /etc/homelab/storage.conf
prueba=$(mktemp /srv/storage/.prueba.XXXXXX)
printf 'Prueba de escritura y lectura\n' > "$prueba"
sync -f "$prueba"
test "$(cat "$prueba")" = 'Prueba de escritura y lectura'
rm -- "$prueba"
df -hT /srv/storage
SSD
```

Esperado: espacio del SSD y bloque terminado sin errores. No se ha formateado nada.

## 3. Seleccionar los archivos de la variante

Realiza la transferencia SFTP del paso 5 del tutorial, incluyendo `variantes/`. **Antes de ejecutar su bloque ARCHIVOS**, sustituye las tres piezas dependientes del almacenamiento en la carpeta de trabajo subida:

```bash
bash <<'VARIANTE'
set -euo pipefail
cd "$HOME/nube-instalacion"
cp variantes/solo-ssd/scripts/cloud-storage-check scripts/cloud-storage-check
cp variantes/solo-ssd/systemd/cloud@.service systemd/cloud@.service
cp variantes/solo-ssd/systemd/cloud.target systemd/cloud.target
VARIANTE
```

Ahora ejecuta el bloque ARCHIVOS del paso 5. Los dos scripts de preparación y los Compose son los mismos; el comprobador verificará el UUID del SSD usando la carpeta, sin exigir un montaje USB.
Omite dentro de ARCHIVOS el bloque PRUEBA_GUARDIA completo: /srv/storage es una carpeta del SSD, no un montaje que se deba desmontar. Conserva la llamada anterior al comprobador y continúa por CARPETAS.

## 4. Tailscale y aplicaciones

Sigue los pasos 6 y 7 del tutorial. **Sustituye todo el paso 8** por este bloque:

```bash
sudo /usr/local/sbin/cloud-storage-check
sudo systemctl daemon-reload
sudo systemctl enable cloud@nextcloud.service cloud@immich.service
sudo systemctl enable --now cloud.target
sudo docker ps
```

Aquí sí se habilita `cloud.target` al encender: no habrá evento de un disco externo que lo solicite. Espera a los ocho contenedores, siete healthy y cron Up. Para diagnosticar usa los comandos del paso 8 original.

Completa los pasos 9 y 10 para contraseñas, usuarios y clientes.

## 5. Validar reinicio

Haz solo la prueba A del paso 11. Omite la prueba B de retirar/conectar el externo: no existe en este montaje. Después del reinicio deben arrancar ambos proyectos y conservarse los archivos de muestra y las URLs.

El paso 12 se limita aquí a apagar y volver a encender: no hay USB que extraer.

## Recuperación y límites

Recovery sigue teniendo sentido para errores, cambios o migraciones, pero una copia en el propio SSD no sobrevive a su pérdida. Guarda las copias de estado y originales en otro dispositivo o destino independiente si quieres cubrir ese fallo. No interpretar «sin externo» como «sin necesidad de backup».

No se instalan cuotas ni alertas en el recorrido principal: vigila `df -hT /`, especialmente al importar fotos/vídeos. Un SSD lleno también afecta a Ubuntu y a las bases.
