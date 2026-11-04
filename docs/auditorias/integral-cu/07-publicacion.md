# Publicación exclusiva de la revisión

Rama en todos los repositorios modificados: `review/auditoria-integral-cu`. No se hicieron PR, merges, force-push, despliegues ni cambios a develop/main/test/navegador-optativos. Las ramas originales y el estado precargado se conservaron.

| Repositorio | Base exacta | Commit de revisión publicado | Cambios |
|---|---|---|---|
| Backend | `bf4da61134e2c04db66f0e21bb99167dfb49306e` | `5fbefe199f175b441f854e02152798a21b85b340` | Un archivo nuevo de prueba H01; ningún producto/contrato/migración/lock |
| Frontend | `1ca0172bec203af3fa860b34925e4562ec11ee44` | `9c07de423f94e6dc0ba1f9538bdbd913b418c287` | Un archivo nuevo de prueba H02; ningún producto/diseño/contrato |
| Mobile | `74a25f1b5b18c7dfc006cf7df747d73b0ec4910a` | Mismo SHA | Sin cambios ni rama nueva |
| Principal | `13aefdb15d0f4d00cd870220e961717dcb48a1fd` | SHA final con `git rev-parse HEAD` en esta rama | Documentación, helpers de revisión y gitlinks de las dos pruebas |

Los submódulos se publicaron primero y se comprobó que la rama remota propia no existía antes de crearla. Los únicos cambios de hijos respecto de las bases son adiciones de pruebas; ambos permanecen deliberadamente rojos para sus defectos. El manifiesto Cloud histórico no se cambió ni se usó como base.

## Verificación remota reproducible

```bash
git clone --no-local --depth 1 --branch review/auditoria-integral-cu --recurse-submodules --shallow-submodules https://github.com/NexoRuta/NexoRuta.git NexoRuta-auditoria-limpia
cd NexoRuta-auditoria-limpia
git status --porcelain
git ls-tree HEAD backend frontend mobile
git submodule status
git -C backend status --porcelain
git -C frontend status --porcelain
git -C mobile status --porcelain
```

No copiar `.local`, `.env`, bases, node_modules, bin/obj, claves ni carpetas de submódulos de otro checkout. Deben obtenerse los tres objetos desde sus remotos. La comprobación observada del clon y del último commit documental se registra a continuación al terminar la publicación.
