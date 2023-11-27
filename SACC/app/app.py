from fastapi import FastAPI, HTTPException, Depends,BackgroundTasks, Request
import requests
import models
from database import engine, SessionLocal
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import Annotated
import json
from itertools import permutations
from enum import Enum
import random
import string
import os
from send_email import send_email_async
from datetime import datetime
from fastapi_mqtt.fastmqtt import FastMQTT
from fastapi_mqtt.config import MQTTConfig
import json
from fastapi.templating import Jinja2Templates

templates = Jinja2Templates(directory="templates")
MQTT = False


locker_state = {
    "station_id": "G1", 
    "lockers": [
    {
        "nickname": "1",
        "state": 0,
        "is_open": False,
        "is_empty": True,
    },
    {
        "nickname": "2",
        "state": 0,
        "is_open": False,
        "is_empty": True,
    },
    {
        "nickname": "3",
        "state": 0,
        "is_open": False,
        "is_empty": True,
    }
    ]
}

# def get_comparisson_locker_state(db_state, locker_id, locker_state=locker_state):
#     for locker in locker_state["lockers"]:
#         if locker["nickname"] == str(locker_id):
#             if locker["state"] == db_state:
#                 return True
#             else:
#                 return False
#     return False


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
        
def load_initial_data(db: Session):
    # Verificar si la tabla Station está vacía
    if not db.query(models.Station).count():
        # Si está vacía, cargar datos
        db_station = models.Station(address="G1", id=1)
        db.add(db_station)
        # db_station = models.Station(address="G3", id=2)
        # db.add(db_station)
        # db_station = models.Station(address="G5", id=3)
        # db.add(db_station)
        db.commit()

    # Verificar si la tabla Locker está vacía
    if not db.query(models.Locker).count():
        # Si está vacía, cargar datos
        db_locker = models.Locker(state=0, height=20, width=40, depth=20, station_id=1, id=1, personal_id=1)
        db.add(db_locker)
        db_locker = models.Locker(state=0, height=30, width=40, depth=20, station_id=1, id=2, personal_id=2)
        db.add(db_locker)
        db_locker = models.Locker(state=0, height=40, width=40, depth=20, station_id=1, id=3, personal_id=3)
        db.add(db_locker)
        db.commit()
        
        # db_locker = models.Locker(state=0, height=20, width=50, depth=25, station_id=2, id=4, personal_id=1)
        # db.add(db_locker)
        # db_locker = models.Locker(state=0, height=20, width=60, depth=25, station_id=2, id=5, personal_id=2)
        # db.add(db_locker)
        # db_locker = models.Locker(state=0, height=20, width=30, depth=25, station_id=2, id=6, personal_id=3)
        # db.add(db_locker)
        # db.commit()
        # db_locker = models.Locker(state=0, height=30, width=30, depth=30, station_id=3, id=7, personal_id=1)
        # db.add(db_locker)
        # db_locker = models.Locker(state=0, height=30, width=40, depth=30, station_id=3, id=8, personal_id=2)
        # db.add(db_locker)
        # db_locker = models.Locker(state=0, height=20, width=50, depth=30, station_id=3, id=9, personal_id=3)
        # db.add(db_locker)
        # db.commit()
        
    if not db.query(models.User).count():
        db_user = models.User(name="operario1", email="mati.munoz.314@gmail.com", typeUser="operario")
        db.add(db_user)
        db_user = models.User(name="operario2", email="oper2@example.com", typeUser="operario")
        db.add(db_user)
        db_user = models.User(name="cliente1", email="mamunoz11@miuandes.cl", typeUser="cliente")
        db.add(db_user)
        db_user = models.User(name="cliente2", email="client2@example.com", typeUser="cliente")
        db.add(db_user)
        db.commit()

    if not db.query(models.States).count():
        lockers = db.query(models.Locker).all()
        for locker in lockers:
            db_state = models.States(locker_id=locker.id, state=locker.state)
            db.add(db_state)
        db.commit()
    
    
