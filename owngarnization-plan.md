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
| App móvil | **PWA** (Web App Manifest + Service Worker) | Instalable gratis desde la web en iOS y Android, sin tiendas ni segundo código |
| Notificaciones | **Web Push** (estándar VAPID) + `pywebpush` | Funciona en Android (Chrome/Edge/Firefox) e iOS ≥ 16.4 (PWA instalada) |
| Disparador de avisos | Cron externo gratuito (cron-job.org) → endpoint protegido | El plan gratis de Render duerme: no se puede depender de un scheduler en proceso |

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
│
│   # --- App móvil PWA y notificaciones (Fases 15-18) ---
│   ├── routers/pwa.py                   # Sirve /manifest.webmanifest y /sw.js desde la raíz (scope global)
│   ├── routers/push.py                  # Thin Controller: suscripciones, preferencias y endpoint de cron
│   ├── services/push_service.py         # Alta/baja de suscripciones y envío con pywebpush (limpia 404/410)
│   ├── services/reminder_service.py     # Cálculo de avisos pendientes por zona horaria y deduplicación
│   ├── templates/components/
│   │   ├── mobile_nav.html              # Barra inferior (Día · Semana · Mes) + botón flotante ＋
│   │   ├── install_banner.html          # Invitación a instalar (Android nativo / instrucciones iOS)
│   │   └── notification_settings.html   # Activar avisos, antelación y prueba de notificación
│   └── static/
│       ├── sw.js                        # Service Worker: caché del shell, push y notificationclick
│       ├── css/mobile.css               # Ajustes mobile-first (bottom sheets, safe areas, táctil)
│       ├── js/pwa.js                    # Registro del SW, detección standalone e instalación
│       ├── js/push.js                   # Permiso, suscripción y sincronización con el backend
│       └── img/icons/                   # icon-192, icon-512, maskable-512, apple-touch-icon-180, badge-72
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

### 5.2 Modelo de datos de notificaciones (PWA)

**User** (campos nuevos)
- `timezone` (IANA, p. ej. `"Europe/Madrid"`; se detecta con `Intl.DateTimeFormat().resolvedOptions().timeZone` y se guarda al iniciar sesión).
- `reminders_enabled` (bool, por defecto `true`) y `reminder_offset_min` (entero: `0`, `5`, `10`, `15`, `30`, `60`; por defecto `10`).

**PushSubscription** (un usuario puede tener varios dispositivos)
- `id`, `user_id` (FK), `endpoint` (único, texto), `p256dh`, `auth`, `user_agent`, `created_at`, `last_success_at`.
- Se elimina automáticamente si el servicio push responde `404` o `410` (suscripción caducada).

**TaskOccurrence** (campo nuevo)
- `reminder_sent_at` (datetime UTC, nullable). Evita avisos duplicados; se **resetea a `NULL`** si cambian `start_time` o `date`.

**Reglas clave**
- Solo generan aviso las ocurrencias con `start_time`, `status != "done"` y tarea activa.
- La "fecha de hoy" se calcula **en la zona horaria del usuario**, no del servidor (Render corre en UTC). Aplicar también al traspaso automático de pendientes.
- Antes de buscar avisos, el dispatcher llama a la generación lazy (`ensure_occurrences`) para el día actual de cada usuario con suscripciones, porque las tareas comunes solo se materializan al consultarse.
- Ventana de envío: `inicio − antelación ≤ ahora ≤ inicio + 15 min`. Si el servidor estuvo dormido más tiempo, el aviso se descarta en lugar de llegar tarde.

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
| GET | `/manifest.webmanifest` · `/sw.js` | Manifest y Service Worker servidos desde la raíz (públicos) |
| GET | `/api/push/public-key` | Clave pública VAPID para suscribirse |
| POST / DELETE | `/api/push/subscriptions` | Registrar / eliminar la suscripción del dispositivo actual |
| GET / PATCH | `/api/me/preferences` | `timezone`, `reminders_enabled`, `reminder_offset_min` |
| POST | `/api/push/test` | Enviar una notificación de prueba a mis dispositivos |
| POST | `/internal/reminders/dispatch` | Llamado por el cron cada minuto. **Sin sesión**: exige cabecera `X-Cron-Secret` (comparación en tiempo constante) |

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
  - Las tareas se muestran como **post-its** rectos (sin rotación), con sombra suave y **separación uniforme** entre tarjetas, coloreados por importancia.
  - Cada post-it muestra: **nombre**, importancia (color), estado (icono), horario si existe y marca de "común".
  - **Orden por defecto**: primero las tareas con hora (cronológico), después las que no tienen hora, ordenadas por prioridad (urgente → alta → media → baja).
  - **Reordenable manualmente** con drag & drop (SortableJS); si el usuario reordena, su orden manda y se persiste en BD.
  - Sección separada: **Tareas comunes** y **Tareas del día**, diferenciadas visualmente (borde superior y fondo distintos). Al filtrar por tipo, el otro panel desaparece y el visible se centra manteniendo su ancho.
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

