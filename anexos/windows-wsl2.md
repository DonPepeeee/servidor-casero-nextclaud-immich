# Recuperación en Windows con WSL2

Windows aporta Docker Desktop y WSL2; Ubuntu WSL monta el externo ext4 y aloja el estado recuperado en su disco Linux virtual. Los originales permanecen en el externo. No extraigas bases PostgreSQL en /mnt/c ni conviertas el disco a NTFS.

Necesitas Windows compatible con WSL2, administrador local, CPU amd64, RAM suficiente y espacio libre real para imágenes y estado SSD. El tutorial usa Ubuntu-24.04 como distribución WSL. Los nombres e identificadores se eligen en los pasos siguientes.

## 1. Preparar Windows antes de trasladar el externo

En PowerShell:

```powershell
wsl --version
wsl --list --verbose
wsl --update --web-download
wsl --install --distribution Ubuntu-24.04 --no-launch
```

Si la distribución ya existe, no la reinstales. Abre Ubuntu-24.04 una vez y completa usuario/contraseña. Reinicia Windows si lo pide el instalador. Instala Docker Desktop, selecciona contenedores Linux y activa Settings → Resources → WSL Integration → Ubuntu-24.04 → Apply & Restart.

En la misma ventana PowerShell selecciona la distribución:

```powershell
$DistroRecuperacion = 'Ubuntu-24.04'
wsl -d $DistroRecuperacion -- docker info --format '{{.OSType}}'
Get-PSDrive -PSProvider FileSystem
```

Esperado: motor linux. Revisa espacio libre de Windows; la capacidad virtual que muestra df dentro de WSL no es espacio libre real en C:.

## 2. Guardar el estado actual y apagar el origen

En el servidor Ubuntu, pausa clientes. Si utilizas la instalación normal:

```bash
sudo /usr/local/sbin/cloud-recovery backup
```

Si utilizas una instalación recuperada, introduce su ruta y guarda sus bases actuales:

```bash
read -r -p 'Carpeta activa /srv/cloud-restore.ID: ' RESTAURACION
sudo /usr/local/sbin/cloud-recovery backup-restored "$RESTAURACION"
```

Elige solo el comando correspondiente. Espera PUNTO COMPLETO, apunta la ruta y verifica:

```bash
read -r -p 'Ruta completa del punto final: ' PUNTO
sudo /usr/local/sbin/cloud-recovery verify "$PUNTO"
sudo systemctl poweroff
```

Espera al apagado físico completo y conecta el externo a Windows. Cancela cualquier propuesta de inicializar o formatear. Que ext4 no tenga letra en el Explorador es normal.

## 3. Identificar y adjuntar el disco

En **PowerShell como administrador**:

```powershell
Get-CimInstance Win32_DiskDrive | Select-Object DeviceID,Model,SerialNumber,Size,InterfaceType
$DiscoRecuperacion = Read-Host 'DeviceID completo del externo verificado por modelo, serie y capacidad (\\.\PHYSICALDRIVE...)'
wsl --mount $DiscoRecuperacion --bare
wsl -d $DistroRecuperacion -u root -- lsblk -o NAME,MODEL,SIZE,FSTYPE,LABEL,UUID,MOUNTPOINTS
```

Si has abierto otra ventana, vuelve a definir $DistroRecuperacion. --bare adjunta el dispositivo, no formatea ni monta ext4. Comprueba el UUID y capacidad. Microsoft documenta limitaciones con dispositivos USB/lectores: si tu caja no admite esta ruta, detente y usa un Ubuntu físico para la recuperación. No cambies formato ni repitas por USB/IP mientras siga adjunto; las cajas y controladores no tienen soporte uniforme.

## 4. Abrir una consola Ubuntu WSL como root

Desde PowerShell:

```powershell
wsl -d $DistroRecuperacion -u root
```

Los siguientes comandos son **Linux dentro de esa consola**. Mantén esta sesión abierta para conservar las variables. Descarga este repositorio en Windows y localiza su ruta Linux, por ejemplo /mnt/c/Users/TU_USUARIO/Downloads/nube-casera. Introduce la ruta real, sin comillas adicionales aunque contenga espacios:

```bash
read -r -p 'Ruta Linux de la carpeta del repositorio: ' REPO
test -f "$REPO/scripts/cloud-recovery"
test -f "$REPO/tests/recovery_acceptance.py"
read -r -p 'UUID ext4 del externo: ' UUID_DISCO
mkdir -p /srv/storage
mount -t ext4 -o ro,noload "UUID=$UUID_DISCO" /srv/storage
findmnt -M /srv/storage -o SOURCE,TARGET,FSTYPE,UUID,OPTIONS
ls -1 /srv/storage/recovery/state-points
read -r -p 'Ruta completa del punto final creado en Ubuntu: ' PUNTO
python3 "$REPO/scripts/cloud-recovery" verify "$PUNTO"
```

Continúa solo con checksums/inventario OK. El montaje inicial es de lectura. Cierra cualquier otra consola o proceso situado dentro del externo y cambia a escritura:

