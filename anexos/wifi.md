# Wi-Fi desde MobaXterm

Para Ubuntu Server con Netplan y systemd-networkd. Mantén Ethernet conectado durante el cambio. La tarjeta Wi-Fi tiene una MAC diferente de Ethernet: la reserva DHCP del router debe usar la de Wi-Fi. No reserves la misma IP simultáneamente a ambas tarjetas activas; usa otra IP para la prueba y libera la anterior si quieres reutilizarla al retirar Ethernet.

## 1. Identificar sin cambiar la red

En la sesión SSH de MobaXterm:

```bash
ip -br link
ip -br address
systemctl is-active systemd-networkd NetworkManager
ls /etc/netplan/
```

Identifica la interfaz Wi-Fi (habitualmente wlp...). Si no aparece ninguna, revisa adaptador, bloqueo y controlador antes de configurar. Si NetworkManager está activo o ya hay una sección wifis para esa tarjeta, adapta su configuración existente: no apliques otra definición superpuesta. No pegues salidas de netplan get ni archivos YAML con contraseñas en chats.

Sustituye wlp2s0 por tu interfaz para leer la MAC que debes reservar en el router:

```bash
cat /sys/class/net/wlp2s0/address
```

## 2. Añadir solo Wi-Fi

Para networkd, instala el soporte Wi-Fi y conserva una copia de Netplan solo en el servidor:

```bash
sudo apt update
sudo apt install wpasupplicant iw rfkill
rfkill list
sudo install -d -m 0700 /root/netplan-backups
sudo cp -a /etc/netplan "/root/netplan-backups/netplan.$(date +%Y%m%d-%H%M%S)"
sudo test -e /etc/netplan/90-home-wifi.yaml || sudo install -m 0600 /dev/null /etc/netplan/90-home-wifi.yaml
sudoedit /etc/netplan/90-home-wifi.yaml
```

Si ese archivo ya existía, no ejecutes install: edítalo conservando su contenido. Si rfkill indica bloqueo físico, desbloquéalo físicamente; si solo es lógico usa sudo rfkill unblock wifi.

Introduce esta configuración, sustituyendo interfaz, SSID y contraseña. Usa espacios, no tabuladores. En cadenas con comillas simples, una comilla simple dentro del valor se escribe dos veces. Esta configuración es para una red doméstica WPA Personal compatible con wpa_supplicant; no para autenticación empresarial.

```yaml
network:
  version: 2
  wifis:
    wlp2s0:
      renderer: networkd
      optional: true
      dhcp4: true
      dhcp-identifier: mac
      dhcp4-overrides:
        route-metric: 600
      access-points:
        'NOMBRE_DE_TU_WIFI':
          password: 'CONTRASENA_DE_TU_WIFI'
```

La métrica alta favorece Ethernet si su ruta tiene menor métrica. El router asigna la dirección por DHCP; aquí no se fija otra IP. La contraseña queda en el YAML protegido del servidor, nunca en el repositorio.

## 3. Probar antes de retirar Ethernet

```bash
sudo netplan generate
sudo netplan try --timeout 120
```

Mientras espera confirmación, abre una segunda sesión MobaXterm por la IP Wi-Fi y comprueba que responde. Si todo está bien, confirma en la primera sesión antes del plazo. Si se pierde acceso, deja expirar el intento; desde consola revisa la restauración y el YAML antes de reiniciar. Un try revertido no garantiza que el archivo editado quede retirado del disco.

```bash
ip -br address
ip route
iw dev wlp2s0 link
tailscale status
```

Con sesión Wi-Fi abierta y acceso físico disponible, retira Ethernet y comprueba acceso a Internet, SSH y ambas webs. Después reinicia con el cable retirado y repite las comprobaciones. Tailscale Serve conserva su dominio. No cambies a la vez Netplan, las URLs y Docker.

Referencia: [ejemplos oficiales Netplan](https://netplan.readthedocs.io/en/stable/examples/). [Volver al índice](README.md).