### 9.8 App móvil (PWA instalable, gratis, iOS y Android)

**Decisión de arquitectura**: PWA sobre la misma web publicada, en lugar de app nativa.

| Opción | Coste | Código | Push en iOS | Veredicto |
|---|---|---|---|---|
| **PWA** | 0 € | El mismo | Sí (iOS ≥ 16.4, instalada) | ✅ Elegida |
| Capacitor / tiendas | 99 €/año Apple + 25 € Google | Wrapper + publicación | Sí | Futuro, si se quiere estar en tiendas |
| Nativa (Swift/Kotlin) | Idem | 2 códigos nuevos | Sí | Descartada |

**Requisitos de instalación**
- `manifest.webmanifest`: `name`, `short_name: "Owngarnization"`, `start_url: "/app?source=pwa"`, `scope: "/"`, `display: "standalone"`, `background_color: #FAF8F5`, `theme_color: #111111`, `lang: "es"`, iconos 192/512 + **maskable** 512.
- `base.html`: `<link rel="manifest">`, `<meta name="theme-color">`, `apple-touch-icon` 180×180, `apple-mobile-web-app-capable`, `apple-mobile-web-app-status-bar-style`, y `viewport` con `viewport-fit=cover`.
- **Service Worker en `/sw.js` (raíz)**, no en `/static/`, para que su `scope` cubra toda la app.
- HTTPS obligatorio (Render ya lo da).

**Experiencia de instalación**
- **Android**: capturar `beforeinstallprompt` y mostrar un botón propio "Instalar app" (no el banner automático).
- **iOS**: no existe prompt programático; si es Safari y no está en modo `standalone`, mostrar mini-guía: *Compartir ⬆️ → "Añadir a pantalla de inicio"*. Descartable y recordado en `localStorage`.
- Aviso para iOS: la PWA instalada tiene **almacenamiento separado de Safari**, así que el usuario inicia sesión una vez dentro de la app. Ampliar la caducidad de la cookie de sesión (p. ej. 30 días) para no pedirlo a menudo.

**Offline (alcance mínimo y honesto)**
- Cache-first para el *app shell* (CSS, JS, iconos, fuentes) con versión de caché (`owng-v{N}`) y limpieza en `activate`.
- Network-first para `/api/*`; sin conexión se muestran los últimos datos cacheados de **solo lectura** y un aviso "Sin conexión".
- Fuera de alcance: crear/editar sin conexión con sincronización posterior.

### 9.9 Notificaciones de tareas con hora

**Flujo**
1. El usuario pulsa "Activar avisos" (el permiso **solo** se pide tras un gesto explícito; iOS lo exige y Chrome penaliza pedirlo al cargar).
2. `push.js` obtiene la clave VAPID, se suscribe con `pushManager.subscribe({ userVisibleOnly: true, applicationServerKey })` y envía la suscripción a `/api/push/subscriptions`.
3. **cron-job.org** llama cada minuto a `POST /internal/reminders/dispatch` con `X-Cron-Secret`.
4. `reminder_service` busca ocurrencias dentro de la ventana de envío (ver 5.2), envía con `pywebpush` a todos los dispositivos del usuario y marca `reminder_sent_at` **en la misma transacción**.
5. `sw.js` muestra la notificación; al pulsarla, enfoca la ventana abierta o abre `/app?date=YYYY-MM-DD&occ={id}` con el detalle de la tarea.

