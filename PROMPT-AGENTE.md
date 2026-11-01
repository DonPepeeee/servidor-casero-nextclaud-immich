# Monta mi nube casera por SSH

Este archivo es un prompt reutilizable para un agente con terminal y capacidad de ejecutar SSH. Se utiliza **después de instalar Ubuntu Server, activar OpenSSH y comprobar la conexión desde MobaXterm**. La instalación del sistema, la conexión de cables y la configuración del router siguen siendo tareas físicas/manuales.

MobaXterm es tu cliente SSH/SFTP. Abrir una sesión allí no da al agente acceso automático a esa ventana ni a sus credenciales: el agente necesita su propia conexión desde el entorno donde ejecuta comandos. Si trabaja en un entorno remoto sin acceso a tu LAN, debe resolver contigo esa conectividad o ejecutarse en un equipo de tu red; nunca abrir el puerto 22 del router para solucionar esto.


## Preparación del usuario

1. Tener Ubuntu instalado en el SSD, OpenSSH activo, usuario con sudo y reserva DHCP local.
2. Verificar desde MobaXterm que el equipo responde y que su huella coincide con la mostrada en su consola física mediante `sudo ssh-keygen -lf /etc/ssh/ssh_host_ed25519_key.pub`.
3. Dar al agente acceso a **esta carpeta completa**, descargada del repositorio. Puede estar en su equipo local o ya subida por SFTP a `~/nube-instalacion` del servidor.
4. Preparar autenticación SSH en el entorno del agente: clave ya autorizada o entrada interactiva privada que soporte su herramienta. Una clave configurada solo en MobaXterm puede no estar disponible para OpenSSH. No pegar contraseñas ni claves privadas en el chat, en este archivo o en el repositorio.
5. Copiar el bloque siguiente en el agente y completar solo los datos no secretos. No es necesario instalar un agente en Ubuntu.

## Prompt para copiar

