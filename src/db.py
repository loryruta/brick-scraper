from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import os

db_url = os.environ["DB_URL"]
db_engine = create_engine(db_url)

Session = sessionmaker(db_engine)