**Contenido de la notificación**
- Título: `⏱️ 09:30 · Reunión con cliente`. Cuerpo: "Empieza en 10 min · Prioridad alta".
- `tag: "occ-{id}"` (si se reenvía, reemplaza la anterior en lugar de duplicarla), `icon`, `badge` monocromo.
- Acción "✓ Marcar como hecha" en Android (iOS no soporta acciones: allí solo se abre la app).

**Preferencias** (`notification_settings.html`, accesible desde el menú de usuario)
- Interruptor general, antelación (0/5/10/15/30/60 min), botón "Enviar notificación de prueba" y estado del permiso del navegador (concedido / bloqueado, con instrucciones para desbloquearlo).

**Compatibilidad y limitaciones (a documentar en el README y en el manual)**
- Android: Chrome, Edge, Firefox y Samsung Internet, con o sin instalar.
- iOS/iPadOS ≥ 16.4: **solo si la PWA está añadida a la pantalla de inicio**. En Safari sin instalar no hay push; la UI debe indicarlo en lugar de mostrar un botón que no funciona.
- Precisión: ±1 min (frecuencia del cron) más el arranque en frío de Render (~30-60 s) si estaba dormido. El cron cada minuto mantiene la instancia despierta; una sola instancia 24/7 consume ~744 h y cabe en las 750 h/mes gratis.
- Modo "No molestar" o ahorro de batería del sistema pueden retrasar o silenciar avisos: no es controlable desde la web.

### 9.10 Experiencia móvil (mobile-first)

**Navegación y layout** (breakpoint principal `≤ 768px`)
- La barra lateral de filtros pasa a **bottom sheet** que se abre con un botón "Filtros" (con contador de filtros activos).
- **Barra inferior fija** con Día · Semana · Mes y **botón flotante ＋** para nueva tarea; la cabecera se reduce a logo, búsqueda (icono que se expande) y menú.
- Vista Día: un solo panel visible a la vez con **pestañas segmentadas "Del día / Comunes"** (reutiliza la lógica del filtro de tipo), en lugar de apilar dos columnas largas.
- Modal de tarea y panel de detalle a **pantalla completa / bottom sheet** con cierre por botón y gesto de deslizar hacia abajo.
- Usar `100dvh` en vez de `100vh` y respetar `env(safe-area-inset-*)` (notch y barra de gestos de iPhone).

**Táctil**
- Áreas táctiles de **mínimo 44×44 px** (botón de estado del post-it incluido).
- SortableJS con `delay: 200` y `delayOnTouchOnly: true` (mantener pulsado para arrastrar) para que no choque con el scroll; feedback visual al "levantar" la tarjeta.
- Efectos `:hover` solo bajo `@media (hover: hover)` para evitar estados pegados en táctil.
- Inputs con `font-size ≥ 16px` (evita el zoom automático de iOS), teclados adecuados (`type="time"`, `type="date"`, `inputmode`, `enterkeyhint`).
- Ocultar la sección de atajos de teclado en dispositivos táctiles.

**Calendario en móvil**
- Mes: `dayMaxEvents: 2` con "+N", tocar un día abre la vista Día.
- Semana: cambiar a `listWeek` (lista agrupada por día) o vista de 3 días, porque 7 columnas no son legibles en 375 px.

**Rendimiento** (objetivo Lighthouse móvil ≥ 90 en Performance, Accessibility, Best Practices)
- `defer` en scripts, cargar FullCalendar solo al entrar en Semana/Mes, iconos y capturas del manual en WebP con `loading="lazy"`.

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

### Bloque móvil (Fases 15-18) — planificado con Review Driven Development (RDD)

**Cómo se trabaja este bloque**
- El trabajo se divide en **PRs pequeños** (objetivo: ≤ ~400 líneas de diff, una sola responsabilidad). Cada PR se diseña **pensando en cómo se va a revisar**: qué se debe mirar, qué evidencias lo prueban y qué lo bloquea.
- Cada PR define **antes de escribir código**: objetivo, alcance y fuera de alcance, riesgos, **checklist de revisión** y **evidencias obligatorias**. Si un PR no se puede revisar en ~20 min, se parte.
- **Gate**: un PR no se mergea sin checklist completo, evidencias adjuntas y tests en verde. La fase siguiente no empieza hasta cerrar la revisión de fase (*phase review*).
- Severidad de comentarios de revisión: **🔴 Bloqueante** (bug, seguridad, pérdida de datos, rompe criterio) · **🟡 Debe arreglarse** antes de cerrar la fase · **🔵 Sugerencia** (se apunta como deuda en el README si no se hace).
- Revisión transversal en **todos** los PRs (además del checklist propio): aislamiento por `user_id`, CSRF en peticiones que modifican, secretos solo en entorno, sin `innerHTML` con datos de usuario sin escapar, textos en español, ningún archivo > ~250 líneas, sin regresiones en escritorio.

