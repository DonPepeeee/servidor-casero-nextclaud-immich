# Pruebas sin privilegios sobre archivos temporales; ejecutar con Python 3 en Linux.
import importlib.machinery, importlib.util, pathlib, tempfile, tarfile, io, json
script = pathlib.Path(__file__).resolve().parents[1] / "scripts/cloud-recovery"
loader=importlib.machinery.SourceFileLoader("recovery", str(script))
spec=importlib.util.spec_from_loader(loader.name,loader)
m=importlib.util.module_from_spec(spec);loader.exec_module(m)
with tempfile.TemporaryDirectory() as tmp:
 p=pathlib.Path(tmp)
 def archive(name, member):
  with tarfile.open(p/name,"w:gz") as t:
   info=tarfile.TarInfo(member);data=b"test";info.size=len(data);t.addfile(info,io.BytesIO(data))
 archive("state.tar.gz","nextcloud/html/config/config.php")
 archive("projects.tar.gz","nextcloud/.env")
 (p/"manifest.json").write_text(json.dumps(dict(format=m.FORMAT,originals_copied=False,state_paths=["nextcloud/html"])))
 for app in m.APPS:(p/f"{app}.compose.json").write_text("{}")
 names=["state.tar.gz","projects.tar.gz","manifest.json","nextcloud.compose.json","immich.compose.json"]
 def sums():(p/"checksums.json").write_text(json.dumps({n:m.sha(p/n) for n in names}))
 (p/"COMPLETE").write_text(m.FORMAT);sums();m.verify(p)
 print("OK: paquete de estado sin originales aceptado")
 (p/"nextcloud.compose.json").write_text("alterado")
 try:m.verify(p)
 except RuntimeError:print("OK: checksum corrupto rechazado")
 else:raise AssertionError("No rechazo corrupcion")
 for path in ["/etc/passwd","../escape","immich/media/foto.jpg"]:
  archive("state.tar.gz",path);sums()
  try:m.verify(p)
  except RuntimeError:print("OK: ruta fuera de inventario rechazada")
  else:raise AssertionError("No rechazo ruta")
print("Pruebas de integridad/inventario completadas, sin usar Docker ni datos del servidor.")
