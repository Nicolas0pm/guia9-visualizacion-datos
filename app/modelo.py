"""Reglas del negocio: validación de los datos ingresados e indicadores de la encuesta.

Este módulo no depende de la interfaz ni de la base de datos, por eso se prueba por separado
(ver tests/test_modelo.py). Toda regla de validación vive aquí y la usan tanto el formulario
como la importación de CSV y el almacén.
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

# Datos de la FASE 1 de la guía: encuesta a 100 estudiantes sobre su tiempo libre.
TITULO_ORIGINAL = "Actividades en el tiempo libre"
POBLACION_ORIGINAL = 100
DATOS_ORIGINALES = [
    ("Ver series o películas", 28),
    ("Escuchar música", 22),
    ("Practicar deporte", 18),
    ("Jugar videojuegos", 15),
    ("Leer", 10),
    ("Otras actividades", 7),
]

LARGO_MIN_NOMBRE = 2
LARGO_MAX_NOMBRE = 40
LARGO_MAX_TITULO = 80
MAX_CATEGORIAS = 15          # más barras que esto ya no se leen bien en el gráfico
POBLACION_MAXIMA = 1_000_000
_PERMITIDOS = re.compile(r"^[\w .,()/&+'-]+$")


class ErrorValidacion(ValueError):
    """Dato rechazado. `campo` indica qué control de la interfaz debe marcarse."""

    def __init__(self, mensaje: str, campo: str = ""):
        super().__init__(mensaje)
        self.campo = campo


@dataclass(frozen=True)
class Categoria:
    """Una fila de la encuesta: una actividad y cuántos estudiantes la eligieron."""
    id: int
    nombre: str
    cantidad: int
    cantidad_original: int | None   # None si la categoría no estaba en los datos de la guía
    origen: str                     # "original", "ingresado" o "importado"


def clave(nombre: str) -> str:
    """Forma comparable de un nombre: sin tildes, sin mayúsculas y sin espacios repetidos.

    Así "Leer", "leer " y "LEÉR" se reconocen como la misma actividad.
    """
    sin_tildes = unicodedata.normalize("NFKD", nombre).encode("ascii", "ignore").decode()
    return " ".join(sin_tildes.casefold().split())


def validar_nombre(texto: str, existentes: list[str] = (), ignorar: str | None = None) -> str:
    """Devuelve el nombre limpio o lanza ErrorValidacion.

    existentes: nombres ya guardados (para impedir duplicados).
    ignorar: nombre actual de la fila que se está editando (puede conservar su propio nombre).
    """
    nombre = " ".join((texto or "").split())
    if not nombre:
        raise ErrorValidacion("Escriba el nombre de la actividad.", "nombre")
    if len(nombre) < LARGO_MIN_NOMBRE:
        raise ErrorValidacion(f"El nombre debe tener al menos {LARGO_MIN_NOMBRE} caracteres.", "nombre")
    if len(nombre) > LARGO_MAX_NOMBRE:
        raise ErrorValidacion(f"El nombre no puede pasar de {LARGO_MAX_NOMBRE} caracteres.", "nombre")
    if not _PERMITIDOS.match(nombre) or "_" in nombre:
        raise ErrorValidacion("El nombre solo admite letras, números, espacios y . , ( ) / & + ' -", "nombre")
    if not any(c.isalpha() for c in nombre):
        raise ErrorValidacion("El nombre debe contener al menos una letra.", "nombre")
    k = clave(nombre)
    for e in existentes:
        if clave(e) == k and (ignorar is None or clave(e) != clave(ignorar)):
            raise ErrorValidacion(f"Ya existe la actividad «{e}». Selecciónela en la tabla para cambiarla.", "nombre")
    return nombre


def validar_entero(texto, campo: str, etiqueta: str, minimo: int, maximo: int) -> int:
    """Convierte texto a entero dentro de [minimo, maximo]. Rechaza decimales y letras."""
    if isinstance(texto, bool):
        raise ErrorValidacion(f"{etiqueta} debe ser un número entero.", campo)
    if isinstance(texto, int):
        valor = texto
    else:
        limpio = str(texto or "").strip()
        if not limpio:
            raise ErrorValidacion(f"Escriba {etiqueta.lower()}.", campo)
        if not re.fullmatch(r"[+-]?\d+", limpio):
            raise ErrorValidacion(f"{etiqueta} debe ser un número entero, sin decimales ni letras.", campo)
        valor = int(limpio)
    if valor < minimo:
        raise ErrorValidacion(f"{etiqueta} no puede ser menor que {minimo}.", campo)
    if valor > maximo:
        raise ErrorValidacion(f"{etiqueta} no puede ser mayor que {maximo:,}.".replace(",", "."), campo)
    return valor


def validar_cantidad(texto, poblacion: int) -> int:
    """Número de estudiantes de una actividad: entero entre 0 y la población encuestada."""
    return validar_entero(texto, "cantidad", "El número de estudiantes", 0, poblacion)


def validar_poblacion(texto, suma_actual: int = 0) -> int:
    """Población encuestada: entero positivo y nunca menor que lo ya registrado."""
    poblacion = validar_entero(texto, "poblacion", "La población encuestada", 1, POBLACION_MAXIMA)
    if poblacion < suma_actual:
        raise ErrorValidacion(
            f"La población ({poblacion}) no puede ser menor que los estudiantes ya registrados ({suma_actual}).",
            "poblacion")
    return poblacion


def validar_titulo(texto: str) -> str:
    titulo = " ".join((texto or "").split())
    if not titulo:
        raise ErrorValidacion("Escriba el título de la encuesta.", "titulo")
    if len(titulo) > LARGO_MAX_TITULO:
        raise ErrorValidacion(f"El título no puede pasar de {LARGO_MAX_TITULO} caracteres.", "titulo")
    return titulo


def validar_coherencia(suma: int, poblacion: int) -> None:
    """La suma de todas las actividades no puede superar a la población encuestada.

    Es la regla de la guía «mantener coherencia entre población e indicadores»: si 100 estudiantes
    respondieron, no puede haber 105 respuestas.
    """
    if suma > poblacion:
        raise ErrorValidacion(
            f"Con este dato la suma sería {suma} estudiantes y la encuesta tiene {poblacion}. "
            f"Sobran {suma - poblacion}.", "cantidad")


@dataclass(frozen=True)
class Indicadores:
    total: int
    poblacion: int
    sin_registrar: int          # población que todavía no está en ninguna actividad
    cobertura_pct: float        # total / población
    promedio: float
    mas_frecuentes: list[str]   # lista porque puede haber empate
    menos_frecuentes: list[str]
    maximo: int
    minimo: int


def porcentaje(parte: int, todo: int) -> float:
    return 0.0 if todo <= 0 else round(parte * 100 / todo, 1)


def calcular_indicadores(categorias: list[Categoria], poblacion: int) -> Indicadores:
    """KPI que muestra el tablero. Funciona con la lista vacía (todo en cero)."""
    total = sum(c.cantidad for c in categorias)
    if categorias:
        maximo = max(c.cantidad for c in categorias)
        minimo = min(c.cantidad for c in categorias)
        mas = [c.nombre for c in categorias if c.cantidad == maximo]
        menos = [c.nombre for c in categorias if c.cantidad == minimo]
        promedio = round(total / len(categorias), 2)
    else:
        maximo = minimo = 0
        mas, menos, promedio = [], [], 0.0
    return Indicadores(total, poblacion, poblacion - total, porcentaje(total, poblacion), promedio,
                       mas, menos, maximo, minimo)


def ordenadas(categorias: list[Categoria]) -> list[Categoria]:
    """De mayor a menor; en empate, por nombre. Se usa en el gráfico horizontal y en Pareto."""
    return sorted(categorias, key=lambda c: (-c.cantidad, clave(c.nombre)))


def acumulados_pct(categorias: list[Categoria]) -> list[float]:
    """Porcentaje acumulado sobre el total registrado (curva de Pareto)."""
    total = sum(c.cantidad for c in categorias)
    salida, corrido = [], 0
    for c in categorias:
        corrido += c.cantidad
        salida.append(porcentaje(corrido, total))
    return salida