#### Revisión 0 — Revisión del plan (antes de cualquier código)
Decisiones que el responsable del producto debe **aprobar o cambiar**:
1. PWA en lugar de app de tiendas (coste 0 €, mismo código).
2. Avisos por Web Push + cron externo cada minuto (cron-job.org).
3. Antelación por defecto: 10 min. Ventana de gracia: 15 min (después se descarta el aviso).
4. Offline solo lectura (sin edición offline en esta versión).
5. Vista Día en móvil con pestañas "Del día / Comunes" en lugar de dos columnas apiladas.
- **Evidencia**: decisiones anotadas en el README (sección "Decisiones"). **Gate**: aprobación explícita.

#### Fase 15 — Experiencia móvil (mobile-first)

**PR 15.0 — Corrección del orden por defecto de la vista Día** *(defecto detectado en revisión)*
- Problema: `position` se rellena siempre al crear ocurrencias, así que el orden por hora/prioridad casi nunca se aplica.
- Solución: marcar si el usuario reordenó ese día (p. ej. `manual_order` en la ocurrencia, puesto a `true` por `/reorder`). Sin orden manual → hora ↑, sin hora al final por prioridad; con orden manual → `position`.
- Checklist: migración reversible · el orden manual sobrevive a recargar · una tarea nueva en un día ya reordenado aparece al final · tests de ambos casos.
- Evidencias: salida de pytest + captura antes/después.

**PR 15.1 — Auditoría móvil (solo documento, sin código)**
- Recorrer login, registro, app (día/semana/mes), drawer, modal, proyectos y manuales a 360/375/390/430 px.
- Entregable: tabla de defectos con captura, severidad y PR que lo resolverá.
- Checklist: cubre todas las pantallas · cada defecto tiene dueño (PR) · nada queda "sin asignar".

**PR 15.2 — Cimientos móviles**
- `mobile.css`, viewport con `viewport-fit=cover`, `100dvh`, safe areas, `:hover` solo bajo `@media (hover: hover)`, inputs ≥ 16 px.
- Checklist: sin scroll horizontal a 360 px · iOS no hace zoom al enfocar inputs · escritorio idéntico al actual.
- Evidencias: capturas 360 px y 1440 px de cada pantalla.

**PR 15.3 — Navegación móvil**
- `mobile_nav.html` (Día · Semana · Mes + ＋ flotante), cabecera compacta, filtros en bottom sheet con contador.
- Checklist: navegación con una mano (zona del pulgar) · bottom sheet se cierra con ✕, fondo y `Esc` · foco atrapado y devuelto · contador refleja filtros activos.
- Evidencias: vídeo corto o GIF del flujo + captura de Lighthouse Accessibility.

**PR 15.4 — Vista Día, modal y drawer táctiles**
- Pestañas "Del día / Comunes", modal y drawer a pantalla completa, botón de estado ≥ 44 px, SortableJS con `delay: 200` y `delayOnTouchOnly`.
- Checklist: arrastrar no bloquea el scroll · el cambio de estado no abre el drawer por error · el teclado virtual no tapa el botón Guardar.
- Evidencias: GIF arrastrando en móvil real o emulado.

**PR 15.5 — Calendario en móvil**
- Mes con `dayMaxEvents: 2`; semana en `listWeek` por debajo de 768 px; FullCalendar cargado solo al entrar en Semana/Mes.
- Checklist: cambiar de tamaño de ventana no deja el calendario roto · tocar un día abre la vista Día.

**Revisión de fase 15** — Gate: sin scroll horizontal a 360 px, áreas táctiles ≥ 44 px, Lighthouse móvil ≥ 90 en Accessibility, todos los defectos 🔴/🟡 de la auditoría cerrados.

