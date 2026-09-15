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