dp_dependecy = Annotated[Session, Depends(get_db)]
rellenar = True
if rellenar:
    load_initial_data(db=SessionLocal())

timeout_seconds = 10

def create_record(db: Session, reservation_id: int, user_id: int, locker_id: int, station_id: int, fecha: datetime, order_id: int, accion: str):
    db_historial = models.Historial(reservation_id=reservation_id, user_id=user_id, locker_id=locker_id, station_id=station_id, fecha=fecha, order_id=order_id, accion=accion)
    db.add(db_historial)
    db.commit()

def get_all_locker_from_station(db: Session, station_id: int):
    sql_query = text(f"SELECT * FROM locker WHERE station_id = {station_id}")
    result = db.execute(sql_query)
    return result.fetchall()

def all_stations(db: Session):
    sql_query = text(f"SELECT * FROM station")
    result = db.execute(sql_query)
    return result.fetchall()

def all_lockers(db: Session):
    sql_query = text(f"SELECT * FROM locker")
    result = db.execute(sql_query)
    return result.fetchall()

def get_locker_by_station_and_personal_id(db: Session, station_id: int, personal_id: int):
    sql_query = text(f"SELECT * FROM locker WHERE station_id = {station_id} AND personal_id = {personal_id}")
    result = db.execute(sql_query)
    return result.fetchone()[0]

def all_users(db: Session):
    sql_query = text(f"SELECT * FROM user")
    result = db.execute(sql_query)
    return result.fetchall()

def get_locker_personal_id(db: Session, locker_id: int):
    sql_query = text(f"SELECT * FROM locker WHERE id = {locker_id}")
    result = db.execute(sql_query)
    return result.fetchone()[1]

def locker_and_station_by_reservation_id(db: Session, reservation_id: int):
    sql_query = text(f"SELECT * FROM locker WHERE id = (SELECT locker_id FROM 'order' WHERE id = (SELECT order_id FROM reservation WHERE id = {reservation_id}))")
    result = db.execute(sql_query)
    return result.fetchone()

def station_by_locker_id(db: Session, locker_id: int):
    sql_query = text(f"SELECT * FROM station WHERE id = (SELECT station_id FROM locker WHERE id = {locker_id})")
    result = db.execute(sql_query)
    return result.fetchone()

def calcular_volumen(tupla):
    alto, ancho, profundo = tupla[3], tupla[4], tupla[5]
    return alto * ancho * profundo

def encontrar_locker_mas_pequeno(alto_paquete, ancho_paquete, profundidad_paquete, lockers):
    lockers_ordenados = sorted(lockers, key=calcular_volumen)
    for i in lockers_ordenados:
        if alto_paquete <= i[3] and ancho_paquete <= i[4] and profundidad_paquete <= i[5]:
            return i
    return None

def generar_clave_alfanumerica(longitud=12):
    """
    Genera una clave alfanumérica aleatoria.

    Args:
    - longitud (int): Longitud de la clave. Por defecto, 12.

    Returns:
    - str: Clave alfanumérica generada.
    """
    caracteres = string.ascii_letters + string.digits  # Letras (mayúsculas y minúsculas) y dígitos
    clave_generada = ''.join(random.choice(caracteres) for _ in range(longitud))
    return clave_generada

app = FastAPI()
if MQTT:
    mqtt_config = MQTTConfig(
        host="ab34c5b092fc416db7e2f21aa7d38514.s1.eu.hivemq.cloud",
        port=8883,
        ssl=True,
        keepalive=60,
        username="M0ki1",
        password="",
    )
    mqtt = FastMQTT(config=mqtt_config)
    mqtt.init_app(app)

mqtt_config = MQTTConfig(
    host="ab34c5b092fc416db7e2f21aa7d38514.s1.eu.hivemq.cloud",
    port=8883,
    ssl=True,
    keepalive=60,
    username="M0ki1",
    password="",
)
mqtt = FastMQTT(config=mqtt_config)
mqtt.init_app(app)

