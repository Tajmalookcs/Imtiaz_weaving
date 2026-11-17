# Build Plans

Each build gets an entry here. Work starts only after the plan is approved.

## Template

```
## Build N: Title

Status: Proposed | Approved | Done | Rejected
Date proposed:
Date approved:

### Goal
What this build achieves.

### Work
What will be built, and which files will change.

### Decisions needed
Anything the owner must decide.

### Outcome
What was actually done, and any differences from the plan.
```

## Builds

## Build 1: Core app

Status: Done locally on 2026-11-02. Not pushed yet.
Date proposed: 2026-11-02
Date approved: 2026-11-02

### Goal
A new invoicing app for manufacturing units that serves several clients and works offline.

### Work
- Step A: design preview with an animated login and loading screens, plus dashboard and invoice entry. All assets are stored locally.
- Step B, after design approval: Django + SQLite app with company profiles, users, products, customers, invoice entry and tax calculation, with tests and a `start.bat` launcher.

Not included: FBR calls, the upload queue, final invoice printing.

### Decisions needed
- How foreign buyers are reported to FBR.
- How a discount is reported to FBR.

### Outcome
Step A: `design_preview/` added and the design approved by the owner.

Step B: app built, with these points to note:
- Added at the owner's request: invoices are saved first, and only an "Approve and send to FBR" click releases them. Until the FBR connection is built, the button only marks the invoice as approved.
- One person uses the app and approves their own invoices. The Users screen is hidden from the menu.
- Tax is worked out after discount.
- Lot size varies, so pieces per lot is entered on each invoice line.
- Foreign buyers' invoices are saved as held and can't be approved.
- Invoices can be edited or deleted until approved, then they're locked. A deleted invoice's number is used again by the next new invoice.
- `start.bat` hasn't been run on Windows yet.

## Build 2: FBR connection (sandbox)

Status: Built and tested against the spec's samples and a fake local server. Not yet tested against FBR.
Date proposed: 2026-11-02
Date approved: 2026-11-02

### Goal
Send approved invoices to the FBR sandbox and run the assigned scenarios.

### Work
- `fbr` app: encrypted token, FBR lists, rate lookup, validate then post, strict reply reading, permanent call log, scenarios table.
- Unknown post results stop for a person to check IRIS, and are never resent automatically.
- Rejected invoices stay editable. Sandbox and demo acceptances never count as final.

Not included: production token, QR code and printing, sending export invoices.

### Decisions needed
- Confirm in sandbox: `valueSalesExcludingST` is sent after discount, and `extraTax` is an empty string as in the IRIS sample.
- Confirm in sandbox: how FED and SRO fields work for the FED and SRO scenarios.

### Outcome
The token test and list download worked against the FBR sandbox. Invoice sending is not yet tested against FBR.

Also added at the owner's request: a clear "page expired" screen instead of the plain security error.

## Build A: Printing

Status: Done locally on 2026-11-03. Not pushed yet.
Date proposed: 2026-11-03
Date approved: 2026-11-03

### Goal
A4 invoice printing that can never pass off an unaccepted invoice as final.

### Work
Print screen with Pending FBR, Sandbox test and final copies, amount in words, and a further tax column only when needed.

### Decisions needed
None.

### Outcome
The final copy has the FBR logo, the IRN and a version 2.0 (25x25) QR code at 1x1 inch holding the IRN, as confirmed by the owner. It only appears after production acceptance, which isn't built yet.

## Build B: Sales register and backup

Status: Done locally on 2026-11-03.
Date proposed: 2026-11-03
Date approved: 2026-11-03

### Goal
Help reconcile the monthly return, and protect the data.

### Work
- Sales register: date and status filters, totals, and an export that opens in Excel.
- `backup.bat`: saves the database, keys and media to a folder outside the project.
- "Send all waiting" was dropped at the owner's request.

### Outcome
Built and tested. The register totals show a warning when they include invoices not accepted in production.

## Build C: Features from the FBR documents

Status: Done locally on 2026-11-03. Not pushed yet, and not yet tested against FBR.
Date proposed: 2026-11-03
Date approved: 2026-11-03

### Goal
Support what the PRAL spec v1.12 and User Manual v1.5 require.

### Work
- QR code on the final copy: version 2.0 (25x25) at 1x1 inch, holding the IRN as confirmed by the owner. The documents don't state the content.
- Lookups: units for an HS code, SRO schedules and SRO items.
- Buyer checks: registration type and active status.
- Debit notes against accepted invoices, with FBR's 180-day and sales tax limits.
- Production mode: separate token, real URLs and no scenario ID. It needs a deliberate switch.

