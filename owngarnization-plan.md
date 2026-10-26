# Owngarnization — Prompt y plan de implementación para OpenCode

> Pega este documento entero en OpenCode (o guárdalo como `PLAN.md` / `AGENTS.md` en la raíz del proyecto) y pídele: **"Implementa este plan fase por fase. Al terminar cada fase, ejecútala, pruébala y avanza a la siguiente."**

---

## 1. Rol y objetivo

Actúa como **desarrollador senior full-stack (Python)**. Construye **Owngarnization**, una aplicación web de gestión de tareas con calendario, inicio de sesión y persistencia de datos por usuario, lista para desplegarse en un servidor **gratuito**.

Prioridades: código limpio, sencillo de mantener, mínimo de dependencias, interfaz minimalista y rápida.

## 2. Supuestos (decisiones ya tomadas)

1. **"Datos guardados en sesión"** = cada usuario inicia sesión y **sus datos quedan guardados en base de datos** asociados a su cuenta (no se pierden al cerrar el navegador).
2. **Tareas comunes** = tareas rutinarias que se repiten **todos los días** (p. ej. "Beber agua", "Revisar correo"). Se definen una vez y aparecen automáticamente cada día.
3. **Tareas del día** = tareas puntuales de **una fecha concreta**.
4. Cada día tiene su **propio estado** para cada tarea (una tarea común puede estar "finalizada" hoy y "sin empezar" mañana).
5. El horario (hora inicio / hora fin) es **siempre opcional**.

## 3. Stack tecnológico

| Capa | Elección | Motivo |
|---|---|---|
| Lenguaje | Python 3.12 | Pedido |
| Backend | **FastAPI** + Uvicorn | Moderno, rápido, API tipada |
| Plantillas | **Jinja2** | Sin build de frontend |
| ORM | **SQLAlchemy 2.x** + Alembic | Cambiar de SQLite a Postgres sin tocar código |
| BD | SQLite (local) / PostgreSQL (producción, vía `DATABASE_URL`) | Gratis y portable |
| Auth | Sesiones con cookie firmada (`itsdangerous`/`SessionMiddleware`) + `passlib[bcrypt]` | Simple y seguro |
| Frontend | HTML + CSS propio + **JavaScript vanilla** | Ligero |
| Calendario | **FullCalendar** (vistas mes/semana/día) por CDN | Resuelve mes y semana |
| Drag & drop post-its | **SortableJS** por CDN | Orden manual en vista día |
| Tests | pytest + httpx | Pruebas de API |

> Si prefieres menos JS: se puede usar HTMX para modales y listas, pero el drag & drop sigue necesitando SortableJS.

## 4. Estructura del proyecto (Arquitectura Modular y Escalable)