estados_generales = {
    0: "available",
    1: "reserved",
    2: "loading",
    3: "used",
    4: "unloading"
}

def get_state_by_state_number(state_number, estados_generales=estados_generales):
    return estados_generales[state_number]
    

if MQTT:
    @mqtt.on_connect()
    def connect(client, flags, rc, properties):
        mqtt.client.subscribe("/mqtt") #subscribing mqtt topic
        print("Connected: ", client, flags, rc, properties)

    @mqtt.on_message()
    async def message(client, topic, payload, qos, properties):
        print("Received message: ",topic, payload.decode(), qos, properties)
        return 0

    @mqtt.subscribe("g1/physical_verification")
    async def message_to_topic(client, topic, payload, qos, properties):
        print("Received message to specific topic: ", topic, payload.decode(), qos, properties)
        print(payload.decode())
        global locker_state
        locker_state = json.loads(payload.decode())

    @mqtt.on_disconnect()
    def disconnect(client, packet, exc=None):
        print("Disconnected")

    @mqtt.on_subscribe()
    def subscribe(client, mid, qos, properties):
        print("subscribed", client, mid, qos, properties)


# del pdf es la 1
@app.get("/stations",tags=['GET STATIONS'])
async def get_available_lockers(db: dp_dependecy):
    try:
        try:
            lockers = all_lockers(db)
            data = {}
            for i in lockers:
                if i[2] == 0:
                    if i[7] not in data:
                        data[i[7]] = {i[1]: ("available", f"{i[3]}x{i[4]}x{i[5]}")}
                    else:
                        data[i[7]][i[1]] = ("available", f"{i[3]}x{i[4]}x{i[5]}")
            for i in all_stations(SessionLocal()):
                if i[0] not in data:
                    data[i[1]] = "No hay casilleros disponibles"
                else:
                    data[i[1]] = data.pop(i[0])
            return {"content": data}
        except Exception as e:
            return {"message": f"Error: {e}"}
    except requests.exceptions.Timeout:
        return {"message": "Timeout error"}

# del pdf es la 2
@app.post('/reserve', tags=['RESERVAR'])
async def reservar(alto_paquete: int, ancho_paquete: int, profundidad_paquete: int, user_id: int, db: dp_dependecy):
    try:
        try:
            sql_query = text(f"SELECT * FROM locker WHERE state = 0")
            result = db.execute(sql_query)
            lockers = result.fetchall()
            if len(lockers) == 0:
                return {"message": "Failed to reserve, no available lockers"}
            sql_query = text(f'SELECT * FROM "user" WHERE id = {user_id}')
            result = db.execute(sql_query)
            user = result.fetchone()
            if user is None:
                return {"message": "Failed to reserve, user does not exist"}
            locker_encontrado = encontrar_locker_mas_pequeno(alto_paquete, ancho_paquete, profundidad_paquete, lockers)
            if locker_encontrado is None:
                return {"message": "Failed to reserve, package is too big for available lockers"}
            else:
                # Creo una orden ficticia, porque debería exisitr una orden de antes
                db_order = models.Order(name="order ficitica", width=ancho_paquete, height=alto_paquete, depth=profundidad_paquete)
                db.add(db_order)
                db.commit()
                # Reservo el locker cambiando el estado
                sql_query = text(f"UPDATE locker SET state = 1 WHERE id = {locker_encontrado[0]}")
                db.execute(sql_query)
                db.commit()
                # Creo la reserva
                db_reservation = models.Reservation(user_id=user_id, order_id=db_order.id, locker_id=locker_encontrado[0], locker_personal_id=get_locker_personal_id(db, locker_encontrado[0]), station_id=station_by_locker_id(db, locker_encontrado[0])[0], fecha=datetime.now(), estado="activa")
                db.add(db_reservation)
                db.commit()
                # asigno un codigo al locker
                clave = generar_clave_alfanumerica()
                sql_query = text(f"UPDATE locker SET code = '{clave}' WHERE locker.id = {locker_encontrado[0]}")
                db.execute(sql_query)
                db.commit()
                # añadir el cambio de estado a la tabla states
                sql_query = text(f"INSERT INTO states (locker_id, state) VALUES ({locker_encontrado[0]}, 1)")
                db.execute(sql_query)
                db.commit()
                sql_query = text(f'SELECT * FROM "locker" WHERE id = {locker_encontrado[0]}')
                result = db.execute(sql_query)
                locker_personal = result.fetchone()
                create_record(db, db_reservation.id, user_id, locker_encontrado[0], station_by_locker_id(db, locker_encontrado[0])[0], datetime.now(), db_order.id, "creacion reserva")
                
                # ACA DEBERIA DE MANDAR EL CORREO Y TAMBIEN MANDAR UN MQTT CON QUE EL ESTADO DE ESE LOCKER 
                #PASA A 1 -> RESERVADO
                #TODO hacer esto dinamico para la estaciona asignada pipipi
                print("no llegue")
                print(locker_encontrado[0])
                if MQTT:
                    mqtt.publish("g1/reserve", {"nickname":f"{locker_personal[1]}","state":"1"}) #publishing mqtt topic
                    print("QUE TA PASANDO")
                    mqtt.publish("g1/verification", {"nickname":""}) #publishing mqtt topic


                return {"message": "Reservation successful", "locker_id": locker_encontrado[0], "station_id": station_by_locker_id(db, locker_encontrado[0])[0], "code": clave}
        except Exception as e:
            return {"message": f"Error: {e}"}
    except requests.exceptions.Timeout:
        return {"message": "Timeout error"}
    
