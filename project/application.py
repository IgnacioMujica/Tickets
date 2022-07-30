from cs50 import SQL
from flask import Flask, render_template, request, redirect, session
from flask_session import Session
from tempfile import mkdtemp
from datetime import datetime, date, timedelta
from air_functions import update, populate_session, price, addlbag_no, if_i_fits

app = Flask(__name__)

db = SQL("sqlite:///airline.db")

app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

CITIES = ["Pato Mojado", "Arrollo Chico", "Tierra Roja"]


######################################## INDEX (GET) ######################################

@app.route("/")
def index():
    update()
    today_date = datetime.today().strftime('%Y-%m-%d')

    # If new session, clear (old unconfirmed reservations)
    if "res_id" not in session:
        db.execute("DELETE FROM Reservations WHERE paid = (?)", "n")
    # Populate session with placeholders needed for rendering
    populate_session(session)
    return render_template("index.html",
                           datetime=str(datetime.now()),
                           cities=CITIES,
                           today_date=str(today_date),
                           trip_type=session["trip_type"],
                           inf_no=session["infants_no"],
                           pet_no=session["pets_no"],
                           pax_no=session["pax_no"],
                           orig=session["origin"],
                           dest=session["destination"],
                           leg1_date=session["go_date"],
                           leg2_date=session["back_date"],
                           leg1_flightno=session["leg_1_flightno"],
                           leg2_flightno=session["leg_2_flightno"],
                           navmenu=1
                           )

######################################## RESULTS (POST GET) ######################################


@app.route("/results", methods=["GET", "POST"])
def results():
    # Populate session with placeholders needed for rendering
    populate_session(session)

    if request.method == "POST":
        # Error checking for POST data
        if (request.form.get("origin") == request.form.get("destination")):
            return "Error. Origin and destination cities must be different from each other."

        session["intended_origin"] = (request.form.get("origin"))
        session["intended_destination"] = (request.form.get("destination"))
        session["trip_type"] = (request.form.get("trip_type"))

        if ((request.form.get("origin") not in CITIES) or ((request.form.get("destination")) not in CITIES)):
            return "Error. Muct select valid origin and destination."

        if not request.form.get("leg1_date"):
            return "Error. Missing departure date."

        if (datetime.strptime((request.form.get("leg1_date")), "%Y-%m-%d").date() < date.today()):
            return "Error. Selected dates date cannot be in the past"

        if (datetime.strptime((request.form.get("leg1_date")), "%Y-%m-%d").date()) > date.today() + timedelta(days=49):
            return "Error. Please select dates no more than 50 days from today."

        session["leg1_intend_date"] = datetime.strptime((request.form.get("leg1_date")), "%Y-%m-%d").date()
        session["leg2_intend_date"] = datetime.strptime("2050-01-01", "%Y-%m-%d").date()

        if (session["trip_type"] == "round_trip"):

            session["leg1_intend_date"] = datetime.strptime((request.form.get("leg1_date")), "%Y-%m-%d").date()
            if not request.form.get("leg2_date"):
                return "Error. Missing return date."
            if (datetime.strptime((request.form.get("leg1_date")), "%Y-%m-%d").date() < date.today() or datetime.strptime((request.form.get("leg2_date")), "%Y-%m-%d").date() < date.today()):
                return "Error. Selected dates cannot be in the past"
            if (datetime.strptime((request.form.get("leg2_date")), "%Y-%m-%d").date()) > date.today() + timedelta(days=49):
                return "Error. Please select dates no more than 50 days from today."
            session["leg2_intend_date"] = datetime.strptime((request.form.get("leg2_date")), "%Y-%m-%d").date()

    # Date ranges to display as results
    leg1_date_fs = session["leg1_intend_date"] + timedelta(days=-6)
    leg1_date_fe = session["leg1_intend_date"] + timedelta(days=6)
    leg1_results = db.execute("SELECT * FROM Itinerary WHERE (date BETWEEN (?) AND (?)) AND ((?) < (?)) AND orig = (?) AND dest = (?)", leg1_date_fs,
                              leg1_date_fe, session["leg1_intend_date"], session["leg2_intend_date"], session["intended_origin"], session["intended_destination"])

    # Obtain prices of each trip
    for result in leg1_results:
        result.update({'price': price(result["Id"], result["date"])})

    if session["trip_type"] == "round_trip":
        # Date ranges to display as results
        leg2_date_fs = session["leg2_intend_date"] + timedelta(days=-6)
        leg2_date_fe = session["leg2_intend_date"] + timedelta(days=6)
        leg2_results = db.execute("SELECT * FROM Itinerary WHERE (date BETWEEN (?) AND (?)) AND ((?) > (?)) AND orig = (?) AND dest = (?)", leg2_date_fs,
                                  leg2_date_fe, session["leg2_intend_date"], session["leg1_intend_date"], session["intended_destination"], session["intended_origin"])
        # Obtain prices of each trip
        for result in leg2_results:
            result.update({'price': price(result["Id"], result["date"])})
    else:
        leg2_results = None

    return render_template("results.html",
                           trip_type=session["trip_type"],
                           inf_no=session["infants_no"],
                           pet_no=session["pets_no"],
                           pax_no=session["pax_no"],
                           leg1_results=leg1_results,
                           leg2_results=leg2_results,
                           orig=session["origin"],
                           dest=session["destination"],
                           intended_orig=session["intended_origin"],
                           intended_dest=session["intended_destination"],
                           leg1_date=session["go_date"],
                           leg2_date=session["back_date"],
                           leg1_flightno=session["leg_1_flightno"],
                           leg2_flightno=session["leg_2_flightno"],
                           navmenu=1
                           )