```
owngarnization/
├── app/
│   ├── main.py              # Instancia FastAPI, configuración de middlewares y rutas
│   ├── config.py            # Gestión tipada de variables de entorno (Pydantic Settings)
│   ├── database.py          # Engine de BD, SessionLocal y Base declarativa
│   ├── models.py            # Modelos ORM (User, Task, TaskOccurrence)
│   ├── schemas.py           # Esquemas Pydantic para validación y serialización
│   ├── security.py          # Hashing de contraseñas y utilidades criptográficas
│   ├── deps.py              # Inyección de dependencias (get_db, get_current_user)
│   ├── routers/             # Controladores delgados (Thin Controllers)
│   │   ├── auth.py          # Endpoints de autenticación (registro, login, logout)
│   │   ├── pages.py         # Controladores de vistas HTML
│   │   └── tasks.py         # Endpoints REST delegados a servicios
│   ├── services/            # Capa de lógica de negocio (Service Layer)
│   │   ├── task_service.py  # Operaciones CRUD y reglas de ciclo de vida de tareas
│   │   └── occurrence_service.py # Generación lazy, rollover automático y reordenación
│   ├── templates/
│   │   ├── base.html        # Shell HTML común, fuentes y assets
│   │   ├── login.html       # Vista de inicio de sesión
│   │   ├── register.html    # Vista de registro de usuario
│   │   ├── app.html         # Ensamblador principal de la app (< 50 líneas)
│   │   └── components/      # Componentes parciales reutilizables (Jinja2)
│   │       ├── header.html
│   │       ├── control_bar.html
│   │       ├── sidebar.html
│   │       ├── board_day.html
│   │       ├── task_modal.html
│   │       ├── detail_drawer.html
│   │       └── guide_modal.html
│   └── static/
│       ├── css/             # Arquitectura modular de estilos
│       │   ├── styles.css   # Índice y manifiesto de imports
│       │   ├── variables.css
│       │   ├── base.css
│       │   ├── auth.css
│       │   ├── layout.css
│       │   ├── board.css
│       │   ├── calendar.css
│       │   ├── modals.css
│       │   ├── guide.css
│       │   └── responsive.css
│       ├── js/              # Módulos JavaScript con responsabilidad única
│       │   ├── api.js       # Cliente HTTP asíncrono
│       │   ├── calendar.js  # Integración y eventos de FullCalendar
│       │   ├── board.js     # Tablero post-its y drag & drop (SortableJS)
│       │   ├── task_modal.js # Formulario modal de creación/edición de tareas
│       │   ├── drawer.js    # Panel deslizante de detalle
│       │   ├── guide.js     # Lógica y navegación del manual de usuario
│       │   └── app.js       # Coordinador de estado global y vistas
│       └── img/             # Logo oficial y capturas de las guías
│
│   # --- Módulo de Proyectos (Fases 12-14; mismo patrón modular) ---
│   ├── routers/projects.py              # Thin Controller: /api/projects/... y páginas /projects
│   ├── services/project_service.py      # Proyectos, miembros, roles y permisos
│   ├── services/project_task_service.py # Tareas, mover entre columnas, reordenar, asignar
│   ├── templates/projects/              # projects.html (listado) · project_board.html (tablero)
│   ├── templates/components/projects/   # project_card, board_column, task_card, task_drawer,
│   │                                    # project_modal, members_modal, projects_guide_modal
│   └── static/
│       ├── css/projects.css (+ projects_board.css, projects_guide.css)
│       ├── js/projects/                 # projects_list.js, project_board.js, project_drawer.js,
│       │                                # project_members.js, projects_guide.js
│       └── img/guide/projects/          # Capturas del manual de Proyectos
├── migrations/              # Control de versiones de la BD con Alembic
├── tests/                   # Pruebas con Pytest (incl. test_projects.py y test_project_permissions.py)
├── requirements.txt
├── .env.example
├── Procfile / render.yaml   # Manifiestos de despliegue
└── README.md
```

## 5. Modelo de datos

**User**
- `id`, `email` (único), `username`, `password_hash`, `created_at`

**Task** (definición de la tarea)
- `id`, `user_id` (FK)
- `title` (obligatorio), `description` (opcional)
- `kind`: `"common"` | `"daily"`
- `importance`: `"low"` | `"medium"` | `"high"` (opcional `"urgent"`)
- `date` (solo para `daily`; `NULL` en `common`)
- `start_time`, `end_time` (opcionales; validar `end_time > start_time` si ambos existen)
- `is_active` (para "borrar" una común sin perder histórico)
- `created_at`, `updated_at`

**TaskOccurrence** (instancia de una tarea en un día concreto)
- `id`, `task_id` (FK), `date`
- `status`: `"not_started"` | `"in_progress"` | `"done"`
- `position` (entero, orden manual en el tablero del día)
- `start_time`, `end_time` (override opcional para ese día)
- Restricción única `(task_id, date)`

**Lógica clave**
- Al pedir un día, el backend crea (lazy, `get_or_create`) una `TaskOccurrence` para cada tarea `common` activa y para cada `daily` de esa fecha.
- Las tareas `daily` crean su ocurrencia al crearse.
- Índices en `(user_id, date)` y `(task_id, date)`.

### 5.1 Modelo de datos del módulo de Proyectos

**Project**
- `id`, `owner_id` (FK User), `name` (obligatorio), `description`, `color` (opcional), `is_archived`, `is_active` (borrado lógico), `created_at`, `updated_at`

**ProjectMember** (quién participa y con qué rol)
- `id`, `project_id` (FK), `user_id` (FK), `role`: `"owner"` | `"member"` | `"viewer"`
- Restricción única `(project_id, user_id)`. El propietario se inserta como miembro `owner` al crear el proyecto.

