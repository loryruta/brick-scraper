from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import os

db_url=f"postgresql+psycopg2://{os.environ['DB_USERNAME']}:{os.environ['DB_PASSWORD']}@{os.environ['DB_HOST']}:{os.environ['DB_PORT']}/{os.environ['DB_DATABASE']}"
db_engine = create_engine(db_url)

Session = sessionmaker(db_engine)