######################################## BOOK PAX NO (POST GET) ######################################

@app.route("/book1", methods=["GET", "POST"])
def book1():

    # Populate session with placeholders needed for rendering
    populate_session(session)

    if request.method == "POST":
        session["leg_1_id"] = request.form["leg_1"]

        session["origin"] = session["intended_origin"]
        session["destination"] = session["intended_destination"]
        if session["trip_type"] == "round_trip":
            session["leg_2_id"] = request.form["leg_2"]
        # Error checking
        if session["trip_type"] == "round_trip":
            if int(session["leg_1_id"]) > (int(session["leg_2_id"]) - 1):
                return "Error: Return date cannot be before departure date."

    # Select legs 1 and 2 to display information
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

    return render_template("book1.html",
                           trip_type=session["trip_type"],
                           inf_no=session["infants_no"],
                           pet_no=session["pets_no"],
                           pax_no=session["pax_no"],
                           leg1_flightno=session["leg_1_flightno"],
                           leg2_flightno=session["leg_2_flightno"],
                           orig=session["origin"],
                           dest=session["destination"],
                           leg1_date=session["go_date"],
                           leg2_date=session["back_date"],
                           leg1_id=session["leg_1_id"],
                           navmenu=1
                           )

######################################## BOOK PAX DETAILS (POST ONLY) ######################################


@app.route("/book_pax", methods=["POST"])
def book_pax():

    if request.method == "POST":
        # Obtain numbers from forms
        session["pax_no"] = int(request.form.get("passenger_number"))
        session["infants_no"] = int(request.form.get("infants_number"))
        session["pets_no"] = int(request.form.get("pets_number"))

        # Update reservations with previously chosen flights and traveller numbers
        if 'res_id' in session.keys():
            if session["trip_type"] == "round_trip":
                db.execute("UPDATE reservations SET L1_flight_id = (?), L2_flight_id = (?), pax_no = (?), infants_no = (?), pet_no = (?) WHERE res_id = (?)",
                           session["leg_1_id"], session["leg_2_id"], session["pax_no"], session["infants_no"], session["pets_no"], session["res_id"])
            else:
                db.execute("UPDATE reservations SET L1_flight_id = (?), L2_flight_id = (?), pax_no = (?), infants_no = (?), pet_no = (?) WHERE res_id = (?)",
                           session["leg_1_id"], None, session["pax_no"], session["infants_no"], session["pets_no"], session["res_id"])

        else:
            if session["trip_type"] == "round_trip":
                db.execute("INSERT INTO reservations (L1_flight_id, L2_flight_id, pax_no, infants_no, pet_no) VALUES(?, ?, ?, ?, ?)",
                           session["leg_1_id"], session["leg_2_id"], session["pax_no"], session["infants_no"], session["pets_no"])
                session["res_id"] = (db.execute("SELECT res_id FROM reservations ORDER BY res_id DESC LIMIT 1")[0]["res_id"])
            else:
                db.execute("INSERT INTO reservations (L1_flight_id, L2_flight_id, pax_no, infants_no, pet_no) VALUES(?, ?, ?, ?, ?)",
                           session["leg_1_id"], None, session["pax_no"], session["infants_no"], session["pets_no"])
                session["res_id"] = (db.execute("SELECT res_id FROM reservations ORDER BY res_id DESC LIMIT 1")[0]["res_id"])

        return render_template("book_pax.html",
                               inf_no=session["infants_no"],
                               pet_no=session["pets_no"],
                               pax_no=session["pax_no"],
                               trip_type=session["trip_type"],
                               leg1_flightno=session["leg_1_flightno"],
                               leg2_flightno=session["leg_2_flightno"],
                               orig=session["origin"],
                               dest=session["destination"],
                               leg1_date=session["go_date"],
                               leg2_date=session["back_date"],
                               navmenu=1
                               )

