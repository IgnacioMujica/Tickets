from cs50 import SQL
from flask import Flask, render_template, request, redirect, session
from flask_session import Session
from tempfile import mkdtemp
from datetime import datetime, date, timedelta
from air_functions import update, populate_session, price, addlbag_no

app = Flask(__name__)

db = SQL("sqlite:///airline.db")

app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

CITIES = ["Pato Mojado", "Arrollo Chico", "Tierra Roja"]



######################################## INDEX (GET) ######################################

@app.route("/3")
def index3():
    update()
    today_date = datetime.today().strftime('%Y-%m-%d')

    populate_session(session)

    return render_template("index.html",\
    datetime = str(datetime.now()),\
    cities = CITIES,\
    today_date = str(today_date),\
    trip_type = session["trip_type"],\
    inf_no = session["infants_no"],\
    pet_no = session["pets_no"],\
    pax_no = session["pax_no"],\
    orig = session["origin"],\
    dest = session["destination"],\
    leg1_date = session["go_date"],\
    leg2_date = session["back_date"],\
    leg1_flightno = session["leg_1_flightno"],\
    leg2_flightno = session["leg_2_flightno"],\
    )

######################################## RESULTS (POST GET) ######################################

@app.route("/results", methods=["GET", "POST"])

def results():

    populate_session(session)

    if request.method == "POST":
        session["intended_origin"] = (request.form.get("origin"))
        session["intended_destination"] = (request.form.get("destination"))
        session["trip_type"] = (request.form.get("trip_type"))
        session["leg1_intend_date"] = datetime.strptime((request.form.get("leg1_date")), "%Y-%m-%d").date()
        session["leg2_intend_date"] = datetime.strptime((request.form.get("leg2_date")), "%Y-%m-%d").date()

    leg1_date_fs = session["leg1_intend_date"] + timedelta(days=-6)
    leg1_date_fe = session["leg1_intend_date"] + timedelta(days=6)
    leg1_results =  db.execute("SELECT * FROM Itinerary WHERE (date BETWEEN (?) AND (?)) AND ((?) < (?)) AND orig = (?) AND dest = (?)", leg1_date_fs, leg1_date_fe, session["leg1_intend_date"], session["leg2_intend_date"], session["intended_origin"], session["intended_destination"])

    if session["trip_type"] == "round_trip":
        leg2_date_fs = session["leg2_intend_date"] + timedelta(days=-6)
        leg2_date_fe = session["leg2_intend_date"] + timedelta(days=6)
        leg2_results =  db.execute("SELECT * FROM Itinerary WHERE (date BETWEEN (?) AND (?)) AND ((?) > (?)) AND orig = (?) AND dest = (?)", leg2_date_fs, leg2_date_fe, session["leg2_intend_date"], session["leg1_intend_date"], session["intended_destination"], session["intended_origin"])
    else:
        leg2_results =  None

    return render_template("results.html",\
    trip_type = session["trip_type"],\
    inf_no = session["infants_no"],\
    pet_no = session["pets_no"],\
    pax_no = session["pax_no"],\
    leg1_results = leg1_results,\
    leg2_results = leg2_results,\
    orig = session["origin"],\
    dest = session["destination"],\
    intended_orig = session["intended_origin"],\
    intended_dest = session["intended_destination"],\
    leg1_date = session["go_date"],\
    leg2_date = session["back_date"],\
    leg1_flightno = session["leg_1_flightno"],\
    leg2_flightno = session["leg_2_flightno"],\
    )


######################################## BOOK PAX NO (POST GET) ######################################

@app.route("/book1", methods=["GET", "POST"])
def book1():

    populate_session(session)

    if request.method == "POST":
        session["leg_1_id"] = request.form["leg_1"]
        if session["trip_type"] == "round_trip":
            session["leg_2_id"] = request.form["leg_2"]
            session["origin"] = session["intended_origin"]
            session["destination"] = session["intended_destination"]

    leg_1 = db.execute("SELECT flightno, orig, dest, date FROM Itinerary WHERE ID = (?)", session["leg_1_id"])
    session["go_date"] = leg_1[0]["date"]
    session["leg_1_flightno"] = leg_1[0]["flightno"]

    if session["trip_type"] == "round_trip":
        leg_2 = db.execute("SELECT flightno, orig, dest, date FROM Itinerary WHERE ID = (?)", session["leg_2_id"])
        session["back_date"] = leg_2[0]["date"]
        session["leg_2_flightno"] = leg_2[0]["flightno"]
    else:
        session["back_date"] = None
        session["leg_2_flightno"] = None

    return render_template("book1.html",\
    trip_type = session["trip_type"],\
    inf_no = session["infants_no"],\
    pet_no = session["pets_no"],\
    pax_no = session["pax_no"],\
    leg1_flightno = session["leg_1_flightno"],\
    leg2_flightno = session["leg_2_flightno"],\
    orig = session["origin"],\
    dest = session["destination"],\
    leg1_date = session["go_date"],\
    leg2_date = session["back_date"],\
    leg1_id = session["leg_1_id"]
    )

