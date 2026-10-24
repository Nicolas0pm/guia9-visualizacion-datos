@echo off
REM Genera dist\VisualizadorEncuestas\ con el .exe portable, lista para copiar a una USB o a otro equipo.
REM Requisito solo en el equipo que construye: Python 3.12 para Windows.
cd /d %~dp0
python -m venv .venv-build || goto :error
call .venv-build\Scripts\activate.bat
pip install -r requirements.txt || goto :error
python -m unittest || goto :error
pyinstaller --noconfirm --onefile --windowed --name VisualizadorEncuestas --paths app --distpath dist\VisualizadorEncuestas app\main.py || goto :error
copy /Y LEEME.txt dist\VisualizadorEncuestas\LEEME.txt
copy /Y ejemplos\encuesta_ejemplo.csv dist\VisualizadorEncuestas\encuesta_ejemplo.csv
echo.
echo Listo: la carpeta dist\VisualizadorEncuestas tiene el programa portable.
exit /b 0
:error
echo Fallo la construccion.
exit /b 1