# pdf parte 3
@app.post('/confirm_reservation', tags=['CONFIRM RESERVATION'])
async def confirm_reservation(reservation: int, db: dp_dependecy):
    try:
        try:
            sql_query = text(f"SELECT * FROM reservation WHERE id = {reservation}")
            result = db.execute(sql_query)
            reserva = result.fetchone()
            if reserva is None:
                return {"message": "Failed to confirm reservation, reservation does not exist"}
            else:
                #get time from reservation and compare with current time
                time_reserved = reserva[6]
                time_now = datetime.now()
                time_difference = time_now - time_reserved
                sql_query = text(f"SELECT * FROM locker WHERE id = {reserva[3]}")
                result = db.execute(sql_query)
                locker_obtenido = result.fetchone()
                #Igual la idea aca es que si pasa mucho tiempo gg y murio la reserva por lo que
                #Habria que borrarla de la BBDD
                if locker_obtenido[2] == 1:
                    #Correo de que el operario debe ver esta 
                    sql_query = text(f'SELECT * FROM "user" WHERE id={1}')
                    result = db.execute(sql_query)
                    operario = result.fetchone()
                    await send_email_async('Verificar medidas',f'{operario[2]}',
                            f"debes verificar la reserva {reservation}")
                    create_record(db, reserva[0], reserva[1], reserva[3], reserva[5], datetime.now(), reserva[2], "No se pudo confirmar por medidas")
                    #TODO va a entregar y el mqtt cambiar el estado del cajon especifico a reservado
                    
                    if MQTT:
                        mqtt.publish("g1/verification", {"nickname":""}) #publishing mqtt topic


                    return {"message": f"Time passed since reservation: {time_difference}"}
                else:
                    #TODO cambiar mqtt a disponible si esto pasa cajon, 0
                    create_record(db, reserva[0], reserva[1], reserva[3], reserva[5], datetime.now(), reserva[2], "reserva confirmada, medidas correctas")
                    if MQTT:
                        mqtt.publish("g1/reserve", {"nickname":locker_obtenido[1],"state":0}) #publishing mqtt topic
                    
                    return {"message": f"Failed to confirm reservation, locker is not reserved, it is {estados_generales[locker_obtenido[2]]} "}
        except Exception as e:
            return {"message": f"Error: {e}"}
    except requests.exceptions.Timeout:
        return {"message": "Timeout error"}
    