#### Fase 16 — PWA instalable

**PR 16.1 — Manifest e iconos**
- Iconos 192/512/maskable/apple-touch-icon/badge, `routers/pwa.py` sirviendo `/manifest.webmanifest`, metaetiquetas iOS en `base.html`.
- Checklist: el icono maskable no se recorta (maskable.app) · `start_url` y `scope` correctos · `theme_color` coherente con la paleta.
- Evidencias: panel *Application → Manifest* de DevTools sin avisos.

**PR 16.2 — Service Worker y offline**
- `/sw.js` en la raíz con `Cache-Control: no-cache`, caché versionada del shell, network-first en `/api/*`, pantalla "Sin conexión".
- Riesgos a revisar con lupa: **servir HTML o datos de otro usuario desde caché** (no cachear respuestas autenticadas compartidas; limpiar caché al cerrar sesión) · usuarios atrapados en versiones viejas (versionado + `skipWaiting` controlado).
- Checklist: logout borra cachés de API · un despliegue nuevo se activa sin pedir borrar datos · modo avión muestra la pantalla offline.
- Evidencias: captura de *Application → Service Workers* y de modo avión.

**PR 16.3 — Experiencia de instalación**
- `pwa.js` + `install_banner.html`: botón con `beforeinstallprompt` (Android) y guía "Compartir → Añadir a inicio" (iOS), descartable y recordado.
- Checklist: no aparece si ya está instalada (`display-mode: standalone`) · no aparece en escritorio si no aplica · no molesta tras descartarlo.

**Revisión de fase 16** — Gate: Lighthouse marca "instalable", instalación probada en Android (Chrome) e iOS (Safari) reales, abre en standalone.

#### Fase 17 — Notificaciones: backend

**PR 17.1 — Modelo de datos y zona horaria**
- Migración: `User.timezone`, `reminders_enabled`, `reminder_offset_min`; `PushSubscription`; `TaskOccurrence.reminder_sent_at`. Guardar zona horaria al iniciar sesión. Calcular "hoy" con la zona del usuario (incluido el traspaso de pendientes).
- Checklist: migración `upgrade` y `downgrade` probadas · zona horaria inválida se rechaza · usuarios existentes reciben valores por defecto.
- Tests: traspaso de pendientes con usuario en `Europe/Madrid` y servidor en UTC alrededor de medianoche.

**PR 17.2 — Suscripciones y preferencias (API)**
- `/api/push/public-key`, `/api/push/subscriptions` (POST/DELETE), `/api/me/preferences`, `push_service.py`.
- Checklist: `endpoint` único (re-suscribirse no duplica) · un usuario no puede borrar la suscripción de otro · validación Pydantic de las claves.

**PR 17.3 — Dispatcher de recordatorios**
- `reminder_service.py` + `/internal/reminders/dispatch` con `X-Cron-Secret` (comparación en tiempo constante, `hmac.compare_digest`).
- Riesgos a revisar con lupa: **avisos duplicados** (marcar `reminder_sent_at` en la misma transacción; tolerar dos crons solapados) · **consultas N+1** con muchos usuarios · suscripciones caducadas (404/410 → borrar) · el endpoint no debe filtrar datos en la respuesta (solo contadores).
- Tests (pywebpush simulado): ventana correcta · sin duplicados · ignora `done` y sin hora · respeta interruptor y antelación · varias zonas horarias · reset al cambiar hora/fecha · 401 sin secreto · aislamiento entre usuarios.

**Revisión de fase 17** — Gate: todos los tests (nuevos y existentes) en verde, revisión de seguridad del endpoint interno y de los secretos VAPID completada.

#### Fase 18 — Notificaciones: frontend y QA en dispositivos reales

**PR 18.1 — Activación y preferencias**
- `push.js` + `notification_settings.html`: permiso solo tras gesto del usuario, antelación, botón de prueba, estado del permiso, mensaje específico para iOS sin instalar.
- Checklist: nunca se pide permiso al cargar · permiso denegado muestra cómo desbloquearlo · desactivar borra la suscripción del dispositivo.

