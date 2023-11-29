from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
import os


URL_DATABASE = 'postgresql://moki:1331Mati??@localhost:5432/sacc'
# URL_DATABASE = 'postgresql://postgres:Admin123@localhost:5432/sacc'
# URL_DATABASE = os.environ.get("DATABASE_URL")

engine = create_engine(URL_DATABASE)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


Base = declarative_base()
