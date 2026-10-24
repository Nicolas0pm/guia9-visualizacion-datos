"""Pruebas automáticas: reglas de validación, almacenamiento, CSV y generación de gráficos.

Ejecutar desde la carpeta del proyecto:   python -m unittest -v
"""
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "app"))

import matplotlib  # noqa: E402

matplotlib.use("Agg")
from matplotlib.figure import Figure  # noqa: E402

import graficos  # noqa: E402
from almacen import Almacen  # noqa: E402
from modelo import (Categoria, ErrorValidacion, acumulados_pct, calcular_indicadores, clave,  # noqa: E402
                    validar_cantidad, validar_coherencia, validar_nombre, validar_poblacion)


class PruebasValidacion(unittest.TestCase):
    def test_nombre_limpia_espacios(self):
        self.assertEqual(validar_nombre("  Montar   bicicleta "), "Montar bicicleta")

    def test_nombre_vacio_corto_largo_o_sin_letras(self):
        for malo in ("", "   ", "a", "x" * 41, "123", "Leer;DROP", "dato_raro"):
            with self.subTest(malo=malo), self.assertRaises(ErrorValidacion) as e:
                validar_nombre(malo)
            self.assertEqual(e.exception.campo, "nombre")

    def test_nombre_duplicado_sin_importar_tildes_ni_mayusculas(self):
        with self.assertRaises(ErrorValidacion):
            validar_nombre("LEÉR", ["Leer"])
        self.assertEqual(clave("  Ver  Series "), "ver series")

    def test_editar_puede_conservar_su_propio_nombre(self):
        self.assertEqual(validar_nombre("leer", ["Leer", "Escuchar música"], ignorar="Leer"), "leer")

    def test_cantidad_entera_en_rango(self):
        self.assertEqual(validar_cantidad(" 15 ", 100), 15)
        self.assertEqual(validar_cantidad("0", 100), 0)
        for malo in ("", "abc", "3.5", "2,5", "-1", "101"):
            with self.subTest(malo=malo), self.assertRaises(ErrorValidacion):
                validar_cantidad(malo, 100)

    def test_coherencia_con_la_poblacion(self):
        validar_coherencia(100, 100)
        with self.assertRaises(ErrorValidacion):
            validar_coherencia(101, 100)

    def test_poblacion_no_menor_que_lo_registrado(self):
        self.assertEqual(validar_poblacion("120", 100), 120)
        with self.assertRaises(ErrorValidacion):
            validar_poblacion("90", 100)
        with self.assertRaises(ErrorValidacion):
            validar_poblacion("0")


class PruebasIndicadores(unittest.TestCase):
    """Los indicadores con los datos de la guía deben dar las respuestas de la FASE 1."""

    def setUp(self):
        self.a = Almacen(":memory:")
        self.ind = calcular_indicadores(self.a.categorias(), self.a.poblacion())

    def tearDown(self):
        self.a.cerrar()

    def test_datos_originales(self):
        self.assertEqual(self.ind.total, 100)
        self.assertEqual(self.ind.sin_registrar, 0)
        self.assertEqual(self.ind.mas_frecuentes, ["Ver series o películas"])
        self.assertEqual(self.ind.menos_frecuentes, ["Otras actividades"])
        self.assertAlmostEqual(self.ind.promedio, 16.67)

    def test_empates(self):
        cats = [Categoria(1, "A", 5, None, "ingresado"), Categoria(2, "B", 5, None, "ingresado")]
        self.assertEqual(calcular_indicadores(cats, 10).mas_frecuentes, ["A", "B"])

    def test_lista_vacia(self):
        ind = calcular_indicadores([], 100)
        self.assertEqual((ind.total, ind.mas_frecuentes, ind.promedio), (0, [], 0.0))

    def test_pareto(self):
        from modelo import ordenadas
        acum = acumulados_pct(ordenadas(self.a.categorias()))
        self.assertEqual(acum, [28.0, 50.0, 68.0, 83.0, 93.0, 100.0])


