"""Almacenamiento de la encuesta en SQLite.

La base es un solo archivo (encuesta.db) que queda en la carpeta datos/ junto al ejecutable, así el
programa sigue siendo portable: se copia la carpeta a otro equipo o a una USB y los datos viajan con ella.

Cada cambio queda en la tabla historial con el valor anterior y el nuevo. Además cada categoría guarda
su cantidad original de la guía, de modo que siempre se puede comparar con los datos de partida
(trazabilidad) o restaurarlos.
"""
from __future__ import annotations

import csv
import io
import sqlite3
from datetime import datetime
from pathlib import Path

from modelo import (DATOS_ORIGINALES, MAX_CATEGORIAS, POBLACION_ORIGINAL, TITULO_ORIGINAL, Categoria,
                    ErrorValidacion, porcentaje, validar_cantidad, validar_coherencia, validar_nombre,
                    validar_poblacion, validar_titulo)

ESQUEMA = """
CREATE TABLE IF NOT EXISTS encuesta (
    id        INTEGER PRIMARY KEY CHECK (id = 1),
    titulo    TEXT    NOT NULL,
    poblacion INTEGER NOT NULL CHECK (poblacion > 0)
);
CREATE TABLE IF NOT EXISTS categoria (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre            TEXT    NOT NULL UNIQUE COLLATE NOCASE,
    cantidad          INTEGER NOT NULL CHECK (cantidad >= 0),
    cantidad_original INTEGER,
    origen            TEXT    NOT NULL CHECK (origen IN ('original', 'ingresado', 'importado')),
    creado            TEXT    NOT NULL,
    modificado        TEXT    NOT NULL
);
CREATE TABLE IF NOT EXISTS historial (
    id      INTEGER PRIMARY KEY AUTOINCREMENT,
    fecha   TEXT NOT NULL,
    accion  TEXT NOT NULL,
    detalle TEXT NOT NULL
);
"""


def ahora() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


