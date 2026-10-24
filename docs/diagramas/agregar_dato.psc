// Diagrama de flujo "Agregar un dato" del Visualizador de Encuestas (Guía 9).
// Abrir con PSeInt y usar "Dibujar diagrama de flujo". Equivale a Almacen.agregar() en app/almacen.py.
Algoritmo AgregarDato
	Definir poblacion, suma, cantidad, n, i Como Entero
	Definir nombre, texto Como Caracter
	Definir valido, repetido Como Logico
	Dimension actividades[15]
	Dimension estudiantes[15]
	// Datos originales de la guía
	actividades[1] <- "ver series o peliculas"; estudiantes[1] <- 28
	actividades[2] <- "escuchar musica";        estudiantes[2] <- 22
	actividades[3] <- "practicar deporte";      estudiantes[3] <- 18
	actividades[4] <- "jugar videojuegos";      estudiantes[4] <- 15
	actividades[5] <- "leer";                   estudiantes[5] <- 10
	actividades[6] <- "otras actividades";      estudiantes[6] <- 7
	n <- 6
	Escribir "Poblacion encuestada:"
	Leer poblacion
	valido <- Falso
	Mientras No valido Hacer
		Escribir "Actividad:"
		Leer nombre
		Escribir "Numero de estudiantes:"
		Leer cantidad
		suma <- 0
		repetido <- Falso
		Para i <- 1 Hasta n Hacer
			suma <- suma + estudiantes[i]
			Si actividades[i] = Minusculas(nombre) Entonces
				repetido <- Verdadero
			FinSi
		FinPara
		Si Longitud(nombre) < 2 O Longitud(nombre) > 40 Entonces
			Escribir "Error: el nombre debe tener entre 2 y 40 caracteres"
		SiNo
			Si repetido Entonces
				Escribir "Error: la actividad ya existe"
			SiNo
				Si cantidad < 0 O cantidad > poblacion Entonces
					Escribir "Error: la cantidad debe estar entre 0 y ", poblacion
				SiNo
					Si suma + cantidad > poblacion Entonces
						Escribir "Error: la suma seria ", suma + cantidad, " y la poblacion es ", poblacion
					SiNo
						valido <- Verdadero
					FinSi
				FinSi
			FinSi
		FinSi
	FinMientras
	n <- n + 1
	actividades[n] <- Minusculas(nombre)
	estudiantes[n] <- cantidad
	Escribir "Guardado. Se redibuja el grafico con ", n, " actividades"
	Para i <- 1 Hasta n Hacer
		Escribir actividades[i], ": ", estudiantes[i], " (", estudiantes[i] * 100 / poblacion, " %)"
	FinPara
FinAlgoritmo
