"""Genera los diagramas de la documentación (PNG en docs/diagramas/) y las gráficas del informe de la FASE 1.

Ejecutar desde la carpeta del proyecto:   python docs/generar_diagramas.py
Los diagramas se dibujan con matplotlib para que cualquiera pueda regenerarlos sin otras herramientas.
"""
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import Ellipse, FancyArrowPatch, FancyBboxPatch, Polygon  # noqa: E402

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "app"))
import graficos  # noqa: E402
from almacen import Almacen  # noqa: E402

SALIDA = RAIZ / "docs" / "diagramas"
AZUL, AZUL_CLARO, NARANJA_CLARO, VERDE_CLARO, GRIS_CLARO = "#2a6fb0", "#dbe8f6", "#fbe3cc", "#d8efe0", "#eeeeee"
TEXTO = "#222222"


def lienzo(ancho, alto):
    fig, ax = plt.subplots(figsize=(ancho, alto), dpi=150)
    ax.set_xlim(0, ancho * 10)
    ax.set_ylim(0, alto * 10)
    ax.axis("off")
    return fig, ax


def caja(ax, x, y, w, h, texto, color=AZUL_CLARO, borde=AZUL, tam=9, negrita=False, forma="round"):
    """Caja con el centro en (x, y). forma: round, cuadrada, rombo, ovalo, cilindro."""
    if forma == "rombo":
        ax.add_patch(Polygon([(x, y + h / 2), (x + w / 2, y), (x, y - h / 2), (x - w / 2, y)],
                             fc=color, ec=borde, lw=1.3))
    elif forma == "ovalo":
        ax.add_patch(Ellipse((x, y), w, h, fc=color, ec=borde, lw=1.3))
    elif forma == "cilindro":
        ax.add_patch(FancyBboxPatch((x - w / 2, y - h / 2), w, h, boxstyle="round,pad=0,rounding_size=1.2",
                                    fc=color, ec=borde, lw=1.3))
        ax.add_patch(Ellipse((x, y + h / 2), w, 2.2, fc=color, ec=borde, lw=1.3))
    else:
        estilo = "round,pad=0.3,rounding_size=0.8" if forma == "round" else "square,pad=0.3"
        ax.add_patch(FancyBboxPatch((x - w / 2, y - h / 2), w, h, boxstyle=estilo, fc=color, ec=borde, lw=1.3))
    ax.text(x, y, texto, ha="center", va="center", fontsize=tam, color=TEXTO,
            fontweight="bold" if negrita else "normal", wrap=True)


def flecha(ax, a, b, texto="", color="#555555", estilo="-|>", lado=(0, 1.2), tam=8, curva=0.0):
    ax.add_patch(FancyArrowPatch(a, b, arrowstyle=estilo, mutation_scale=13, color=color, lw=1.2,
                                 connectionstyle=f"arc3,rad={curva}"))
    if texto:
        ax.text((a[0] + b[0]) / 2 + lado[0], (a[1] + b[1]) / 2 + lado[1], texto, ha="center", va="center",
                fontsize=tam, color="#444444", bbox={"fc": "white", "ec": "none", "pad": 1})