class Almacen:
    """Repositorio de la encuesta. Valida cada operación antes de escribir y la registra en el historial."""

    def __init__(self, ruta: Path | str):
        self.ruta = Path(ruta) if ruta != ":memory:" else ruta
        if isinstance(self.ruta, Path):
            self.ruta.parent.mkdir(parents=True, exist_ok=True)
        self.con = sqlite3.connect(str(self.ruta))
        self.con.row_factory = sqlite3.Row
        self.con.executescript(ESQUEMA)
        if self.con.execute("SELECT COUNT(*) FROM encuesta").fetchone()[0] == 0:
            self._cargar_originales("Base de datos creada con los datos de la guía")

    def cerrar(self) -> None:
        self.con.close()

    # ---------- lectura ----------

    def titulo(self) -> str:
        return self.con.execute("SELECT titulo FROM encuesta WHERE id = 1").fetchone()[0]

    def poblacion(self) -> int:
        return self.con.execute("SELECT poblacion FROM encuesta WHERE id = 1").fetchone()[0]

    def categorias(self) -> list[Categoria]:
        """En el orden en que se ingresaron (el orden de la tabla de la guía)."""
        filas = self.con.execute(
            "SELECT id, nombre, cantidad, cantidad_original, origen FROM categoria ORDER BY id").fetchall()
        return [Categoria(**dict(f)) for f in filas]

    def suma(self, excepto_id: int | None = None) -> int:
        sql, args = "SELECT COALESCE(SUM(cantidad), 0) FROM categoria", ()
        if excepto_id is not None:
            sql, args = sql + " WHERE id <> ?", (excepto_id,)
        return self.con.execute(sql, args).fetchone()[0]

    def historial(self, limite: int = 500) -> list[sqlite3.Row]:
        return self.con.execute(
            "SELECT fecha, accion, detalle FROM historial ORDER BY id DESC LIMIT ?", (limite,)).fetchall()

    def _nombres(self) -> list[str]:
        return [f[0] for f in self.con.execute("SELECT nombre FROM categoria")]

    def _por_id(self, id_: int) -> Categoria:
        fila = self.con.execute(
            "SELECT id, nombre, cantidad, cantidad_original, origen FROM categoria WHERE id = ?", (id_,)).fetchone()
        if fila is None:
            raise ErrorValidacion("La actividad seleccionada ya no existe. Actualice la tabla.")
        return Categoria(**dict(fila))

    # ---------- escritura ----------

    def _registrar(self, accion: str, detalle: str) -> None:
        self.con.execute("INSERT INTO historial (fecha, accion, detalle) VALUES (?, ?, ?)",
                         (ahora(), accion, detalle))

    def agregar(self, nombre: str, cantidad, origen: str = "ingresado") -> Categoria:
        """Valida y guarda una actividad nueva. Devuelve la categoría creada."""
        if len(self._nombres()) >= MAX_CATEGORIAS:
            raise ErrorValidacion(f"Se admiten como máximo {MAX_CATEGORIAS} actividades para que el gráfico se lea bien.")
        nombre = validar_nombre(nombre, self._nombres())
        poblacion = self.poblacion()
        cantidad = validar_cantidad(cantidad, poblacion)
        validar_coherencia(self.suma() + cantidad, poblacion)
        with self.con:
            cur = self.con.execute(
                "INSERT INTO categoria (nombre, cantidad, cantidad_original, origen, creado, modificado) "
                "VALUES (?, ?, NULL, ?, ?, ?)", (nombre, cantidad, origen, ahora(), ahora()))
            self._registrar("Agregar", f"{nombre}: {cantidad} estudiantes")
        return self._por_id(cur.lastrowid)

    def actualizar(self, id_: int, nombre: str, cantidad) -> Categoria:
        actual = self._por_id(id_)
        nombre = validar_nombre(nombre, self._nombres(), ignorar=actual.nombre)
        poblacion = self.poblacion()
        cantidad = validar_cantidad(cantidad, poblacion)
        validar_coherencia(self.suma(excepto_id=id_) + cantidad, poblacion)
        if nombre == actual.nombre and cantidad == actual.cantidad:
            return actual
        with self.con:
            self.con.execute("UPDATE categoria SET nombre = ?, cantidad = ?, modificado = ? WHERE id = ?",
                             (nombre, cantidad, ahora(), id_))
            cambios = []
            if nombre != actual.nombre:
                cambios.append(f"nombre «{actual.nombre}» → «{nombre}»")
            if cantidad != actual.cantidad:
                cambios.append(f"estudiantes {actual.cantidad} → {cantidad}")
            self._registrar("Actualizar", f"{actual.nombre}: " + ", ".join(cambios))
        return self._por_id(id_)

    def eliminar(self, id_: int) -> None:
        actual = self._por_id(id_)
        with self.con:
            self.con.execute("DELETE FROM categoria WHERE id = ?", (id_,))
            self._registrar("Eliminar", f"{actual.nombre} ({actual.cantidad} estudiantes)")

    def configurar(self, titulo: str, poblacion) -> None:
        """Cambia título y población. La población no puede quedar por debajo de lo ya registrado."""
        titulo = validar_titulo(titulo)
        poblacion = validar_poblacion(poblacion, self.suma())
        antes_t, antes_p = self.titulo(), self.poblacion()
        if (titulo, poblacion) == (antes_t, antes_p):
            return
        with self.con:
            self.con.execute("UPDATE encuesta SET titulo = ?, poblacion = ? WHERE id = 1", (titulo, poblacion))
            cambios = []
            if titulo != antes_t:
                cambios.append(f"título «{antes_t}» → «{titulo}»")
            if poblacion != antes_p:
                cambios.append(f"población {antes_p} → {poblacion}")
            self._registrar("Encuesta", ", ".join(cambios))

    def restaurar_originales(self) -> None:
        """Vuelve a los datos de la guía. El historial se conserva."""
        with self.con:
            self.con.execute("DELETE FROM categoria")
            self.con.execute("DELETE FROM encuesta")
            self._cargar_originales("Se restauraron los datos originales de la guía", transaccion=False)

    def _cargar_originales(self, detalle: str, transaccion: bool = True) -> None:
        def cargar():
            self.con.execute("INSERT INTO encuesta (id, titulo, poblacion) VALUES (1, ?, ?)",
                             (TITULO_ORIGINAL, POBLACION_ORIGINAL))
            # Se reinicia el contador para que los ids vuelvan a 1..6 en el orden de la guía.
            self.con.execute("DELETE FROM sqlite_sequence WHERE name = 'categoria'")
            for nombre, cantidad in DATOS_ORIGINALES:
                self.con.execute(
                    "INSERT INTO categoria (nombre, cantidad, cantidad_original, origen, creado, modificado) "
                    "VALUES (?, ?, ?, 'original', ?, ?)", (nombre, cantidad, cantidad, ahora(), ahora()))
            self._registrar("Datos originales", detalle)
        if transaccion:
            with self.con:
                cargar()
        else:
            cargar()

    # ---------- CSV ----------

    def exportar_csv(self, ruta: Path | str) -> None:
        """Guarda actividad, estudiantes y porcentaje sobre la población. Usa ; para que Excel en español lo abra bien."""
        poblacion = self.poblacion()
        with open(ruta, "w", newline="", encoding="utf-8-sig") as f:
            w = csv.writer(f, delimiter=";")
            w.writerow(["actividad", "estudiantes", "porcentaje"])
            for c in self.categorias():
                w.writerow([c.nombre, c.cantidad, str(porcentaje(c.cantidad, poblacion)).replace(".", ",")])
        with self.con:
            self._registrar("Exportar CSV", str(ruta))

    def importar_csv(self, ruta: Path | str, reemplazar: bool = True) -> int:
        """Carga actividades desde un CSV con columnas actividad y estudiantes (separado por ; o ,).

        La importación es todo o nada: si una fila no pasa la validación no se guarda ninguna y el
        error dice en qué línea está el problema. Devuelve cuántas filas se cargaron.
        """
        texto = Path(ruta).read_text(encoding="utf-8-sig")
        filas = leer_filas_csv(texto)
        poblacion = self.poblacion()
        vistos = [] if reemplazar else self._nombres()
        limpias, errores = [], []
        for linea, nombre, cantidad in filas:
            try:
                n = validar_nombre(nombre, vistos)
                q = validar_cantidad(cantidad, poblacion)
            except ErrorValidacion as e:
                errores.append(f"Línea {linea}: {e}")
                continue
            vistos.append(n)
            limpias.append((n, q))
        if errores:
            raise ErrorValidacion("No se importó nada. Corrija el archivo:\n" + "\n".join(errores[:10]))
        if not limpias:
            raise ErrorValidacion("El archivo no tiene filas de datos.")
        if len(vistos) > MAX_CATEGORIAS:
            raise ErrorValidacion(f"El archivo deja {len(vistos)} actividades; el máximo es {MAX_CATEGORIAS}.")
        base = 0 if reemplazar else self.suma()
        validar_coherencia(base + sum(q for _, q in limpias), poblacion)
        with self.con:
            if reemplazar:
                self.con.execute("DELETE FROM categoria")
            originales = {n.casefold(): q for n, q in DATOS_ORIGINALES}
            for n, q in limpias:
                self.con.execute(
                    "INSERT INTO categoria (nombre, cantidad, cantidad_original, origen, creado, modificado) "
                    "VALUES (?, ?, ?, 'importado', ?, ?)", (n, q, originales.get(n.casefold()), ahora(), ahora()))
            modo = "reemplazando" if reemplazar else "agregando a"
            self._registrar("Importar CSV", f"{len(limpias)} filas {modo} los datos, desde {ruta}")
        return len(limpias)


def leer_filas_csv(texto: str) -> list[tuple[int, str, str]]:
    """Devuelve (número de línea, actividad, estudiantes). Detecta ; o , y exige el encabezado."""
    primera = texto.splitlines()[0] if texto.strip() else ""
    separador = ";" if primera.count(";") >= primera.count(",") and ";" in primera else ","
    lector = csv.reader(io.StringIO(texto), delimiter=separador)
    encabezado = [h.strip().casefold() for h in next(lector, [])]
    try:
        i_nombre = next(i for i, h in enumerate(encabezado) if h in ("actividad", "categoria", "categoría", "nombre"))
        i_cant = next(i for i, h in enumerate(encabezado) if h in ("estudiantes", "cantidad", "valor", "frecuencia"))
    except StopIteration:
        raise ErrorValidacion("El CSV debe tener encabezado con las columnas «actividad» y «estudiantes».") from None
    filas = []
    for numero, fila in enumerate(lector, start=2):
        if not any(c.strip() for c in fila):
            continue
        if len(fila) <= max(i_nombre, i_cant):
            raise ErrorValidacion(f"Línea {numero}: faltan columnas.")
        filas.append((numero, fila[i_nombre], fila[i_cant]))
    return filas