######################################## BOOK PAX DETAILS (POST ONLY) ######################################

@app.route("/book_pax", methods=["POST"])
def book_pax():

    if request.method == "POST":
        session["pax_no"] = int(request.form.get("passenger_number"))
        session["infants_no"] = int(request.form.get("infants_number"))
        session["pets_no"] = int(request.form.get("pets_number"))
        if 'res_id' in session.keys():
            if session["trip_type"] == "round_trip":
                db.execute("UPDATE reservations SET L1_flight_id = (?), L2_flight_id = (?), pax_no = (?), infants_no = (?), pet_no = (?) WHERE res_id = (?)", session["leg_1_id"], session["leg_2_id"], session["pax_no"], session["infants_no"], session["pets_no"],session["res_id"])
            else:
                db.execute("UPDATE reservations SET L1_flight_id = (?), L2_flight_id = (?), pax_no = (?), infants_no = (?), pet_no = (?) WHERE res_id = (?)", session["leg_1_id"], None, session["pax_no"], session["infants_no"], session["pets_no"],session["res_id"])

        else:
            if session["trip_type"] == "round_trip":
                db.execute("INSERT INTO reservations (L1_flight_id, L2_flight_id, pax_no, infants_no, pet_no) VALUES(?, ?, ?, ?, ?)", session["leg_1_id"], session["leg_2_id"], session["pax_no"], session["infants_no"], session["pets_no"])
                session["res_id"] = (db.execute("SELECT res_id FROM reservations ORDER BY res_id DESC LIMIT 1")[0]["res_id"])
            else:
                db.execute("INSERT INTO reservations (L1_flight_id, L2_flight_id, pax_no, infants_no, pet_no) VALUES(?, ?, ?, ?, ?)", session["leg_1_id"], None, session["pax_no"], session["infants_no"], session["pets_no"])
                session["res_id"] = (db.execute("SELECT res_id FROM reservations ORDER BY res_id DESC LIMIT 1")[0]["res_id"])

        return render_template("book_pax.html",\
        inf_no = session["infants_no"],\
        pet_no = session["pets_no"],\
        pax_no = session["pax_no"],\
        trip_type = session["trip_type"],\
        leg1_flightno = session["leg_1_flightno"],\
        leg2_flightno = session["leg_2_flightno"],\
        orig = session["origin"],\
        dest = session["destination"],\
        leg1_date = session["go_date"],\
        leg2_date = session["back_date"]
        )

######################################## BOOK PET / KIDS DETAILS (POST ONLY) ######################################

@app.route("/book_petinf", methods=["POST"])
def book_petinf():

    if request.method == "POST":
        db.execute("DELETE FROM passengers WHERE res_no = (?)", session["res_id"])
        for pax in range(1, session["pax_no"]+1):
            pax_first_name = request.form.get("passenger_fname_" + str(pax))
            pax_last_name = request.form.get("passenger_lname_" + str(pax))
            pax_pass_no = request.form.get("passenger_pnumber_" + str(pax))
            bag_no = request.form.get("passenger_bag_no_" + str(pax))
            seat_class = request.form.get("seat_class_" + str(pax))
            wchr = request.form.get("spec_assist_" + str(pax))
            db.execute("INSERT INTO passengers (pax_first_name, pax_last_name, pass_no, bag_no, seat_class, wchr, res_no) VALUES(?, ?, ?, ?, ?, ?, ?)", pax_first_name, pax_last_name, pax_pass_no, bag_no, seat_class, wchr, session["res_id"])

    if (session["infants_no"] != 0 or session["pets_no"] != 0):
        return render_template("book_petinf.html",\
        inf_no = session["infants_no"],\
        pet_no = session["pets_no"],\
        pax_no = session["pax_no"],\
        trip_type = session["trip_type"],\
        leg1_flightno = session["leg_1_flightno"],\
        leg2_flightno = session["leg_2_flightno"],\
        orig = session["origin"],\
        dest = session["destination"],\
        leg1_date = session["go_date"],\
        leg2_date = session["back_date"]
        )

    else:
        return render_template("details.html",\
        inf_no = session["infants_no"],\
        pet_no = session["pets_no"],\
        pax_no = session["pax_no"],\
        trip_type = session["trip_type"],\
        orig = session["origin"],\
        dest = session["destination"],\
        leg1_date = session["go_date"],\
        leg2_date = session["back_date"],\
        leg1_flightno = session["leg_1_flightno"],\
        leg2_flightno = session["leg_2_flightno"],\
        petlist = [],\
        infantlist = [],\
        paxlist = db.execute("SELECT pax_first_name, pax_last_name, pass_no, bag_no, seat_class, wchr FROM passengers WHERE res_no = (?)", session["res_id"]),\
        )