### Decisions needed
- Errors 0027 and 0028 mention a reason for debit notes, but the spec has no field for it. Confirm in sandbox.
- The spec names STATL and Get_Reg_Type as GET with a JSON body. POST is tried if GET is refused.
- Credit notes appear only in error messages, so they aren't built. Ask PRAL.

### Outcome
Built and tested against the spec's samples and a fake local server.

Also changed at the owner's request: the company now has a required NTN (0000000-0) and an optional CNIC. Invoices print only the NTN, and FBR receives its 7 digits.

## Build D: Print and offline rules from FBR's Sales Tax Rules

Status: Done locally on 2026-11-03. Not yet tested against FBR.
Date proposed: 2026-11-03
Date approved: 2026-11-03

### Goal
Cover what Rule 150R(13) and Rule 150XC require.

### Work
- Print: tax period, unit, and SRO and serial number where used.
- Offline: invoices saved without internet, or that couldn't reach FBR, are marked as offline on screen and in print, with a 24-hour warning on the dashboard.
- `docs/PRAL_QUESTIONS.md`: questions for PRAL support.

### Decisions needed
- The rules say a 7x7 mm QR, but PRAL's spec says 1x1 inch. The app follows PRAL's spec until PRAL confirms.
- The e-invoicing software registration number isn't printed yet. Ask PRAL what it is when PRAL is the integrator.

### Outcome
Built and tested locally.

## Build E: Selling by KG

Status: Done locally on 2026-11-04. Not yet tested against FBR.
Date proposed: 2026-11-04
Date approved: 2026-11-04

### Goal
The client's FBR sales report is in KG, but invoices only allowed pieces and lots. The app serves several clients, so KG becomes the default and piece and lot stay.

### Work
- A product whose FBR unit is KG or Kilogram is invoiced by KG. Any other product is invoiced by piece or lot.
- New products start on KG, and a new invoice starts on the first KG product if there is one.
- The saving step refuses a selling method that doesn't fit the product's unit, because the quantity goes to FBR in that unit.
- The invoice form, invoice screen, print copy and product screens show the right unit.
- One KG sample product and invoice added to the demo data.
- In sandbox, an invoice whose items are all Processing/Conversion of Goods suggests SN016. Approved by the owner on 2026-11-04.

### Decisions needed
- The client's starting invoice number. The app starts at 1 and has no setting for this yet.
- The client's report shows whole rupees, while the app keeps paisa. Watch this in the sandbox.

### Outcome
Built and tested locally with a fake server.

## Build F: Pack lines with KG, job number, buyer STRN and last invoice number

Status: Done locally on 2026-11-04. Not yet tested against FBR.
Date proposed: 2026-11-04
Date approved: 2026-11-04

### Goal
The first client charges by the set or pack, but reports KG to FBR, because that's the unit for its HS code (the client's statement). The app needs both on each line.

### Work
- A KG product can have a pack unit. Its invoice line has packs, a rate per pack and KG. The value comes from packs and rate.
- Total weight shows at the end of the invoice, on screen and in print.
- "Your reference" is now "Job no.". It prints but doesn't go to FBR.
- Customers have a STRN. It prints with the NTN but doesn't go to FBR.
- FBR gets KG as the quantity. Pack lines that match on HS code, sale type, rate, unit, SRO details and fixed value go as one item, with KG, value and tax added up. Pack lines that differ go as separate items. Other lines stay separate.
- Companies can enter their last invoice number. New invoices take the lowest free number after it, so a deleted number is used again. A blank prefix gives plain numbers like 119.

### Decisions needed
- Does FBR accept the combined item? Yes in the sandbox: the owner's SN016 test on 2026-11-04 was accepted with three pack lines sent as one item.

### Outcome
Built and tested locally with a fake server.

## Build G: One install, demo and registration

Status: Done locally on 2026-11-04. Not yet tested against FBR.
Date proposed: 2026-11-04
Date approved: 2026-11-04

### Goal
Each client gets a separate install, used by one person. New installs run as a demo until the developer registers them.

