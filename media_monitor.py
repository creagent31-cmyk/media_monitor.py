import io
import os
import smtplib
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from bs4 import BeautifulSoup
import pandas as pd
import requests

EMAIL_USER = os.environ.get("EMAIL_USER")
EMAIL_PASSWORD = os.environ.get("EMAIL_PASSWORD")
RECIPIENTS = ["jindra@cresco.cz", "petrjindr31@gmail.com"]

QUERY = '"Cresco Real Estate"'


def search_mentions():
    mentions = []

    sources = {
        "Česko (Google News CZ)": f"https://news.google.com/rss/search?q={QUERY}&hl=cs&gl=CZ&ceid=CZ:cs",
        "Slovensko (Google News SK)": f"https://news.google.com/rss/search?q={QUERY}&hl=sk&gl=SK&ceid=SK:sk",
    }

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            " (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
    }

    for region, url in sources.items():
        try:
            r = requests.get(url, headers=headers, timeout=15)
            if r.status_code == 200:
                soup = BeautifulSoup(r.text, "xml")
                items = soup.find_all("item")

                for item in items:
                    title = item.title.text if item.title else "Bez názvu"
                    link = item.link.text if item.link else ""
                    pub_date = item.pubDate.text if item.pubDate else ""
                    source_name = item.source.text if item.source else region

                    mentions.append(
                        {
                            "Region/Zdroj": region,
                            "Médiu/Zdroj": source_name,
                            "Titulok článku": title,
                            "Dátum publikácie": pub_date,
                            "Odkaz": link,
                        }
                    )
            else:
                print(
                    f"⚠️ Chyba HTTP {r.status_code} při stahování pro {region}"
                )
        except Exception as e:
            print(f"❌ Chyba pri sťahovaní {region}: {e}")

    return mentions


def main():
    print("🔍 Spúšťam monitorovanie zmienok o Cresco Real Estate...")

    if not EMAIL_USER or not EMAIL_PASSWORD:
        print(
            "❌ CHYBA: Chybí přístupové údaje EMAIL_USER nebo EMAIL_PASSWORD v proměnných prostředí!"
        )
        return

    mentions = search_mentions()
    print(f"ℹ️ Nalezeno celkem {len(mentions)} zmínek.")

    # Vytvorenie Excelu
    excel_buffer = io.BytesIO()
    df = pd.DataFrame(mentions)

    with pd.ExcelWriter(excel_buffer, engine="openpyxl") as writer:
        if not df.empty:
            df.to_excel(
                writer, sheet_name="Zmienky Cresco Real Estate", index=False
            )
        else:
            pd.DataFrame(
                [
                    {
                        "Info": (
                            "Za posledný týždeň neboli nájdené žiadne nové"
                            " články."
                        )
                    }
                ]
            ).to_excel(writer, sheet_name="Zmienky", index=False)

    excel_buffer.seek(0)

    # Sestavenie e-mailu
    msg = MIMEMultipart()
    msg["Subject"] = (
        f"📰 Media Monitor: Zmienky Cresco Real Estate ({len(mentions)} nájdených)"
    )
    msg["From"] = f"Media Monitor <{EMAIL_USER}>"
    msg["To"] = ", ".join(RECIPIENTS)

    rows_html = ""
    for m in mentions[:10]:  # Zobrazíme top 10 článkov priamo v maili
        rows_html += f"<tr><td style='padding:8px;border:1px solid #ddd;'>{m['Médiu/Zdroj']}</td><td style='padding:8px;border:1px solid #ddd;'><a href='{m['Odkaz']}'>{m['Titulok článku']}</a></td><td style='padding:8px;border:1px solid #ddd;'>{m['Dátum publikácie']}</td></tr>"

    table_content = (
        "<table style='border-collapse:collapse;width:100%;'><tr"
        " style='background:#f2f2f2;'><th>Zdroj</th><th>Názov"
        f" článku</th><th>Dátum</th></tr>{rows_html}</table>"
        if mentions
        else "<p><b>Za posledný týždeň neboli nájdené žiadne nové články.</b></p>"
    )

    body = f"""
    <html>
    <body style="font-family: Arial, sans-serif;">
        <h2>📰 Týždenný prehľad zmienok: Cresco Real Estate</h2>
        <p>Ahoj, tu je prehľad článkov a zmienok v českých a slovenských médiách za posledné obdobie:</p>
        
        {table_content}
        
        <p>Kompletný zoznam nájdeš v priloženom Exceli.</p>
    </body>
    </html>
    """
    msg.attach(MIMEText(body, "html"))

    # Priloženie Excelu
    attachment = MIMEApplication(
        excel_buffer.read(), Name="Cresco_Media_Monitor.xlsx"
    )
    attachment["Content-Disposition"] = (
        'attachment; filename="Cresco_Media_Monitor.xlsx"'
    )
    msg.attach(attachment)

    # Odeslání přes Gmail SMTP
    try:
        print("✉️ Připojuji se k SMTP serveru Gmailu...")
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(EMAIL_USER, EMAIL_PASSWORD)
            server.sendmail(EMAIL_USER, RECIPIENTS, msg.as_string())
        print("✅ E-mail s monitorom médií bol úspešne odoslaný!")
    except Exception as e:
        print(f"❌ Chyba pri odesílaní e-mailu: {e}")


if __name__ == "__main__":
    main()
