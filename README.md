# Kadasprop - Extractor de InfoMapa Rosario

Una herramienta moderna para buscar, visualizar y extraer datos de lotes y mapas oficiales de la Municipalidad de Rosario.

## Características

*   **Búsqueda Inteligente:** Encuentra direcciones y alturas exactas.
*   **Mapa Interactivo:** Visualiza capas oficiales (catastro, infraestructura, normas) sobre un mapa Leaflet.
*   **Extracción Automática:** Utiliza API oficial para capturar el plano oficial y LLMs para extraer datos de lotes.
*   **Historial:** Guarda tus búsquedas y recupera los datos en cualquier momento.

## Tecnologías

*   **Backend:** Python, FastAPI, Requests, LangChain.
*   **Frontend:** Vue 3, TypeScript, Tailwind CSS, Leaflet.
*   **Infraestructura:** Docker, Nginx.

## Instalación (Desarrollo)

1.  Clonar el repositorio.
2.  Configurar `.env` con `OPENAI_API_KEY`.
3.  Instalar dependencias de backend:
    ```bash
    pip install -r requirements.txt
    ```
4.  Instalar dependencias de frontend:
    ```bash
    cd frontend
    npm install
    ```
5.  Correr ambos servidores.

## Despliegue

Ver [DEPLOY.md](DEPLOY.md) para instrucciones detalladas de producción con Docker.
