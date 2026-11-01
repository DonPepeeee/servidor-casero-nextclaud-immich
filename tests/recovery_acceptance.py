#!/usr/bin/env python3
"""Ensayo autorizado sobre /srv/cloud-restore.*. Inicia solo la restauracion.

Uso: sudo python3 recovery_acceptance.py /srv/cloud-restore.ID
Antes de ejecutarlo, el origen debe permanecer bloqueado y parado.
No sustituye comprobacion visual y descarga desde los clientes.
"""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time


def run(args, **kwargs):
    return subprocess.run([str(a) for a in args], check=True, **kwargs)


def out(args):
    return run(args, capture_output=True, text=True).stdout.strip()


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def sample(roots):
    result = {}
    for root in roots:
        if not root.is_dir():
            continue
        count = 0
        for parent, dirs, files in os.walk(root):
            dirs.sort()
            for name in sorted(files):
                path = Path(parent) / name
                if path.is_symlink() or name.startswith('.') or path.stat().st_size > 64 * 1024**2:
                    continue
                result[str(path)] = digest(path)
                count += 1
                if count >= 10:
                    break
            if count >= 10:
                break
    return result


def main():
    assert os.geteuid() == 0 and len(sys.argv) == 2, 'Usar sudo y la ruta de ensayo.'
    os.umask(0o077)
    dest = Path(sys.argv[1]).resolve(strict=True)
    assert dest.parent == Path('/srv') and dest.name.startswith('cloud-restore.')
    point = Path((dest / 'SOURCE_POINT').read_text().strip()).resolve(strict=True)
    assert Path('/etc/homelab/recovery-maintenance').read_text().strip() == str(point)
    assert not (dest / 'originals-before.json').exists(), 'Ya hay ensayo previo; no repetir a ciegas.'
    for prefix in ('mb', 'cloud'):
        for app in ('nextcloud', 'immich'):
            assert not out(['docker', 'ps', '-q', '--filter',
                            f'label=com.docker.compose.project={prefix}-{app}']), 'Origen activo.'
    print('Ocupacion del PUNTO NUEVO:', flush=True)
    run(['du', '-sh', point])
    print('Ocupacion TOTAL de recovery (incluye ensayos anteriores):', flush=True)
    run(['du', '-sh', '/srv/storage/recovery'])
    roots = list(Path('/srv/storage/nextcloud/data').glob('*/files'))
    roots += [Path('/srv/storage/immich/media/upload'), Path('/srv/storage/immich/media/library')]
    before = sample(roots)
    assert before, 'No se encontraron originales para la muestra; revisar antes de iniciar.'
    (dest / 'originals-before.json').write_text(json.dumps(before, indent=2) + '\n')
    print(f'Hashes previos guardados: {len(before)} originales; no se copian sus contenidos.', flush=True)
    portable = (dest / 'PORTABLE').exists()
    if portable:
        for app in ('nextcloud', 'immich'):
            run(['docker', 'compose', '--project-name', f'cloud-restore-{app}',
                 '--file', dest / f'{app}.compose.json', 'up', '-d'])
    else:
        run(['systemctl', 'start', 'cloud-restore@nextcloud.service', 'cloud-restore@immich.service'])
    deadline = time.monotonic() + 300
    containers = []
    while time.monotonic() < deadline:
        ids = []
        for app in ('nextcloud', 'immich'):
            ids += out(['docker', 'ps', '-aq', '--filter',
                        f'label=com.docker.compose.project=cloud-restore-{app}']).split()
        if len(ids) == 8:
            containers = json.loads(out(['docker', 'inspect', *ids]))
            ready = all(c['State']['Running'] and
                        (c['Config']['Labels']['com.docker.compose.service'] == 'cron'
                         or c['State'].get('Health', {}).get('Status') == 'healthy') for c in containers)
            if ready:
                break
        print('Esperando salud de los ocho contenedores...', flush=True)
        time.sleep(15)
    else:
        raise RuntimeError('Salud no alcanzada en 5 minutos; conservar estado y revisar registros.')
    for c in containers:
        assert not c['State']['OOMKilled'], 'Contenedor con OOM.'
        for mount in c['Mounts']:
            if mount['Type'] == 'bind':
                source = mount['Source']
                if not portable:
                    assert source.startswith((str(dest / 'appdata') + '/', '/srv/storage/')), 'Dependencia del SSD antiguo.'
    print('Ocho contenedores: siete healthy y cron Up; montajes del ensayo comprobados.', flush=True)
    for name, expected in before.items():
        assert digest(Path(name)) == expected, 'Un original de muestra ha cambiado.'
    print(f'Hashes posteriores: {len(before)} originales intactos.', flush=True)
    nc = ['docker', 'compose', '--project-name', 'cloud-restore-nextcloud', '--file', dest / 'nextcloud.compose.json']
    status = out(nc + ['exec', '-T', '--user', 'www-data', 'app', 'php', 'occ', 'status', '--output=json'])
    parsed = json.loads(status)
    assert parsed['installed'] and not parsed['maintenance'] and not parsed['needsDbUpgrade']
    users = json.loads(out(nc + ['exec', '-T', '--user', 'www-data', 'app', 'php', 'occ', 'user:list', '--output=json']))
    print(f'Nextcloud instalado, sin migracion pendiente; cuentas recuperadas: {len(users)}.', flush=True)
    im = ['docker', 'compose', '--project-name', 'cloud-restore-immich', '--file', dest / 'immich.compose.json',
          'exec', '-T', 'database', 'psql', '-U', 'postgres', '-d', 'immich', '-At', '-c']
    tables = out(im + ["SELECT tablename FROM pg_tables WHERE schemaname='public' AND tablename IN ('asset','user','album')"]).splitlines()
    assert 'asset' in tables, 'No aparece la tabla de recursos Immich.'
    counts = {table: int(out(im + [f'SELECT count(*) FROM public."{table}"'])) for table in tables}
    print('Recuentos recuperados Immich: ' + json.dumps(counts), flush=True)
    report = dict(point=str(point), sample_files=len(before), original_hashes_ok=True,
                  containers_healthy=7, cron_running=True, nextcloud_users=len(users), immich_counts=counts,
                  browser_validation='pending', clean_host_restore='pending')
    (dest / 'acceptance.json').write_text(json.dumps(report, indent=2) + '\n')
    print('PRUEBA TECNICA OK. Pendiente abrir ambas webs y descargar originales desde clientes.', flush=True)
    print('Origen sigue bloqueado. No quitar el mantenimiento ni volver a su base antigua.', flush=True)


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        print(f'ERROR DE VALIDACION: {exc}. No reanudar el origen; revisar.', file=sys.stderr)
        sys.exit(1)
