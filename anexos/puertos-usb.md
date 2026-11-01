# Comparar puertos y cables USB

La prueba escribe un archivo de 4 GiB y lo lee con verificación CRC32C y E/S directa. Entre conexiones se verifica también SHA-256. No formatea ni escribe sobre el dispositivo crudo. Hazla **después del paso 4 y antes de instalar aplicaciones**; necesitas al menos 5 GiB libres en el externo.

## 1. Preparar archivos y herramientas

Adelanta solo la transferencia SFTP del paso 5 del tutorial: crea ~/nube-instalacion y copia ahí el contenido del repositorio. No ejecutes todavía la preparación de aplicaciones. Instala únicamente el comprobador y las herramientas:

```bash
sudo apt install fio usbutils
sed -i 's/\r$//' "$HOME/nube-instalacion/scripts/cloud-storage-check"
sudo install -m 0755 "$HOME/nube-instalacion/scripts/cloud-storage-check" /usr/local/sbin/cloud-storage-check
sudo /usr/local/sbin/cloud-storage-check
lsusb -t
```

Anota físicamente qué puerto/cable son A, B y C. 480M/5000M describen el enlace negociado, no el rendimiento real de archivos. Mantén iguales los demás factores.

## 2. Ejecutar una prueba

Cambia solo PUERTO por A, B o C. Copia el bloque completo. Puede tardar varios minutos; no desconectes mientras trabaja.

```bash
sudo -v
bash <<'PRUEBA_USB'
set -euo pipefail
PUERTO=A
case "$PUERTO" in A|B|C) ;; *) exit 1 ;; esac
sudo /usr/local/sbin/cloud-storage-check
test -z "$(sudo docker ps -q)"
PRUEBA=/srv/storage/prueba-puertos
sudo mkdir -p "$PRUEBA"
if [ -f "$HOME/usb-anterior.sha256" ]; then
  sudo sha256sum -c "$HOME/usb-anterior.sha256"
fi
sudo fio --name=usb --filename="$PRUEBA/usb-benchmark.bin" \
  --size=4G --rw=write --bs=1M --ioengine=psync --iodepth=1 \
  --direct=1 --verify=crc32c --do_verify=1 --verify_fatal=1 \
  --end_fsync=1 --group_reporting | tee "$HOME/usb-${PUERTO}.txt"
sudo sha256sum "$PRUEBA/usb-benchmark.bin" > "$HOME/usb-anterior.sha256"
PRUEBA_USB
```

Esperado: err=0, resultados WRITE y READ y verificación sin errores. El guardado del checksum termina sin salida si todo va bien. Ante un error conserva la muestra y la salida; no sigas al siguiente puerto.

## 3. Cambiar de puerto

```bash
sudo systemctl poweroff
```

Espera al apagado completo, cambia de puerto/cable y enciende. Vuelve por SSH y ejecuta el bloque con PUERTO=B o C. El checksum inicial comprueba el archivo anterior antes de sobrescribirlo. El montaje debe producirse automáticamente desde fstab. No repitas una prueba terminada por cambiar de sesión.

## 4. Verificar la última conexión y limpiar

Después de apagar y volver a conectar por última vez:

```bash
sudo /usr/local/sbin/cloud-storage-check && sudo sha256sum -c "$HOME/usb-anterior.sha256"
```

Solo si indica OK, borra exclusivamente la muestra:

```bash
sudo rm -- /srv/storage/prueba-puertos/usb-benchmark.bin
sudo rmdir -- /srv/storage/prueba-puertos
rm -- "$HOME/usb-anterior.sha256"
```

Compara BW de lectura/escritura y errores en ~/usb-A.txt, etc. Si empatan, elige por comodidad y sujeción. Una muestra de 4 GiB no certifica toda la capacidad ni la vida útil. Retoma el paso 5 del tutorial después de terminar.

Referencia: [fio](https://fio.readthedocs.io/en/latest/fio_doc.html). [Volver al índice](README.md).