######################################## BOOK PET / KIDS DETAILS (POST ONLY) ######################################


@app.route("/book_petinf", methods=["POST"])
def book_petinf():

    if request.method == "POST":
        # Delete old passengers for this reservation
        db.execute("DELETE FROM passengers WHERE res_no = (?)", session["res_id"])
        for pax in range(1, session["pax_no"]+1):
            if not request.form.get("passenger_fname_" + str(pax)):
                return("Error. Missing passenger first name.")
            pax_first_name = request.form.get("passenger_fname_" + str(pax))
            if not request.form.get("passenger_lname_" + str(pax)):
                return("Error. Missing passenger last name.")
            pax_last_name = request.form.get("passenger_lname_" + str(pax))
            if not request.form.get("passenger_pnumber_" + str(pax)):
                return("Error. Missing passenger passport No.")
            pax_pass_no = request.form.get("passenger_pnumber_" + str(pax))

            bag_no = request.form.get("passenger_bag_no_" + str(pax))
            seat_class = request.form.get("seat_class_" + str(pax))
            wchr = request.form.get("spec_assist_" + str(pax))

            res_pas_nums = db.execute("SELECT pass_no FROM passengers WHERE res_no = (?)", session["res_id"])
            for pas in range(0, len(res_pas_nums)):
                if res_pas_nums[pas]["pass_no"] == request.form.get("passenger_pnumber_" + str(pax)):
                    db.execute("DELETE FROM passengers WHERE res_no = (?)", session["res_id"])
                    return "Error. Passport numbers must be different for all passengers."

            db.execute("INSERT INTO passengers (pax_first_name, pax_last_name, pass_no, bag_no, seat_class, wchr, res_no) VALUES(?, ?, ?, ?, ?, ?, ?)",
                       pax_first_name, pax_last_name, pax_pass_no, bag_no, seat_class, wchr, session["res_id"])

    # If infants or pets chosen, render corresponding template
    if (session["infants_no"] != 0 or session["pets_no"] != 0):
        return render_template("book_petinf.html",
                               inf_no=session["infants_no"],
                               pet_no=session["pets_no"],
                               pax_no=session["pax_no"],
                               trip_type=session["trip_type"],
                               leg1_flightno=session["leg_1_flightno"],
                               leg2_flightno=session["leg_2_flightno"],
                               orig=session["origin"],
                               dest=session["destination"],
                               leg1_date=session["go_date"],
                               leg2_date=session["back_date"],
                               navmenu=1
                               )

    # If infants or pets not chosen, skip to reservation details
    else:
        return render_template("details.html",
                               inf_no=session["infants_no"],
                               pet_no=session["pets_no"],
                               pax_no=session["pax_no"],
                               trip_type=session["trip_type"],
                               orig=session["origin"],
                               dest=session["destination"],
                               leg1_date=session["go_date"],
                               leg2_date=session["back_date"],
                               leg1_flightno=session["leg_1_flightno"],
                               leg2_flightno=session["leg_2_flightno"],
                               petlist=[],
                               infantlist=[],
                               paxlist=db.execute(
                                   "SELECT pax_first_name, pax_last_name, pass_no, bag_no, seat_class, wchr FROM passengers WHERE res_no = (?)", session["res_id"]),
                               navmenu=1
                               )

######################################## DETAILS (POST, GET) ######################################


@app.route("/details", methods=["GET", "POST"])
def details():

    if request.method == "POST":
        # Delete old dependant info
        db.execute("DELETE FROM dependants WHERE res_no = (?)", session["res_id"])
        # Gather new dependant info
        if (session["infants_no"] > 0):
            for infant in range(1, session["infants_no"]+1):
                dep_first_name = request.form.get("infant_first_name_" + str(infant))
                dep_last_name = request.form.get("infant_last_name_" + str(infant))
                dep_pass_no = request.form.get("infant_pass_no_" + str(infant))
                if (dep_first_name == None or dep_last_name == None or dep_pass_no == None):
                    return ("Error. Incomplete infant form.")
                db.execute("INSERT INTO dependants (dep_first_name, dep_last_name, dep_pass_no, kind, res_no) VALUES(?, ?, ?, ?, ?)",
                           dep_first_name, dep_last_name, dep_pass_no, "I", session["res_id"])
        # Gather new dependant info
        if (session["pets_no"] > 0):
            for pet in range(1, session["pets_no"]+1):
                dep_first_name = request.form.get("pet_" + str(pet))
                kind = request.form.get("pet_species_" + str(pet))
                if (dep_first_name == None or kind == None):
                    return ("Error. Incomplete pet form.")
                db.execute("INSERT INTO dependants (dep_first_name, kind, res_no) VALUES(?, ?, ?)",
                           dep_first_name, kind, session["res_id"])
    # Render details for current booking
    return render_template("details.html",
                           trip_type=session["trip_type"],
                           inf_no=session["infants_no"],
                           pet_no=session["pets_no"],
                           pax_no=session["pax_no"],
                           orig=session["origin"],
                           dest=session["destination"],
                           leg1_date=session["go_date"],
                           leg2_date=session["back_date"],
                           leg1_flightno=session["leg_1_flightno"],
                           leg2_flightno=session["leg_2_flightno"],
                           paxlist=db.execute(
                               "SELECT pax_first_name, pax_last_name, pass_no, bag_no, seat_class, wchr FROM passengers WHERE res_no = (?)", session["res_id"]),
                           infantlist=db.execute(
                               "SELECT dep_first_name, dep_last_name, dep_pass_no FROM dependants WHERE kind = (?) AND res_no = (?)", "I", session["res_id"]),
                           petlist=db.execute(
                               "SELECT dep_first_name, kind FROM dependants WHERE (kind = (?) OR kind = (?)) AND res_no = (?)", "D", "C", session["res_id"]),
                           navmenu=0
                           )