class PruebasAlmacen(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.ruta = Path(self.dir.name) / "datos" / "encuesta.db"
        self.a = Almacen(self.ruta)

    def tearDown(self):
        self.a.cerrar()
        self.dir.cleanup()

    def test_crea_la_base_con_los_datos_de_la_guia(self):
        self.assertTrue(self.ruta.exists())
        self.assertEqual([(c.nombre, c.cantidad) for c in self.a.categorias()][0], ("Ver series o películas", 28))
        self.assertEqual(self.a.poblacion(), 100)

    def test_los_datos_persisten_al_reabrir(self):
        self.a.configurar("Encuesta", 120)
        self.a.agregar("Dibujar", 12)
        self.a.cerrar()
        self.a = Almacen(self.ruta)
        self.assertIn(("Dibujar", 12), [(c.nombre, c.cantidad) for c in self.a.categorias()])

    def test_no_permite_superar_la_poblacion(self):
        with self.assertRaises(ErrorValidacion):
            self.a.agregar("Dibujar", 1)          # ya hay 100 de 100
        self.assertEqual(self.a.suma(), 100)

    def test_actualizar_y_eliminar_quedan_en_el_historial(self):
        leer = next(c for c in self.a.categorias() if c.nombre == "Leer")
        self.a.actualizar(leer.id, "Leer libros", 8)
        self.assertEqual(self.a.suma(), 98)
        self.a.eliminar(leer.id)
        acciones = [h["accion"] for h in self.a.historial()]
        self.assertEqual(acciones[:2], ["Eliminar", "Actualizar"])
        self.assertIn("10 → 8", self.a.historial()[1]["detalle"])

    def test_actualizar_respeta_coherencia(self):
        leer = next(c for c in self.a.categorias() if c.nombre == "Leer")
        with self.assertRaises(ErrorValidacion):
            self.a.actualizar(leer.id, "Leer", 11)

    def test_restaurar_vuelve_a_los_originales(self):
        self.a.eliminar(self.a.categorias()[0].id)
        self.a.restaurar_originales()
        self.assertEqual(len(self.a.categorias()), 6)
        self.assertEqual(self.a.categorias()[0].id, 1)
        self.assertEqual(self.a.suma(), 100)

    def test_csv_ida_y_vuelta(self):
        archivo = Path(self.dir.name) / "datos.csv"
        self.a.exportar_csv(archivo)
        self.a.restaurar_originales()
        self.assertEqual(self.a.importar_csv(archivo), 6)
        self.assertEqual(self.a.suma(), 100)

    def test_csv_con_error_no_importa_nada(self):
        archivo = Path(self.dir.name) / "malo.csv"
        archivo.write_text("actividad,estudiantes\nCantar,10\n,5\nBailar,dos\n", encoding="utf-8")
        with self.assertRaises(ErrorValidacion) as e:
            self.a.importar_csv(archivo)
        self.assertIn("Línea 3", str(e.exception))
        self.assertIn("Línea 4", str(e.exception))
        self.assertEqual(len(self.a.categorias()), 6)

    def test_csv_que_supera_la_poblacion_se_rechaza(self):
        archivo = Path(self.dir.name) / "grande.csv"
        archivo.write_text("actividad;estudiantes\nCantar;60\nBailar;50\n", encoding="utf-8")
        with self.assertRaises(ErrorValidacion):
            self.a.importar_csv(archivo)


class PruebasGraficos(unittest.TestCase):
    def test_todos_los_tipos_se_generan(self):
        a = Almacen(":memory:")
        cats = a.categorias()
        with tempfile.TemporaryDirectory() as d:
            for i, tipo in enumerate(graficos.TIPOS):
                with self.subTest(tipo=tipo):
                    ruta = os.path.join(d, f"g{i}.png")
                    graficos.exportar_png(ruta, tipo, cats, 100, "Prueba", resaltar="Leer")
                    self.assertGreater(os.path.getsize(ruta), 10_000)
        a.cerrar()

    def test_barras_tienen_los_valores_ingresados(self):
        a = Almacen(":memory:")
        fig = Figure()
        graficos.dibujar(fig, graficos.TIPOS[0], a.categorias(), 100, "Prueba")
        alturas = [b.get_height() for b in fig.axes[0].patches]
        self.assertEqual(alturas, [28, 22, 18, 15, 10, 7])
        a.cerrar()

    def test_sin_datos_muestra_mensaje(self):
        fig = Figure()
        graficos.dibujar(fig, graficos.TIPOS[0], [], 100, "Vacío")
        self.assertIn("No hay datos", fig.axes[0].texts[0].get_text())


if __name__ == "__main__":
    unittest.main()
