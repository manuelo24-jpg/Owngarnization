# Owngarnization 📋🗓️

> Aplicación web minimalista y elegante de gestión de tareas y rutinas con calendario interactivo (mes, semana y día), tablero de post-its reordenables y aislamiento de datos por usuario. Diseñada para desplegarse fácilmente en plataformas gratuitas (como Render + Neon o PythonAnywhere).

---

## 📑 Tabla de Contenidos

1. [Descripción General](#-descripción-general)
2. [Características Principales](#-características-principales)
3. [Stack Tecnológico](#-stack-tecnológico)
4. [Estructura del Proyecto](#-estructura-del-proyecto)
5. [Modelo de Datos](#-modelo-de-datos)
6. [API REST (Endpoints)](#-api-rest-endpoints)
7. [Diseño Visual y Sistema de Estilos](#-diseño-visual-y-sistema-de-estilos)
8. [Requisitos Previos e Instalación Local](#-requisitos-previos-e-instalación-local)
9. [Variables de Entorno](#-variables-de-entorno)
10. [Ejecución y Pruebas](#-ejecución-y-pruebas)
11. [Guía de Despliegue Gratuito](#-guía-de-despliegue-gratuito)
12. [Estado del Plan de Implementación](#-estado-del-plan-de-implementación)

---

## 🌟 Descripción General

**Owngarnization** combina la flexibilidad de un calendario con la agilidad visual de un tablero de post-its físicos. Permite a los usuarios organizar su día a día sin fricciones, distinguiendo entre **tareas comunes** (rutinas diarias automáticas como "beber agua" o "revisar correo") y **tareas del día** (puntuales para una fecha específica).

Cada día mantiene un **estado independiente** para cada tarea (pudiendo completar una rutina hoy sin que afecte a la de mañana) y permite ordenar los post-its manualmente con **drag & drop** persistente.

---

## ✨ Características Principales

- 🔐 **Autenticación y Privacidad Total**: Registro, inicio y cierre de sesión con cookies HTTP-only firmadas y contraseñas cifradas con `bcrypt`. Cada usuario sólo tiene acceso a sus propios datos.
- 🔁 **Tareas Comunes (con selección de días)**: Rutinas que se repiten en días específicos de la semana (ej. de Lunes a Viernes, fines de semana o días concretos como L, X, V) o todos los días, manteniendo un estado independiente por cada fecha.
- ⏩ **Traspaso Automático (*Rollover*) de Tareas del Día Pendientes**: Si una tarea puntual no se completa en su fecha (`status != 'done'`), se traslada automáticamente al día de hoy para que nunca se quede olvidada en el pasado. Las tareas completadas se conservan en su fecha original.
- 📅 **Calendario Multivista**:
  - **Mes**: Vista global con resumen de tareas y acceso directo por día.
  - **Semana**: Vista por columnas semanales con soporte para arrastrar tareas entre días.
  - **Día (Tablero de Post-its)**: Vista detallada con post-its estilo notas adhesivas con color por nivel de importancia y orden manual arrastrable (SortableJS).
- 🏷️ **Niveles de Importancia y Estados**:
  - **Importancia**: Baja (`pi-low`), Media (`pi-medium`), Alta (`pi-high`), Urgente (`pi-urgent`).
  - **Estados**: Sin empezar (`○`), En proceso (`◐`), Finalizada (`✓`).
- ⏱️ **Horarios Opcionales**: Las tareas pueden o no tener hora de inicio y fin, con validación de coherencia horaria (`fin > inicio`).
- 🔍 **Búsqueda y Filtros en Tiempo Real**: Filtrado por texto (título/descripción), estado, importancia y tipo de tarea.
- 🪟 **Panel Deslizante / Modal**: Creación, edición rápida y eliminación de tareas sin perder el contexto visual ni recargar la página.


---

## 🛠️ Stack Tecnológico

| Capa | Tecnología | Justificación |
|---|---|---|
| **Lenguaje** | Python 3.12+ (compatible con 3.14) | Robusto, limpio y tipado |
| **Backend** | FastAPI + Uvicorn | Rendimiento asíncrono excepcional, OpenAPI automático y validación tipada |
| **Plantillas** | Jinja2 | Renderizado del lado del servidor sin sobrecarga de frameworks JS |
| **Base de Datos & ORM** | SQLAlchemy 2.x + Alembic | SQLite en local y PostgreSQL en producción sin modificar código |
| **Seguridad** | Cookies firmadas (`SessionMiddleware` / `itsdangerous`) + `bcrypt` | Sesión segura sin tokens expuestos en `localStorage` |
| **Frontend** | HTML5 semántico + Vanilla CSS + Vanilla JS | Ultraligero, rápido y sin paso de transpilación/build |
| **Librerías UI CDN** | FullCalendar (vistas mes/semana) + SortableJS (drag & drop) | Estándares de la industria cargados vía CDN |
| **Testing** | Pytest + HTTPX | Pruebas unitarias y de integración de endpoints |

---

## 📁 Estructura del Proyecto

```
Owngarnization/
├── app/
│   ├── __init__.py
│   ├── main.py              # Instancia FastAPI, configuración de middlewares y rutas
│   ├── config.py            # Gestión tipada de variables de entorno (Pydantic Settings)
│   ├── database.py          # Engine de BD, SessionLocal y Base declarativa
│   ├── models.py            # Modelos ORM (User, Task, TaskOccurrence)
│   ├── schemas.py           # Esquemas Pydantic para validación y serialización
│   ├── security.py          # Hashing de contraseñas y utilidades criptográficas
│   ├── deps.py              # Inyección de dependencias (get_db, get_current_user)
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── auth.py          # Endpoints de autenticación (registro, login, logout)
│   │   ├── pages.py         # Controladores de vistas HTML (Jinja2)
│   │   └── tasks.py         # API REST JSON de tareas y ocurrencias
│   ├── templates/
│   │   ├── base.html        # Layout común, cabecera y assets
│   │   ├── login.html       # Vista de inicio de sesión
│   │   ├── register.html    # Vista de registro de usuario
│   │   └── app.html         # Pantalla principal (calendario + panel post-its)
│   └── static/
│       ├── css/
│       │   └── styles.css   # Variables de diseño y estilos de la aplicación
│       └── js/
│           ├── api.js       # Cliente HTTP centralizado para la API
│           ├── board.js     # Lógica del tablero de post-its y SortableJS
│           ├── calendar.js  # Integración y eventos de FullCalendar
│           └── modal.js     # Gestión de modales y panel deslizante
├── migrations/              # Control de versiones de la BD con Alembic
│   ├── env.py
│   └── versions/
├── tests/                   # Pruebas automatizadas con Pytest
│   ├── __init__.py
│   ├── test_health.py
│   ├── test_auth.py
│   └── test_tasks.py
├── .env.example             # Plantilla de variables de entorno
├── .gitignore               # Exclusiones de Git
├── alembic.ini              # Configuración de migraciones
├── Procfile                 # Instrucción de arranque para PaaS
├── render.yaml              # Manifiesto de despliegue en Render
├── requirements.txt         # Dependencias Python fijadas
└── README.md                # Este documento
```

---

## 🗄️ Modelo de Datos

```mermaid
erDiagram
    USER ||--o{ TASK : "crea"
    TASK ||--o{ TASK_OCCURRENCE : "genera"

    USER {
        int id PK
        string email UK
        string username
        string password_hash
        datetime created_at
    }

    TASK {
        int id PK
        int user_id FK
        string title
        string description
        string kind "common | daily"
        string importance "low | medium | high | urgent"
        date date "NULL si es common"
        time start_time "opcional"
        time end_time "opcional"
        boolean is_active
        datetime created_at
        datetime updated_at
    }

    TASK_OCCURRENCE {
        int id PK
        int task_id FK
        date date
        string status "not_started | in_progress | done"
        int position "orden manual"
        time start_time "override opcional"
        time end_time "override opcional"
    }
```

### Reglas de Negocio Clave
1. **Generación Perezosa (Lazy)**: Al solicitar la información de una fecha determinada, el sistema verifica y genera (`get_or_create`) la `TaskOccurrence` para cada tarea común activa y para las tareas del día de esa fecha.
2. **Restricción de unicidad**: Cada par `(task_id, date)` es único en `TaskOccurrence`.
3. **Persistencia de orden**: El campo `position` almacena la secuencia elegida por el usuario al arrastrar los post-its en el día.

---

## 🔌 API REST (Endpoints)

Todas las rutas privadas validan la sesión activa del usuario.

| Método | Endpoint | Descripción |
|---|---|---|
| `POST` | `/auth/register` | Registro de nuevo usuario (email, username, password) |
| `POST` | `/auth/login` | Autenticación y creación de cookie de sesión |
| `POST` | `/auth/logout` | Invalidación y eliminación de cookie de sesión |
| `GET` | `/api/occurrences` | Obtiene ocurrencias en rango (`start`, `end`, filtros `q`, `status`, `importance`) |
| `POST` | `/api/tasks` | Creación de tarea (común o puntual) y generación de ocurrencia inicial |
| `GET` | `/api/tasks/{id}` | Detalle completo de una tarea |
| `PATCH` | `/api/tasks/{id}` | Modificación de datos generales de la tarea |
| `DELETE` | `/api/tasks/{id}` | Eliminación física o desactivación lógica de la tarea |
| `PATCH` | `/api/occurrences/{id}` | Actualización de estado (`not_started`, `in_progress`, `done`), fecha u horas del día |
| `POST` | `/api/occurrences/reorder` | Persiste el nuevo orden manual tras drag & drop (`{date, ordered_ids: []}`) |

---

## 🎨 Diseño Visual y Sistema de Estilos

La interfaz sigue una estética **minimalista y cálida**, basada en tonos tierra, negros suaves y beiges:

```css
:root {
  --bg: #FFFFFF;
  --surface: #FAF8F5;        /* Blanco cálido para fondos secundarios */
  --ink: #111111;            /* Negro tipográfico de alto contraste */
  --ink-soft: #555555;       /* Texto atenuado y metadatos */
  --line: #E7E2DA;           /* Separadores y bordes sutiles */
  --accent: #C9B49A;         /* Marrón claro elegante */
  --accent-strong: #A8906F;

  /* Post-its por nivel de importancia */
  --pi-low: #EFE9E0;         /* Beige suave */
  --pi-medium: #E3CFB4;      /* Marrón claro */
  --pi-high: #C9A57C;        /* Marrón caramelo medio */
  --pi-urgent: #111111;      /* Negro con texto blanco contrastado */
}
```

- **Post-its con personalidad**: Rotación ligera aleatoria ($\pm 1^\circ$), esquinas suavemente redondeadas (`8px`) y sombras difusas.
- **Iconografía semántica**:
  - Sin empezar: `○`
  - En proceso: `◐`
  - Finalizada: `✓` (con opacidad atenuada y texto tachado)
- **Accesibilidad**: Contraste adecuado (WCAG AA), navegación asistida por teclado (`Esc` para cerrar paneles, `N` para nueva tarea) y foco visualmente marcado.

---

## 💻 Requisitos Previos e Instalación Local

### 1. Requisitos
- **Python**: 3.12 o superior (3.12, 3.13, 3.14).
- **Git** instalado.

### 2. Clonar el repositorio
```bash
git clone https://github.com/tu-usuario/owngarnization.git
cd owngarnization
```

### 3. Crear y activar el entorno virtual
En Windows (PowerShell):
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

En Linux / macOS:
```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 4. Instalar dependencias
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 5. Configurar variables de entorno
Copia la plantilla `.env.example`:
```bash
cp .env.example .env
```

---

## ⚙️ Variables de Entorno

| Variable | Tipo | Por defecto | Descripción |
|---|---|---|---|
| `SECRET_KEY` | `str` | `dev-secret-key-...` | Clave secreta para firmar cookies de sesión |
| `ENV` | `str` | `development` | Entorno de ejecución (`development` o `production`) |
| `DATABASE_URL` | `str` | `sqlite:///./owngarnization.db` | Cadena de conexión para SQLite o PostgreSQL |
| `PORT` | `int` | `8000` | Puerto en el que escucha el servidor web |

---

## 🚀 Guía Rápida para Arrancar y Testear la Aplicación

Sigue estos sencillos pasos para levantar el servidor y comprobar el estado actual de la aplicación en tu navegador:

### 1. Activar el entorno virtual

Abre tu terminal en la carpeta raíz del proyecto (`Owngarnization`):

- **En Windows (PowerShell)**:
  ```powershell
  .\.venv\Scripts\Activate.ps1
  ```
  *(O si usas CMD clásico: `.\.venv\Scripts\activate.bat`)*

- **En Linux o macOS**:
  ```bash
  source .venv/bin/activate
  ```

---

### 2. Arrancar el servidor de desarrollo

Ejecuta el siguiente comando:

```powershell
uvicorn app.main:app --reload --port 8000
```
> *(También puedes arrancarlo con: `python -m uvicorn app.main:app --reload --port 8000`)*

Verás una salida similar a esta indicando que el servidor está listo:
```text
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
INFO:     Started reloader process [...]
INFO:     Application startup complete.
```

---

### 3. ¿Qué puedes testear ahora mismo?

Con las **Fases 0 y 1** completadas, ya puedes probar todo el flujo de autenticación y protección de rutas:

1. **Protección de rutas privadas**:
   - Abre tu navegador en [http://localhost:8000](http://localhost:8000).
   - Como aún no has iniciado sesión, el sistema te redirigirá automáticamente a [http://localhost:8000/login](http://localhost:8000/login).

2. **Registro de un nuevo usuario**:
   - Haz clic en **"Regístrate gratis"** o entra directamente a [http://localhost:8000/register](http://localhost:8000/register).
   - Introduce tu nombre de usuario, correo y una contraseña (mínimo 6 caracteres).
   - Al enviar el formulario, el usuario se guardará en la base de datos SQLite con contraseña hasheada en `bcrypt` y se creará la sesión cifrada.

3. **Acceso a la pantalla principal**:
   - Tras registrarte o iniciar sesión, serás llevado automáticamente a [http://localhost:8000/](http://localhost:8000/).
   - Verás la cabecera con el saludo a tu usuario (ej. *"Hola, **tu_usuario**"*) y el botón de cerrar sesión.

4. **Cierre de sesión y protección**:
   - Haz clic en **"Cerrar sesión"**. La cookie de sesión se destruirá y volverás a la pantalla de login.
   - Si intentas volver atrás a `/`, se denegará el acceso y serás devuelto al login.

5. **Documentación interactiva de la API**:
   - Entra en [http://localhost:8000/docs](http://localhost:8000/docs) (Swagger UI) para probar directamente los endpoints:
     - `GET /health` (Estado y versión del servicio)
     - `POST /auth/register`
     - `POST /auth/login`
     - `POST /auth/logout`
     - `GET /auth/me` (Devuelve tus datos si la sesión está activa, o error 401 si no lo está)

---

### 4. Ejecutar pruebas automatizadas

Para validar que todo el código cumple los criterios de calidad y seguridad:

```powershell
pytest -v
```
Todos los tests pasarán en verde con sus aserciones.


---

## ☁️ Guía de Despliegue en Servidor Gratuito

La aplicación incluye todos los manifiestos de infraestructura necesarios ([render.yaml](file:///c:/Users/ichig/Documents/Owngarnization/render.yaml) y [Procfile](file:///c:/Users/ichig/Documents/Owngarnization/Procfile)) para desplegarse gratis en **Render** con base de datos **Neon (PostgreSQL Serverless)**.

### Paso 1: Subir los últimos cambios a GitHub
Asegúrate de que tu repositorio local esté sincronizado con tu GitHub:
```powershell
git push origin master
```

---

### Paso 2: Crear Base de Datos PostgreSQL Gratuita en Neon
1. Entra en [Neon.tech](https://neon.tech) y regístrate con tu cuenta de GitHub (gratis, sin tarjeta).
2. Haz clic en **"Create Project"** (nombre: `owngarnization-db`).
3. En el panel de control de Neon, copia la cadena de conexión **Connection string** (asegúrate de que termine en `?sslmode=require`).
   - Ejemplo: `postgresql://neondb_owner:xyz123@ep-cool-fog-123456.us-east-2.aws.neon.tech/neondb?sslmode=require`

---

### Paso 3: Desplegar en Render
Tienes dos opciones sencillas en [Render.com](https://render.com):

#### Método Rápido A: Vía Blueprint Automático (Recomendado)
1. Inicia sesión en [Render.com](https://render.com).
2. Haz clic en **"New +"** $\to$ **"Blueprint"**.
3. Selecciona tu repositorio `Owngarnization`. Render detectará automáticamente el archivo [render.yaml](file:///c:/Users/ichig/Documents/Owngarnization/render.yaml).
4. Cuando te solicite la variable `DATABASE_URL`, pega la URL que copiaste de Neon.
5. Haz clic en **"Apply"**. Render instalará dependencias, ejecutará las migraciones de Alembic (`alembic upgrade head`) y levantará el servicio.

#### Método Manual B: Web Service Estándar
1. En Render, selecciona **"New +"** $\to$ **"Web Service"** y conecta el repositorio `Owngarnization`.
2. Configura los siguientes campos:
   - **Name**: `owngarnization`
   - **Runtime**: `Python 3`
   - **Branch**: `master`
   - **Build Command**:
     ```bash
     pip install -r requirements.txt && alembic upgrade head
     ```
   - **Start Command**:
     ```bash
     uvicorn app.main:app --host 0.0.0.0 --port $PORT --proxy-headers
     ```
   - **Plan**: `Free`
3. En la sección **"Environment Variables"**, añade:
   - `DATABASE_URL`: *(Tu cadena de conexión de Neon con `sslmode=require`)*
   - `SECRET_KEY`: *(Cadena larga y aleatoria para firmar cookies)*
   - `ENV`: `production`
   - `PYTHON_VERSION`: `3.12.0`
4. Haz clic en **"Create Web Service"**.

---

### Paso 4: Verificación en Producción
Una vez finalizado el despliegue (suele tardar 2-3 minutos la primera vez):
1. Render te asignará una URL pública segura con HTTPS (ej. `https://owngarnization.onrender.com`).
2. Entra a `https://owngarnization.onrender.com/health` para comprobar que responde `{"status": "ok"}`.
3. Entra a `https://owngarnization.onrender.com/` para crear tu primera cuenta de producción y comenzar a organizar tus tareas y rutinas.

> **Nota sobre el plan gratuito de Render**: Tras 15 minutos sin peticiones, el servicio entra en reposo (*sleep*). Cuando alguien accede de nuevo, puede tardar entre 30 y 45 segundos en reactivarse. Gracias a la base de datos persistente en Neon, todos tus datos y estados diarios estarán siempre seguros.

---

## 🗺️ Estado del Plan de Implementación

- [x] **Fase 0 — Preparación del entorno**: Entorno virtual, dependencias, `.gitignore`, `.env.example`, estructura de directorios, `Procfile`, `render.yaml`, test `/health`.
- [x] **Fase 1 — Base de datos y autenticación**: Modelos SQLAlchemy, Alembic, registro, login, logout, control de sesión.
- [x] **Fase 2 — API de tareas**: Lógica de tareas comunes/del día, ocurrencias lazy, reordenación, pruebas unitarias.
- [x] **Fase 3 — UI base y estilos**: Plantillas Jinja2, diseño responsive blanco/negro/marrón.
- [x] **Fase 4 — Calendario**: Integración con FullCalendar (mes y semana), cambio de días por arrastre.
- [x] **Fase 5 — Tablero de Día**: Post-its con SortableJS, rotación, cambio rápido de estado y reordenación persistente.
- [x] **Fase 6 — Modal de Detalle y Edición**: Panel deslizante sin recarga, selector de horas opcionales.
- [x] **Fase 7 — Búsqueda y Filtros**: Filtrado en tiempo real en las 3 vistas.
- [x] **Fase 8 — Pulido y Accesibilidad**: Atajos de teclado, mensajes de estado (toasts), navegación móvil.
- [x] **Fase 9 — Despliegue**: Configuración de `render.yaml`, `Procfile`, PostgreSQL serverless en Neon y guía paso a paso.