######################################## CONFIRM (POST) ######################################


@app.route("/confirm", methods=["POST"])
def confirm():

    reservation = db.execute(
        "SELECT L1_flight_id, L2_flight_id, pax_no, pet_no, infants_no, res_id FROM reservations WHERE res_id = (?)", session["res_id"])

    # Calculate prices
    trip_type = "one_way"
    leg1_itinerary = db.execute("SELECT flightno, orig, dest, date FROM Itinerary WHERE Id = (?)", reservation[0]["L1_flight_id"])
    pax_unit_price = price(reservation[0]["L1_flight_id"], leg1_itinerary[0]["date"])

    leg2_itinerary = [{'flightno': None, 'date': None}]

    if reservation[0]["L2_flight_id"] != None:
        trip_type = "round_trip"
        leg2_itinerary = db.execute("SELECT flightno, orig, dest, date FROM Itinerary WHERE Id = (?)",
                                    reservation[0]["L2_flight_id"])
        pax_unit_price = price(reservation[0]["L1_flight_id"], leg1_itinerary[0]["date"]) + price(reservation[0]["L2_flight_id"], leg2_itinerary[0]["date"])

    # Render template with prices and booking
    return render_template("confirm.html",
                           orig=leg1_itinerary[0]["orig"],
                           dest=leg1_itinerary[0]["dest"],
                           leg1_date=leg1_itinerary[0]["date"],
                           leg2_date=leg2_itinerary[0]["date"],
                           leg1_flightno=leg1_itinerary[0]["flightno"],
                           leg2_flightno=leg2_itinerary[0]["flightno"],
                           trip_type=trip_type,
                           pax_no=reservation[0]["pax_no"],
                           pax_unit_price=pax_unit_price,
                           bus_no=db.execute("SELECT COUNT(*) FROM passengers WHERE seat_class = (?) AND res_no = (?)",
                                             "Business", reservation[0]["res_id"])[0]['COUNT(*)'],
                           pet_no=reservation[0]["pet_no"],
                           inf_no=reservation[0]["infants_no"],
                           addlbag_no=addlbag_no(reservation[0]["res_id"]),
                           navmenu=0
                           )

######################################## VIEW RESERVATION (POST) ######################################


