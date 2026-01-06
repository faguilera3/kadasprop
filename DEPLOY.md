# Guía de Despliegue para Kadasprop

Esta aplicación utiliza Docker para facilitar el despliegue. Al usar Playwright (navegadores) y almacenamiento de archivos, se recomienda usar un servidor VPS (Virtual Private Server).

## Requisitos Previos

1.  Una cuenta en **GitHub** (para subir tu código).
2.  Una cuenta en un proveedor de nube (**DigitalOcean**, **AWS**, **Hetzner**, etc.).
3.  Tu `OPENAI_API_KEY`.

---

## Paso 1: Subir el código a GitHub

Desde tu terminal local (asegúrate de tener Git instalado):

```bash
# 1. Inicializar repositorio
git init

# 2. Agregar archivos
git add .

# 3. Guardar cambios
git commit -m "Initial commit: Kadasprop app"

# 4. Crear el repositorio "kadasprop" en GitHub.com y copiar el link.
# 5. Conectar y subir (reemplaza TU_USUARIO)
git remote add origin https://github.com/TU_USUARIO/kadasprop.git
git branch -M main
git push -u origin main
```

---

## Paso 2: Configurar el Servidor (VPS)

1.  Crea un nuevo servidor (**Droplet** en DigitalOcean o **EC2** en AWS).
    *   **OS:** Ubuntu 22.04 (LTS) x64.
    *   **RAM:** Mínimo 2GB (4GB recomendado).
2.  Conéctate por SSH:
    ```bash
    ssh root@TU_IP_DEL_SERVIDOR
    ```

---

## Paso 3: Instalación en el Servidor

Una vez dentro de la terminal del servidor:

1.  **Instalar Docker:**
    ```bash
    snap install docker
    # Opcional: Instalar git si no viene
    apt update && apt install git -y
    ```

2.  **Clonar tu código:**
    ```bash
    git clone https://github.com/TU_USUARIO/kadasprop.git
    cd kadasprop
    ```

3.  **Configurar Variables de Entorno:**
    Crea el archivo `.env`:
    ```bash
    nano .env
    ```
    Pega tu clave dentro:
    ```
    OPENAI_API_KEY=sk-tus-claves-aqui...
    ```
    *(Guarda con `Ctrl+O`, `Enter`, y sal con `Ctrl+X`)*

4.  **Iniciar la Aplicación:**
    ```bash
    docker-compose up -d --build
    ```

---

## Mantenimiento

*   **Ver si está corriendo:**
    ```bash
    docker-compose ps
    ```

*   **Ver logs (errores):**
    ```bash
    docker-compose logs -f
    ```

*   **Actualizar la aplicación (cuando hagas cambios en el código):**
    ```bash
    git pull
    docker-compose up -d --build
    ```

*   **Detener todo:**
    ```bash
    docker-compose down
    ```

## Acceso

Tu aplicación estará disponible en: `http://TU_IP_DEL_SERVIDOR`
