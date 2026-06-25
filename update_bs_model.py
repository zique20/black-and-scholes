import yfinance as yf
import openpyxl
import os

# Chiedi ticker e percorso file
ticker = input("Inserisci il ticker (es. ^GSPC per S&P500, AAPL per Apple): ").strip()
if not ticker:
    ticker = "^GSPC"

excel_file = input("Inserisci il percorso completo del file Excel: ").strip()
if not excel_file:
    excel_file = "/Users/lvgh/Desktop/black and scholes opzioni /BS model spx.xlsx"
print(f"\nScaricando dati per {ticker}...")

# Scarica 27 settimane di dati
stock = yf.Ticker(ticker)
df = stock.history(period="7mo", interval="1wk")
df = df.tail(27)

if df.empty:
    print("❌ Ticker non trovato o dati non disponibili")
    exit()

# Apri Excel
try:
    wb = openpyxl.load_workbook(excel_file)
except FileNotFoundError:
    print(f"❌ File Excel non trovato: {excel_file}")
    exit()

# Inserisci prezzi in Stock Prices
ws = wb["Stock Prices"]
closes = df["Close"].tolist()
for i, price in enumerate(closes):
    ws[f"B{i+4}"] = round(price, 2)

# Aggiorna prezzo corrente in BS calc
bs_sheet = wb["BS calc"]
bs_sheet["B4"] = round(closes[-1], 2)

wb.save(excel_file)
print(f"\n✅ Aggiornati {len(closes)} prezzi settimanali")
print(f"✅ Prezzo corrente {ticker}: {round(closes[-1], 2)}")
print(f"✅ File salvato: {excel_file}")