@app.route("/reservation", methods=["POST"])
def reservation():

    if request.form.get("resno"):
        session["res_id"] = request.form.get("resno")

    # Get booking count values for reservation
    reservation = db.execute(
        "SELECT L1_flight_id, L2_flight_id, pax_no, pet_no, infants_no, res_id, l1_checked, l2_checked FROM reservations WHERE res_id = (?)", session["res_id"])
    res_bep = {'B': db.execute("SELECT COUNT(*) FROM passengers WHERE seat_class = (?) AND res_no = (?)", "Business", reservation[0]["res_id"])[0]['COUNT(*)'], 'E': reservation[0]["pax_no"] - (
        db.execute("SELECT COUNT(*) FROM passengers WHERE seat_class = (?) AND res_no = (?)", "Business", reservation[0]["res_id"]))[0]['COUNT(*)'], 'P': reservation[0]["pet_no"]}
    # Declare plane capacity
    bep_cap = {'B': 16, 'E': 138, 'P': 5}

    # Get booking count values for flight leg 1
    l1_bep = (db.execute("SELECT B, E, P FROM itinerary WHERE Id = (?)", reservation[0]["L1_flight_id"]))[0]
    for bep in res_bep:
        if res_bep[bep] + l1_bep[bep] > bep_cap[bep]:
            return "Not enough l1 cap"
    # Get booking count values for flight leg 2 (If leg 2 exists)
    if reservation[0]["L2_flight_id"] != None:
        l2_bep = (db.execute("SELECT B, E, P FROM itinerary WHERE Id = (?)", reservation[0]["L2_flight_id"]))[0]
        for bep in res_bep:
            if res_bep[bep] + l2_bep[bep] > bep_cap[bep]:
                return "Not enough l2 cap"

    trip_type = "one_way"
    leg1_itinerary = db.execute("SELECT flightno, orig, dest, date FROM Itinerary WHERE Id = (?)", reservation[0]["L1_flight_id"])
    pax_unit_price = price(reservation[0]["L1_flight_id"], leg1_itinerary[0]["date"])

    leg2_itinerary = [{'flightno': None, 'date': "2050-01-01"}]

    if reservation[0]["L2_flight_id"] != None:
        trip_type = "round_trip"
        leg2_itinerary = db.execute("SELECT flightno, orig, dest, date FROM Itinerary WHERE Id = (?)",
                                    reservation[0]["L2_flight_id"])
        pax_unit_price = price(reservation[0]["L1_flight_id"], leg1_itinerary[0]["date"]) + price(reservation[0]["L2_flight_id"], leg2_itinerary[0]["date"])

    # Update leg 1
    db.execute("UPDATE itinerary SET B = (?), E = (?), P = (?) WHERE Id = (?)",
               res_bep["B"] + l1_bep["B"], res_bep["E"] + l1_bep["E"], res_bep["P"] + l1_bep["P"], reservation[0]["L1_flight_id"])
    # Update leg 2 (If leg 2 exists)
    if reservation[0]["L2_flight_id"] != None:
        db.execute("UPDATE itinerary SET B = (?), E = (?), P = (?) WHERE Id = (?)",
                   res_bep["B"] + l2_bep["B"], res_bep["E"] + l2_bep["E"], res_bep["P"] + l2_bep["P"], reservation[0]["L2_flight_id"])

    db.execute("UPDATE Reservations SET paid = (?) WHERE res_id = (?)", "y", reservation[0]["res_id"])

    return render_template("reservation.html",
                           paxlist=db.execute(
                               "SELECT pax_first_name, pax_last_name, pass_no, bag_no, seat_class, wchr FROM passengers WHERE res_no = (?)", reservation[0]["res_id"]),
                           infantlist=db.execute(
                               "SELECT dep_first_name, dep_last_name, dep_pass_no FROM dependants WHERE kind = (?) AND res_no = (?)", "I", reservation[0]["res_id"]),
                           petlist=db.execute(
                               "SELECT dep_first_name, kind FROM dependants WHERE (kind = (?) OR kind = (?)) AND res_no = (?)", "D", "C", reservation[0]["res_id"]),
                           orig=leg1_itinerary[0]["orig"],
                           dest=leg1_itinerary[0]["dest"],
                           leg1_date=leg1_itinerary[0]["date"],
                           leg2_date=leg2_itinerary[0]["date"],
                           days_to_leg1=(datetime.strptime((leg1_itinerary[0]["date"]), "%Y-%m-%d").date() - date.today()).days,
                           days_to_leg2=(datetime.strptime((leg2_itinerary[0]["date"]), "%Y-%m-%d").date() - date.today()).days,
                           leg1_flightno=leg1_itinerary[0]["flightno"],
                           leg2_flightno=leg2_itinerary[0]["flightno"],
                           trip_type=trip_type,
                           pax_no=reservation[0]["pax_no"],
                           pax_unit_price=pax_unit_price,
                           bus_no=db.execute("SELECT COUNT(*) FROM passengers WHERE seat_class = (?) AND res_no = (?)",
                                             "Business", reservation[0]["res_id"])[0]['COUNT(*)'],
                           pet_no=reservation[0]["pet_no"],
                           inf_no=reservation[0]["infants_no"],
                           addlbag_no=addlbag_no(reservation[0]["res_id"]),
                           navmenu=0,
                           l1_checked=reservation[0]["l1_checked"],
                           l2_checked=reservation[0]["l2_checked"]
                           )

######################################## GET SEAT (POST) ######################################