# del pdf es la 4
@app.post('/cancel_reservation', tags=['CANCEL RESERVATION'])
async def cancel_reservation(reservation: int, db: dp_dependecy): #TODO NUMERO DE CAJON
    try:
        try:
            sql_query = text(f"SELECT * FROM reservation WHERE id = {reservation}")
            result = db.execute(sql_query)
            reserva = result.fetchone()
            if reserva is None:
                return {"message": "Failed to cancel reservation, reservation does not exist"}
            else:
                sql_query = text(f"SELECT * FROM locker WHERE id = {reserva[2]}")
                result = db.execute(sql_query)
                locker_obtenido = result.fetchone()
                if locker_obtenido[2] == 1:
                    sql_query = text(f"UPDATE locker SET state = 0 WHERE id = {locker_obtenido[0]}")
                    db.execute(sql_query)
                    db.commit()
                    sql_query = text(f"UPDATE locker SET code = NULL WHERE id = {locker_obtenido[0]}")
                    db.execute(sql_query)
                    db.commit()
                    sql_query = text(f"UPDATE reservation SET estado = 'cancelada' WHERE reservation.id = {reservation}")
                    db.execute(sql_query)
                    db.commit()
                    sql_query = text(f"INSERT INTO states (locker_id, state) VALUES ({locker_obtenido[0]}, 0)")
                    db.execute(sql_query)
                    db.commit()
                    create_record(db, reserva[0], reserva[1], reserva[3], reserva[5], datetime.now(), reserva[2], "cancelacion reserva")
                    #TODO Cambiar cajon a disponible con el mqtt
                    if MQTT:
                        mqtt.publish("g1/reserve", {"nickname":locker_obtenido[1],"state":0}) #publishing mqtt topic
                        mqtt.publish("g1/verification", {"nickname":""}) #publishing mqtt topic






                    return {"message": "Reservation canceled successfully"}
                else:
                    return {"message": f"Failed to cancel reservation, locker is not reserved, it is {estados_generales[locker_obtenido[2]]} "}
        except Exception as e:
            return {"message": f"Error: {e}"}
    except requests.exceptions.Timeout:
        return {"message": "Timeout error"}

# del pdf es la 5
@app.post('/reservation_state', tags=['RESERVATION STATE'])
async def reservation_state(reservation: int, db: dp_dependecy):
    data = []
    try:
        try:
            sql_query = text(f"SELECT * FROM reservation WHERE id = {reservation}")
            result = db.execute(sql_query)
            locker_id = result.fetchone()[3]
            if locker_id is None:
                return {"message": "Failed to get reservation state, reservation does not exist"}
            else:
                sql_query = text(f"SELECT * FROM states WHERE locker_id = {locker_id}")
                result = db.execute(sql_query)
                states = result.fetchall()
                

                for state in states:
                    data.append({"locker_id": state[1], "state": estados_generales[state[2]]})
                
                actual_state = data[-1]["state"]
                message = [f"Current Locker state {reservation} is {actual_state}"]
                for state in data[:-1]:
                    message.append(f"Past Locker state {state['locker_id']} was {state['state']}")
                return {"content": message}
                
            
        except Exception as e:
            return {"message": f"Error: {e}"} 
    except requests.exceptions.Timeout:
        return {"message": "Timeout error"}
    
