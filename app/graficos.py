"""Generación automática de los gráficos a partir de los datos guardados.

Cada función recibe una Figure de matplotlib y la redibuja completa. No usan Tkinter, así que las
mismas funciones sirven para la ventana, para exportar PNG y para las pruebas automáticas.

Por qué cada tipo de gráfico (pregunta orientadora de la guía):
- Barras verticales: compara cantidades entre categorías; es el gráfico que propone la guía.
- Barras horizontales ordenadas: ordena de mayor a menor y muestra el porcentaje; los nombres largos
  se leen completos. Es el que se propone para presentar los resultados a la institución.
- Circular (dona): muestra la parte de cada actividad sobre el total de la población (suma 100 %).
- Pareto: barras ordenadas más el porcentaje acumulado; muestra qué pocas actividades concentran
  la mayoría de las respuestas.
- Comparación con los datos originales: muestra lado a lado el dato de la guía y el actual, para
  conservar la trazabilidad cuando se editan los datos.
"""
from __future__ import annotations

from matplotlib.figure import Figure
from matplotlib.ticker import MaxNLocator, PercentFormatter

from modelo import Categoria, acumulados_pct, ordenadas, porcentaje

AZUL = "#2a6fb0"
NARANJA = "#e07b24"      # dato recién ingresado o seleccionado
GRIS = "#9aa5b1"
TEXTO = "#2b2b2b"
PALETA_CIRCULAR = ["#2a6fb0", "#e07b24", "#2e8b57", "#8e5ea2", "#c8a400", "#d1495b",
                   "#3caea3", "#7a7a7a", "#5b8def", "#f4a259", "#6aa84f", "#b07aa1",
                   "#9c755f", "#e15759", "#76b7b2"]

TIPOS = [
    "Barras verticales",
    "Barras horizontales ordenadas (%)",
    "Circular (proporción)",
    "Pareto (frecuencia y % acumulado)",
    "Comparación con datos originales",
]


def dibujar(figura: Figure, tipo: str, categorias: list[Categoria], poblacion: int, titulo: str,
            resaltar: str | None = None) -> None:
    """Punto de entrada único: limpia la figura y dibuja el tipo pedido.

    resaltar: nombre de la actividad que se pinta en naranja (el dato que se acaba de ingresar o
    la fila seleccionada en la tabla).
    """
    figura.clear()
    figura.set_facecolor("white")
    if not categorias:
        ax = figura.add_subplot()
        ax.axis("off")
        ax.text(0.5, 0.5, "No hay datos.\nAgregue una actividad para generar el gráfico.",
                ha="center", va="center", fontsize=12, color=GRIS)
        return
    funciones = {
        TIPOS[0]: _barras_verticales,
        TIPOS[1]: _barras_horizontales,
        TIPOS[2]: _circular,
        TIPOS[3]: _pareto,
        TIPOS[4]: _comparacion,
    }
    if tipo not in funciones:
        raise ValueError(f"Tipo de gráfico desconocido: {tipo}")
    funciones[tipo](figura, categorias, poblacion, resaltar)
    total = sum(c.cantidad for c in categorias)
    figura.suptitle(titulo, fontsize=13, fontweight="bold", color=TEXTO)
    figura.axes[0].set_title(f"n = {total} de {poblacion} estudiantes encuestados",
                             loc="right", fontsize=8.5, color=GRIS)


def _colores(categorias: list[Categoria], resaltar: str | None) -> list[str]:
    return [NARANJA if resaltar and c.nombre == resaltar else AZUL for c in categorias]


def _limpiar_ejes(ax) -> None:
    for lado in ("top", "right"):
        ax.spines[lado].set_visible(False)
    ax.tick_params(colors=TEXTO)


def _barras_verticales(figura, categorias, poblacion, resaltar):
    ax = figura.add_subplot()
    nombres = [c.nombre for c in categorias]
    valores = [c.cantidad for c in categorias]
    barras = ax.bar(range(len(nombres)), valores, color=_colores(categorias, resaltar), width=0.65)
    ax.bar_label(barras, padding=3, fontsize=10, color=TEXTO)
    ax.set_xticks(range(len(nombres)), _envolver(nombres), fontsize=9)
    ax.set_ylabel("Número de estudiantes")
    ax.set_xlabel("Actividad")
    ax.yaxis.set_major_locator(MaxNLocator(integer=True))
    ax.set_ylim(0, max(valores) * 1.15 + 1)
    ax.grid(axis="y", alpha=0.3)
    ax.set_axisbelow(True)
    _limpiar_ejes(ax)


def _barras_horizontales(figura, categorias, poblacion, resaltar):
    ax = figura.add_subplot()
    orden = ordenadas(categorias)[::-1]          # la mayor queda arriba
    valores = [c.cantidad for c in orden]
    barras = ax.barh([c.nombre for c in orden], valores, color=_colores(orden, resaltar), height=0.6)
    ax.bar_label(barras, labels=[f"{c.cantidad}  ({porcentaje(c.cantidad, poblacion):g} %)" for c in orden],
                 padding=4, fontsize=10, color=TEXTO)
    ax.set_xlabel("Número de estudiantes (porcentaje sobre la población encuestada)")
    ax.xaxis.set_major_locator(MaxNLocator(integer=True))
    ax.set_xlim(0, max(valores) * 1.3 + 1)
    ax.grid(axis="x", alpha=0.3)
    ax.set_axisbelow(True)
    _limpiar_ejes(ax)