**ProjectColumn** (celda/estado del tablero)
- `id`, `project_id` (FK), `name`, `position` (orden), `is_done` (marca la columna que cuenta como "completada" para el % de progreso)
- Al crear un proyecto se generan: Pendiente, En curso, En revisión, Hecho (`is_done=true`).

**ProjectTask**
- `id`, `project_id` (FK), `column_id` (FK), `title` (obligatorio), `description`
- `priority`: `"low"` | `"medium"` | `"high"` | `"urgent"`
- `position` (orden dentro de la columna), `due_date` (opcional), `is_active`, `created_by` (FK User), `created_at`, `updated_at`

**ProjectTaskAssignee** (asignación N:M)
- `task_id` (FK), `user_id` (FK) — solo se puede asignar a miembros del proyecto. PK compuesta `(task_id, user_id)`.

**Reglas clave**
- Toda consulta filtra por pertenencia: un usuario solo ve proyectos donde es miembro.
- Permisos por rol comprobados en la capa de servicios, no en el router.
- Mover una tarea a una columna `is_done` registra la finalización; índices en `(project_id, column_id, position)`.

## 6. Autenticación y seguridad

- Registro (email + usuario + contraseña con validación mínima) y login.
- Contraseñas con **bcrypt**. Nunca en texto plano.
- Sesión por cookie firmada: `httponly`, `samesite=lax`, `secure=True` en producción.
- Todas las consultas filtran por `user_id` del usuario en sesión (un usuario jamás ve datos de otro).
- Protección CSRF para formularios y peticiones que modifican datos (token o cabecera personalizada verificada).
- Rate limiting básico en login (opcional: `slowapi`).
- Secretos solo por variables de entorno.

## 7. API (JSON, requiere sesión)

| Método | Ruta | Descripción |
|---|---|---|
| POST | `/auth/register` · `/auth/login` · `/auth/logout` | Autenticación |
| GET | `/api/occurrences?start=YYYY-MM-DD&end=YYYY-MM-DD&q=texto&status=&importance=` | Ocurrencias en rango (alimenta mes/semana/día) con búsqueda y filtros |
| GET | `/api/tasks/{id}` | Detalle completo |
| POST | `/api/tasks` | Crear tarea (común o del día) |
| PATCH | `/api/tasks/{id}` | Editar tarea |
| DELETE | `/api/tasks/{id}` | Eliminar / desactivar |
| PATCH | `/api/occurrences/{id}` | Cambiar estado, horario o fecha (mover en calendario) |
| POST | `/api/occurrences/reorder` | Guardar orden manual `{date, ordered_ids: []}` |

Validar todo con Pydantic y devolver errores claros (422/404/403).

## 8. Diseño visual (minimalista)

**Paleta**
```css
:root {
  --bg: #FFFFFF;
  --surface: #FAF8F5;        /* blanco cálido */
  --ink: #111111;            /* negro principal */
  --ink-soft: #555555;
  --line: #E7E2DA;
  --accent: #C9B49A;         /* marrón clarito */
  --accent-strong: #A8906F;

  /* Post-its por importancia (tonos suaves, coherentes con la paleta) */
  --pi-low: #EFE9E0;         /* beige muy claro */
  --pi-medium: #E3CFB4;      /* marrón claro */
  --pi-high: #C9A57C;        /* marrón medio */
  --pi-urgent: #111111;      /* negro, texto blanco */
}
```
- Tipografía: una sans-serif limpia (Inter o system-ui). Títulos en peso 600.
- Bordes finos, esquinas redondeadas (8–12 px), sombras muy suaves.
- Sin degradados ni colores chillones. Estados diferenciados con **icono + etiqueta**, no solo color:
  - Sin empezar: círculo vacío ○
  - En proceso: medio círculo ◐
  - Finalizada: check ✓ (post-it con ligera opacidad y título tachado)
- Responsive (usable en móvil) y accesible (contraste AA, foco visible, `aria-label`, cierre con `Esc`).

## 9. Pantallas y comportamiento

### 9.1 Login / Registro
Pantalla centrada, logo/nombre **Owngarnization**, formularios simples, mensajes de error claros.