# 6 del pdf
@app.post('/confirm', tags=['CONFIRM'])
async def confirm(height: int, width: int, depth: int, reservation: int, db: dp_dependecy):
    try:
        try:
            sql_query = text(f"SELECT * FROM reservation WHERE id = {reservation}")
            result = db.execute(sql_query)
            reserva = result.fetchone()
            if reserva is None:
                return {"message": "Failed to confirm, reservation does not exist"}
            else:
                sql_query = text(f'SELECT * FROM locker WHERE id = {reserva[2]}')
                result = db.execute(sql_query)
                locker = result.fetchone()
                if locker is None:
                    return {"message": "Failed to confirm, locker does not exist"}
                else:
                    #compare the dimensions of the package with the dimensions of the locker
                    if height <= locker[3] and width <= locker[4] and depth <= locker[5]:

                        #TODO
                        #Mandar correo a operario con la clave de este locker para que lo 
                        #pueda abrir
                        sql_query = text(f'SELECT * FROM "user" WHERE id={1}')
                        result = db.execute(sql_query)
                        operario = result.fetchone()
                        await send_email_async('Entregar Product',f'{operario[2]}',
                                f"Debes entregar en la Estacion G1 en el espacio {locker[1]} el paquete con reservacion {reservation} con el codigo: {locker[6]}")
                        return {"message": "Package confirmed"}
                    else:
                        sql_query = text(f"UPDATE locker SET state = 0 WHERE id = {locker[0]}")
                        #TODO mandar mqtt para cambiar el estado del locker a disponible
                        if MQTT:
                            mqtt.publish("g1/reserve", {"nickname":locker[1],"state":0}) #publishing mqtt topic
                        
                        db.execute(sql_query)
                        db.commit()
                        sql_query = text(f"UPDATE reservation SET estado = 'cancelada' WHERE reservation.id = {reservation}")
                        db.execute(sql_query)
                        db.commit()
                        sql_query = text(f"INSERT INTO states (locker_id, state) VALUES ({locker[0]}, 0)")
                        db.execute(sql_query)
                        db.commit()
                        sql_query = text(f"SELECT * FROM locker WHERE state = 0")
                        result = db.execute(sql_query)
                        lockers = result.fetchall()
                        if len(lockers) == 0:
                            return {"message": "Failed to reserve, no available lockers"}
                        locker = encontrar_locker_mas_pequeno(height,width,depth,lockers)
                        if locker is None:
                            return {"message": "Failed to confirm, no available lockers"}
                        else:
                            sql_query = text(f"UPDATE locker SET state = 1 WHERE id = {locker[0]}")
                            db.execute(sql_query)
                            db.commit()
                            sql_query = text(f"UPDATE reservation SET locker_id = {locker[0]}, locker_personal_id = {locker[1]}, station_id = {locker[7]} WHERE id = {reservation}")
                            db.execute(sql_query)
                            db.commit()
                            sql_query = text(f"INSERT INTO states (locker_id, state) VALUES ({locker[0]}, 1)")
                            db.execute(sql_query)
                            db.commit()
                            create_record(db, reserva[0], reserva[1], reserva[3], reserva[5], datetime.now(), reserva[2], "Reasignacion de locker por espacio, reserva sigue activa y confirmada")
                            if MQTT:
                                mqtt.publish("g1/reserve", {"nickname":locker[1],"state":0}) #publishing mqtt topic
                                mqtt.publish("g1/verification", {"nickname":""}) #publishing mqtt topic

                            return {"message": f"Package re-assigned to locker {locker[0]}"}

        except Exception as e:
            return {"message": f"Error: {e}"}
    except requests.exceptions.Timeout:
        return {"message": "Timeout error"}
    



# 7 del pdf
@app.post('/ready', tags=['READY'])
async def ready(reservation: int, db: dp_dependecy):
    try:
        try:
            sql_query = text(f"SELECT * FROM reservation WHERE id = {reservation}")
            result = db.execute(sql_query)
            reserva = result.fetchone()
            if reserva is None:
                return {"message": "Failed to ready, reservation does not exist"}
            else:
                sql_query = text(f'SELECT * FROM "user" WHERE id = {reserva[1]}')
                result = db.execute(sql_query)
                user = result.fetchone()
                if user is None:
                    return {"message": "Failed to ready, user does not exist"}
                else:
                    #TODO ACA MANDAR UN CORREO AL USER
                    create_record(db, reserva[0], reserva[1], reserva[3], reserva[5], datetime.now(), reserva[2], "Listo para retirar")
                    return {"message": f'user {user[1]} ready to pick up package'}
        except Exception as e:
            return {"message": f"Error: {e}"}
    except requests.exceptions.Timeout:
        return {"message": "Timeout error"}
    