**PR 18.2 — Service Worker: push y clic**
- Eventos `push`, `notificationclick` (enfocar o abrir `/app?date=…&occ=…`) y `pushsubscriptionchange`; acción "✓ Marcar como hecha" en Android.
- Checklist: `tag: occ-{id}` evita duplicados visuales · el clic abre la tarea correcta aunque la app esté cerrada · la acción respeta CSRF y sesión.

**PR 18.3 — Operación y documentación**
- Configurar cron-job.org cada minuto con alertas de fallo; README (variables VAPID, `CRON_SECRET`, limitaciones iOS); pestaña "App móvil y avisos" en el manual.

**Revisión de fase 18 (QA final)** — Matriz de pruebas con evidencia (captura o vídeo) por celda:

| Caso | iPhone PWA (iOS ≥ 16.4) | Android Chrome (PWA) | Android Chrome (sin instalar) | Escritorio |
|---|---|---|---|---|
| Aviso con app cerrada | | | | |
| Aviso con pantalla bloqueada | | | | |
| Dos dispositivos del mismo usuario | | | | |
| Permiso denegado | | | | |
| Cambio de hora tras el aviso → nuevo aviso | | | | |
| Clic abre la tarea correcta | | | | |

Gate: una tarea a +12 min con antelación de 10 min genera **una sola** notificación en ±1 min en iOS y Android, y al pulsarla se abre su detalle.

**Plantilla de descripción de PR** (copiar en cada PR del bloque)
```markdown
## Objetivo
## Alcance / Fuera de alcance
## Cómo revisarlo (orden de lectura de archivos y qué mirar)
## Riesgos
## Checklist de revisión
- [ ] Propio del PR (copiado del plan)
- [ ] Transversal (aislamiento, CSRF, secretos, escape HTML, español, tamaño de archivos, escritorio sin regresiones)
## Evidencias (tests, capturas 360/1440 px, Lighthouse, vídeo)
## Deuda anotada (sugerencias 🔵 no aplicadas)
```

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

**Añadidos para PWA y notificaciones**
- Variables nuevas: `VAPID_PUBLIC_KEY`, `VAPID_PRIVATE_KEY`, `VAPID_SUBJECT` (`mailto:tu@email.com`), `CRON_SECRET` (cadena larga aleatoria). Nunca en el repo.
- Añadir `pywebpush` a `requirements.txt`.
- **cron-job.org** (gratis): tarea cada minuto → `POST https://<tu-app>.onrender.com/internal/reminders/dispatch` con cabecera `X-Cron-Secret`. Activar avisos de fallo por email.
- Alternativa a evaluar si se migra de Render: un host sin suspensión permitiría un scheduler en proceso (APScheduler), pero el endpoint + cron externo sigue siendo válido y más fácil de probar.

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
- [ ] **Móvil**: todas las pantallas se ven y se usan bien desde 360 px (sin scroll horizontal, navegación inferior, bottom sheets, áreas táctiles ≥ 44 px, drag & drop táctil).
- [ ] **PWA**: la app se instala gratis desde la web publicada en iOS (Safari) y Android (Chrome), abre a pantalla completa y tiene icono propio.
- [ ] **Notificaciones**: las tareas con hora avisan con la antelación elegida, una sola vez, en la zona horaria del usuario, también con la app cerrada; al pulsar se abre la tarea.
- [ ] Las limitaciones de iOS (push solo con la PWA instalada, iOS ≥ 16.4) se explican en la UI, el manual y el README.

## 13. Reglas de trabajo para el agente

1. Trabaja **fase a fase**; no avances si la anterior no cumple su criterio de hecho.
2. Ejecuta y prueba el código tras cada fase; corrige errores antes de continuar.
3. No añadas dependencias innecesarias ni sobrediseñes (sin microservicios, sin frameworks JS pesados).
4. Commits pequeños con mensaje claro por fase.
5. Si algo del plan es ambiguo, aplica los **supuestos de la sección 2** y deja la decisión anotada en el README.
6. Todo el texto visible de la interfaz en **español**.
7. **Review Driven Development** en el bloque móvil y en todo trabajo nuevo: diseña cada PR para ser revisado (objetivo, riesgos, checklist y evidencias definidos antes del código), usa la plantilla de PR de la Fase 18 y no mergees sin pasar el gate.
