from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from app.config import settings

# Configuración de conexiones optimizada para escalabilidad y alta concurrencia
connect_args = {}
engine_kwargs = {
    "pool_pre_ping": True,  # Comprueba que la conexión está viva antes de usarla
}

if settings.normalized_database_url.startswith("sqlite"):
    connect_args["check_same_thread"] = False
else:
    # Optimización para PostgreSQL en producción (Neon, Render, Supabase, etc.)
    engine_kwargs.update({
        "pool_size": 10,       # Conexiones base del pool
        "max_overflow": 20,    # Conexiones adicionales permitidas bajo picos de carga
        "pool_recycle": 300,   # Reciclar conexiones inactivas cada 5 min (evita desconexiones por timeout en Neon)
        "pool_timeout": 30,    # Segundos máximos de espera antes de error si el pool está saturado
    })

engine = create_engine(
    settings.normalized_database_url,
    connect_args=connect_args,
    **engine_kwargs
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()