@app.post('/load', tags = ["LOAD"])
async def load(reservation: int,code: str, db: dp_dependecy):
    try:
        try:
            sql_query = text(f"SELECT * FROM reservation WHERE id = {reservation}")
            result = db.execute(sql_query)
            reserva = result.fetchone()
            if reserva is None:
                return {"message": "Failed to confirm, reservation does not exist"}
            else:
                sql_query = text(f'SELECT * FROM locker WHERE id = {reserva[3]}')
                result = db.execute(sql_query)
                locker = result.fetchone()
                if locker is None:
                    return {"message": "Failed to confirm, locker does not exist"}
                else:
                    if locker[6] != code:
                        print(locker[6])
                        return {"message":"Clave incorrecta"}
                    sql_query = text(f"INSERT INTO states (locker_id, state) VALUES ({locker[0]}, 3)")
                    db.execute(sql_query)
                    db.commit()
                    sql_query = text(f"UPDATE locker SET state = 3 WHERE id = {locker[0]}")
                    db.execute(sql_query)
                    db.commit()
                    print(locker[6])
                    #TODO aca debo hacer la llamada MQTT para abrir el cajon
                    if MQTT:
                        mqtt.publish("g1/load", {"nickname":locker[1]}) #publishing mqtt topic

                    sql_query = text(f'SELECT * FROM "user" WHERE id = {reserva[1]}')
                    result = db.execute(sql_query)
                    user = result.fetchone()
                    clave = generar_clave_alfanumerica()
                    sql_query = text(f"UPDATE locker SET code = '{clave}' WHERE locker.id = {locker[0]}")
                    db.execute(sql_query)
                    db.commit()
                    create_record(db, reserva[0], reserva[1], reserva[3], reserva[5], datetime.now(), reserva[2], "Paquete cargador en locker")
                    print(f"Nueva clave: ${clave}")
                    #TODO mandar el correo a este usuario con la nueva clave
                    sql_query = text(f'SELECT * FROM "user" WHERE id={3}')
                    result = db.execute(sql_query)
                    cliente = result.fetchone()
                    await send_email_async('Retirar producto',f'{cliente[2]}',
                            f"Debes retirar en la Estacion G1 en el espacio {locker[1]} el paquete con reservacion {reservation} con el codigo: {clave}")
                    if MQTT:
                        mqtt.publish("g1/verification", {"nickname":""}) #publishing mqtt topic




                    return {"message": f"Se ha abierto el espacio {locker[1]}, la nueva clave es {clave}"}
        except Exception as E:
            return {"message": f"{E}"}
    except requests.exceptions.Timeout:
        return {"message": "Timeout error"}


