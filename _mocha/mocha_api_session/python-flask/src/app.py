from flask import Flask
from flask import Flask, request, jsonify, Response
from datetime import datetime
import uuid

import logging
import sys
logging.basicConfig(stream=sys.stdout, level=logging.INFO)
logger = logging.getLogger(__name__)

from sqlalchemy.ext.automap import automap_base
from sqlalchemy.orm import Session
from sqlalchemy import create_engine, select

Base = automap_base()

# engine, suppose it has two tables 'user' and 'address' set up
engine = create_engine("mysql+mysqlconnector://root:root@localhost:3306/CabServiceDb")

# reflect the tables
Base.prepare(autoload_with=engine)
session = Session(engine)

Users = Base.classes.Users
Trips = Base.classes.Trips
LocationLogs = Base.classes.LocationLogs
DriverProfiles = Base.classes.DriverProfiles

app = Flask(__name__)


@app.route("/api/login", methods=["GET"])
def login():
    data = request.get_json()
    if not data:
        return jsonify({"msg": "invalid input"}), 400
    try:
        with Session(engine) as session, session.begin():
            email = data.get('email')
            password = data.get('password')
            
            if email == "" or password == "":
              return jsonify({"msg": "invalid input"}), 400

            user = session.scalars(
                select(Users)
                .where(Users.Email == email)
                .where(Users.PasswordHash == password)
            ).first()
            

            if user is None:

              return jsonify({"msg": "invalid password"}), 401

                
            if user.IsSuspended == 1:
              return jsonify({"msg": "accuont suspended"}), 401

            result = {
              "userId": user.UserId, 
              "userTypeId": user.UserTypeId
            }

            return jsonify(result), 200

    except Exception as e:
        logger.error("Error creating project: %s", e)
        return jsonify({"msg": str(e)}), 500

@app.route("/api/signup", methods=["POST"])
def signup():
    data = request.get_json()
    email = data.get("email")
    password = data.get("password")
    try:
      with Session(engine) as session, session.begin():
        user_id = str(uuid.uuid4())
        if email == "" or password == "":
          return jsonify({"msg": "invalid input"}), 409
        user_exist = session.scalars(
            select(Users)
            .where(Users.Email == data.get("email"))
        ).first()

        if user_exist:
          return jsonify({"msg": "user exists"}), 409

        user = Users(UserId=user_id, FullName=data.get("full_name"), Email=data.get("email"), 
        PhoneNumber=data.get('phone_number'), PasswordHash=data.get("password"), UserTypeId=1)
        session.add(user)
        session.flush()
        result = {
            "userId": user_id,
            "userTypeId": user.UserTypeId
        }
        return jsonify(result), 201

    except Exception as e:
        logger.error("Error creating project: %s", e)
        return jsonify({"error": str(e)}), 500

@app.route("/api/trips/request", methods=["POST"])
def req_trip():
    data = request.get_json()
    try:
      with Session(engine) as session, session.begin():
        if (data.get("pickupLat") < -90 or data.get("pickupLat") > 90) or (data.get("dropoffLat") < -90 or data.get("dropoffLat") > 90) or (data.get("pickupLng") < -180 or data.get("pickupLng") > 180) or (data.get("dropoffLng") < -180 or data.get("dropoffLng") > 180):
          return jsonify({"msg": "invalid coordinates"}), 409
        
        is_driver_online = False
        driver = session.scalars(
            select(DriverProfiles)
            .where(DriverProfiles.ShiftStatus == "ONLINE")\
            .where(DriverProfiles.ApprovalStatus == "APPROVED")
            .where(DriverProfiles.DocumentsVerified == 1)
        ).first()



    except Exception as e:
        logger.error("Error creating project: %s", e)
        return jsonify({"error": str(e)}), 500

@app.route("/api/drivers/location", methods=["POST"])
def ping_loc():
    data = request.get_json()
    lat = data.get("lat")
    lng = data.get("lng")
    try:
      with Session(engine) as session, session.begin():
        trip = session.scalars(
          select(Trips)
          .where(Trips.DriverId == data.get("driverId"))
        ).first()

        if (lat < -90 and lat > 90) or (lng < -180 and lng > 180):
          return jsonify({"msg": "invalid coordinates"}), 400  
        
        driver = session.scalars(
            select(DriverProfiles)
            .where(DriverProfiles.DriverId == data.get("driverId"))
            .where(DriverProfiles.ShiftStatus == "ONLINE")\
            .where(DriverProfiles.ApprovalStatus == "APPROVED")
            .where(DriverProfiles.DocumentsVerified == 1)
        ).first()

        if not driver:
          return jsonify({"msg": "driver offline or banned"}), 403
        
        log_location = LocationLogs(
          DriverId=data.get("driverId"),
          TripId=trip.TripId,
          Latitude=data.get("lat"),
          Longitude=data.get("lng"),
          Bearing=data.get("bearing")
        )

        session.add(log_location)
        session.flush()
        return jsonify({"success": True}), 200

    except Exception as e:
        logger.error("Error creating project: %s", e)
        return jsonify({"error": str(e)}), 500

@app.route("/api/trips/<tripId>/accept", methods=["POST"])
def accept_trip(tripId):
  data = request.get_json()
  try:
    with Session(engine) as session, session.begin():
        trip = Trips(TripId=tripId)
        if trip:
          trip.DriverId = data.get("driverId")
          trip.Status = "ACCEPTED"
          result = {
              "tripId": tripId,
              "status": "ACCEPTED"
          }
          
          return jsonify({"msg": "trip accepted"}), 200

  except Exception as e:
      logger.error("Error creating project: %s", e)
      return jsonify({"error": str(e)}), 500

@app.route("/")
def hello():
  logger.info("hello endpoint hit")
  return "Hello, world!"

if __name__ == "__main__":
  app.run("0.0.0.0", 3000, debug=True)
