
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey

from database import Base

class Station(Base):
    __tablename__ = "station"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, unique=True)
    address = Column(String, unique=True)
    
class Locker(Base):
    __tablename__ = "locker"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    personal_id = Column(Integer)
    state = Column(Integer)
    height = Column(Integer)
    width = Column(Integer)
    depth = Column(Integer)
    code = Column(String, unique=True, nullable=True)
    station_id = Column(Integer, ForeignKey("station.id"))
    
class Order(Base):
    __tablename__ = "order"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String)
    width = Column(Integer)
    height = Column(Integer)
    depth = Column(Integer)
    
class User(Base):
    __tablename__ = "user"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String)
    token = Column(String)
    timeforpickup = Column(Integer)
    
    
class Reservation(Base):
    __tablename__ = "reservation"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    client_email = Column(String)
    order_id = Column(Integer, ForeignKey("order.id"))
    locker_id = Column(Integer, ForeignKey("locker.id"))
    locker_personal_id = Column(Integer)
    station_id = Column(Integer, ForeignKey("station.id"))
    fecha = Column(DateTime)
    estado = Column(String)
    user_id = Column(Integer, ForeignKey("user.id"))

    
class States(Base):
    __tablename__ = "states"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    locker_id = Column(Integer, ForeignKey("locker.id"))
    state = Column(Integer)
    
class Historial(Base):
    __tablename__ = "historial"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    reservation_id = Column(Integer, ForeignKey("reservation.id"))
    user_id = Column(Integer, ForeignKey("user.id"))
    locker_id = Column(Integer, ForeignKey("locker.id"))
    station_id = Column(Integer, ForeignKey("station.id"))
    fecha = Column(DateTime)
    order_id = Column(Integer, ForeignKey("order.id"))
    accion = Column(String)
    email = Column(String)