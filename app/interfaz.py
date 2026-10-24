"""Ventana principal: formulario de ingreso, tabla, indicadores, gráfico e historial.

La interfaz no valida por su cuenta: le pasa lo escrito al Almacen, que aplica las reglas de
modelo.py, y si algo falla muestra el mensaje junto al campo que hay que corregir. Después de cada
cambio se llama a refrescar(), que vuelve a leer la base y redibuja tabla, indicadores y gráfico,
así el gráfico siempre corresponde a lo que está guardado.
"""
from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

import matplotlib

matplotlib.use("TkAgg")
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk  # noqa: E402
from matplotlib.figure import Figure  # noqa: E402

import graficos  # noqa: E402
from almacen import Almacen  # noqa: E402
from modelo import ErrorValidacion, calcular_indicadores, porcentaje  # noqa: E402

ROJO = "#c0392b"
FONDO_KPI = "#eef3f9"
NOMBRE_APP = "Visualizador de Encuestas"
VERSION = "1.0"


def carpeta_documentos() -> Path:
    for candidata in (Path.home() / "Documents", Path.home() / "Documentos", Path.home()):
        if candidata.exists():
            return candidata
    return Path.home()


class Tarjeta(ttk.Frame):
    """Recuadro de un indicador (KPI): título pequeño arriba y valor grande abajo."""

    def __init__(self, padre, titulo: str):
        super().__init__(padre, style="Kpi.TFrame", padding=(12, 8))
        ttk.Label(self, text=titulo, style="KpiTitulo.TLabel").pack(anchor="w")
        self.valor = ttk.Label(self, text="—", style="KpiValor.TLabel")
        self.valor.pack(anchor="w")
        self.detalle = ttk.Label(self, text="", style="KpiTitulo.TLabel")
        self.detalle.pack(anchor="w")

    def mostrar(self, valor: str, detalle: str = "") -> None:
        self.valor.configure(text=valor)
        self.detalle.configure(text=detalle)


