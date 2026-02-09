# Investment_app
My app built to track my investments

PLAN/ARCHITECTURE:
- build DB backbone
- add basic app functionality using FastAPI, uvicorn, sqlalchemy (might change)
- add html templates and basic style.css
- add functionalities starting from the most critical

USE CASES:
1. Track portfolio content and valuation
2. Provide some sort of visual dashboard - portfolio breakdown, valuation history etc.
3. Allow import of historical asset valuations from a file
4. Allow manual addition of asset value
5. Allow import of transaction data from brokerage services that I use in a unified forat (manually formatted data)
6. Automatic calculation of interest accrued on bonds and automatic coupon transactions based on bond type and other factors (assuming I don't sell bonds and wait till their expiration)

FUNCTIONALITIES:
1. Current portfolio listing w details
2. Transaction listing w details 
3. Manual Investment insertion
4. Investment import (csv)
5. Manual Asset insertion
6. Manual Asset Valuation insetion
7. Asset Valuation import (csv)
8. Manual transaction insetion
9. Transaciton import (csv)
10. Automatic reevaluation of portfolio once new asset valuation loaded + historical portfolio value recorded
11. Pie chart presentation of the portfolio breakdown
12. Simple accounting & booking system providing  an aggregate status of each account (Cash, Dividends, etc.) 

