import os
from pathlib import Path

from alembic import context
from sqlalchemy import pool, create_engine
from sqlalchemy.engine import make_url
from dotenv import load_dotenv

from registry.models import Base

config = context.config
load_dotenv(Path(__file__).resolve().parents[1] / ".env.registry")
url = os.getenv("REGISTRY_DATABASE_URL") or config.get_main_option("sqlalchemy.url")
parsed = make_url(url)
if parsed.get_backend_name() == "sqlite" and parsed.database and parsed.database != ":memory:":
    Path(parsed.database).parent.mkdir(parents=True, exist_ok=True)
options = dict(target_metadata=Base.metadata, version_table="registry_alembic_version")

if context.is_offline_mode():
    context.configure(url=url, literal_binds=True, **options)
    with context.begin_transaction():
        context.run_migrations()
else:
    engine = create_engine(url, poolclass=pool.NullPool)
    with engine.connect() as connection:
        context.configure(connection=connection, **options)
        with context.begin_transaction():
            context.run_migrations()
