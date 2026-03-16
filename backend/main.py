from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import os

load_dotenv()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)

IBM_API_KEY = os.getenv("IBM_API_KEY")



@app.get("/")
def root():
    return {"message": f"Hello, World!"}


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/companies")
def get_companies():
    from analytics import get_company_list
    return {"companies": get_company_list()}


@app.get("/analyze/{company}")
def analyze(company: str):
    from analytics import analyze_company
    result = analyze_company(company)
    if result is None:
        return {"error": "Company not found"}, 404
    return result


# --- ACENT-READY ENDPOINTS (Skills) ---

@app.get("/api/minerals/list")
def list_minerals():
    from analytics import get_all_minerals
    return {"minerals": get_all_minerals()}


@app.get("/api/company/minerals/{company}")
def company_minerals(company: str):
    from analytics import get_company_minerals
    return {"company": company, "minerals": get_company_minerals(company)}


@app.get("/api/mineral/risk/{mineral}")
def mineral_risk(mineral: str):
    from analytics import get_mineral_risk
    return get_mineral_risk(mineral)


@app.get("/api/company/summary/{company}")
def company_summary(company: str):
    from analytics import analyze_company
    result = analyze_company(company)
    if result:
        return {"company": company, "summary": result['summary']}
    return {"error": "Company not found"}, 404


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="localhost", port=8000)