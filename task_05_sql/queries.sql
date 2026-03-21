-- 1.1
SELECT * 
FROM booking.ticket_flights;

--1.2
SELECT ticket_no, amount
FROM booking.ticket_flights
WHERE fare_conditions = 'Business';

--1.3
SELECT airport_code
FROM booking.airports_data
WHERE timezone = 'Europe/Moscow';

-- 1.4
SELECT * FROM booking.flights
WHERE flight_no = 'PG0216';

-- 1.5
SELECT * FROM booking.flights
WHERE departure_airport = 'DME'
AND arrival_airport = 'LED';

-- 1.6
SELECT * FROM booking.flights
WHERE scheduled_departure
BETWEEN '2017-02-10' AND '2017-04-10';

-- 1.7
SELECT model ->> 'en' AS model
FROM booking.aircrafts_data
WHERE range < 5000;

-- 1.8
SELECT * FROM booking.tickets
ORDER BY passenger_name DESC
LIMIT 100;

-- 1.9
SELECT ticket_no, passenger_name
FROM booking.tickets
WHERE passenger_name = 'VIKTORIYA SMIRNOVA';

-- 1.10
SELECT ticket_no, passenger_name
FROM booking.tickets
WHERE passenger_name LIKE '%NOV'
OR passenger_name LIKE '%OVA'
ORDER BY ticket_no DESC, passenger_name DESC;



-- 2.1
SELECT COUNT(*) AS total_aircrafts
FROM booking.aircrafts_data;

-- 2.2
SELECT AVG(range) AS avg_range
FROM booking.aircrafts_data;

-- 2.3
SELECT MAX(range) AS max_range
FROM booking.aircrafts_data;

-- 2.4
SELECT COUNT(*) AS total_airports
FROM booking.airports_data;


-- 2.5
SELECT
AVG(total_amount) AS avg_amount,

PERCENTILE_CONT(0.5) WITHIN GROUP
(ORDER BY total_amount) AS median_amount,

MODE() WITHIN GROUP
(ORDER BY total_amount) AS mode_amount

FROM booking.bookings;


-- 2.6
SELECT book_ref, total_amount
FROM booking.bookings
ORDER BY total_amount DESC
LIMIT 5;

-- 2.7
SELECT COUNT(*) AS total_boarding_passes
FROM booking.boarding_passes;

-- 2.8
SELECT SUM(amount) AS total_comfort
FROM booking.ticket_flights
WHERE fare_conditions = 'Comfort';

-- 2.9
SELECT flight_no, scheduled_departure
FROM booking.flights
WHERE scheduled_departure = (SELECT MIN(scheduled_departure) FROM booking.flights)
OR scheduled_departure = (SELECT MAX(scheduled_departure) FROM booking.flights);

-- 2.10
SELECT fare_conditions, AVG(amount) AS avg_amount
FROM booking.ticket_flights
GROUP BY fare_conditions