### 9.2 Pantalla principal
- **Cabecera**: nombre de la app, buscador, botón "＋ Nueva tarea", menú de usuario (logout).
- **Barra lateral / filtros**: filtrar por estado, importancia y tipo (común / del día). Buscar por texto en título y descripción.
- **Selector de vista**: **Mes · Semana · Día** + navegación anterior/siguiente/hoy.

### 9.3 Vistas del calendario
- **Mes**: cada día muestra mini-tarjetas (máx. 3 + "+N más"). Clic en un día → vista Día.
- **Semana**: 7 columnas con post-its compactos. Se pueden **arrastrar entre días** para cambiar la fecha.
- **Día (tablero de post-its)**:
  - Las tareas se muestran como **post-its** (ligera rotación ±1°, sombra suave) coloreados por importancia.
  - Cada post-it muestra: **nombre**, importancia (color), estado (icono), horario si existe y marca de "común".
  - **Reordenable manualmente** con drag & drop (SortableJS) y orden persistido en BD.
  - Sección separada: **Tareas comunes** y **Tareas del día**.
  - Cambio rápido de estado desde el propio post-it (clic en icono o menú).

### 9.4 Panel emergente de detalle (sin salir de la pantalla)
- Al hacer clic en un post-it o tarjeta se abre un **modal / panel lateral deslizante**.
- Muestra: nombre, descripción completa, tipo, importancia, estado, fecha, intervalo horario.
- Permite **editar y eliminar** desde el panel.
- Se cierra con botón ✕, tecla `Esc` o clic fuera. La vista de fondo conserva su estado y scroll.

### 9.5 Crear / editar tarea (modal)
Campos:
1. Nombre (obligatorio)
2. Descripción (opcional)
3. Tipo: **Común (con selección de días de la semana o todos los días)** / **Del día** (con selector de fecha; por defecto el día que se está viendo)
4. Importancia (baja / media / alta / urgente)
5. Estado inicial (por defecto "sin empezar")
6. **Hora inicio y hora fin (opcionales)** con validación de coherencia

### 9.6 Módulo de Proyectos (pantalla aparte)
**Objetivo**: gestionar proyectos personales o en equipo con un tablero visual por estados, independiente del calendario de tareas diarias.

**Navegación**: nueva entrada "Proyectos" en la cabecera principal que abre `/projects` (otra pantalla, con su propia plantilla, CSS y JS; el calendario no se carga aquí).

**Listado de proyectos (`/projects`)**
- Tarjetas con nombre, descripción corta, nº de tareas, progreso (% en columna final) y avatares de miembros.
- Botón "＋ Nuevo proyecto" (modal con nombre obligatorio, descripción y color/icono opcionales).
- Archivar y eliminar proyectos (borrado lógico).

**Tablero del proyecto (`/projects/{id}`)**
- Columnas (celdas) por estado, por defecto: **Pendiente · En curso · En revisión · Hecho**. Se pueden **añadir, renombrar, reordenar y eliminar** columnas (mínimo 1).
- Tarjetas de tarea con: título, prioridad (color + etiqueta: baja/media/alta/urgente), asignados (avatares/iniciales), fecha límite opcional y contador de subtareas/comentarios opcional.
- **Drag & drop** de tarjetas entre columnas y reorden dentro de la columna (SortableJS); el orden persiste.
- Panel lateral de detalle/edición de tarea (reutiliza el patrón de *drawer*): descripción, prioridad, columna, asignados, fecha límite, borrar.
- **Asignación a personas**: el propietario invita miembros por email (usuarios ya registrados) y asigna tareas a uno o varios miembros. Roles: `owner` (todo), `member` (crea/edita/mueve tareas), `viewer` (solo lectura).
- Filtros: por prioridad, por asignado (incluido "sin asignar" y "mis tareas"), búsqueda por texto.
- Estados vacíos, toasts de error/éxito y atajos (`N` nueva tarea del proyecto, `Esc` cerrar).

**Alcance fuera de esta versión** (futuro): comentarios, adjuntos, notificaciones por email, plantillas de proyecto.

**API JSON de Proyectos** (requiere sesión; permisos por rol en servicios)

