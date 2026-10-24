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

## 4. Estructura del proyecto

```
owngarnization/
├── app/
│   ├── main.py              # instancia FastAPI, middlewares, routers
│   ├── config.py            # variables de entorno (SECRET_KEY, DATABASE_URL)
│   ├── database.py          # engine, SessionLocal, Base
│   ├── models.py            # User, Task, TaskOccurrence
│   ├── schemas.py           # Pydantic
│   ├── security.py          # hash/verify password, helpers de sesión
│   ├── deps.py              # get_db, get_current_user
│   ├── routers/
│   │   ├── auth.py          # registro, login, logout
│   │   ├── pages.py         # vistas HTML
│   │   └── tasks.py         # API JSON de tareas
│   ├── templates/
│   │   ├── base.html
│   │   ├── login.html
│   │   ├── register.html
│   │   └── app.html         # pantalla principal (calendario + panel)
│   └── static/
│       ├── css/styles.css
│       └── js/{calendar.js, board.js, modal.js, api.js}
├── migrations/              # Alembic
├── tests/
├── requirements.txt
├── .env.example
├── Procfile / render.yaml   # despliegue
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
3. Tipo: **Común (todos los días)** / **Del día** (con selector de fecha; por defecto el día que se está viendo)
4. Importancia (baja / media / alta / urgente)
5. Estado inicial (por defecto "sin empezar")
6. **Hora inicio y hora fin (opcionales)** con validación de coherencia

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

## 13. Reglas de trabajo para el agente

1. Trabaja **fase a fase**; no avances si la anterior no cumple su criterio de hecho.
2. Ejecuta y prueba el código tras cada fase; corrige errores antes de continuar.
3. No añadas dependencias innecesarias ni sobrediseñes (sin microservicios, sin frameworks JS pesados).
4. Commits pequeños con mensaje claro por fase.
5. Si algo del plan es ambiguo, aplica los **supuestos de la sección 2** y deja la decisión anotada en el README.
6. Todo el texto visible de la interfaz en **español**.