@app.route("/check_in_l1", methods=["POST"])
def check_in_l1():

    # GET RESERVATION DETAILS (RES NO, FLIGHT 1 AND 2)
    reservation = db.execute(
        "SELECT L1_flight_id, L2_flight_id, pax_no, pet_no, infants_no, res_id, l1_checked, l2_checked FROM reservations WHERE res_id = (?)", session["res_id"])

    trip_type = "one_way"
    leg1_itinerary = db.execute("SELECT flightno, orig, dest, date FROM Itinerary WHERE Id = (?)", reservation[0]["L1_flight_id"])
    pax_unit_price = price(reservation[0]["L1_flight_id"], leg1_itinerary[0]["date"])

    leg2_itinerary = [{'flightno': None, 'date': "2050-01-01"}]

    if reservation[0]["L2_flight_id"] != None:
        trip_type = "round_trip"
        leg2_itinerary = db.execute("SELECT flightno, orig, dest, date FROM Itinerary WHERE Id = (?)",
                                    reservation[0]["L2_flight_id"])
        pax_unit_price = price(reservation[0]["L1_flight_id"], leg1_itinerary[0]["date"]) + price(reservation[0]["L2_flight_id"], leg2_itinerary[0]["date"])

    # CREATE L1 SEAT MAP IF IT DOESNT EXIST
    db.execute("CREATE TABLE IF NOT EXISTS " + "SEAT_MAP_" +
               str(reservation[0]["L1_flight_id"]) + " (row INT AUTO_INCREMENT, A VARCHAR(50) DEFAULT null, B VARCHAR(50) DEFAULT null, C VARCHAR(50) DEFAULT null, D VARCHAR(50) DEFAULT null, E VARCHAR(50) DEFAULT null, F VARCHAR(50) DEFAULT null)")
    # SELECT L1 SEAT MAP
    seatmap = (db.execute("SELECT * FROM " + "SEAT_MAP_" + str(reservation[0]["L1_flight_id"])))
    # IF NEW, POPULATE
    if len(seatmap) == 0:
        for i in range(1, 24):
            db.execute("INSERT INTO " + "SEAT_MAP_" + str(reservation[0]["L1_flight_id"])
                       + " (row, A, B, C, D, E, F) VALUES ((?), null, null, null, null, null, null)", i)
    # SELECT L1 SEAT MAP
    seatmap = (db.execute("SELECT * FROM " + "SEAT_MAP_" + str(reservation[0]["L1_flight_id"])))
    # GET USER SUBMITTED SEAT
    selected_seat = request.form.get("seat_selector")
    if selected_seat:
        pax_list = db.execute(
            "SELECT pax_first_name, pax_last_name, pass_no, l1_seat FROM passengers WHERE res_no = (?)", reservation[0]["res_id"])
        db.execute("UPDATE passengers SET l1_seat = (?) WHERE pass_no = (?) and res_no = (?)",
                   selected_seat, session["pass_no"], reservation[0]["res_id"])
        seat_row = selected_seat[1:]
        db.execute("UPDATE " + "SEAT_MAP_" + str(reservation[0]["L1_flight_id"]) + " SET (?) = (?) WHERE row = (?)",
                   selected_seat[0], str(reservation[0]["res_id"]) + "_" + session["pass_no"], int(seat_row))
        seatmap = (db.execute("SELECT * FROM " + "SEAT_MAP_" + str(reservation[0]["L1_flight_id"])))

    pax_list = db.execute(
        "SELECT pax_first_name, pax_last_name, pass_no, seat_class, l1_seat FROM passengers WHERE res_no = (?)", reservation[0]["res_id"])
    for i in range(len(pax_list)):
        if (pax_list[i]["l1_seat"]) == None:
            pax = pax_list[i]
            session["pass_no"] = pax_list[i]["pass_no"]
            return render_template("check_in_l1.html",
                                   seatmap=seatmap,
                                   pax=pax,
                                   all_seated=0,
                                   i=i,
                                   pax_list=pax_list,
                                   navmenu=0
                                   )

    db.execute("UPDATE Reservations SET l1_checked = (?) WHERE res_id = (?)", "y", reservation[0]["res_id"])
    reservation = db.execute(
        "SELECT L1_flight_id, L2_flight_id, pax_no, pet_no, infants_no, res_id, l1_checked, l2_checked FROM reservations WHERE res_id = (?)", session["res_id"])

    return render_template("reservation.html",
                           paxlist=db.execute(
                               "SELECT pax_first_name, pax_last_name, pass_no, bag_no, seat_class, wchr FROM passengers WHERE res_no = (?)", reservation[0]["res_id"]),
                           infantlist=db.execute(
                               "SELECT dep_first_name, dep_last_name, dep_pass_no FROM dependants WHERE kind = (?) AND res_no = (?)", "I", reservation[0]["res_id"]),
                           petlist=db.execute(
                               "SELECT dep_first_name, kind FROM dependants WHERE (kind = (?) OR kind = (?)) AND res_no = (?)", "D", "C", reservation[0]["res_id"]),
                           orig=leg1_itinerary[0]["orig"],
                           dest=leg1_itinerary[0]["dest"],
                           leg1_date=leg1_itinerary[0]["date"],
                           leg2_date=leg2_itinerary[0]["date"],
                           days_to_leg1=(datetime.strptime((leg1_itinerary[0]["date"]), "%Y-%m-%d").date() - date.today()).days,
                           days_to_leg2=(datetime.strptime((leg2_itinerary[0]["date"]), "%Y-%m-%d").date() - date.today()).days,
                           leg1_flightno=leg1_itinerary[0]["flightno"],
                           leg2_flightno=leg2_itinerary[0]["flightno"],
                           trip_type=trip_type,
                           pax_no=reservation[0]["pax_no"],
                           pax_unit_price=pax_unit_price,
                           bus_no=db.execute("SELECT COUNT(*) FROM passengers WHERE seat_class = (?) AND res_no = (?)",
                                             "Business", reservation[0]["res_id"])[0]['COUNT(*)'],
                           pet_no=reservation[0]["pet_no"],
                           inf_no=reservation[0]["infants_no"],
                           addlbag_no=addlbag_no(reservation[0]["res_id"]),
                           navmenu=0,
                           l1_checked=reservation[0]["l1_checked"],
                           l2_checked=reservation[0]["l2_checked"]
                           )


