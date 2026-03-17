import math

import pandas as pd
import sqlite3
import os
import numpy as np

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "mineralwatch.db")

def get_db_conn():
    """Get a database connection and ensure it's valid."""
    if not os.path.exists(DB_PATH):
        raise FileNotFoundError(f"Database not found at {DB_PATH}")
    return sqlite3.connect(DB_PATH)

def get_company_list():
    """Get list of unique companies from database."""
    try:
        conn = get_db_conn()
        query = "SELECT DISTINCT Company FROM edgar_filing_details"
        companies = pd.read_sql_query(query, conn)['Company'].tolist()
        conn.close()
    except Exception as e:
        print(f"Database error in get_company_list: {e}")
        return []
    
    clean_companies = []
    for c in companies:
        name = c.split('(')[0].strip()
        if name and name not in clean_companies:
            clean_companies.append(name)
            
    return sorted(clean_companies)

RISK_SCORE_MAP = {'LOW': 20, 'MODERATE': 50, 'HIGH': 70, 'CRITICAL': 90}


def _normalize_hhi(hhi: float) -> float:
    """Map HHI (0-10000) to risk score (0-100) using DOJ/FTC antitrust thresholds."""
    if hhi <= 1500:
        return (hhi / 1500) * 30
    elif hhi <= 2500:
        return 30 + ((hhi - 1500) / 1000) * 30
    elif hhi <= 5000:
        return 60 + ((hhi - 2500) / 2500) * 25
    else:
        return 85 + min((hhi - 5000) / 5000, 1.0) * 15


def compute_hhi(trade_data):
    """Compute Herfindahl-Hirschman Index using Customs Value (USD)."""
    val_col = 'Customs Value (USD)'
    if trade_data.empty or trade_data[val_col].sum() == 0:
        return 0
    
    total_val = trade_data[val_col].sum()
    shares = trade_data.groupby('Country')[val_col].sum() / total_val
    hhi = (shares ** 2).sum()
    return hhi

def analyze_company(company_name):
    """Perform full risk analysis for a given company using SQL."""
    try:
        conn = get_db_conn()
        
        # 1. Get findings for the company
        query_filings = "SELECT * FROM edgar_filing_details WHERE Company LIKE ?"
        company_filings = pd.read_sql_query(query_filings, conn, params=(f"%{company_name}%",))
        
        if company_filings.empty:
            conn.close()
            return None
    except Exception as e:
        print(f"Error analyzing company {company_name}: {e}")
        return None
    
    minerals = company_filings['Mineral'].unique().tolist()
    
    # 2. Get trade flows and compute concentration
    trade_flows = []
    mineral_hhis = []
    val_col = 'Customs Value (USD)'
    
    for mineral in minerals:
        # Match mineral to trade data
        query_trade = "SELECT * FROM trade_data WHERE Mineral LIKE ?"
        mineral_trade = pd.read_sql_query(query_trade, conn, params=(f"%{mineral}%",))
        
        if not mineral_trade.empty:
            total_val = mineral_trade[val_col].sum()
            shares = (mineral_trade.groupby('Country')[val_col].sum() / total_val * 100).round(1)
            
            for country, share in shares.items():
                if share > 0.1:
                    trade_flows.append({
                        "mineral": mineral,
                        "country": country,
                        "share": share,
                        "risk": "high" if share > 50 else "elevated" if share > 20 else "low"
                    })
            
            hhi = compute_hhi(mineral_trade)
            mineral_hhis.append(hhi)
    
    avg_hhi = np.mean(mineral_hhis) if mineral_hhis else 0
    
    # 3. Compute Scores
    # Trade score: convert HHI (0-1 scale from compute_hhi) to 0-10000, then apply piecewise normalization
    trade_score = _normalize_hhi(avg_hhi * 10000)

    # Corporate score: severity-weighted average of USGS supply risk per mineral
    placeholders = ','.join(['?'] * len(minerals))
    query_usgs = f"SELECT * FROM usgs_minerals WHERE \"USGS Commodity Name\\n(exact CSV name)\" IN ({placeholders})"
    relevant_usgs = pd.read_sql_query(query_usgs, conn, params=minerals)

    if not relevant_usgs.empty and 'Supply Risk' in relevant_usgs.columns:
        mineral_scores = [
            RISK_SCORE_MAP.get(str(r).upper(), 50)
            for r in relevant_usgs['Supply Risk']
            if pd.notna(r)
        ]
        corporate_score = round(sum(mineral_scores) / len(mineral_scores)) if mineral_scores else 50
    else:
        corporate_score = min(round((len(minerals) / 10.0) * 100), 100)

    # Substitutability Risk: average across all company minerals, correct scale (high risk = high score)
    subst_scores = []
    if not relevant_usgs.empty and 'Supply Risk' in relevant_usgs.columns:
        for r in relevant_usgs['Supply Risk']:
            if pd.notna(r) and isinstance(r, str):
                subst_scores.append(RISK_SCORE_MAP.get(r.upper(), 50))
    subst_score = round(sum(subst_scores) / len(subst_scores)) if subst_scores else 50

    composite_score = round(trade_score * 0.40 + corporate_score * 0.35 + subst_score * 0.25)
    
    # 4. Summary
    summary = company_filings['Snippet'].iloc[0] if 'Snippet' in company_filings.columns else "No specific filing snippets found."

    conn.close()
    
    return {
        "company": company_name,
        "score": composite_score,
        "breakdown": {
            "trade": round(trade_score),
            "corporate": round(corporate_score),
            "substitutability": round(subst_score)
        },
        "minerals": minerals,
        "trade_flows": trade_flows,
        "summary": summary
    }

def get_all_minerals():
    """Get list of all critical minerals tracked."""
    conn = get_db_conn()
    query = "SELECT DISTINCT Mineral FROM edgar_filing_details"
    minerals = pd.read_sql_query(query, conn)['Mineral'].tolist()
    conn.close()
    return sorted(minerals)

def get_company_minerals(company_name):
    """Get minerals for a specific company."""
    conn = get_db_conn()
    query = "SELECT DISTINCT Mineral FROM edgar_filing_details WHERE Company LIKE ?"
    minerals = pd.read_sql_query(query, conn, params=(f"%{company_name}%",))['Mineral'].tolist()
    conn.close()
    return minerals

def get_mineral_risk(mineral_name):
    """Get trade concentration and supply risk for a single mineral."""
    conn = get_db_conn()
    
    # Trade concentration
    query_trade = "SELECT * FROM trade_data WHERE Mineral LIKE ?"
    df_trade = pd.read_sql_query(query_trade, conn, params=(f"%{mineral_name}%",))
    
    hhi = compute_hhi(df_trade)
    
    # Supply risk from USGS
    query_usgs = "SELECT \"Supply Risk\" FROM usgs_minerals WHERE \"USGS Commodity Name\\n(exact CSV name)\" LIKE ?"
    df_usgs = pd.read_sql_query(query_usgs, conn, params=(f"%{mineral_name}%",))
    
    supply_risk = df_usgs['Supply Risk'].iloc[0] if not df_usgs.empty else "UNKNOWN"
    
    conn.close()
    return {
        "mineral": mineral_name,
        "hhi": round(hhi, 3),
        "concentration_score": round(_normalize_hhi(hhi * 10000), 1),
        "supply_risk": supply_risk
    }
