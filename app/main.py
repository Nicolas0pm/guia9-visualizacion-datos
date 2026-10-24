"""Visualizador de Encuestas — aplicación de escritorio portable (Guía 9, FASE 2).

Permite ingresar los datos de la encuesta, validarlos, guardarlos y generar los gráficos de forma
automática. Se empaqueta con PyInstaller en un solo .exe que no necesita instalación ni Python.

Desarrollo:   python app/main.py
Opciones:     --db RUTA            usa otra base de datos (por defecto datos/encuesta.db junto al programa)
              --captura RUTA.png   abre la ventana, guarda una captura y se cierra (para la documentación)
              --tipo N             tipo de gráfico inicial (0 a 4), útil junto con --captura
              --historial          abre en la pestaña de historial, útil junto con --captura
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path


def carpeta_programa() -> Path:
    """Carpeta del .exe (en la USB) o del proyecto en desarrollo."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent


def ruta_base_datos() -> Path:
    """datos/encuesta.db junto al programa; si esa carpeta es de solo lectura, en Documentos del usuario."""
    preferida = carpeta_programa() / "datos"
    try:
        preferida.mkdir(parents=True, exist_ok=True)
        prueba = preferida / ".escritura"
        prueba.write_text("ok", encoding="utf-8")
        prueba.unlink()
        return preferida / "encuesta.db"
    except OSError:
        respaldo = Path.home() / "Documents" / "VisualizadorEncuestas"
        respaldo.mkdir(parents=True, exist_ok=True)
        return respaldo / "encuesta.db"


def main(argv: list[str] | None = None) -> int:
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from almacen import Almacen
    from graficos import TIPOS
    from interfaz import Aplicacion

    p = argparse.ArgumentParser(description="Visualizador de Encuestas")
    p.add_argument("--db", type=Path)
    p.add_argument("--captura", type=Path)
    p.add_argument("--tipo", type=int, default=0, choices=range(len(TIPOS)))
    p.add_argument("--historial", action="store_true")
    args = p.parse_args(argv)

    app = Aplicacion(Almacen(args.db or ruta_base_datos()))
    app.v_tipo.set(TIPOS[args.tipo])
    app.redibujar()
    if args.historial:
        app.pestanas.select(1)
    if args.captura:
        app.after(2500, lambda: _capturar(app, args.captura))
    app.mainloop()
    return 0


def _capturar(app, ruta: Path) -> None:
    """Guarda una imagen de la ventana tal como se ve (usa PIL, que ya viene con matplotlib)."""
    from PIL import ImageGrab
    app.update()
    x, y = app.winfo_rootx(), app.winfo_rooty()
    ImageGrab.grab(bbox=(x, y, x + app.winfo_width(), y + app.winfo_height())).save(ruta)
    app.salir()


if __name__ == "__main__":
    sys.exit(main())