######################################## PRINT BOARDING PASS (POST) ######################################

@app.route("/check_in_l2", methods=["POST"])
def check_in_l2():

    # GET RESERVATION DETAILS (RES NO, FLIGHT 2)
    reservation = db.execute(
        "SELECT L1_flight_id, L2_flight_id, pax_no, pet_no, infants_no, res_id, l1_checked, l2_checked FROM reservations WHERE res_id = (?)", session["res_id"])

    trip_type = "one_way"
    leg1_itinerary = db.execute("SELECT flightno, orig, dest, date FROM Itinerary WHERE Id = (?)",
                                reservation[0]["L1_flight_id"])
    pax_unit_price = price(reservation[0]["L1_flight_id"], leg1_itinerary[0]["date"])

    leg2_itinerary = [{'flightno': None, 'date': "2050-01-01"}]

    if reservation[0]["L2_flight_id"] != None:
        trip_type = "round_trip"
        leg2_itinerary = db.execute("SELECT flightno, orig, dest, date FROM Itinerary WHERE Id = (?)",
                                    reservation[0]["L2_flight_id"])
        pax_unit_price = price(reservation[0]["L1_flight_id"], leg1_itinerary[0]["date"]) + price(reservation[0]["L2_flight_id"], leg2_itinerary[0]["date"])

    # CREATE L1 SEAT MAP IF IT DOESNT EXIST
    db.execute("CREATE TABLE IF NOT EXISTS " + "SEAT_MAP_" +
               str(reservation[0]["L2_flight_id"]) + " (row INT AUTO_INCREMENT, A VARCHAR(50) DEFAULT null, B VARCHAR(50) DEFAULT null, C VARCHAR(50) DEFAULT null, D VARCHAR(50) DEFAULT null, E VARCHAR(50) DEFAULT null, F VARCHAR(50) DEFAULT null)")
    # SELECT L1 SEAT MAP
    seatmap = (db.execute("SELECT * FROM " + "SEAT_MAP_" + str(reservation[0]["L2_flight_id"])))
    # IF NEW, POPULATE
    if len(seatmap) == 0:
        for i in range(1, 24):
            db.execute("INSERT INTO " + "SEAT_MAP_" + str(reservation[0]["L2_flight_id"]) +
                       " (row, A, B, C, D, E, F) VALUES ((?), null, null, null, null, null, null)", i)
    # SELECT L1 SEAT MAP
    seatmap = (db.execute("SELECT * FROM " + "SEAT_MAP_" + str(reservation[0]["L2_flight_id"])))
    # GET USER SUBMITTED SEAT
    selected_seat = request.form.get("seat_selector")
    if selected_seat:
        pax_list = db.execute(
            "SELECT pax_first_name, pax_last_name, pass_no, l2_seat FROM passengers WHERE res_no = (?)", reservation[0]["res_id"])
        db.execute("UPDATE passengers SET l2_seat = (?) WHERE pass_no = (?) and res_no = (?)",
                   selected_seat, session["pass_no"], reservation[0]["res_id"])
        seat_row = selected_seat[1:]
        db.execute("UPDATE " + "SEAT_MAP_" + str(reservation[0]["L2_flight_id"]) + " SET (?) = (?) WHERE row = (?)",
                   selected_seat[0], str(reservation[0]["res_id"]) + "_" + session["pass_no"], int(seat_row))
        seatmap = (db.execute("SELECT * FROM " + "SEAT_MAP_" + str(reservation[0]["L2_flight_id"])))

    pax_list = db.execute(
        "SELECT pax_first_name, pax_last_name, pass_no, seat_class, l2_seat FROM passengers WHERE res_no = (?)", reservation[0]["res_id"])
    for i in range(len(pax_list)):
        if (pax_list[i]["l2_seat"]) == None:
            pax = pax_list[i]
            session["pass_no"] = pax_list[i]["pass_no"]
            return render_template("check_in_l2.html",
                                   seatmap=seatmap,
                                   pax=pax,
                                   all_seated=0,
                                   i=i,
                                   pax_list=pax_list,
                                   navmenu=0
                                   )

    db.execute("UPDATE Reservations SET l2_checked = (?) WHERE res_id = (?)", "y", reservation[0]["res_id"])
    reservation = db.execute(
        "SELECT L1_flight_id, L2_flight_id, pax_no, pet_no, infants_no, res_id, l1_checked, l2_checked FROM reservations WHERE res_id = (?)", session["res_id"])

    return render_template("reservation.html",
                           paxlist=db.execute(
                               "SELECT pax_first_name, pax_last_name, pass_no, bag_no, seat_class, wchr FROM passengers WHERE res_no = (?)", reservation[0]["res_id"]),
                           infantlist=db.execute(
                               "SELECT dep_first_name, dep_last_name, dep_pass_no FROM dependants WHERE kind = (?) AND res_no = (?)", "I", reservation[0]["res_id"]),
                           petlist=db.execute(
                               "SELECT dep_first_name, kind FROM dependants WHERE (kind = (?) OR kind = (?)) AND res_no = (?)", "D", "C", reservation[0]["res_id"]),
                           orig=leg1_itinerary[0]["orig"],
                           dest=leg1_itinerary[0]["dest"],
                           leg1_date=leg1_itinerary[0]["date"],
                           leg2_date=leg2_itinerary[0]["date"],
                           days_to_leg1=(datetime.strptime((leg1_itinerary[0]["date"]), "%Y-%m-%d").date() - date.today()).days,
                           days_to_leg2=(datetime.strptime((leg2_itinerary[0]["date"]), "%Y-%m-%d").date() - date.today()).days,
                           leg1_flightno=leg1_itinerary[0]["flightno"],
                           leg2_flightno=leg2_itinerary[0]["flightno"],
                           trip_type=trip_type,
                           pax_no=reservation[0]["pax_no"],
                           pax_unit_price=pax_unit_price,
                           bus_no=db.execute("SELECT COUNT(*) FROM passengers WHERE seat_class = (?) AND res_no = (?)",
                                             "Business", reservation[0]["res_id"])[0]['COUNT(*)'],
                           pet_no=reservation[0]["pet_no"],
                           inf_no=reservation[0]["infants_no"],
                           addlbag_no=addlbag_no(reservation[0]["res_id"]),
                           navmenu=0,
                           l1_checked=reservation[0]["l1_checked"],
                           l2_checked=reservation[0]["l2_checked"]
                           )