| Método | Ruta | Descripción |
|---|---|---|
| GET / POST | `/api/projects` | Listar mis proyectos / crear proyecto (genera columnas por defecto) |
| GET / PATCH / DELETE | `/api/projects/{id}` | Detalle con columnas y tareas / editar o archivar / borrado lógico |
| GET / POST | `/api/projects/{id}/members` | Listar / invitar miembro por email |
| PATCH / DELETE | `/api/projects/{id}/members/{user_id}` | Cambiar rol / quitar miembro |
| POST | `/api/projects/{id}/columns` | Crear columna |
| PATCH / DELETE | `/api/projects/{id}/columns/{col_id}` | Renombrar / eliminar (mueve sus tareas a otra columna) |
| POST | `/api/projects/{id}/columns/reorder` | Reordenar columnas |
| POST | `/api/projects/{id}/tasks` | Crear tarea |
| GET / PATCH / DELETE | `/api/projects/{id}/tasks/{task_id}` | Detalle / editar (prioridad, asignados, fecha) / eliminar |
| POST | `/api/projects/{id}/tasks/move` | Mover tarea a columna y posición `{task_id, column_id, position}` |

Páginas HTML: `GET /projects` y `GET /projects/{id}` (redirigen a `/login` si no hay sesión).

### 9.7 Manual de usuario integrado (ventana emergente)
- Icono de ayuda con símbolo de pregunta (`?`) situado en la cabecera principal junto a las acciones de usuario.
- Al hacer clic (o presionar el atajo `?`), se abre una **ventana modal emergente** limpia y guiada.
- Estructura organizada por pestañas o bloques de navegación temática:
  1. **Primeros pasos y conceptos**: Tareas comunes (rutinas con selector de días) vs Tareas del día (con traspaso automático de pendientes).
  2. **Vistas del calendario**: Cómo navegar y aprovechar las vistas de Mes, Semana (arrastrar tareas entre fechas) y Día (tablero post-its).
  3. **Tablero y post-its**: Códigos de color por importancia, reordenación con drag & drop, y cambio rápido de estados (○ Sin empezar, ◐ En proceso, ✓ Finalizada).
  4. **Gestión de tareas**: Creación con horas opcionales, edición rápida en panel lateral y eliminación.
  5. **Atajos de teclado**: `N` (nueva tarea), `?` (abrir manual), `Esc` (cerrar cualquier modal).
- Accesibilidad: Cierre con botón ✕, tecla `Esc` o clic fuera del modal sin perder el estado de la pantalla.

## 10. Plan de implementación por fases

### Fase 0 — Preparación
- Crear entorno virtual, `requirements.txt` (`fastapi`, `uvicorn[standard]`, `sqlalchemy`, `alembic`, `jinja2`, `python-multipart`, `passlib[bcrypt]`, `itsdangerous`, `pydantic-settings`, `psycopg[binary]`, `pytest`, `httpx`).
- Estructura de carpetas, `.env.example`, `.gitignore`, `git init`.
- **Criterio de hecho**: `uvicorn app.main:app --reload` arranca y responde `/health`.

### Fase 1 — Base de datos y autenticación
- Modelos, migración inicial con Alembic, registro/login/logout, `get_current_user`.
- **Hecho cuando**: puedo registrarme, iniciar sesión, cerrar sesión, y las rutas privadas redirigen a `/login`.

### Fase 2 — API de tareas
- CRUD de `Task`, generación lazy de `TaskOccurrence`, endpoints de rango, búsqueda y filtros, reorder.
- Tests de: aislamiento entre usuarios, tareas comunes que aparecen cada día, estado independiente por día, validación horaria.
- **Hecho cuando**: los tests pasan.

### Fase 3 — UI base y estilo
- `base.html`, CSS con variables de la paleta, login/registro y layout principal.
- **Hecho cuando**: el diseño blanco/negro/marrón es consistente y responsive.

### Fase 4 — Calendario (mes y semana)
- Integrar FullCalendar con datos de `/api/occurrences`, vista mes y semana, navegación, mover tareas entre días (PATCH de fecha).
- **Hecho cuando**: puedo cambiar de mes/semana y arrastrar una tarea a otro día con persistencia.

