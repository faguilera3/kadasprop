# Extractor de Lotes Catastrales

Este programa en Python procesa imágenes de planos catastrales y extrae automáticamente los lotes individuales, recortándolos con precisión incluso si tienen formas irregulares.

## Requisitos

Instala las dependencias necesarias:

```bash
pip install -r requirements.txt
```

## Uso

Ejecuta el script proporcionando la ruta de la imagen del plano:

```bash
python extractor_lotes.py ruta/a/tu/plano.jpg
```

### Opciones

- `--out`: Directorio donde se guardarán los recortes (por defecto: `lotes_extraidos`).
- `--min_area`: Área mínima en píxeles para considerar un lote (por defecto: `5000`). Ajusta esto si tus lotes son muy pequeños o si detecta mucho ruido.

Ejemplo:

```bash
python extractor_lotes.py plano_catastral.png --out mis_lotes --min_area 2000
```

## Características

- **Detección de formas irregulares**: No se limita a rectángulos; detecta polígonos complejos.
- **Enmascaramiento preciso**: El recorte final tiene el fondo transparente o blanco fuera de los límites del lote.
- **Filtrado inteligente**: Ignora márgenes, marcos y texto pequeño.
- **Imagen de depuración**: Genera `debug_detected_lots.jpg` en la carpeta de salida para verificar qué se detectó.