class Aplicacion(tk.Tk):
    def __init__(self, almacen: Almacen):
        super().__init__()
        self.almacen = almacen
        self.id_seleccionado: int | None = None
        self.resaltar: str | None = None          # actividad que se pinta en naranja
        self.title(f"{NOMBRE_APP} — Guía 9 Business Analytics")
        self.geometry("1280x760")
        self.minsize(1080, 640)
        self._estilos()
        self._menu()
        self._construir()
        self.protocol("WM_DELETE_WINDOW", self.salir)
        self.refrescar()
        self.avisar(f"Listo. Los datos se guardan en {self.almacen.ruta}")
        self.e_nombre.focus_set()

    # ---------- construcción de la ventana ----------

    def _estilos(self) -> None:
        estilo = ttk.Style(self)
        if "clam" in estilo.theme_names():
            estilo.theme_use("clam")
        estilo.configure("Kpi.TFrame", background=FONDO_KPI)
        estilo.configure("KpiTitulo.TLabel", background=FONDO_KPI, foreground="#55606e", font=("Segoe UI", 9))
        estilo.configure("KpiValor.TLabel", background=FONDO_KPI, foreground="#1f4e79",
                         font=("Segoe UI", 15, "bold"))
        estilo.configure("Error.TLabel", foreground=ROJO, font=("Segoe UI", 9))
        estilo.configure("Seccion.TLabelframe.Label", font=("Segoe UI", 10, "bold"))
        estilo.configure("Treeview", rowheight=24)
        estilo.configure("Accion.TButton", font=("Segoe UI", 10, "bold"))

    def _menu(self) -> None:
        barra = tk.Menu(self)
        archivo = tk.Menu(barra, tearoff=False)
        archivo.add_command(label="Importar CSV…", command=self.importar_csv)
        archivo.add_command(label="Exportar datos a CSV…", command=self.exportar_csv)
        archivo.add_command(label="Exportar gráfico a PNG…", command=self.exportar_png)
        archivo.add_separator()
        archivo.add_command(label="Restaurar datos originales de la guía", command=self.restaurar)
        archivo.add_separator()
        archivo.add_command(label="Salir", command=self.salir)
        barra.add_cascade(label="Archivo", menu=archivo)
        ayuda = tk.Menu(barra, tearoff=False)
        ayuda.add_command(label="Cómo usar", command=self.mostrar_ayuda)
        ayuda.add_command(label="Acerca de", command=self.acerca_de)
        barra.add_cascade(label="Ayuda", menu=ayuda)
        self.configure(menu=barra)

    def _construir(self) -> None:
        # La barra de estado se empaqueta primero para que no desaparezca si la ventana es pequeña.
        self.estado = ttk.Label(self, text="", relief="sunken", anchor="w", padding=(8, 2))
        self.estado.pack(fill="x", side="bottom")
        raiz = ttk.Frame(self, padding=10)
        raiz.pack(fill="both", expand=True)

        # Encuesta: título y población (denominador de todos los porcentajes)
        enc = ttk.LabelFrame(raiz, text="Encuesta", style="Seccion.TLabelframe", padding=(10, 6))
        enc.pack(fill="x")
        ttk.Label(enc, text="Título:").grid(row=0, column=0, sticky="w")
        self.v_titulo = tk.StringVar()
        self.e_titulo = ttk.Entry(enc, textvariable=self.v_titulo, width=48)
        self.e_titulo.grid(row=0, column=1, sticky="we", padx=(4, 16))
        ttk.Label(enc, text="Población encuestada:").grid(row=0, column=2, sticky="w")
        self.v_poblacion = tk.StringVar()
        self.e_poblacion = ttk.Entry(enc, textvariable=self.v_poblacion, width=10,
                                     validate="key", validatecommand=(self.register(_solo_digitos), "%P"))
        self.e_poblacion.grid(row=0, column=3, sticky="w", padx=(4, 8))
        ttk.Button(enc, text="Aplicar", command=self.aplicar_encuesta).grid(row=0, column=4)
        self.err_encuesta = ttk.Label(enc, text="", style="Error.TLabel")
        self.err_encuesta.grid(row=1, column=0, columnspan=5, sticky="w")
        enc.columnconfigure(1, weight=1)

        # Indicadores
        kpis = ttk.Frame(raiz)
        kpis.pack(fill="x", pady=8)
        self.k_total = Tarjeta(kpis, "Estudiantes registrados")
        self.k_mas = Tarjeta(kpis, "Actividad más frecuente")
        self.k_menos = Tarjeta(kpis, "Actividad menos frecuente")
        self.k_prom = Tarjeta(kpis, "Promedio por actividad")
        for i, t in enumerate((self.k_total, self.k_mas, self.k_menos, self.k_prom)):
            t.grid(row=0, column=i, sticky="nsew", padx=(0 if i == 0 else 8, 0))
            kpis.columnconfigure(i, weight=1, uniform="kpi")

        cuerpo = ttk.PanedWindow(raiz, orient="horizontal")
        cuerpo.pack(fill="both", expand=True)
        izq = ttk.Frame(cuerpo, padding=(0, 0, 8, 0))
        der = ttk.Frame(cuerpo)
        cuerpo.add(izq, weight=2)
        cuerpo.add(der, weight=5)

        # Formulario de ingreso
        form = ttk.LabelFrame(izq, text="Ingreso de datos", style="Seccion.TLabelframe", padding=10)
        form.pack(fill="x")
        ttk.Label(form, text="Actividad:").grid(row=0, column=0, sticky="w")
        self.v_nombre = tk.StringVar()
        self.e_nombre = ttk.Entry(form, textvariable=self.v_nombre, width=30)
        self.e_nombre.grid(row=0, column=1, sticky="we", padx=(6, 0))
        self.err_nombre = ttk.Label(form, text="", style="Error.TLabel", wraplength=300)
        self.err_nombre.grid(row=1, column=1, sticky="w", padx=(6, 0))
        ttk.Label(form, text="N.º de estudiantes:").grid(row=2, column=0, sticky="w")
        self.v_cantidad = tk.StringVar()
        self.e_cantidad = ttk.Entry(form, textvariable=self.v_cantidad, width=10,
                                    validate="key", validatecommand=(self.register(_solo_digitos), "%P"))
        self.e_cantidad.grid(row=2, column=1, sticky="w", padx=(6, 0))
        self.err_cantidad = ttk.Label(form, text="", style="Error.TLabel", wraplength=300)
        self.err_cantidad.grid(row=3, column=1, sticky="w", padx=(6, 0))
        self.l_disponible = ttk.Label(form, text="", foreground="#55606e")
        self.l_disponible.grid(row=4, column=0, columnspan=2, sticky="w", pady=(2, 6))
        botones = ttk.Frame(form)
        botones.grid(row=5, column=0, columnspan=2, sticky="we")
        self.b_agregar = ttk.Button(botones, text="Agregar", style="Accion.TButton", command=self.agregar)
        self.b_actualizar = ttk.Button(botones, text="Actualizar", command=self.actualizar)
        self.b_eliminar = ttk.Button(botones, text="Eliminar", command=self.eliminar)
        self.b_limpiar = ttk.Button(botones, text="Limpiar", command=self.limpiar_formulario)
        for i, b in enumerate((self.b_agregar, self.b_actualizar, self.b_eliminar, self.b_limpiar)):
            b.grid(row=0, column=i, sticky="we", padx=(0 if i == 0 else 4, 0))
            botones.columnconfigure(i, weight=1)
        form.columnconfigure(1, weight=1)
        for e in (self.e_nombre, self.e_cantidad):
            e.bind("<Return>", lambda _ev: self.actualizar() if self.id_seleccionado else self.agregar())

        # Tabla de datos
        tabla = ttk.LabelFrame(izq, text="Datos registrados", style="Seccion.TLabelframe", padding=6)
        tabla.pack(fill="both", expand=True, pady=(8, 0))
        cols = ("nombre", "cantidad", "pct", "origen")
        self.tabla = ttk.Treeview(tabla, columns=cols, show="headings", selectmode="browse", height=10)
        for col, texto, ancho, ancla in (("nombre", "Actividad", 180, "w"), ("cantidad", "Estudiantes", 80, "e"),
                                         ("pct", "% población", 80, "e"), ("origen", "Origen", 80, "center")):
            self.tabla.heading(col, text=texto)
            self.tabla.column(col, width=ancho, anchor=ancla, stretch=col == "nombre")
        self.tabla.tag_configure("par", background="#f6f8fb")
        self.tabla.pack(fill="both", expand=True)
        self.tabla.bind("<<TreeviewSelect>>", self._al_seleccionar)
        self.tabla.bind("<Delete>", lambda _ev: self.eliminar())
        self.l_total = ttk.Label(tabla, text="", font=("Segoe UI", 9, "bold"))
        self.l_total.pack(anchor="e", pady=(4, 0))

        # Pestañas: gráfico e historial
        pestanas = ttk.Notebook(der)
        pestanas.pack(fill="both", expand=True)
        self.pestanas = pestanas
        pg = ttk.Frame(pestanas, padding=6)
        pestanas.add(pg, text="Gráfico")
        arriba = ttk.Frame(pg)
        arriba.pack(fill="x")
        ttk.Label(arriba, text="Tipo de gráfico:").pack(side="left")
        self.v_tipo = tk.StringVar(value=graficos.TIPOS[0])
        tipo = ttk.Combobox(arriba, textvariable=self.v_tipo, values=graficos.TIPOS, state="readonly", width=36)
        tipo.pack(side="left", padx=6)
        tipo.bind("<<ComboboxSelected>>", lambda _ev: self.redibujar())
        ttk.Button(arriba, text="Exportar PNG…", command=self.exportar_png).pack(side="right")
        self.figura = Figure(figsize=(8, 5), dpi=100, layout="constrained")
        self.lienzo = FigureCanvasTkAgg(self.figura, master=pg)
        barra = NavigationToolbar2Tk(self.lienzo, pg, pack_toolbar=False)
        barra.update()
        barra.pack(side="bottom", fill="x")
        self.lienzo.get_tk_widget().pack(fill="both", expand=True, pady=(6, 0))

        ph = ttk.Frame(pestanas, padding=6)
        pestanas.add(ph, text="Historial de cambios")
        self.hist = ttk.Treeview(ph, columns=("fecha", "accion", "detalle"), show="headings")
        for col, texto, ancho in (("fecha", "Fecha y hora", 140), ("accion", "Acción", 110), ("detalle", "Detalle", 520)):
            self.hist.heading(col, text=texto)
            self.hist.column(col, width=ancho, stretch=col == "detalle")
        barra_h = ttk.Scrollbar(ph, orient="vertical", command=self.hist.yview)
        self.hist.configure(yscrollcommand=barra_h.set)
        self.hist.pack(side="left", fill="both", expand=True)
        barra_h.pack(side="right", fill="y")

    # ---------- refresco ----------

    def refrescar(self) -> None:
        """Lee la base y actualiza todo lo que se ve. Se llama después de cada cambio."""
        categorias = self.almacen.categorias()
        poblacion = self.almacen.poblacion()
        self.v_titulo.set(self.almacen.titulo())
        self.v_poblacion.set(str(poblacion))

        self.tabla.delete(*self.tabla.get_children())
        for i, c in enumerate(categorias):
            self.tabla.insert("", "end", iid=str(c.id), tags=("par",) if i % 2 else (),
                              values=(c.nombre, c.cantidad, f"{porcentaje(c.cantidad, poblacion):g} %", c.origen))
        if self.id_seleccionado and self.tabla.exists(str(self.id_seleccionado)):
            self.tabla.selection_set(str(self.id_seleccionado))
        else:
            self.id_seleccionado = None

        ind = calcular_indicadores(categorias, poblacion)
        self.l_total.configure(text=f"Total: {ind.total} de {poblacion} estudiantes ({ind.cobertura_pct:g} %)")
        self.l_disponible.configure(
            text=f"Quedan {ind.sin_registrar} estudiantes por asignar de {poblacion}." if ind.sin_registrar
            else f"Los {poblacion} estudiantes de la encuesta ya están asignados.")
        self.k_total.mostrar(f"{ind.total} / {poblacion}", f"Cobertura {ind.cobertura_pct:g} %")
        self.k_mas.mostrar(_corto(" / ".join(ind.mas_frecuentes) or "—"),
                           f"{ind.maximo} estudiantes ({porcentaje(ind.maximo, poblacion):g} %)" if categorias else "")
        self.k_menos.mostrar(_corto(" / ".join(ind.menos_frecuentes) or "—"),
                             f"{ind.minimo} estudiantes ({porcentaje(ind.minimo, poblacion):g} %)" if categorias else "")
        self.k_prom.mostrar(f"{ind.promedio:g}", f"{len(categorias)} actividades")

        self.hist.delete(*self.hist.get_children())
        for fila in self.almacen.historial():
            self.hist.insert("", "end", values=(fila["fecha"], fila["accion"], fila["detalle"]))

        self._botones()
        self.redibujar(categorias, poblacion)

    def redibujar(self, categorias=None, poblacion=None) -> None:
        """Genera el gráfico elegido con los datos guardados."""
        categorias = self.almacen.categorias() if categorias is None else categorias
        poblacion = self.almacen.poblacion() if poblacion is None else poblacion
        graficos.dibujar(self.figura, self.v_tipo.get(), categorias, poblacion, self.almacen.titulo(),
                         self.resaltar)
        self.lienzo.draw_idle()

    def _botones(self) -> None:
        hay = "!disabled" if self.id_seleccionado else "disabled"
        self.b_actualizar.state([hay])
        self.b_eliminar.state([hay])

    # ---------- acciones del formulario ----------

    def _limpiar_errores(self) -> None:
        for l in (self.err_nombre, self.err_cantidad, self.err_encuesta):
            l.configure(text="")
        for e in (self.e_titulo, self.e_poblacion, self.e_nombre, self.e_cantidad):
            e.selection_clear()

    def _mostrar_error(self, e: ErrorValidacion) -> None:
        """Pone el mensaje junto al campo responsable y le da el foco."""
        destino = {"nombre": (self.err_nombre, self.e_nombre), "cantidad": (self.err_cantidad, self.e_cantidad),
                   "poblacion": (self.err_encuesta, self.e_poblacion), "titulo": (self.err_encuesta, self.e_titulo)}
        if e.campo in destino:
            etiqueta, entrada = destino[e.campo]
            etiqueta.configure(text=str(e))
            entrada.focus_set()
            entrada.select_range(0, "end")
        else:
            messagebox.showwarning(NOMBRE_APP, str(e), parent=self)
        self.avisar(f"No se guardó: {e}")

    def agregar(self) -> None:
        self._limpiar_errores()
        try:
            nueva = self.almacen.agregar(self.v_nombre.get(), self.v_cantidad.get())
        except ErrorValidacion as e:
            self._mostrar_error(e)
            return
        self.resaltar = nueva.nombre
        self.limpiar_formulario(conservar_resaltado=True)
        self.refrescar()
        self.avisar(f"Se agregó «{nueva.nombre}» con {nueva.cantidad} estudiantes. El gráfico la muestra en naranja.")

    def actualizar(self) -> None:
        if not self.id_seleccionado:
            return
        self._limpiar_errores()
        try:
            cat = self.almacen.actualizar(self.id_seleccionado, self.v_nombre.get(), self.v_cantidad.get())
        except ErrorValidacion as e:
            self._mostrar_error(e)
            return
        self.resaltar = cat.nombre
        self.refrescar()
        self.avisar(f"Se actualizó «{cat.nombre}»: {cat.cantidad} estudiantes.")

    def eliminar(self) -> None:
        if not self.id_seleccionado:
            return
        nombre = self.v_nombre.get() or "la actividad"
        if not messagebox.askyesno(NOMBRE_APP, f"¿Eliminar «{nombre}»? El cambio queda en el historial.", parent=self):
            return
        try:
            self.almacen.eliminar(self.id_seleccionado)
        except ErrorValidacion as e:
            self._mostrar_error(e)
            return
        self.limpiar_formulario()
        self.refrescar()
        self.avisar(f"Se eliminó «{nombre}».")

    def limpiar_formulario(self, conservar_resaltado: bool = False) -> None:
        self._limpiar_errores()
        self.v_nombre.set("")
        self.v_cantidad.set("")
        self.id_seleccionado = None
        if not conservar_resaltado:
            self.resaltar = None
        self.tabla.selection_remove(*self.tabla.selection())
        self._botones()
        self.e_nombre.focus_set()
        if not conservar_resaltado:
            self.redibujar()

    def _al_seleccionar(self, _ev=None) -> None:
        sel = self.tabla.selection()
        if not sel:
            return
        self._limpiar_errores()
        self.id_seleccionado = int(sel[0])
        nombre, cantidad, *_ = self.tabla.item(sel[0], "values")
        self.v_nombre.set(nombre)
        self.v_cantidad.set(cantidad)
        self.resaltar = nombre
        self._botones()
        self.redibujar()

    def aplicar_encuesta(self) -> None:
        self._limpiar_errores()
        try:
            self.almacen.configurar(self.v_titulo.get(), self.v_poblacion.get())
        except ErrorValidacion as e:
            self._mostrar_error(e)
            return
        self.refrescar()
        self.avisar("Se actualizaron el título y la población de la encuesta.")

    # ---------- archivo ----------

    def importar_csv(self) -> None:
        ruta = filedialog.askopenfilename(parent=self, title="Importar CSV", initialdir=carpeta_documentos(),
                                          filetypes=[("CSV", "*.csv"), ("Todos", "*.*")])
        if not ruta:
            return
        reemplazar = messagebox.askyesnocancel(
            NOMBRE_APP, "¿Reemplazar los datos actuales con los del archivo?\n\n"
                        "Sí: reemplazar.   No: agregar a los actuales.", parent=self)
        if reemplazar is None:
            return
        try:
            n = self.almacen.importar_csv(ruta, reemplazar=reemplazar)
        except (ErrorValidacion, OSError, UnicodeDecodeError) as e:
            messagebox.showerror(NOMBRE_APP, str(e), parent=self)
            return
        self.limpiar_formulario()
        self.refrescar()
        self.avisar(f"Se importaron {n} actividades desde {Path(ruta).name}.")

    def exportar_csv(self) -> None:
        ruta = filedialog.asksaveasfilename(parent=self, title="Exportar datos", defaultextension=".csv",
                                            initialdir=carpeta_documentos(), initialfile="encuesta.csv",
                                            filetypes=[("CSV", "*.csv")])
        if not ruta:
            return
        try:
            self.almacen.exportar_csv(ruta)
        except OSError as e:
            messagebox.showerror(NOMBRE_APP, f"No se pudo guardar: {e}", parent=self)
            return
        self.refrescar()
        self.avisar(f"Datos exportados a {ruta}")

    def exportar_png(self) -> None:
        nombre = self.v_tipo.get().split(" (")[0].lower().replace(" ", "_")
        ruta = filedialog.asksaveasfilename(parent=self, title="Exportar gráfico", defaultextension=".png",
                                            initialdir=carpeta_documentos(), initialfile=f"grafico_{nombre}.png",
                                            filetypes=[("Imagen PNG", "*.png")])
        if not ruta:
            return
        try:
            graficos.exportar_png(ruta, self.v_tipo.get(), self.almacen.categorias(), self.almacen.poblacion(),
                                  self.almacen.titulo(), self.resaltar)
        except OSError as e:
            messagebox.showerror(NOMBRE_APP, f"No se pudo guardar: {e}", parent=self)
            return
        self.avisar(f"Gráfico guardado en {ruta}")

    def restaurar(self) -> None:
        if not messagebox.askyesno(NOMBRE_APP, "Se reemplazarán los datos actuales por los 6 datos originales de "
                                               "la guía (100 estudiantes). El historial se conserva. ¿Continuar?",
                                   parent=self):
            return
        self.almacen.restaurar_originales()
        self.limpiar_formulario()
        self.refrescar()
        self.avisar("Se restauraron los datos originales de la guía.")

    def mostrar_ayuda(self) -> None:
        messagebox.showinfo(NOMBRE_APP, (
            "1. Escriba la actividad y el número de estudiantes y pulse Agregar (o Enter).\n"
            "2. Para corregir un dato, selecciónelo en la tabla, cámbielo y pulse Actualizar.\n"
            "3. Elija el tipo de gráfico arriba del gráfico; se genera solo con los datos guardados.\n"
            "4. La suma de estudiantes no puede pasar de la población encuestada.\n"
            "5. Todo cambio queda en la pestaña Historial de cambios.\n\n"
            f"Los datos se guardan en:\n{self.almacen.ruta}"), parent=self)

    def acerca_de(self) -> None:
        messagebox.showinfo(NOMBRE_APP, (
            f"{NOMBRE_APP} {VERSION}\n"
            "Guía 9 — Business Analytics e Inteligencia Artificial\n"
            "Inteligencia de Negocios Avanzada y Toma de Decisiones\n\n"
            "Python · Tkinter · matplotlib · SQLite\nAplicación portable, no requiere instalación."), parent=self)

    def avisar(self, texto: str) -> None:
        self.estado.configure(text=texto)

    def salir(self) -> None:
        self.almacen.cerrar()
        self.destroy()


def _solo_digitos(propuesto: str) -> bool:
    """Filtro de teclado: el campo solo acepta dígitos (máx. 7). La regla completa está en modelo.py."""
    return propuesto == "" or (propuesto.isdigit() and len(propuesto) <= 7)


def _corto(texto: str, largo: int = 24) -> str:
    return texto if len(texto) <= largo else texto[: largo - 1] + "…"