### Fase 5 — Vista Día (post-its)
- Tablero con post-its, color por importancia, iconos de estado, secciones común/del día, orden manual persistente, cambio rápido de estado.
- **Hecho cuando**: recargo la página y el orden y estados se mantienen.

### Fase 6 — Modal de detalle y formulario
- Panel emergente (ver, editar, eliminar, cerrar con `Esc`/clic fuera), formulario de creación con horas opcionales.
- **Hecho cuando**: el flujo completo crear → ver → editar → eliminar funciona sin recargar la página.

### Fase 7 — Búsqueda y filtros
- Buscador por texto, filtros por estado/importancia/tipo, aplicados a las tres vistas.

### Fase 8 — Pulido
- Estados vacíos ("No hay tareas hoy"), mensajes de error/éxito (toasts), accesibilidad, atajos de teclado (`N` nueva tarea, `Esc` cerrar), pruebas manuales en móvil.

### Fase 9 — Despliegue
Ver sección 11.

### Fase 10 — Manual de usuario guiado (In-App)
- Integrar botón de ayuda (`?`) accesible en la cabecera de la aplicación.
- Modal emergente con manual interactivo organizado por secciones claras y lenguaje sencillo.
- Navegación interna amigable para que cualquier usuario comprenda el funcionamiento de la app en menos de 2 minutos.
- Soporte para atajo de teclado (`?`) y cierre con `Esc` o clic exterior.
- **Criterio de hecho**: El usuario puede abrir la ayuda desde cualquier punto de la app, consultar las guías de uso de forma visual y comprensible, y cerrarla sin recargar ni alterar su estado.

### Fase 11 — Refactorización para Escalabilidad y Modularidad (Senior Architecture)
- **Backend (Service Layer Pattern)**: Desacoplar `app/routers/tasks.py` extrayendo la lógica de negocio y consultas pesadas a `app/services/task_service.py` y `app/services/occurrence_service.py`. Mantener los controladores como *Thin Controllers*.
- **Plantillas Jinja2 (Component-Based)**: Modularizar `app/templates/app.html` descomponiéndolo en componentes reutilizables en `app/templates/components/` (`header.html`, `control_bar.html`, `sidebar.html`, `board_day.html`, `task_modal.html`, `detail_drawer.html`, `guide_modal.html`). Reducir `app.html` a un ensamblador de < 50 líneas.
- **Estilos CSS (Modular CSS Architecture)**: Dividir `styles.css` en módulos temáticos específicos (`variables.css`, `base.css`, `auth.css`, `layout.css`, `board.css`, `calendar.css`, `modals.css`, `guide.css`, `responsive.css`) orquestados limpiamente.
- **Frontend JS (Desacoplamiento)**: Desglosar módulos con responsabilidad única (`task_modal.js`, `drawer.js`, `guide.js`).
- **Criterio de hecho**: Ningún archivo con acumulación excesiva de líneas, código legible y mantenible según estándares de ingeniería de software senior, y 100% de los tests pasando sin regresiones.

### Fase 12 — Proyectos: modelo de datos y API (backend)
- Modelos `Project`, `ProjectMember`, `ProjectColumn`, `ProjectTask` (ver sección 5.1) y migración Alembic.
- `app/services/project_service.py` (CRUD de proyectos, miembros, permisos) y `app/services/project_task_service.py` (CRUD de tareas, mover entre columnas, reordenar, asignar).
- `app/routers/projects.py` como *Thin Controller* con los endpoints de la sección 9.6.
- Tests: aislamiento entre usuarios, permisos por rol, mover/reordenar tareas, asignación solo a miembros, columnas por defecto al crear proyecto.
- **Criterio de hecho**: los tests nuevos y los 16 existentes pasan en verde.

### Fase 13 — Proyectos: pantalla de tablero (frontend)
- Ruta de página `/projects` (listado) y `/projects/{id}` (tablero), enlazadas desde la cabecera principal.
- Componentes Jinja2 en `app/templates/projects/` y `components/projects/`, estilos en `css/projects.css` y JS modular en `js/projects/`.
- Tablero tipo Kanban con celdas/columnas por estado, drag & drop de tarjetas entre columnas y reorden (SortableJS), prioridad por color, avatares de asignados, filtros y buscador.
- **Criterio de hecho**: crear proyecto → crear tareas → moverlas entre columnas → priorizar → asignar a miembros → recargar y comprobar que todo persiste, también en móvil.

