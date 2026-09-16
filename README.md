###### Smart Personal Finance API #####


## I-ExpenseTracketr MCP Server


uv run fastmcp dev inspector main.py -----To run in the Inspector of MCP server 

uv run fastmcp install claude-desktop main.py ---To run the local mcp server



NOTE:when we type expenses in the claude it will create the expnses.db and add the data to it 

Eg : 
add an expense - groceries yesterday for Rs 500
add an expense - cab ride to bangalore to Hassan last saturday fare was 900Rs

# Query to list down my expenses
list my expenses from september 1st week and also write the summary
| Date  | Category         | Note                    | Amount |
|-------|-------------------|--------------------------|--------|
| Sep 1 | Groceries         | DMart                    | ₹1,600 |
| Sep 3 | Travel            | Train ticket to Mysore   | ₹450   |
| Sep 5 | Health & Fitness  | Medicines from pharmacy  | ₹320   |
| Sep 7 | Food              | Swiggy order             | ₹540   |


# Query to summarise expenses
can you summarise my total expense from Aug 5th to aug 30th

| Category         | Total    | Entries |
|-------------------|----------|---------|
| Housing           | ₹15,000  | 1       |
| Food              | ₹2,480   | 3       |
| Shopping          | ₹2,350   | 1       |
| Health & Fitness  | ₹2,000   | 1       |
| Travel            | ₹1,720   | 2       |
| Utilities         | ₹1,398   | 2       |
| Entertainment     | ₹800     | 1       |


# Edit an expense

Change my food expense from Sep 23 to Rs 900
Output: Done — the Sep 23 Food expense ("Dinner date") is updated from ₹1,800 to ₹900.

# Credit expense
I received a mutual fund payout of Rs 5000 on Sep 20, add as credit
Output: Added — ₹5,000 credit on Sep 20, categorized as Investment, note "Mutual fund payout" (entry id 36).


# Budgets

Q1: Set my budget for food this month to Rs 8000
Output: Set — Food budget for September 2026 is now ₹8,000.

Q2: what's the current expense for september month in food category
Output: 
You've spent ₹1,440 on Food this September — well under your ₹8,000 budget, with ₹6,560 remaining.

Q3: How am I doing against my budget for September?
Output : That's the only budget you've set so far — Food — so here's the full picture:

Food — September 2026

Budget: ₹8,000
Spent: ₹1,440
Remaining: ₹6,560
Status: well under budget ✅



NOTE: We will add categories.json to force the schema of categories to clade to make sure it should pic the categories from that list , instead of adding some random categories



# II-We have added the FastAPI 
uv run uvicorn ExpenseTracker_with_FastAPI:app --reload   -->TO run the FastAPI application

Expense Tracker API METHODS

GET     /expenses
POST    /expenses
PUT     /expenses/{id}
DELETE  /expenses/{id}

POST    /credits

GET     /expenses/summary

POST    /budgets
GET     /budgets/{month}



# III - Converting FastAPI application to an MCP Server using Server.py
uv run fastmcp dev inspector server.py  ---->To run the FastAPI app in MCP server 