### Work
- Removed new company, switch company, user screens and the operator role. The database structure stays, so existing data is safe.
- Setup needs the developer password. Without the demo file, this copy says it isn't ready.
- Demo: 15 days from first use. Invoices say DEMO on screen and in print, the sandbox works and production is refused. After 15 days, or if the date moves back, new invoices and sending stop, while old data stays open.
- Registration: a file signed with the developer's private key, tied to the client's NTN, replaces the demo. It holds the hash of that client's developer password.
- Production: needs registration, a production token and the existing confirmation tick.
- Company details ask for the developer password, and stay open for 10 minutes.
- The last invoice number has its own box on the new invoice screen, which closes after the first invoice.
- Developer commands: `setup_licensing` and `make_licence`.

### Limits
- Someone who can change the code can remove these checks. The code runs on the client's computer.

### Decisions needed
- Done on 2026-11-05: the owner ran `setup_licensing`, and `licensing/demo.json` and `licensing/public_key.pem` were added to the repository.

### Outcome
Built and tested locally with a fake server.

## Build H: Seed data and STRN display

Status: Done locally on 2026-11-05. Not yet tested against FBR.
Date proposed: 2026-11-04
Date approved: 2026-11-04. The owner asked for the STRN display on 2026-11-05.

### Goal
Add the first client's records in one step, and a saved test invoice for each sandbox scenario still to run.

### Work
- `add_seed_data` and `add_seed_data.bat` read a local file, `instance/seed_data.json`. It holds tax numbers, so it's never pushed.
- It adds the client's products and buyer, then test products, a test buyer and saved test invoices. Their job number starts with TEST-, and their scenario is already chosen.
- It keeps existing records and can run more than once. It adds no test records outside sandbox mode, or with `--real-only`. It sends nothing to FBR.
- STRN is saved with no dashes. Dashes show only on the invoice screen and in print.
- Tests use made-up data and no FBR connection.

### Scenarios
- In the data file: SN001, SN002, SN005, SN006, SN007, SN009, SN017 and SN024. Sale types are from FBR's list. Rates, SRO schedules and item numbers are from the owner's FBR lookups on 2026-11-05.
- Where FBR offered several SROs or items, the test uses one of them. These are test values only, and say nothing about the client's real sales.
- HS codes for these tests start with the client's code, and change if FBR refuses it.
- SN017: HS code 2710.1240, unit Liter, quantity 1, value 100 and sales tax 118 passed in the sandbox. These values came from a Manager.io forum post, not an official document. FBR refused 18% plus Rs. 80 per liter worked out on 100 liters (error 0131). The formula is unconfirmed, so it isn't a rule for real invoices.

### Decisions needed
- None.

### Outcome
Built and tested locally without any FBR connection. SN001 and SN002 were accepted in the sandbox on 2026-11-05. SN005, SN006, SN007, SN009, SN017 and SN024 were accepted too, so all 9 assigned scenarios have passed the sandbox.

## Build I: Show the FBR unit on piece lines

Status: Done locally on 2026-11-05.
Date proposed: 2026-11-05
Date approved: 2026-11-05

### Goal
The owner saw a product in Liter shown as "100 pieces" on its invoice.

### Work
- A line sold by piece now shows the product's FBR unit on the invoice screen and in print, such as "100 Liter".
- Numbers, pieces, units still shows as piece or pieces, because the full name is long. Lots stay as they were.
- Tax and what goes to FBR don't change.

### Outcome
Built and tested locally without any FBR connection.

## Build J: New client setup guide

Status: Done on 2026-11-05. The owner asked for it directly.

### Work
- `docs/CLIENT_SETUP_GUIDE.md` records the steps, the sandbox values that passed and the lessons, so the next client takes less time.
- `docs/seed_data.example.json` is a starting point with made-up details.
- `licensing/demo.json` and `licensing/public_key.pem` added, so new installs can be set up.

## Build K: Invoice layout like the client's slip

Status: Done locally on 2026-11-05.
Date proposed: 2026-11-05
Date approved: 2026-11-05

### Goal
The owner compared the app with the client's Excel slip. The app mixed quantity and unit, and was harder to read.

### Work
- Invoice screen and print: separate Qty and Unit columns, HS code on each line in its own column, a totals row with total quantity, and Total weight below.
- Discount, further tax and FED columns show only when they have an amount.
- Invoice form: Qty, Unit, Product, Rate. One Unit list replaces Sold by and Pack unit. Discount stays hidden until clicked.
- One Total KG for the invoice. Pack lines that go to FBR as one item share it in proportion to their packs. Lines that differ get their own Total KG.
- Tax and the invoice data sent to FBR don't change.