### Fase 14 — Proyectos: manual de usuario independiente
- Icono `?` en la pantalla de proyectos que abre un modal propio (`projects_guide_modal.html` + `projects_guide.js`) con pestañas: crear proyecto, columnas y estados, tareas y prioridades, asignar personas, atajos.
- Capturas reales del tablero en `static/img/guide/projects/`.
- Se mantiene el manual existente para tareas/calendario como documento aparte (un manual por sección de la app).
- **Criterio de hecho**: cada pantalla tiene su manual contextual, abierto con `?` y cerrado con `Esc`.

## 11. Despliegue en servidor gratuito

**Opción recomendada A: Render (web service gratis) + Neon (PostgreSQL gratis)**
1. Subir el repo a GitHub.
2. Crear base en **Neon** y copiar su `DATABASE_URL`.
3. Crear *Web Service* en **Render** conectado al repo:
   - Build: `pip install -r requirements.txt && alembic upgrade head`
   - Start: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
   - Variables: `SECRET_KEY` (cadena larga aleatoria), `DATABASE_URL`, `ENV=production`.
4. Nota: el plan gratuito de Render "duerme" tras inactividad (primer acceso lento). El disco es efímero, **por eso no usar SQLite en producción** en esta opción.

**Opción B (más simple, sin Postgres): PythonAnywhere (plan gratuito)**
- Soporta SQLite con disco persistente. Requiere configurar WSGI (usar `a2wsgi` para adaptar FastAPI) o usar Flask.

Incluir en el repo un `render.yaml` o `Procfile`, y documentar los pasos en el `README.md`.

> Los planes gratuitos cambian con el tiempo: verifica las condiciones actuales antes de elegir.

## 12. Criterios de aceptación finales

- [ ] Registro, login y logout funcionan; los datos son privados por usuario.
- [ ] Las tareas **comunes** aparecen cada día con estado independiente.
- [ ] Las tareas **del día** solo aparecen en su fecha.
- [ ] Horario opcional con validación; la tarea funciona sin horas.
- [ ] Vistas **mes, semana y día** operativas con navegación y búsqueda.
- [ ] En vista día, tareas como **post-its** reordenables manualmente (persistente).
- [ ] Color por importancia y 3 estados (sin empezar / en proceso / finalizada).
- [ ] Detalle en **panel emergente** que se cierra sin salir de la pantalla.
- [ ] Estilo blanco/negro/marrón claro, responsive y accesible.
- [ ] Tests pasan y la app está desplegada en un servicio gratuito.
- [ ] `README.md` con instalación local, variables de entorno y despliegue.
- [x] Manual de usuario interactivo y guiado accesible desde el icono de ayuda (`?`) en la cabecera.
- [x] Arquitectura modular escalable: archivos concisos con responsabilidad única (SRP), capa de servicios en backend y componentes Jinja2 desacoplados.
- [ ] **Proyectos**: pantalla aparte (`/projects`) donde crear proyectos personales, gestionar sus tareas en un tablero de columnas por estado, ordenarlas, priorizarlas y asignarlas a personas.
- [ ] Los proyectos y sus tareas son privados por usuario (y compartidos solo con los miembros invitados), con tests de aislamiento y permisos.
- [ ] El módulo de proyectos respeta la arquitectura modular (router delgado + servicios + componentes + CSS/JS propios, ningún archivo > ~250 líneas).
- [ ] Manual de usuario independiente para Proyectos, accesible desde un icono `?` en la propia pantalla de proyectos.

## 13. Reglas de trabajo para el agente

1. Trabaja **fase a fase**; no avances si la anterior no cumple su criterio de hecho.
2. Ejecuta y prueba el código tras cada fase; corrige errores antes de continuar.
3. No añadas dependencias innecesarias ni sobrediseñes (sin microservicios, sin frameworks JS pesados).
4. Commits pequeños con mensaje claro por fase.
5. Si algo del plan es ambiguo, aplica los **supuestos de la sección 2** y deja la decisión anotada en el README.
6. Todo el texto visible de la interfaz en **español**.
