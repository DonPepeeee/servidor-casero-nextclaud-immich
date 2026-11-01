# Batería del portátil: recovery y apagado

Ampliación opcional para la instalación normal cloud con externo. El código tiene pruebas simuladas; antes de depender de él hay que probar alimentación, tiempo de copia, apagado y retorno en el equipo real. No instalar en una restauración cloud-restore ni en la variante solo SSD.

## Alimentación necesaria

Si el externo usa enchufe, la batería del portátil no lo mantiene encendido. Necesitas un SAI que alimente el externo y, para conservar la red y recibir correo, router/ONT y demás elementos de red necesarios. El disco debe permanecer alimentado durante toda la copia y el apagado. Si se corta antes, puede perderse el punto nuevo y dañarse el sistema de archivos.

Este monitor lee la batería interna y el adaptador Mains del portátil; no lee un SAI. Para detectar el corte con este diseño, el cargador del portátil debe quedar fuera del SAI: al cortarse la luz, pasa a su batería interna mientras el externo sigue alimentado por el SAI. Si también conectas el cargador al SAI, el monitor no verá el corte hasta que se agote: necesitas otra integración con el SAI (por ejemplo NUT), no este procedimiento sin cambios. No se presupone compatibilidad de un modelo de SAI concreto.

## 1. Diagnóstico y copia manual

Primero configura y prueba [los avisos de ocupación](avisos-ocupacion.md), que también proporcionan el canal SMTP. Luego, en MobaXterm:

```bash
ls /sys/class/power_supply/
for fuente in /sys/class/power_supply/*; do
  [ -d "$fuente" ] || continue
  printf '\n%s\n' "$fuente"
  for dato in type status capacity online energy_now energy_full energy_full_design power_now; do
    if [ -r "$fuente/$dato" ]; then
      printf '%s: ' "$dato"
      cat "$fuente/$dato"
    fi
  done
done
systemd-inhibit --list
```

Pausa clientes y mide una copia real, conectado a corriente:

```bash
time sudo /usr/local/sbin/cloud-recovery backup-and-resume
```

Verifica el punto con el anexo de recuperación. Mide autonomía con el externo mantenido por el SAI y carga representativa; no agotes la batería. El porcentaje no equivale a minutos. Revisa políticas de tapa, suspensión y batería crítica: ninguna debe suspender el servidor antes de terminar. El monitor no las cambia.

El job permite como máximo 10 minutos entre comprobación y copia; después cancela todo su grupo de procesos e intenta apagar igualmente. El umbral debe dejar margen para esos 10 minutos, el aviso, el apagado de Docker y del sistema y degradación de batería, tanto en el portátil como en el SAI. Si la copia tarda más, adapta el límite y vuelve a medir. No existe un umbral universal de 10 %, 20 % o 30 % seguro.

## 2. Instalar sin activar

```bash
cd "$HOME/nube-instalacion"
sudo install -m 0755 scripts/cloud-battery scripts/cloud-space scripts/cloud-recovery /usr/local/sbin/
sudo install -m 0644 systemd/cloud-battery.service systemd/cloud-battery.timer systemd/cloud-battery-shutdown.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemd-analyze verify /etc/systemd/system/cloud-battery.service /etc/systemd/system/cloud-battery.timer /etc/systemd/system/cloud-battery-shutdown.service
sudo /usr/local/sbin/cloud-battery status
sudoedit /etc/homelab/battery.json
```

Guarda este JSON. 50 es solo ejemplo para simulación; sustituye el umbral tras medir. Mantén external_power_confirmed en false hasta comprobar físicamente el SAI y la alimentación del externo:

```json
{
  "shutdown_percent": 50,
  "external_power_confirmed": false
}
```

```bash
sudo chmod 0600 /etc/homelab/battery.json
sudo /usr/local/sbin/cloud-battery simulate --percent 80
sudo /usr/local/sbin/cloud-battery simulate --percent 40
python3 "$HOME/nube-instalacion/tests/battery.py"
```

Simulate no envía correo, no copia y no apaga. Con umbral 50 muestra apagado solo para 40 y sin corriente. Si la lectura de batería/adaptador no es válida, el monitor falla y deja error en journal: no presupone un porcentaje ni garantiza protección.

## 3. Prueba real y activación

Solo tras verificar alimentación/autonomía, configura el umbral medido y external_power_confirmed en true. Para una primera prueba supervisada, con datos de prueba y clientes pausados, corta únicamente la corriente del cargador del portátil, manteniendo el externo y la red protegidos. Ejecuta check antes de activar el timer: puede iniciar el apagado si la batería está bajo el umbral. Para ensayar sin descargarla del todo puedes usar temporalmente un umbral superior a la carga actual (máximo 95), restaurando el umbral medido antes de la activación habitual.

```bash
sudo /usr/local/sbin/cloud-battery check
```

Esperado bajo el umbral y sin corriente: aviso de batería baja, parada/copia fría, registro de resultado e intento de apagado ordenado. Si falla la copia, el disco falta, existe mantenimiento o se supera el tiempo, también intenta apagar: no declara una copia válida por haber apagado. El bloqueo de recovery evita dos copias simultáneas; durante esta prueba no ejecutes copias ni despliegues manuales. La pérdida de red/SMTP no impide la acción local; los avisos pueden no llegar durante el corte.

No inicies cloud-battery-shutdown.service para consultar su estado: iniciarlo o detenerlo durante una copia provoca un intento de apagado. No lo habilites al arranque.

Al volver la luz, conecta el cargador, enciende y revisa:

```bash
sudo journalctl -b -1 -u cloud-battery.service -u cloud-battery-shutdown.service --no-pager
sudo cat /etc/homelab/recovery-maintenance
```

Para conservar el registro entre arranques, configura antes journald persistente si tu sistema no lo usa (Storage=persistent en un drop-in de journald.conf; reinicia systemd-journald y ejecuta journalctl --flush). Si no hay marcador, la copia pudo fallar antes de detener aplicaciones: revisa logs y salud. Si hay marcador, verifica la ruta guardada con cloud-recovery verify. Solo un punto completo aceptado sirve para reanudar mediante cloud-recovery resume-source. No borres bloqueos ni uses un .partial para reanudar. La nube queda bloqueada después de la copia incluso tras reiniciar, hasta esa revisión manual.

Tras superar la prueba real, activa:

```bash
sudo systemctl enable --now cloud-battery.timer
systemctl list-timers cloud-battery.timer --no-pager
sudo journalctl -u cloud-battery.service -n 30 --no-pager
```

Para desactivar el monitor sin iniciar otro apagado:

```bash
sudo systemctl disable --now cloud-battery.timer
```

Este job no sustituye las copias periódicas: el SSD puede fallar con corriente presente. No hay retención/borrado automático. La recuperación contiene secretos y no incluye configuración Wi-Fi, identidad Tailscale, SMTP o todo el sistema operativo: estos se reconstruyen aparte. Conserva otra copia independiente de los originales.

Referencias: [alimentación sysfs del kernel](https://www.kernel.org/doc/Documentation/ABI/testing/sysfs-class-power), [servicios y límites systemd](https://www.freedesktop.org/software/systemd/man/latest/systemd.service.html). [Volver al índice](README.md).