######################################## DETAILS (POST, GET) ######################################

@app.route("/details", methods=["GET", "POST"])
def details():

    if request.method == "POST":
        db.execute("DELETE FROM dependants WHERE res_no = (?)", session["res_id"])
        if (session["infants_no"] > 0):
            for infant in range(1, session["infants_no"]+1):
                dep_first_name = request.form.get("infant_first_name_" + str(infant))
                dep_last_name = request.form.get("infant_last_name_" + str(infant))
                dep_pass_no = request.form.get("infant_pass_no_" + str(infant))
                if (dep_first_name == None or dep_last_name == None or dep_pass_no == None):
                    return ("Error. Incomplete infant form.")
                db.execute("INSERT INTO dependants (dep_first_name, dep_last_name, dep_pass_no, kind, res_no) VALUES(?, ?, ?, ?, ?)", dep_first_name, dep_last_name, dep_pass_no, "I", session["res_id"])

        if (session["pets_no"] > 0):
            for pet in range(1, session["pets_no"]+1):
                dep_first_name = request.form.get("pet_" + str(pet))
                kind = request.form.get("pet_species_" + str(pet))
                if (dep_first_name == None or kind == None):
                    return ("Error. Incomplete pet form.")
                db.execute("INSERT INTO dependants (dep_first_name, kind, res_no) VALUES(?, ?, ?)", dep_first_name, kind, session["res_id"])

    return render_template("details.html",\
    trip_type = session["trip_type"],\
    inf_no = session["infants_no"],\
    pet_no = session["pets_no"],\
    pax_no = session["pax_no"],\
    orig = session["origin"],\
    dest = session["destination"],\
    leg1_date = session["go_date"],\
    leg2_date = session["back_date"],\
    leg1_flightno = session["leg_1_flightno"],\
    leg2_flightno = session["leg_2_flightno"],\
    paxlist = db.execute("SELECT pax_first_name, pax_last_name, pass_no, bag_no, seat_class, wchr FROM passengers WHERE res_no = (?)", session["res_id"]),\
    infantlist = db.execute("SELECT dep_first_name, dep_last_name, dep_pass_no FROM dependants WHERE kind = (?) AND res_no = (?)", "I", session["res_id"]),\
    petlist = db.execute("SELECT dep_first_name, kind FROM dependants WHERE (kind = (?) OR kind = (?)) AND res_no = (?)", "D", "C", session["res_id"]),\
    )

######################################## CONFIRM (POST) ######################################

@app.route("/", methods=["GET"])
def index():
    session["res_id"] = 166
    reservation = db.execute("SELECT L1_flight_id, L2_flight_id, pax_no, pet_no, infants_no, res_id FROM reservations WHERE res_id = (?)", session["res_id"])
    leg1_itinerary = db.execute("SELECT flightno, orig, dest, date FROM Itinerary WHERE Id = (?)", reservation[0]["L1_flight_id"])
    leg2_itinerary = db.execute("SELECT flightno, orig, dest, date FROM Itinerary WHERE Id = (?)", reservation[0]["L2_flight_id"])

    if reservation[0]["L2_flight_id"] != None:
        trip_type = "round_trip"
        pax_unit_price = price(leg1_itinerary[0]["flightno"]) + price(leg2_itinerary[0]["flightno"])
    else:
        pax_unit_price = price(leg1_itinerary[0]["flightno"])

    return render_template("confirm.html",\
    orig = leg1_itinerary[0]["orig"],\
    dest = leg1_itinerary[0]["dest"],\
    leg1_date = leg1_itinerary[0]["date"],\
    leg2_date = leg2_itinerary[0]["date"],\
    leg1_flightno = leg1_itinerary[0]["flightno"],\
    leg2_flightno = leg2_itinerary[0]["flightno"],\
    trip_type = trip_type,\
    pax_no = reservation[0]["pax_no"],\
    pax_unit_price = pax_unit_price,\
    bus_no = (db.execute("SELECT COUNT(*) FROM passengers WHERE seat_class = (?) AND res_no = (?)", "Business", reservation[0]["res_id"]))[0]['COUNT(*)'],\
    pet_no = reservation[0]["pet_no"],\
    inf_no = reservation[0]["infants_no"],\
    addlbag_no = addlbag_no(reservation[0]["res_id"]),\
    )