### Decisions
- Total KG as above: the owner agreed on 2026-11-05.
- HS code on every line: the owner's instruction on 2026-11-05.

### Outcome
Built and tested locally, with the client's invoice 101 figures on made-up details. Totals matched the slip. No FBR connection was used.

## Build L: Open the app with no black window

Status: Done on 2026-11-06.
Date proposed: 2026-11-05
Date approved: 2026-11-05

### Work
- `start_app.vbs` opens the app with no window. If the app is already running, it only opens the browser. On a first run it uses `start.bat`, so the install progress shows. It shows a message box if something fails, and writes details to `instance/app.log`.
- `stop_app.vbs` stops the app.
- The first run of `start_app.vbs` adds desktop shortcuts to start and stop the app.
- `start.bat` doesn't change.

### Outcome
The owner tried both on Windows on 2026-11-06. `stop_app.vbs` first showed an error, because the venv's launcher and its Python end together. That's fixed, and both now work.

## Build M: Send the client's invoice number to FBR

Status: Done on 2026-11-06. Confirmed in the sandbox and in production.
Date proposed: 2026-11-05
Date approved: 2026-11-06

### Goal
FBR's Annex-C report has an Invoice No. column with the client's own numbers. Invoices sent by the app so far leave IRIS's Source Invoice No. column empty.

### Plan
- PRAL's specification names no field for this. It says `invoiceRefNo` is only for debit notes. Two third-party sources disagree, with one using `invoiceNumber` and the other `invoiceRefNo`.
- Try `invoiceNumber` first, then `invoiceRefNo`, on a test database. The owner runs these sandbox tests from the home connection.
- Keep the field that shows the number in IRIS. If neither works, hold real invoices until PRAL answers.

### Outcome
- `invoiceNumber`: the sandbox accepted the invoice on 2026-11-06, but the Source Invoice No. column in IRIS stayed empty.
- `invoiceRefNo`: the sandbox accepted the invoice on 2026-11-06, but the column stayed empty.
- The sample JSON in IRIS has no other field for this.
- `sourceInvoiceNo`: tried last, with the owner's approval. The sandbox accepted the invoice and IRIS showed the number in Source Invoice No. The app now sends this field.
- FBR's replies have this field, but PRAL's specification and the IRIS sample don't.
- The first real invoice, sent on 2026-11-06, showed its number in Source Invoice No. in IRIS's production list. The Invoice No. column in Annex-C is still to be checked.

## Build N: Developer password on FBR setup

Status: Done locally on 2026-11-06.
Date proposed: 2026-11-06
Date approved: 2026-11-06

### Goal
A client could change the FBR mode or token by accident, which can stop real invoices or send them as tests.

### Work
- FBR setup, the token, mode, scenarios, connection test, FBR lists, Find tax rates, Lookups and FBR logs now ask for the developer password. It stays open for 10 minutes.
- Invoices, sending to FBR, printing, Customers and the buyer check stay open.
- Tax and the invoice data sent to FBR don't change.

### Outcome
Built and tested locally without any FBR connection.

## Imtiaz Weaving build 1: Weaving invoices by the metre

Status: Done locally on 2026-11-13.
Date proposed: 2026-11-13
Date approved: 2026-11-13