def _circular(figura, categorias, poblacion, resaltar):
    ax = figura.add_subplot()
    visibles = [c for c in categorias if c.cantidad > 0]
    nombres = [c.nombre for c in visibles]
    valores = [c.cantidad for c in visibles]
    colores = [PALETA_CIRCULAR[i % len(PALETA_CIRCULAR)] for i in range(len(visibles))]
    sin_registrar = poblacion - sum(valores)
    if sin_registrar > 0:                         # la parte que falta se muestra en gris, no se esconde
        nombres.append("Sin registrar")
        valores.append(sin_registrar)
        colores.append("#dddddd")
    separacion = [0.08 if resaltar and n == resaltar else 0 for n in nombres]
    cuñas, _, textos = ax.pie(valores, labels=None, colors=colores, explode=separacion, startangle=90,
                              counterclock=False, autopct=lambda p: f"{p:.0f} %" if p >= 3 else "",
                              pctdistance=0.78, wedgeprops={"width": 0.45, "edgecolor": "white"})
    for t, color in zip(textos, colores):
        t.set_color(TEXTO if color == "#dddddd" else "white")
        t.set_fontsize(9)
        t.set_fontweight("bold")
    ax.text(0, 0, f"{poblacion}\nestudiantes", ha="center", va="center", fontsize=11, color=TEXTO)
    ax.legend(cuñas, [f"{n} ({v})" for n, v in zip(nombres, valores)], loc="center left",
              bbox_to_anchor=(1.0, 0.5), frameon=False, fontsize=9)
    ax.set_aspect("equal")


def _pareto(figura, categorias, poblacion, resaltar):
    ax = figura.add_subplot()
    orden = ordenadas(categorias)
    valores = [c.cantidad for c in orden]
    x = range(len(orden))
    barras = ax.bar(x, valores, color=_colores(orden, resaltar), width=0.65)
    ax.bar_label(barras, padding=3, fontsize=9, color=TEXTO)
    ax.set_xticks(x, _envolver([c.nombre for c in orden]), fontsize=9)
    ax.set_ylabel("Número de estudiantes")
    ax.yaxis.set_major_locator(MaxNLocator(integer=True))
    ax.set_ylim(0, max(valores) * 1.15 + 1)
    _limpiar_ejes(ax)
    ax2 = ax.twinx()
    acumulado = acumulados_pct(orden)
    ax2.plot(x, acumulado, color=NARANJA if not resaltar else TEXTO, marker="o", linewidth=2)
    for xi, yi in zip(x, acumulado):
        ax2.annotate(f"{yi:g} %", (xi, yi), textcoords="offset points", xytext=(0, 8),
                     ha="center", fontsize=8, color=TEXTO,
                     bbox={"boxstyle": "round,pad=0.15", "fc": "white", "ec": "none", "alpha": 0.85})
    ax2.axhline(80, color=GRIS, linestyle="--", linewidth=1)
    ax2.set_ylim(0, 110)
    ax2.yaxis.set_major_formatter(PercentFormatter())
    ax2.set_ylabel("% acumulado de las respuestas")
    ax2.spines["top"].set_visible(False)


def _comparacion(figura, categorias, poblacion, resaltar):
    ax = figura.add_subplot()
    x = range(len(categorias))
    ancho = 0.38
    originales = [c.cantidad_original or 0 for c in categorias]
    actuales = [c.cantidad for c in categorias]
    b1 = ax.bar([i - ancho / 2 for i in x], originales, ancho, color=GRIS, label="Dato original (guía)")
    b2 = ax.bar([i + ancho / 2 for i in x], actuales, ancho, color=_colores(categorias, resaltar),
                label="Dato actual")
    ax.bar_label(b1, labels=[str(c.cantidad_original) if c.cantidad_original is not None else "nuevo"
                             for c in categorias], padding=2, fontsize=8, color=GRIS)
    ax.bar_label(b2, padding=2, fontsize=8, color=TEXTO)
    ax.set_xticks(list(x), _envolver([c.nombre for c in categorias]), fontsize=9)
    ax.set_ylabel("Número de estudiantes")
    ax.yaxis.set_major_locator(MaxNLocator(integer=True))
    ax.set_ylim(0, max(originales + actuales) * 1.18 + 1)
    ax.legend(frameon=False, loc="upper right")
    ax.grid(axis="y", alpha=0.3)
    ax.set_axisbelow(True)
    _limpiar_ejes(ax)


def _envolver(nombres: list[str], ancho: int = 12) -> list[str]:
    """Parte los nombres largos en dos líneas para que no se monten en el eje X."""
    salida = []
    for n in nombres:
        if len(n) <= ancho:
            salida.append(n)
            continue
        palabras, lineas, actual = n.split(), [], ""
        for p in palabras:
            if actual and len(actual) + 1 + len(p) > ancho:
                lineas.append(actual)
                actual = p
            else:
                actual = f"{actual} {p}".strip()
        lineas.append(actual)
        salida.append("\n".join(lineas))
    return salida


def exportar_png(ruta, tipo, categorias, poblacion, titulo, resaltar=None) -> None:
    """Genera el gráfico en alta resolución sin abrir ventanas (para informes)."""
    figura = Figure(figsize=(10, 5.6), dpi=150, layout="constrained")
    dibujar(figura, tipo, categorias, poblacion, titulo, resaltar)
    figura.savefig(ruta, dpi=150)