```bash
cd /
umount /srv/storage
mount -t ext4 -o noatime "UUID=$UUID_DISCO" /srv/storage
python3 "$REPO/scripts/cloud-recovery" prepare-restore "$PUNTO" --portable
```

Espera a RESTAURACION PREPARADA EN SSD NUEVO y copia esa ruta. El script comprueba digests y que Docker Desktop ve los mismos archivos WSL/USB. Si falla esa comprobación, corrige la integración; no la suprimas ni arranques aplicaciones con montajes vacíos.

## 5. Arrancar y comprobar

```bash
read -r -p 'Carpeta SSD /srv/cloud-restore.ID impresa por el script: ' RESTAURACION
python3 "$REPO/tests/recovery_acceptance.py" "$RESTAURACION"
docker ps
```

Esperado: ocho contenedores, siete healthy y cron Up; hashes de originales muestreados intactos y cuentas/recursos recuperados. El test no debe repetirse si dejó un resultado parcial; revisa la salida antes de actuar.

En el navegador de Windows abre:

- Nextcloud: http://localhost:18080
- Immich: http://localhost:12283

Entra con las cuentas recuperadas. Comprueba permisos, archivos, álbumes y descarga de originales. Para comparar una descarga en Windows puedes usar Get-FileHash -Algorithm SHA256 desde PowerShell con la ruta del archivo. Si faltan miniaturas Immich: Administración → Colas de trabajo → Generar Miniaturas → Todos.

Estas URLs son locales al PC. Los móviles configurados con el dominio del servidor Ubuntu no cambian de destino automáticamente. El acceso local basta para recuperar y descargar archivos; para acceso remoto configura Tailscale/HTTPS y dominios confiables en el equipo sustituto, sin publicar estos puertos HTTP a Internet.

## 6. Sellar el estado final y retirar de Windows

Pausa todos los clientes. En la consola Ubuntu WSL que conserva REPO y RESTAURACION:

```bash
python3 "$REPO/scripts/cloud-recovery" backup-restored "$RESTAURACION"
```

Espera PUNTO COMPLETO. Este comando detiene ambos proyectos y crea un punto independiente con las bases actuales, sin duplicar originales. Anota y verifica el punto nuevo:

```bash
read -r -p 'Ruta completa del punto final creado en Windows: ' PUNTO_FINAL
python3 "$REPO/scripts/cloud-recovery" verify "$PUNTO_FINAL"
docker ps --filter label=com.docker.compose.project=cloud-restore-nextcloud
docker ps --filter label=com.docker.compose.project=cloud-restore-immich
cd /
sync -f /srv/storage
umount /srv/storage
```

Los dos listados deben estar vacíos y umount debe terminar sin errores. No fuerces el desmontaje. Cierra procesos que usen el externo y revisa antes de continuar si falla.

En **PowerShell como administrador**, con el mismo DeviceID verificado:

```powershell
wsl --unmount $DiscoRecuperacion
wsl -d $DistroRecuperacion -u root -- lsblk -o NAME,SIZE,FSTYPE,UUID,MOUNTPOINTS
```

Espera éxito y comprueba que ya no aparece el UUID. Solo entonces retira el cable. Cerrar la consola WSL, Docker Desktop o usar wsl --shutdown no sustituye este cierre coordinado.

## 7. Volver a Ubuntu con el punto vigente

Conecta el externo al servidor, enciende y verifica que las aplicaciones anteriores siguen detenidas. No retires bloqueos para arrancar sus bases antiguas. En un Ubuntu nuevo sigue el anexo de recuperación con --new-host.

Para un servidor que ya conserva un origen bloqueado o una restauración anterior, instala la versión de cloud-recovery de este repositorio, monta el externo por su entrada fstab y selecciona **el punto final de Windows**:

```bash
sudo mount /srv/storage
sudo /usr/local/sbin/cloud-storage-check
read -r -p 'Ruta completa del punto final de Windows: ' PUNTO_FINAL
sudo /usr/local/sbin/cloud-recovery verify "$PUNTO_FINAL"
sudo /usr/local/sbin/cloud-recovery prepare-next "$PUNTO_FINAL"
```

Si el disco ya está montado, omite solo mount. prepare-next exige que los proyectos estén detenidos, conserva controles anteriores en /etc/homelab/before-restore.ID y extrae el estado a otra carpeta SSD. Si se interrumpe, no lo repitas ni retires el marcador recovery-next-started: revisa la salida y la carpeta registrada en ese archivo.

Continúa con los pasos 4–6 del [anexo Ubuntu](recuperacion.md): iniciar/comprobar el nuevo estado, revisar URLs y habilitar la instalación recuperada. Esto recupera las escrituras hechas en Windows sin reactivar bases antiguas.

Referencias: [discos Linux en WSL](https://learn.microsoft.com/en-us/windows/wsl/wsl2-mount-disk), [Docker Desktop y WSL](https://docs.docker.com/desktop/features/wsl/), [backup Immich](https://docs.immich.app/administration/backup-and-restore/). [Volver al índice](README.md).