```text
Quiero que instales mi nube casera de Nextcloud e Immich siguiendo este repositorio. Ejecuta tú los pasos por SSH; no te limites a darme comandos para copiar. Soy responsable de la instalación física previa y de las acciones que requieran mi intervención.

DATOS NO SECRETOS
- Servidor/IP o alias SSH: <COMPLETAR>
- Usuario Ubuntu: <COMPLETAR>
- Puerto SSH: <22 u otro configurado>
- Huella de host verificada por mí: <SHA256:...>
- Autenticación disponible en tu entorno: <clave autorizada / entrada interactiva privada>
- Ruta local de esta carpeta del repositorio, si la tienes: <COMPLETAR o no disponible>
- Ruta remota de los archivos, si ya los subí: <~/nube-instalacion o no subidos>
- Referencia/commit del repositorio, si se conoce: <COMPLETAR o desconocido>
- Variante: <disco externo / solo SSD>
- Disco externo candidato por /dev/disk/by-id/: <COMPLETAR o identificar juntos>
- Autorización para borrar ese disco: NO, salvo confirmación expresa posterior sobre el dispositivo identificado.
- Interrupciones/reinicios: puedes reiniciar el servidor durante esta instalación nueva, avisando antes y reconectando después.

OBJETIVO Y FUENTE DE VERDAD
Lee primero README.md, ambos compose.yaml, scripts/, systemd/ y el índice anexos/README.md. Si elijo solo SSD, lee anexos/solo-ssd.md y aplica sus sustituciones completas. Lee anexos/recuperacion.md antes de proponer cualquier prueba de recuperación.

Trabaja sobre estos archivos, con sus versiones fijadas. No inventes Dockerfiles: se utilizan imágenes distribuidas por los proyectos. No cambies imágenes por latest, no conviertas esto en una actualización y no añadas servicios ajenos al tutorial. Instala anexos solo cuando los solicite; sigue sus comandos y pruebas, incluyendo las entradas privadas de SMTP cuando corresponda. Si una versión ya no está disponible o es incompatible, documenta el bloqueo y el cambio concreto necesario antes de adaptar el despliegue.

Esta es una instalación nueva. No apliques el recorrido sobre una nube existente ni sobre un servidor con otra instalación. Antes de escribir inspecciona host, discos, montajes, /etc/fstab, /etc/homelab, /opt/homelab, /srv/appdata, /srv/storage, contenedores y unidades cloud*, mb-* o de restauración. Si hay datos, proyectos, montajes o marcadores de mantenimiento previos, detén solo los pasos afectados y explica lo encontrado. No borres ni inicialices para dejar el equipo aparentemente limpio.

CONEXIÓN SSH
1. Comprueba desde TU terminal si tienes ssh disponible (por ejemplo ssh -V). No presupongas que puedes usar la sesión ya abierta en MobaXterm.
2. Con los datos reales, conecta con:
   ssh -p <PUERTO> <USUARIO>@<HOST>
   Si ya existe un alias configurado y verificado, puedes usar ssh <ALIAS>.
3. Compara la huella con la proporcionada antes de aceptar una primera conexión. Si cambia, detente y compruébala conmigo. No desactives StrictHostKeyChecking ni uses un known_hosts vacío para eludirlo.
4. No escribas contraseñas en argumentos, scripts, logs o chat. No uses sshpass, no leas claves privadas ni exportes credenciales de MobaXterm. Si no tienes un canal privado de autenticación, pídeme que configure una clave o el acceso interactivo compatible con tu entorno.
5. Confirma el destino con hostname, whoami, /etc/os-release y uname -m. Para una comprobación remota breve puedes usar:
   ssh -p <PUERTO> <USUARIO>@<HOST> 'hostname; whoami; uname -m'
   Los elementos entre <> son marcadores: sustitúyelos antes de ejecutar.
6. Comprueba sudo sin pedir ni imprimir la contraseña en el chat. Para pasos interactivos usa un terminal SSH persistente con PTY si tu herramienta lo permite (ssh -t ...). El permiso sudo de MobaXterm no se transfiere a tu conexión; tampoco presupongas que una validación sudo persiste entre conexiones separadas. Si mi intervención es necesaria, coordínala por el canal privado disponible. No habilites NOPASSWD general ni desactives autenticación.

MÉTODO DE EJECUCIÓN
- Empieza por un inventario de solo lectura y comunica variante, equipo y recorrido detectado; después ejecuta los pasos rutinarios ya autorizados sin pedir confirmación por cada bloque.
- Distingue siempre terminal local y terminal remota. Nunca ejecutes en mi PC los comandos de administración de Ubuntu.
- Transfiere los archivos, si hace falta, a ~/nube-instalacion mediante SFTP/SCP desde la copia local disponible. Verifica que dentro están README.md, nextcloud/, immich/, scripts/, systemd/ y, cuando corresponda, variantes/ y tests/. No inventes una URL pública si no se ha proporcionado. Conserva una copia de referencia antes de adaptar la variante solo SSD.
- Sigue el orden del README: herramientas/reinicio, Docker, externo/montaje (o sustitución SSD), instalación de archivos, Tailscale/HTTPS, preparación de proyectos, automatización, clientes y validación. Puedes transferir los archivos antes para leerlos.
- Ejecuta cada bloque por separado en Bash, preservando heredocs y variables; comprueba salida y código de retorno antes de seguir. No pegues toda la guía en una única ejecución. No repitas inicializaciones, formateos ni los bloques que añaden ajustes a .env.
- Antes de particionar/formatear, muestra modelo, tamaño, identificador estable y montajes; comprueba que no es el SSD del sistema ni tiene particiones montadas. Pide autorización explícita de borrado sobre ESE identificador. Conserva la confirmación interactiva del bloque del README; si tus herramientas no permiten realizarla conmigo, deja ese bloque para ejecución manual. No automatices el sí ni saltes la guardia. Si ya existe autorización inequívoca sobre ese mismo dispositivo en esta sesión, no la pidas de nuevo.
- En solo SSD omite por completo formateo externo, fstab USB y udev; aplica las sustituciones del anexo. No mezcles variantes.
- Revisa el instalador descargado de Tailscale antes de ejecutarlo. Déjame completar el login/autorización web y configurar los clientes. No solicites tokens en el chat. Mantén Serve privado, Funnel desactivado y puertos de aplicaciones en loopback. No abras puertos en el router.
- Los scripts generan secretos internos en el servidor. No muestres .env ni la salida completa de docker compose config; usa config --quiet. No incluyas secretos en informes. El cambio de contraseña web es interactivo; no uses la contraseña de la base para entrar en las aplicaciones.
- Si falla algo, conserva el estado y diagnostica con consultas acotadas. No uses docker compose down -v, podas, rm recursivo o recreación de bases como arreglo automático. No regeneres secretos existentes.
- Mantén un registro local sin secretos con fase, comando/bloque ejecutado, comprobación y siguiente paso. Tras una desconexión inspecciona el estado antes de reanudar. Un paso iniciado no equivale a completado.

INTERVENCIONES HUMANAS
Agrupa las solicitudes cuando sea posible: identificación/autorización del disco; login Tailscale y autorización HTTPS; contraseñas/cuentas web; instalación de clientes; muestra de archivos/fotos; apagar/encender y conectar el USB para las pruebas. Explica qué hago y qué comprobarás tú después. Si no puedes verificar una acción de móvil o navegador, espera mi resultado y márcalo como confirmado por mí, no como observado por ti.

ACEPTACIÓN
No declares éxito solo porque compose terminó sin error. Comprueba y registra:
1. Disco y rutas correctos para la variante, permisos y comprobación de lectura/escritura del README.
2. Ocho contenedores: siete healthy y cron Up tras inicializar; ninguna base en reinicio continuo.
3. Serve ofrece las dos URLs HTTPS privadas; Nextcloud usa 443 e Immich 8443. Incluye las URLs en el informe privado del usuario, sin credenciales.
4. Nextcloud: cuenta normal, archivo de prueba subido y descargado, cliente Windows/móvil. Cuando tengas ambos archivos compara SHA-256.
5. Immich: cuenta, fotos y vídeo de prueba, galería y descarga de original; no confundas una miniatura con el original.
6. Acceso móvil con Wi-Fi apagado y Tailscale conectado, confirmado por el usuario.
7. Extracción segura y reconexión del paso 12, con apagado completo; reinicio con disco conectado; para externo, prueba adicional de encender sin disco y conectarlo después, siguiendo el README. Nunca tirar del USB mientras esté en uso.
8. No más de una instalación escribiendo sobre los mismos originales.

RECUPERACIÓN Y CIERRE
Lee el estado del anexo, separa instalación operativa de recuperación validada y explica que recovery en el mismo externo no protege ante pérdida del externo. backup deja servicios detenidos y una guardia persistente. backup-and-resume crea una copia y reanuda únicamente el origen normal; úsalo solo si solicito esa operación y no hay una restauración abierta.

Coordina conmigo la prueba de recuperación y su interrupción antes de ejecutarla. Sigue el anexo para reanudar un origen sin restauración, o para usar el estado recuperado. No retires bloqueos por tu cuenta ni arranques bases anteriores después de escrituras en una restauración.

Termina con un informe breve: fases completadas, comprobaciones observadas, confirmaciones del usuario, pendientes/bloqueos, URLs privadas, rutas de configuración sin secretos y forma de apagar ordenadamente. Si falta mi intervención, indica el siguiente paso concreto. No digas que el montaje está terminado si quedan verificaciones necesarias.
```

## Referencias de conexión

La sintaxis de conexión y ejecución remota se apoya en [OpenSSH](https://man.openbsd.org/ssh) y en el [cliente SSH de Windows](https://learn.microsoft.com/en-us/windows/terminal/tutorials/ssh). Consultadas el 30 de octubre de 2026; describen la conexión, no garantizan que la herramienta concreta del agente admita entrada interactiva ni que alcance tu red.