### Goal
Imtiaz Weaving Factory charges for weaving by the metre, and reports it to FBR in Meter (from the client's Annex-C reports, July to September 2026, and its sales ledger, January to September 2026). Its invoices must look like its own sales tax invoice slip.

### Work
- New way of selling: Metre. A product whose unit for FBR is Meter is always sold by the metre: metres times the rate per metre. New products start on Meter.
- The rate per metre is typed on each invoice line, because it changes from invoice to invoice.
- The printed invoice follows the client's slip: Sales Tax Invoice title, name, address, G.S.T # and NTN# with its check digit; invoice no., date and tax period; customer box with name, address, G.S.T. # and NTN#; empty Cash and Credit boxes; then Qty with MTRS, the description with WEAVING CHARGES, the rate per metre and the HS code, value excluding tax, rate of S.T, sales tax and value including tax. The FBR logo, QR code and IRN stay at the bottom.
- WEAVING CHARGES prints only on Processing/Conversion of Goods lines, not on cloth sales.
- Amounts print in rupees and paisa, as FBR records them.
- Tests check the slips' figures and the FBR data for metres. No client names or numbers are in the tests.

### Outcome
Built and tested locally without any FBR connection.

## Imtiaz Weaving build 2: Quality on each invoice line

Status: Done locally on 2026-11-13.
Date proposed: 2026-11-13
Date approved: 2026-11-13

### Goal
Products are the fabric type only (name, HS code, unit, sale type and tax). The cloth quality, such as 76x68/30x30 98" CTN, changes from invoice to invoice, so it's typed on each line. The owner wants the quality on FBR's record too, so lost local data can be rebuilt from the IRIS sales ledger.

### Work
- Each invoice line has an optional Quality box, up to 150 characters.
- The box suggests every quality used before, for any product. Picking one fills the rate it was last sold at, which can still be changed.
- FBR's productDescription is NAME - QUALITY, for example COTTON MIXED FABRIC - 76x68/30x30 98" CTN. With no quality, it's the product name only.
- The printed invoice's table was changed on 2026-11-14 to the owner's sample: QTY, UoM, Description (NAME - QUALITY), Rate, Value Excluding Sales Tax, Rate of Sales Tax, Sales Tax Payable, Value Including Sales Tax. The WEAVING CHARGES and HS CODE lines were dropped from the print; the HS code still goes to FBR.
- Not confirmed: PRAL's specification gives no maximum length for productDescription. The app limits the whole text to 255 characters. The sandbox will show whether FBR accepts it.

### Outcome
Built and tested locally without any FBR connection.

## Imtiaz Weaving build 3: Product redesign

Status: Done locally on 2026-11-14.
Date proposed: 2026-11-14
Date approved: 2026-11-14

### Goal
A simpler product form in the owner's order, with what goes to FBR shown on the page, and nothing kept that isn't needed.

### Work
- Product form, in order: product name, HS code, unit reported to FBR (dropdown), sale type (dropdown), sales tax rate % (up to 2 decimals), further tax rate %, FED rate %, retail price per unit, then SRO schedule no. and SRO item no. under "Only if this sale falls under an SRO", and available on new invoices.
- The rate text FBR gets is made from the rate, for example 18 becomes 18%. Exempt goods go as Exempt. It shows read-only on the form as "Rate sent to FBR", and updates as the rate is typed.
- A product whose rate text can't be made from the rate, such as the SN017 sandbox test (18% and Rs. 80 per Liter), keeps its text. The seed file and the migration mark it.
- FBR's Fixed / notified value or Retail Price shows read-only on the form, and stays 0, as on the client's Annex-C.
- Retail price per unit is the product's price. A new invoice line starts with it.
- Units until FBR's lists are downloaded: Meter, KG, Square Metre, Numbers, pieces, units, Liter, KWH. Each source is noted in fbr/constants.py. After Download FBR lists, FBR's full list replaces them. PRAL's specification v1.12 has no full unit list, only samples.
- Sale types until FBR's lists are downloaded: the spellings FBR's sandbox accepted on 2026-11-05 and the client's Annex-C used.
- The products list shows HS code, unit, sale type, rate to FBR, further tax, FED, retail price per unit and SRO.
- Removed completely: Description for FBR, and selling by the pack (SET PACK, PAIR PACK, PIECE PACK, the shared total KG, and combining pack lines into one FBR item). Each invoice line is now its own FBR item. Two migrations remove the columns; any old pack line becomes a plain KG line.

- Layout, approved from a mockup on 2026-11-14: two boxes per row for HS code and unit, sales tax rate and rate sent to FBR, further tax and FED, retail price per unit and the fixed or notified retail price, and the two SRO boxes. Product name and sale type stay full width. On narrow screens the pairs stack.
- Tidy-up, approved on 2026-11-14: no captions under the boxes (the SRO heading stays), plain text boxes with no up and down arrows for the rate, further tax, FED and retail price, and a new product starts with further tax 4, as on the client's January 2026 sales to unregistered buyers.

### Outcome
Built and tested locally without any FBR connection. The migrations were tried on a copy of the PC's database.

## Imtiaz Weaving build 4: Remove Job no.

Status: Done locally on 2026-11-14.
Date proposed: 2026-11-14
Date approved: 2026-11-14

### Work
- Job no. is gone from the invoice form, the invoice page and the print, and its column is deleted.
- The seed file finds test invoices by scenario: one per scenario, so running it again adds nothing.
- Demo invoices carry a hidden yes/no marker instead of a Job no. starting with DEMO, so they still can't be sent to FBR. The migration marks old demo invoices.
- The owner plans to delete the database, start the migrations again and write a new seed file once the app is complete.

### Outcome
Built and tested locally without any FBR connection. The migration was tried on a copy of the PC's database, and the 9 test invoices kept their scenarios.

## Imtiaz Weaving build 5: Invoice line order

Status: Done locally on 2026-11-14.
Date proposed: 2026-11-14
Date approved: 2026-11-14

### Work
- Each invoice line is Product, Qty, Unit and Rate, in that order, with Description below.
- The Quality box is labelled Description, with the placeholder For example 76x68/30x30 98". FBR still gets NAME - DESCRIPTION, exactly as typed, so the cloth type isn't repeated in the description.
- The database column keeps the name quality until the owner starts the migrations again.

### Outcome
Built and tested locally without any FBR connection.

## Imtiaz Weaving build 6: Fixed unregistered buyer

Status: Done locally on 2026-11-14.
Date proposed: 2026-11-14
Date approved: 2026-11-14

### Work
- Every company has a fixed buyer, UN-REGISTERED BUYER: unregistered, no NTN or CNIC, the company's province, address Faisalabad.
- It's first in the buyer list on the invoice form, and in the customers list with a Fixed tag.
- Its name, type, NTN, STRN, country and availability can't be changed. Its address, province and phone can.
- New companies get it when they're created. The migration adds it to existing companies.
- Further tax applies on its invoices from each product's further tax rate, as for any unregistered buyer.

### Outcome
Built and tested locally without any FBR connection. The migration was tried on a copy of the PC's database.

## Imtiaz Weaving build 7: Search for buyer and product

Status: Done locally on 2026-11-14.
Date proposed: 2026-11-14
Date approved: 2026-11-14

### Work
- On the invoice form, Buyer and each line's Product are search boxes: typing part of a name shows only the matches, in any case. Click one, or use the arrow keys and Enter. Esc closes the list, and No match shows when nothing fits. Only names from the list can be chosen.
- The search box is the app's own script, static/js/combobox.js, so it works offline. The hidden list underneath still saves the form as before.
- Links to scripts and styles now carry the file's change time (core/storage.py), so browsers fetch new copies after an update without Ctrl+F5.

### Outcome
Built and tested locally without any FBR connection, and tried in a browser on a copy of the PC's database.

## Imtiaz Weaving build 8: Fresh migrations and database

Status: Done locally on 2026-11-16. The owner runs reset_database.bat on the PC.
Date proposed: 2026-11-16
Date approved: 2026-11-16

### Goal
The production token was issued. Start real invoicing on a clean database, with one migration per app.

### Work
- billing, core and fbr each have one 0001_initial.py, made from the current models. The older migration files are gone.
- reset_database.bat: stops if the app is running, asks for YES, keeps the old database as instance\db_old_<date and time>.sqlite3, deletes instance\db.sqlite3 and the old migration files. Registration, the secret key, the seed file and media stay.
- instance\seed_data.json (on the PC only): the 3 products and 2 registered buyers, with no test records. UN-REGISTERED BUYER is made when the company is set up.

- Sandbox before production, approved on 2026-11-16: instance\seed_sandbox.json (PC only) holds the test products, the test buyer and one test invoice per scenario, and add_sandbox_tests.bat adds them. After the scenarios pass, reset_database.bat runs again, so real invoice numbers start clean.
- reset_database.bat asks for a Y key press, after typing YES didn't work on the PC.

### Outcome
All 219 tests pass on the fresh migrations. A brand-new database, a company and the new seed file were tried here: 3 products, 3 buyers and no invoices.

## Imtiaz Weaving build 9: Inch sign and FBR's error words

Status: Done locally on 2026-11-16.
Date proposed: 2026-11-16
Date approved: 2026-11-16

### Why
In the sandbox on 2026-11-16, a description with the inch sign (98") made FBR reply HTTP 500, code 03, "Requested JSON in Malformed". The app's message said only "Try again later". The same two-item invoice without the sign was accepted (one IRN, items numbered -1 and -2).

### Work
- The inch sign becomes "in" as it's typed in an invoice line's Description and in a product name, and again when they're saved, so FBR never gets it: 98" becomes 98in.
- When FBR answers with an error, the app shows FBR's own words and code, for example "FBR said: Requested JSON in Malformed (code 03) (HTTP 500)", and says that sending the same invoice again gives the same answer.

### Outcome
Built and tested locally without any FBR connection, and tried in a browser.

## Imtiaz Weaving build 10: HS Code column, no payment boxes

Status: Done locally on 2026-11-17.
Date proposed: 2026-11-17
Date approved: 2026-11-17, after the client saw the sample

### Work
- The printed invoice has an HS Code column after UoM, with each line's own HS code.
- The Mode of Payment (Cash / Credit) boxes are gone, and the customer box takes the full width.
- Narrower padding and a slightly smaller font in the table, so all 10 columns fit an A4 page.
- The client decided against a logo on the slip (2026-11-17).

### Outcome
Built and tested locally without any FBR connection, and printed to A4 in a browser.

## Imtiaz Weaving build 11: Form layout, date in words, contact line, passwords

Status: Done locally on 2026-11-17.
Date proposed: 2026-11-17
Date approved: 2026-11-17

### Work
- Invoice date: the date shows in words next to the box, for example 10-Oct-2026 (Saturday), because the box's own format follows Windows and day and month can be mixed up. A date more than 30 days old, or in the future, shows a red warning.
- Invoice lines: row 1 has Product, with its HS code under it, and Description. Row 2 has Qty, Unit, Rate and remove. The line's bottom note no longer repeats the HS code.
- Printed invoice: a small line at the bottom, "Digital Invoicing setup & support: Alamgir Developers · 0304-6270546", from DEVELOPER_CONTACT in config/settings.py. An empty name prints no line. It doesn't show on screens and doesn't go to FBR.
- Change password: a link by the user name in the menu. Current password, then the new one twice, with the usual password rules. The user stays signed in.
- Login: closing the browser signs the user out. A tick box, "Remember my user name and password on this computer", keeps both in this browser's storage and fills them in next time; Log in is still pressed each time. The owner chose this over the browser's own password saving, knowing anyone using that browser can see the saved password.

### Outcome
Built and tested locally without any FBR connection, and tried in a browser.

## Imtiaz Weaving build 12: Print heading, and no pending marks in production

Status: Done locally on 2026-11-17.
Date proposed: 2026-11-17
Date approved: 2026-11-17

### Work
- Print heading: "Sales Tax Invoice", then the business name, then the address, then one line with "NTN:" (with its check digit, as saved) and "STRN:" (with dashes). All come from the company saved with the invoice.
- Invoice page: the mode line, "Check the details below…" and "This is not a final invoice…" show only in sandbox mode. In production mode they're hidden.
- Print in production mode, before FBR accepts the invoice: no PENDING FBR watermark, no "Not a final invoice" notice, no "IRN not issued yet" box, and no "Pending FBR" tab title. The owner chose this, knowing an unsent print then differs from a final one only by the missing FBR logo, QR code and IRN.
- Unchanged: invoices accepted in production print the FBR logo, QR code and IRN as before. Sandbox, sandbox-test and demo prints keep their marks.
- Rounding taxes to whole rupees was discussed and left out (2026-11-17).

### Outcome
Built and tested locally without any FBR connection. 241 tests pass.

## Imtiaz Weaving build 13: Delivery folder

Status: Done locally on 2026-11-17.
Date proposed: 2026-11-17
Date approved: 2026-11-17

### Work
- New `make_delivery.bat` makes `D:\Imtiaz_Weaving_Delivery` for the client's computer. It is made again from scratch each time, after Y.
- It copies the app folders (billing, config, core, fbr, licensing, templates, static) without `__pycache__`, `tests.py` or `.pyc` files; `manage.py`, `requirements.txt`, `start.bat`, `start_app.vbs`, `stop_app.vbs`, `backup.bat`; and from `instance` only `db.sqlite3`, `fbr_key.txt`, `secret_key.txt` and `licence.json`.
- It leaves out `venv` and `staticfiles` (start.bat makes them), docs, media, CLAUDE.md, README.md, old databases, seed files, the log, and the reset, demo, seed and sandbox-test bat files.
- It stops if the app is running, or if the database or FBR key is missing, and checks the key files arrived.
- Real invoices are made on one computer only. After delivery, the owner's copy shouldn't be used for real invoices. The client computer's IP goes into IRIS before its first invoice.

### Outcome
Built locally. Not yet run on the owner's computer.

## Later builds (not approved yet)

3. Run the sandbox scenarios from the whitelisted computer.
6. Go live: first real invoice, training.
