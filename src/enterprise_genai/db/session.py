from sqlalchemy import Engine, create_engine, text

from enterprise_genai.core.config import get_settings

settings = get_settings()

engine: Engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
)


def check_database() -> None:
    """Verify PostgreSQL connectivity and required extensions."""

    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))

        vector_installed = connection.execute(
            text(
                """
                SELECT EXISTS (
                    SELECT 1
                    FROM pg_extension
                    WHERE extname = 'vector'
                )
                """
            )
        ).scalar_one()

        if not vector_installed:
            raise RuntimeError("Required PostgreSQL extension 'vector' is unavailable.")
