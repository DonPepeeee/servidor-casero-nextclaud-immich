# Avisos de ocupación del SSD y del externo

Recibe correo al alcanzar el 75 %, 85 % y 90 % de ocupación, con porcentaje y espacio disponible. El monitor comprueba cada 15 minutos, notifica cambios de nivel y recuerda cada 24 horas si continúa alto. Al bajar exige tres puntos de margen para evitar mensajes repetidos alrededor de un umbral.

Necesitas un proveedor SMTP con autenticación por usuario/contraseña o contraseña de aplicación. Consulta en tu proveedor servidor, puerto y tipo TLS: 465 suele usar SSL y 587 STARTTLS. Si tu cuenta exige exclusivamente OAuth, usa un servicio SMTP compatible; no desactives TLS. No hace falta otro contenedor.

Con [Resend SMTP](https://resend.com/docs/send-with-smtp), usa servidor smtp.resend.com, TLS ssl, puerto 465, usuario resend y tu API key como contraseña. El remitente debe pertenecer a tu dominio verificado en Resend. Introduce la API key únicamente en configure, nunca en comandos, archivos públicos o el chat. Comprueba la entrega real antes de activar el timer. No necesitas integrar la API HTTP.

## 1. Instalar el monitor

En Ubuntu por SSH, después de transferir este repositorio a ~/nube-instalacion:

```bash
cd "$HOME/nube-instalacion"
python3 -m py_compile scripts/cloud-space
sudo install -m 0755 scripts/cloud-space /usr/local/sbin/cloud-space
sudo install -m 0644 systemd/cloud-space.service systemd/cloud-space.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemd-analyze verify /etc/systemd/system/cloud-space.service /etc/systemd/system/cloud-space.timer
```

## 2. Introducir tus datos de correo

```bash
sudo /usr/local/sbin/cloud-space configure
```

Responde, en orden: servidor SMTP, ssl o starttls, puerto, usuario, remitente autorizado, destinatario y contraseña SMTP/de aplicación. La contraseña no aparece al teclear. La configuración queda en /etc/homelab/space-mail.json, solo legible por root; no la copies a GitHub.

```bash
sudo /usr/local/sbin/cloud-space test-mail
```

Espera el mensaje de aceptación SMTP y comprueba que recibes el correo, incluida la carpeta spam. Aceptación por SMTP no equivale a entrega en bandeja. Si falla, revisa datos/proveedor con sudoedit /etc/homelab/space-mail.json y repite la prueba antes de activar el timer.

## 3. Probar umbrales sin llenar discos

Cada comando envía un correo marcado SIMULACION y no modifica el estado del monitor:

```bash
sudo /usr/local/sbin/cloud-space simulate --percent 75
sudo /usr/local/sbin/cloud-space simulate --percent 85
sudo /usr/local/sbin/cloud-space simulate --percent 90
sudo /usr/local/sbin/cloud-space simulate --percent 60
```

Confirma cuatro correos con niveles 75, 85, 90 y 0. El comportamiento de escalada, recuperación, repetición y fallo de entrega se puede comprobar sin SMTP real con la prueba automatizada:

```bash
python3 "$HOME/nube-instalacion/tests/operations.py"
```

## 4. Activar las mediciones reales

```bash
sudo /usr/local/sbin/cloud-space check
sudo systemctl enable --now cloud-space.timer
systemctl list-timers cloud-space.timer --no-pager
```

La salida manual muestra SSD y, si es válido, USB. El externo se mide solo si pasa cloud-storage-check; si falta, no se confunde su carpeta con el SSD ni se envía alarma de ocupación por su ausencia deliberada. El estado se guarda en /var/lib/cloud-space/state.json. Un fallo SMTP no guarda el aviso como enviado y se reintenta en la próxima medición.

Consultar ejecución y fallos:

```bash
sudo systemctl status cloud-space.timer cloud-space.service --no-pager
sudo journalctl -u cloud-space.service -n 50 --no-pager
```

Un servicio oneshot puede estar inactive tras acabar correctamente. Para comprobar el canal periódicamente repite test-mail: si servidor, red o proveedor fallan no puede garantizarse un correo. El monitor no borra archivos ni impide llenar el disco; una carga grande puede superar varios umbrales entre mediciones.

## 5. Consultar consumo y desactivar

```bash
sudo /usr/local/sbin/cloud-storage-check && df -hT / /srv/storage
sudo du -xhd1 /srv/appdata
sudo /usr/local/sbin/cloud-storage-check && sudo du -xhd1 /srv/storage
```

Para detener solo las notificaciones:

```bash
sudo systemctl disable --now cloud-space.timer
```

En la variante solo SSD, mide únicamente /; este monitor está diseñado para la instalación con externo del tutorial. No lo actives con el comprobador sustituido de la variante, que aceptaría la carpeta del SSD como USB.

Referencias: [SMTP en Python](https://docs.python.org/3/library/smtplib.html), [temporizadores systemd](https://www.freedesktop.org/software/systemd/man/latest/systemd.timer.html). [Volver al índice](README.md).
