# google-hackathon
Gen AI Exchange Hackathon


rough

Flights / Long-distance travel (bus/train/flight)
Flights
Amadeus API → global flights, seat maps, prices, bookings. (enterprise-grade, widely used).
Skyscanner API → for search + pricing.
Duffel API → modern flight booking API, developer-friendly, works with IATA airlines.
Kiwi.com API → powerful for low-cost carriers & multi-hop itineraries.
Trains
IRCTC APIs (India) → official APIs are limited; but 3rd-party integrators like Confirmtkt, RailYatri, or Trainman provide IRCTC booking integration.
For international → Trainline API (Europe), Amtrak APIs (USA).
Buses
RedBus API (India).
Abhibus API (India).
FlixBus API (Europe/US).

:oncoming_taxi: Local mobility (cabs, rentals, bikes/cars)
Cabs
Uber API → price estimates, time-to-pickup, ride booking.
Ola API → for India, cabs + autos.
Lyft API (if targeting US).
Self-drive rentals (cars/bikes)
Zoomcar API (India, cars).
Bounce API (India, scooters).
Revv API (India, cars).
Turo API (US, peer-to-peer car rentals).
Bike-sharing APIs (some public systems, e.g., Nextbike, CitiBike, etc.).

:hotel: Hotels & stays
Booking.com API → accommodations worldwide.
Expedia Rapid API → hotels, flights, cars, packages.
Airbnb API → unofficial, limited access; you can go via partners.
TripAdvisor API → reviews + hotels + restaurants.
Agoda API → alternative for Asia.

:admission_tickets: Activities, events, places
Google Places API / Maps API → attractions, restaurants, reviews, ratings, photos.
Viator API (TripAdvisor-owned) → tours, activities, excursions.
GetYourGuide API → activities & tickets.
Eventbrite API → local events, concerts.
Tiqets API → attractions/museum ticketing.

:credit_card: Unified booking & payments
Once you aggregate options, you'll want one-click checkout:
Razorpay (India) or Stripe (Global) → payment gateway to collect money once.
Then your backend orchestrates splitting that payment into individual bookings (via APIs above).
This is exactly what you described with the unified checkout → "user pays once, backend executes many bookings."

