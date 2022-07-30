from cs50 import SQL
from datetime import datetime, date, timedelta

db = SQL("sqlite:///airline.db")



weekly_sched = {0: ["111", "112", "311"], # Mon
                1: ["312", "411"], # Tue
                2: ["211", "212"], # Wed
                3: ["111", "112", "311"], # Thu
                4: ["312", "412"], # Fri
                5: ["211", "212"], # Sat
                6: []} # Sun

flight_routes = {"111": ['Pato Mojado', 'Arrollo Chico', 300],
                 "112": ['Arrollo Chico', 'Pato Mojado', 300],
                 "211": ['Arrollo Chico', 'Tierra Roja', 200],
                 "212": ['Tierra Roja', 'Arrollo Chico', 200],
                 "311": ['Pato Mojado', 'Tierra Roja', 150],
                 "312": ['Tierra Roja', 'Pato Mojado', 150]
                }

def update():
    today_date = datetime.today().strftime('%Y-%m-%d')
    db.execute("DELETE FROM Itinerary WHERE date < (?);", today_date)
    db.execute("INSERT INTO Itinerary (Flightno, date, F, B, E, P) VALUES(1, ?, 0, 0, 0, 0)", today_date)

    current_ldit = datetime.strptime(((db.execute("SELECT MAX(date) as date FROM Itinerary"))[0]["date"]), "%Y-%m-%d").date()
    desired_ldit = date.today() + timedelta(days=49)
    days_to_add = (desired_ldit - current_ldit).days
    day = date.today()
    day = current_ldit + timedelta(days=1)

    for i in range(days_to_add):
        day_weekday = datetime.weekday(day)
        days_flights = weekly_sched[day_weekday]
        if len(days_flights) != 0:
            for flight in range(len(days_flights)):
                flight_to_insert = days_flights[flight]
                db.execute("INSERT INTO Itinerary (Flightno, date, F, B, E, P) VALUES(?, ?, 0, 0, 0, 0)", flight_to_insert, day)
        day = day + timedelta(days=1)

    flights = list(flight_routes)

    # For each flight (or route)
    for flight in range(len(flights)):
        flight_no = flights[flight]
        orig = flight_routes[flight_no][0]
        dest = flight_routes[flight_no][1]
        db.execute("UPDATE Itinerary SET orig = (?), dest = (?) WHERE Flightno=(?)", orig, dest, flight_no)

def populate_session(session):
    if "origin" not in session:
        session["trip_type"] = "-"
        session["origin"] = "-"
        session["destination"] = "-"
    if "go_date" not in session:
        session["go_date"] = "-"
        session["back_date"] = "-"
        session["leg_1_flightno"] = "-"
        session["leg_2_flightno"] = "-"
    if "pax_no" not in session:
        session["infants_no"] = "-"
        session["pets_no"] = "-"
        session["pax_no"] = "-"

def price(flight_id, flight_date):
    flight = db.execute("SELECT flightno, date FROM Itinerary WHERE Id = (?)", flight_id)
    base_price = flight_routes[str(flight[0]["flightno"])][2]
    today_date = date.today()
    target_day = datetime.strptime(flight[0]["date"], "%Y-%m-%d").date()
    day_delta = (target_day - today_date).days
    if day_delta < 25:
        final_price = base_price - ( base_price * 0.01 * day_delta)
    else:
        final_price = base_price + ( base_price * 0.01 * day_delta)
    return final_price

def addlbag_no(res_id):
    addl_baggers = db.execute("SELECT bag_no FROM passengers WHERE bag_no > 1 and res_no = (?)", res_id)
    addlbag_no = 0
    for count in range(len(addl_baggers)):
        addlbag_no = addlbag_no + addl_baggers[count]["bag_no"] -1
    return addlbag_no

def if_i_fits(res_id):
    reservation = db.execute("SELECT L1_flight_id, L2_flight_id, pax_no, pet_no, infants_no, res_id FROM reservations WHERE res_id = (?)", res_id)
    res_bep = {'B': db.execute("SELECT COUNT(*) FROM passengers WHERE seat_class = (?) AND res_no = (?)", "Business", reservation[0]["res_id"])[0]['COUNT(*)'],'E': reservation[0]["pax_no"] - (db.execute("SELECT COUNT(*) FROM passengers WHERE seat_class = (?) AND res_no = (?)", "Business", reservation[0]["res_id"]))[0]['COUNT(*)'], 'P': reservation[0]["pet_no"]}
    flight_bep = (db.execute("SELECT B, E, P FROM itinerary WHERE Id = (?)", reservation[0]["L1_flight_id"]))[0]
    bep_cap = {'B': 16, 'E': 138, 'P': 5}
    for bep in res_bep:
        if res_bep[bep] + flight_bep[bep] > bep_cap[bep]:
            return False
        else:
            return True

def recount_flights(res_id):
    reservation = db.execute("SELECT L1_flight_id, L2_flight_id, pax_no, pet_no, infants_no, res_id FROM reservations WHERE res_id = (?)", res_id)
    res_bep = {'B': db.execute("SELECT COUNT(*) FROM passengers WHERE seat_class = (?) AND res_no = (?)", "Business", reservation[0]["res_id"])[0]['COUNT(*)'],'E': reservation[0]["pax_no"] - (db.execute("SELECT COUNT(*) FROM passengers WHERE seat_class = (?) AND res_no = (?)", "Business", reservation[0]["res_id"]))[0]['COUNT(*)'], 'P': reservation[0]["pet_no"]}
    bep_cap = {'B': 16, 'E': 138, 'P': 5}

    l1_bep = (db.execute("SELECT B, E, P FROM itinerary WHERE Id = (?)", reservation[0]["L1_flight_id"]))[0]
    for bep in res_bep:
        if res_bep[bep] + l1_bep[bep] > bep_cap[bep]:
            return "Not enough cap"
    if reservation[0]["L2_flight_id"] != None:
        l2_bep = (db.execute("SELECT B, E, P FROM itinerary WHERE Id = (?)", reservation[0]["L2_flight_id"]))[0]
        for bep in res_bep:
            if res_bep[bep] + l2_bep[bep] > bep_cap[bep]:
                return "Not enough cap"

    if reservation[0]["L2_flight_id"] != None:
        db.execute("UPDATE itinerary SET B = (?), E = (?), P = (?) WHERE Id = (?)", b + bep[0]["B"], e + bep[0]["E"], p + bep[0]["P"], reservation[0]["L2_flight_id"])
    db.execute("UPDATE itinerary SET B = (?), E = (?), P = (?) WHERE Id = (?)", b + bep[0]["B"], e + bep[0]["E"], p + bep[0]["P"], reservation[0]["L1_flight_id"])
