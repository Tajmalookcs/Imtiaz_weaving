# Project Brief

## Confirmed

- What we are building: FBR digital invoicing for Imtiaz Weaving Factory, Faisalabad, Punjab
- Starting point: a copy of the Aysha Garments app, taken on 2026-11-13. The Aysha Garments project is not changed.
- Business, from the client's IRIS registration: manufacture of other textiles. Individual (sole proprietor), registered for sales tax, status Operative, tax office RTO Faisalabad
- Selling, from the sales ledger (January to September 2026, 52 invoices) and the Annex-C reports (July to September 2026): weaving charges, reported as Processing/Conversion of Goods, by the metre (Meter), at 18%, to registered buyers. In January 2026 there were also 7 sales of cloth to unregistered customers as Goods at standard rate (default), at 18% plus 4% further tax
- Invoices are plain numbers in order. The last in the ledger is 269, on 30 Sep 2026; number 229 is missing from it
- Buyers and products will be added in the app by the owner
- Products are the fabric type only: COTTON MIXED FABRIC (5211.1100), POLY COTTON FABRIC (5513.1110), PURE COTTON FABRIC (5208.1200). The cloth quality is typed on each invoice line, and FBR gets NAME - QUALITY (owner's decision, 2026-11-13)
- Products hold name, HS code, unit, sale type, sales tax rate, further tax, FED, retail price per unit and SRO. The rate text sent to FBR is made from the rate (owner's decision, 2026-11-14)
- The client's invoice shows: quantity in metres, the cloth quality (for example 76x68/30x30 98" CTN), "Weaving charges", the rate per metre, the HS code, value excluding tax, the sales tax rate, sales tax, and value including tax
- One install, one company, one user, as for Aysha Garments
- Client identity details, the IP, tokens and passwords are deliberately not stored in this repository

## Open questions

1. Which sandbox scenarios has FBR assigned to this client?
2. The same buyer's cloth was reported under 5211.1100 in some months and 5211.1200 in others. Which applies to which quality?
3. Were any invoices made after 269 (October, November)? Was 229 cancelled?
4. One registered buyer's slip shows no STRN. Its STRN is needed for the buyer record.
5. Some old invoices rounded the value to whole rupees (8,114 metres at 33.48 is 271,656.72, reported as 271,657). The app keeps paisa. Confirm this is fine.
6. Which name and address print on invoices and go to FBR: the invoices show Imtiaz Weaving Factory at Ghousia Road, Dhudiwala; IRIS also lists a branch at Chak No 204 RB.
7. Static IP: not confirmed yet. The sandbox token has been issued.