@app.post('/unload', tags = ["UNLOAD"])
async def load(reservation: int,code: str, db: dp_dependecy):
    try:
        try:
            sql_query = text(f"SELECT * FROM reservation WHERE id = {reservation}")
            result = db.execute(sql_query)
            reserva = result.fetchone()
            if reserva is None:
                return {"message": "Failed to confirm, reservation does not exist"}
            else:
                sql_query = text(f'SELECT * FROM locker WHERE id = {reserva[3]}')
                result = db.execute(sql_query)
                locker = result.fetchone()
                if locker is None:
                    return {"message": "Failed to confirm, locker does not exist"}
                else:
                    if locker[6] != code:
                        print(locker[6])
                        return {"message":"Clave incorrecta"}
                    sql_query = text(f"INSERT INTO states (locker_id, state) VALUES ({locker[0]}, 0)")
                    db.execute(sql_query)
                    db.commit()
                    sql_query = text(f"UPDATE locker SET state = 0 WHERE id = {locker[0]}")
                    db.execute(sql_query)
                    db.commit()
                    sql_query = text(f"UPDATE reservation SET estado = 'finalizada' WHERE id = {reservation}")
                    db.execute(sql_query)
                    db.commit()
                    create_record(db, reserva[0], reserva[1], reserva[3], reserva[5], datetime.now(), reserva[2], "Paquete retirado de locker")
                    print(locker[6])
                    #TODO aca debo hacer la llamada MQTT para abrir el cajon
                    if MQTT:
                        mqtt.publish("g1/unload", {"nickname":locker[1]}) #publishing mqtt topic

                        mqtt.publish("g1/verification", {"nickname":""}) #publishing mqtt topic

                   
                    sql_query = text(f"UPDATE locker SET code = NULL WHERE locker.id = {locker[0]}")
                    db.execute(sql_query)
                    db.commit()




                    return {"message": f"Se ha abierto el espacio {locker[1]}"}
        except Exception as E:
            return {"message": f"{E}"}
    except requests.exceptions.Timeout:
        return {"message": "Timeout error"}



@app.get("/Physical_verification",tags=["PHYSICAL"])
async def func():
    global locker_state
    return {"result": True,"message":locker_state }


@app.get("/")
async def name(request: Request, db: dp_dependecy):
    return templates.TemplateResponse("home.html", {"request": request})


@app.get('/estado_casilleros/')
async def estado_casilleros(request: Request, db: dp_dependecy):
    sql_query = text(f"SELECT * FROM locker")
    result = db.execute(sql_query)
    lockers = result.fetchall()
    dic = {}
    dic_aux = {}
    for cont, locker in enumerate(lockers):
        if cont == len(lockers)-1:
            dic_aux[locker[0]] = {"id": locker[0], "personal_id": locker[1], "state": get_state_by_state_number(locker[2]), "height": locker[3], "width": locker[4], "depth": locker[5], "station_id": locker[7], "code": locker[6]}
            dic[locker[7]] = dic_aux
            break
        if cont == 0:
            dic_aux[locker[0]] = {"id": locker[0], "personal_id": locker[1], "state": get_state_by_state_number(locker[2]), "height": locker[3], "width": locker[4], "depth": locker[5], "station_id": locker[7], "code": locker[6]}
            continue
        if locker[7] != lockers[cont+1][7]:
            dic_aux[locker[0]] = {"id": locker[0], "personal_id": locker[1], "state": get_state_by_state_number(locker[2]), "height": locker[3], "width": locker[4], "depth": locker[5], "station_id": locker[7], "code": locker[6]}
            dic[locker[7]] = dic_aux
            dic_aux = {}
        else:
            dic_aux[locker[0]] = {"id": locker[0], "personal_id": locker[1], "state": get_state_by_state_number(locker[2]), "height": locker[3], "width": locker[4], "depth": locker[5], "station_id": locker[7], "code": locker[6]}
 
    return templates.TemplateResponse("estado_casilleros.html", {"request": request, "saccs": dic})

@app.get('/bitacora/')
async def bitacora(request: Request, db: dp_dependecy, reservation_id: int = None):
    sql_query = text(f"SELECT * FROM historial WHERE reservation_id = {reservation_id}")
    result = db.execute(sql_query)
    acciones = result.fetchall()
    datos = []
    for i in acciones:
        sql_query = text(f'SELECT * FROM "user" where id = {i[1]}')
        result = db.execute(sql_query)
        usuario = result.fetchone()
        datos.append((i[0], usuario[1], i[2], i[3], i[4], i[5], i[6], i[7], usuario[3]))
    
    return templates.TemplateResponse("bitacora.html", {"request": request, "acciones": datos})

@app.get('/reservas/')
async def reservas(request: Request, db: dp_dependecy):
    sql_query = text(f"SELECT * FROM reservation")
    result = db.execute(sql_query)
    reservas = result.fetchall()
    return templates.TemplateResponse("reservas.html", {"request": request, "reservas": reservas})