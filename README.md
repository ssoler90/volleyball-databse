# Volleyball Database

<<<<<<< HEAD
This project aims to build a comprehensive volleyball database,
starting with the Polish PlusLiga, using web scraping and data processing.

## Structure
- `scripts/`: scraping and processing scripts.
- `data/raw`: raw data obtained from sources.
- `data/processed`: cleaned and transformed data.
- `notebooks/`: exploratory analysis and validations.

## Project Status
- [x] Scraping of PlusLiga team names.
- [ ] Scraping of match schedule.
- [ ] Statistics per match.
=======
Este repositorio construye una **base de datos de voleibol** empezando por PlusLiga (Polonia) mediante *web scraping*, limpieza y análisis reproducibles.

## Estructura
```
volleyball-database/
├── data/
│   ├── raw/        # Datos crudos obtenidos de las fuentes
│   └── processed/  # Datos limpios/listos para análisis
├── notebooks/      # Jupyter notebooks de exploración y validación
├── scripts/        # Scripts de scraping, limpieza y ETL
├── README.md       # Esta descripción del proyecto
└── requirements.txt# Dependencias de Python
```

## Cómo usar
1. Crea y activa un entorno (recomendado):
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Windows: .venv\Scripts\activate
   ```
2. Instala dependencias:
   ```bash
   pip install -r requirements.txt
   ```
3. Ejecuta scripts desde `scripts/` y guarda resultados en `data/raw` o `data/processed`.
4. Usa `notebooks/` para el EDA y validaciones.

## Buenas prácticas
- Commits pequeños y descriptivos.
- Mantén `data/raw` inmutable; toda transformación debe dejar trazabilidad hacia `data/processed`.
- Añade *fuentes y licencias* de los datos en los notebooks/README correspondientes.
>>>>>>> c76f5ac (Initial structure of the project volleyball-database)