def guardar(fig, nombre, titulo=None):
    if titulo:
        fig.suptitle(titulo, fontsize=12, fontweight="bold", color=TEXTO)
    fig.savefig(SALIDA / nombre, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def arquitectura():
    fig, ax = lienzo(11, 6.4)
    caja(ax, 12, 52, 16, 7, "Usuario\n(estudiante / docente)", GRIS_CLARO, "#777777", negrita=True)
    caja(ax, 55, 52, 46, 8, "Capa de presentación — interfaz.py (Tkinter)\nformulario · tabla · KPI · gráfico · historial",
         negrita=True)
    caja(ax, 30, 33, 30, 9, "Reglas del negocio — modelo.py\nvalidación · coherencia\nindicadores (KPI) · Pareto",
         NARANJA_CLARO, "#d9822b")
    caja(ax, 80, 33, 30, 9, "Visualización — graficos.py\n(matplotlib)\n5 tipos de gráfico · exportar PNG",
         VERDE_CLARO, "#2e8b57")
    caja(ax, 30, 14, 30, 8, "Acceso a datos — almacen.py\nCRUD · historial · CSV · restaurar", NARANJA_CLARO, "#d9822b")
    caja(ax, 80, 14, 22, 8, "datos/encuesta.db\n(SQLite, junto al .exe)", GRIS_CLARO, "#777777", forma="cilindro")
    caja(ax, 102, 33, 12, 6, "PNG", GRIS_CLARO, "#777777")
    caja(ax, 4.5, 14, 7, 6, "CSV", GRIS_CLARO, "#777777")
    flecha(ax, (20.5, 52), (31.5, 52), "usa")
    flecha(ax, (45, 47.5), (34, 38), "datos escritos")
    flecha(ax, (68, 47.5), (78, 38), "dibujar()")
    flecha(ax, (30, 28.2), (30, 18.4), "valida antes\nde guardar", lado=(6, 0))
    flecha(ax, (45.5, 14), (68.5, 14), "SQL")
    flecha(ax, (80, 18.5), (80, 28.2), "lee categorías", lado=(6.5, 0))
    flecha(ax, (95.5, 33), (95.6, 33))
    flecha(ax, (8.5, 14), (14.5, 14), "", estilo="<|-|>")
    ax.text(55, 3, "Todo corre en un solo ejecutable (PyInstaller --onefile). No usa internet ni servidor.",
            ha="center", fontsize=9, style="italic", color="#555555")
    guardar(fig, "01_arquitectura.png", "Arquitectura del software por capas")


def flujo_bi():
    fig, ax = lienzo(12, 3.4)
    pasos = [("Fuente de datos\nencuesta a 100\nestudiantes / CSV", GRIS_CLARO, "#777777"),
             ("Ingreso y ETL\nlimpieza de texto\nvalidación de tipos\ny coherencia", NARANJA_CLARO, "#d9822b"),
             ("Almacenamiento\nSQLite\n(categoria,\nhistorial)", GRIS_CLARO, "#777777"),
             ("Indicadores\ntotal · moda ·\nmínimo · promedio\n% · % acumulado", AZUL_CLARO, AZUL),
             ("Visualización\nbarras · dona ·\nPareto · compara-\nción · tabla", VERDE_CLARO, "#2e8b57"),
             ("Toma de\ndecisiones\nconclusiones de\nla institución", AZUL_CLARO, AZUL)]
    for i, (t, c, b) in enumerate(pasos):
        x = 10 + i * 20
        caja(ax, x, 16, 15, 17, t, c, b, tam=8.5, forma="cilindro" if i == 2 else "round")
        if i:
            flecha(ax, (x - 12.3, 16), (x - 7.7, 16))
    guardar(fig, "02_flujo_bi.png", "Flujo de la información: de la fuente a la decisión")


def flujo_agregar():
    fig, ax = lienzo(9, 11.5)
    x = 35
    caja(ax, x, 110, 16, 5, "Inicio", "#d8efe0", "#2e8b57", forma="ovalo", negrita=True)
    caja(ax, x, 100, 30, 6, "Leer actividad y N.º de estudiantes", forma="cuadrada")
    caja(ax, x, 89, 26, 8, "¿Nombre válido?\n(2–40 caracteres, con letras)", "#fff6d5", "#c8a400", forma="rombo", tam=8)
    caja(ax, x, 77, 26, 8, "¿Nombre repetido?\n(sin tildes ni mayúsculas)", "#fff6d5", "#c8a400", forma="rombo", tam=8)
    caja(ax, x, 65, 26, 8, "¿Cantidad entera\nentre 0 y la población?", "#fff6d5", "#c8a400", forma="rombo", tam=8)
    caja(ax, x, 53, 26, 8, "¿Suma + cantidad\n≤ población?", "#fff6d5", "#c8a400", forma="rombo", tam=8)
    caja(ax, x, 42, 30, 6, "Guardar en SQLite y\nregistrar en el historial", forma="cuadrada")
    caja(ax, x, 32, 30, 6, "Recalcular KPI y redibujar el gráfico\n(dato nuevo en naranja)", forma="cuadrada")
    caja(ax, x, 22, 16, 5, "Fin", "#d8efe0", "#2e8b57", forma="ovalo", negrita=True)
    caja(ax, 74, 71, 22, 9, "Mostrar mensaje junto al\ncampo con el error y\ndevolver el foco", "#f8d7da", "#c0392b",
         forma="cuadrada", tam=8.5)
    for a, b in ((107.5, 103), (97, 93), (85, 81), (73, 69), (61, 57), (49, 45), (39, 35), (29, 24.5)):
        flecha(ax, (x, a), (x, b), "sí" if a in (85, 61, 49) else ("no" if a == 73 else ""), lado=(2.5, 0))
    for y, t in ((89, "no"), (77, "sí"), (65, "no"), (53, "no")):
        flecha(ax, (x + 13, y), (63, 71 + (y - 71) * 0.25), t, lado=(0, 1.3))
    flecha(ax, (74, 66.5), (74, 100), "", curva=0)
    flecha(ax, (74, 100), (50.3, 100), "corregir", lado=(0, 1.3))
    guardar(fig, "03_flujo_agregar.png", "Diagrama de flujo: agregar un dato")


def casos_de_uso():
    fig, ax = lienzo(10, 8.4)
    ax.add_patch(FancyBboxPatch((24, 2), 72, 80, boxstyle="round,pad=0,rounding_size=1.5", fc="white",
                                ec="#777777", lw=1.2))
    ax.text(60, 79, "Visualizador de Encuestas", ha="center", fontsize=10, fontweight="bold")
    # actor
    ax.add_patch(plt.Circle((9, 48), 2.2, fc="white", ec=TEXTO, lw=1.3))
    ax.plot([9, 9], [45.8, 38], color=TEXTO, lw=1.3)
    ax.plot([5, 13], [43, 43], color=TEXTO, lw=1.3)
    ax.plot([9, 5.5], [38, 32], color=TEXTO, lw=1.3)
    ax.plot([9, 12.5], [38, 32], color=TEXTO, lw=1.3)
    ax.text(9, 28.5, "Usuario", ha="center", fontsize=9, fontweight="bold")
    casos = ["CU1 Agregar actividad", "CU2 Actualizar actividad", "CU3 Eliminar actividad",
             "CU4 Configurar encuesta (título, población)", "CU5 Elegir tipo de gráfico",
             "CU6 Exportar gráfico (PNG)", "CU7 Importar / exportar CSV", "CU8 Consultar historial",
             "CU9 Restaurar datos originales"]
    validar = (82, 48)
    caja(ax, *validar, 20, 8, "Validar datos\n(modelo.py)", NARANJA_CLARO, "#d9822b", forma="ovalo", tam=8.5)
    for i, c in enumerate(casos):
        cy = 72 - i * 8.2
        caja(ax, 46, cy, 34, 6.4, c, AZUL_CLARO, AZUL, forma="ovalo", tam=8)
        ax.plot([13, 29], [43, cy], color="#999999", lw=0.8)
        if i in (0, 1, 3, 6):
            flecha(ax, (63, cy), (validar[0] - 10, validar[1] + (cy - validar[1]) * 0.08), color="#d9822b")
    ax.text(82, 56, "«include»", ha="center", fontsize=8, color="#d9822b")
    guardar(fig, "04_casos_de_uso.png", "Diagrama de casos de uso")


def clases():
    fig, ax = lienzo(12, 7.6)

    def clase(x, y, w, nombre, atributos, metodos, color=AZUL_CLARO):
        lineas_a, lineas_m = len(atributos), len(metodos)
        h_n, h_a, h_m = 4, 2.6 * lineas_a + 1.2, 2.6 * lineas_m + 1.2
        arriba = y
        for alto, fondo in ((h_n, color), (h_a, "white"), (h_m, "white")):
            ax.add_patch(plt.Rectangle((x, arriba - alto), w, alto, fc=fondo, ec=AZUL, lw=1.2))
            arriba -= alto
        ax.text(x + w / 2, y - h_n / 2, nombre, ha="center", va="center", fontsize=9, fontweight="bold")
        for i, a in enumerate(atributos):
            ax.text(x + 1, y - h_n - 1.9 - i * 2.6, a, fontsize=7.3, va="center", family="monospace")
        for i, m in enumerate(metodos):
            ax.text(x + 1, y - h_n - h_a - 1.9 - i * 2.6, m, fontsize=7.3, va="center", family="monospace")
        return x, y, w, h_n + h_a + h_m

    clase(2, 70, 38, "Aplicacion (tk.Tk) — interfaz.py",
          ["- almacen: Almacen", "- id_seleccionado: int", "- resaltar: str", "- figura: Figure"],
          ["+ refrescar()", "+ redibujar()", "+ agregar() / actualizar()", "+ eliminar() / aplicar_encuesta()",
           "+ importar_csv() / exportar_csv()", "+ exportar_png() / restaurar()"])
    clase(48, 70, 42, "Almacen — almacen.py",
          ["- con: sqlite3.Connection", "- ruta: Path"],
          ["+ categorias(): list[Categoria]", "+ titulo() / poblacion() / suma()",
           "+ agregar(nombre, cantidad): Categoria", "+ actualizar(id, nombre, cantidad)", "+ eliminar(id)",
           "+ configurar(titulo, poblacion)", "+ importar_csv(ruta) / exportar_csv(ruta)",
           "+ historial() / restaurar_originales()"], NARANJA_CLARO)
    clase(95, 70, 24, "Tarjeta (ttk.Frame)", ["- valor: Label", "- detalle: Label"], ["+ mostrar(valor, det.)"])
    clase(48, 26, 30, "Categoria «dataclass»",
          ["+ id: int", "+ nombre: str", "+ cantidad: int", "+ cantidad_original: int?", "+ origen: str"], [],
          NARANJA_CLARO)
    clase(86, 26, 33, "Indicadores «dataclass»",
          ["+ total, poblacion: int", "+ cobertura_pct, promedio", "+ mas_frecuentes: list", "+ menos_frecuentes: list"],
          [], NARANJA_CLARO)
    clase(2, 31, 40, "modelo.py / graficos.py (funciones)", [],
          ["validar_nombre(), validar_cantidad()", "validar_poblacion(), validar_coherencia()",
           "calcular_indicadores(): Indicadores", "ordenadas(), acumulados_pct()",
           "graficos.dibujar(figura, tipo, ...)", "graficos.exportar_png(ruta, ...)"], VERDE_CLARO)
    flecha(ax, (40, 60), (48, 60), "1", lado=(0, 1.2))
    ax.plot([21, 21, 107], [70, 73.5, 73.5], color="#555555", lw=1.2)
    flecha(ax, (107, 73.5), (107, 70.2))
    ax.text(64, 75, "la ventana contiene 4 tarjetas de KPI", ha="center", fontsize=8, color="#444444")
    flecha(ax, (72, 38.5), (63, 26.5), "crea 0..*", lado=(6, 0))
    flecha(ax, (21, 37.6), (21, 31.4), "")
    ax.text(23, 34.5, "usa", fontsize=8, color="#444444")
    flecha(ax, (55, 38.5), (36, 31.5), "valida con", lado=(4, 1.5))
    ax.plot([22, 22, 102], [9, 4, 4], color="#555555", lw=1.2)
    flecha(ax, (102, 4), (102, 9.2))
    ax.text(62, 2.2, "calcular_indicadores() devuelve Indicadores", ha="center", fontsize=8, color="#444444")
    guardar(fig, "05_clases.png", "Diagrama de clases y módulos")


def modelo_datos():
    fig, ax = lienzo(10.5, 4.6)

    def tabla(x, y, w, nombre, campos):
        ax.add_patch(plt.Rectangle((x, y - 4), w, 4, fc=AZUL, ec=AZUL))
        ax.text(x + w / 2, y - 2, nombre, ha="center", va="center", color="white", fontsize=9, fontweight="bold")
        for i, (c, t) in enumerate(campos):
            yy = y - 4 - (i + 1) * 3.2
            ax.add_patch(plt.Rectangle((x, yy), w, 3.2, fc="white" if i % 2 else "#f4f7fb", ec="#bbbbbb", lw=0.6))
            ax.text(x + 1, yy + 1.6, c, va="center", fontsize=7.5, fontweight="bold" if c.startswith("PK") else "normal")
            ax.text(x + w - 1, yy + 1.6, t, va="center", ha="right", fontsize=7, color="#555555")

    tabla(2, 42, 30, "encuesta", [("PK id", "INTEGER = 1"), ("titulo", "TEXT NOT NULL"),
                                  ("poblacion", "INTEGER > 0")])
    tabla(37, 42, 34, "categoria", [("PK id", "INTEGER AUTOINC."), ("nombre", "TEXT UNIQUE NOCASE"),
                                    ("cantidad", "INTEGER ≥ 0"), ("cantidad_original", "INTEGER NULL"),
                                    ("origen", "original|ingresado|importado"), ("creado", "TEXT fecha"),
                                    ("modificado", "TEXT fecha")])
    tabla(76, 42, 28, "historial", [("PK id", "INTEGER AUTOINC."), ("fecha", "TEXT"), ("accion", "TEXT"),
                                    ("detalle", "TEXT")])
    flecha(ax, (32, 34), (37, 34), "1 : N", estilo="-", lado=(0, 1.5))
    ax.text(53, 5, "Regla entre tablas (se valida en modelo.py): SUM(categoria.cantidad) ≤ encuesta.poblacion",
            ha="center", fontsize=8.5, style="italic")
    ax.text(90, 20, "Cada cambio queda\nregistrado aquí\n(trazabilidad)", ha="center", fontsize=8, color="#555555")
    guardar(fig, "06_modelo_datos.png", "Modelo de datos (SQLite: datos/encuesta.db)")


def graficas_fase1():
    """Gráficas del informe de la FASE 1, hechas con el mismo módulo de la aplicación."""
    a = Almacen(":memory:")
    cats, pob, tit = a.categorias(), a.poblacion(), "Actividades en el tiempo libre (n = 100)"
    graficos.exportar_png(SALIDA / "f1_barras.png", graficos.TIPOS[0], cats, pob, tit)
    graficos.exportar_png(SALIDA / "f1_propuesta_horizontal.png", graficos.TIPOS[1], cats, pob, tit)
    graficos.exportar_png(SALIDA / "f1_pareto.png", graficos.TIPOS[3], cats, pob, tit)
    graficos.exportar_png(SALIDA / "f1_circular.png", graficos.TIPOS[2], cats, pob, tit)
    a.cerrar()


if __name__ == "__main__":
    SALIDA.mkdir(parents=True, exist_ok=True)
    for f in (arquitectura, flujo_bi, flujo_agregar, casos_de_uso, clases, modelo_datos, graficas_fase1):
        f()
    print("Diagramas en", SALIDA)
