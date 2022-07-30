# TICKETS
#### Video Demo:  https://youtu.be/wCgVPnE4YjY
#### Description:
Airline webpage for buying tickets using Python and Flask.

This web application uses Flask and Python.
It has custom CSS. It does not use Bootstrap or Javascript. Changes at DOM level are by Flask.
It mostly uses tables to render information.
Upon program start, a function will analyze the tables in DB and compare the lastest date in tables to our current date.
After this, it will populate the database table accordingly with another function, based on destinations and itinerarios contained in hard-coded arrays. This allows seamless simulation of a real web app for tickets.
Implementation of new destinations and itineraries must be done manually, however it is as simple as altering the corresponding arrays or lists in the python file.

This project was very useful for me in learning a variety of skills:
- Working with dictionaries and indexing lists, keys, and extracting and manipulating databases.
- CSS basics, ways to format divisions, blocks vs width, alignment, floating divs, etc.
- Using tables to present information in ways that dont look like tables.
- Creating html content recursively.
- Setting up different pages that can be navigated to and from


Project uses sessions to store the selections, then upon confirmation it stores the selection into a database.
This way the selections can be modified easily, but are read directly from the database for confirmation avoiding possible errors.

Previous reservations may be accessed providing the reservation number in the fields in the header bar. Once in the reservation page, user may check-in as normal if not done yet.

A navigation menu exists during the reservation process so the user may go back and change previous selections (like dates or passenger number). This menu is disabled for those pages in which the required information is not already provided.

It turned out using cosmetically modfied tables was one of the most useful ways to present information.
Both the seat map and the boarding pass (the things I wanted to make the most) are made with tables, and using them simplified the process greatly.

A description of each page and their features:

Index:
Search for flights.
Select a departure city and an arrival city.
Select if the trip will be round or one way.
select the dates of the trip from the calendar.
Error handling avoids selecting the same origin and destination, selecting a return flight that happens before a departure flight,
or selecting flights that are in the past.

Results:
Returns a list of results (+/- 1 week from user provided desired date).
Displays price and capacity for each flight. This capacity is read from the database, and the price is calculated by importing a function that
considers the current day and the target day of the reservation. The closer, the more expensive the trip is.
Error handling avoids selection of return flights taking place before the departure flights. This is done by comparing the keys in the database.
Ie a flight with key 49 takes place after a flight with key 33, so 33 cannot be selected as a return flight.

Book:
Choose number of passengers, pets and infants from drop down menus.
Chose if traveling with infants and pets with the radio buttons.

Book pax:
Enter the name, last name and passport information for passengers. 
Error handling avoids providing incomplete form information or repeating passport numbers inside the same reservation.

Book pet / inf:
Enter the name, last name and passport information for infants or the name and species of pets.
Error handling avoids providing incomplete form information or repeating passport numbers inside the same reservation.

Details:
Review the total of your selections. This information is extracted from the database and not from the session.
Here you can see a compilation of all the information provided, and may use the nav bar to go back and modify a selection,
like the flights or the passenger information.

Confirm:
View price of the selections and choose a payment method using the radio button.

Reservation:
View your reservation as it was confirmed. From this page you can proceed to checking in if the date allows it. (Can check in 72 hrs or less before the flight).

Check in:
If not checked in and if within threshold of 3 days of flight date, passenger may choose a seat and be considered checked in.
Business passengers may select any seat, but economy passengers are restricted to selecting seats in the economy cabin.

Print boarding pass:
A boarding pass for each passenger is rendered using CSS, tables, and the information from the database. The passes are of a fixed size, which allows fitting on a page and printing.

Pending:
Applying JavaScript to prevent the user from inserting wrong values or making incorrect selections. Right now this alerts are presented by redirects to error pages.
Apply Javascript to make seat selection screen more pleasing to user.
Applying a barcode generator to insert a realistic barcode in the rendered boarding ticket (last stage, print ticket).