@app.route("/exit", methods=["POST"])
def exit():
    # Clear session data
    session.clear()
    return "Bye"


@app.route("/boarding_pass_l1", methods=["POST"])
def boarding_pass_l1():
    # Render boarding ticket
    reservation = db.execute(
        "SELECT L1_flight_id, L2_flight_id, pax_no, pet_no, infants_no, res_id, l1_checked, l2_checked FROM reservations WHERE res_id = (?)", session["res_id"])
    return render_template("boarding_pass_l1.html",
                           paxlist=db.execute(
                               "SELECT pax_first_name, pax_last_name, pass_no, bag_no, seat_class, l1_seat, wchr FROM passengers WHERE res_no = (?)", reservation[0]["res_id"]),
                           leg1_itinerary=db.execute(
                               "SELECT flightno, orig, dest, date FROM Itinerary WHERE Id = (?)", reservation[0]["L1_flight_id"])[0]
                           )


@app.route("/boarding_pass_l2", methods=["POST"])
def boarding_pass_l2():
    # Render boarding ticket
    reservation = db.execute(
        "SELECT L1_flight_id, L2_flight_id, pax_no, pet_no, infants_no, res_id, l1_checked, l2_checked FROM reservations WHERE res_id = (?)", session["res_id"])
    return render_template("boarding_pass_l1.html",
                           paxlist=db.execute(
                               "SELECT pax_first_name, pax_last_name, pass_no, bag_no, seat_class, l2_seat, wchr FROM passengers WHERE res_no = (?)", reservation[0]["res_id"]),
                           leg1_itinerary=db.execute(
                               "SELECT flightno, orig, dest, date FROM Itinerary WHERE Id = (?)", reservation[0]["L1_flight_id"])[0]
                           )
