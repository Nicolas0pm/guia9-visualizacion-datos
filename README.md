# Visualizador de Encuestas — Guía 9 (Business Analytics e IA)

Aplicación de escritorio **portable** (no web) para ingresar los datos de una encuesta, validarlos, guardarlos en
SQLite y generar gráficos e indicadores de forma automática. Trae cargada la encuesta de la FASE 1 (100 estudiantes,
6 actividades).

| Capa | Archivo | Tecnología |
|---|---|---|
| Presentación | `app/interfaz.py` | Tkinter + matplotlib (FigureCanvasTkAgg) |
| Reglas del negocio | `app/modelo.py` | validación, coherencia, KPI |
| Datos | `app/almacen.py` | SQLite (`datos/encuesta.db` junto al .exe), historial, CSV |
| Gráficos | `app/graficos.py` | 5 tipos: barras, horizontales %, dona, Pareto, comparación |

## Entrega

- `entrega/VisualizadorEncuestas/` — el `.exe` portable (no está en git por su tamaño), LEEME y CSV de ejemplo.
- `entrega/Fase1_Interpretacion_de_datos.docx` — respuestas, propuesta de gráfico, reto y conclusiones.
- `entrega/Fase2_Documentacion_Software.docx` — requisitos, arquitectura, diagramas, pruebas y manual.

## Desarrollo

```bash
python -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python app/main.py            # abrir la aplicación
.venv/bin/python -m unittest -v         # 23 pruebas
.venv/bin/python docs/generar_diagramas.py
.venv/bin/python docs/generar_documentos.py
```

## Construir el .exe

En Windows con Python 3.12: `construir_windows.bat` (instala, prueba y empaqueta en `dist\VisualizadorEncuestas`).
También lo hace el workflow `.github/workflows/construir-exe.yml` en cada push.

Desde Linux se puede construir con Python para Windows dentro de Wine:

```bash
wine python.exe -m PyInstaller --noconfirm --onefile --windowed --name VisualizadorEncuestas --paths app app/main.py
```
