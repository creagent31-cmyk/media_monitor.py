from datetime import datetime, timedelta
import email.utils
import os
import smtplib
import urllib.parse
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from bs4 import BeautifulSoup
import requests

# Příjemci e-mailu
RECIPIENTS = ["jindra@cresco.cz", "petrjindr31@gmail.com"]

EMAIL_USER = os.environ.get("EMAIL_USER")
EMAIL_PASSWORD = os.environ.get("EMAIL_PASSWORD")

# Maximální stáří článku ve dnech (např. 2 dny pro denní monitoring)
MAX_AGE_DAYS = 2

SEARCH_QUERY = (
    "("
    '"Cresco Real Estate" OR "Cresco Group" OR "SO-HO Residence" OR "SO-HO Rezidencie" OR '
    '"River Park" OR "Slnečnice Bratislava" OR "rezidencia Slnečnice" OR "projekt Slnečnice" OR '
    '"Yards Praha" OR "Yards Cresco"'
    ") "
    "-site:vietnam.vn -site:prazsky.denik.cz "
    "-policie -nehoda -požár -krimi -recept -olej -semínka"
)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
}


def is_recent(pub_date_str, max_days):
    """Zkontroluje, zda je datum v RSS mladší než max_days."""
    try:
        # Příklad formátu z RSS: 'Tue, 21 Jul 2026 14:30:00 GMT'
        parsed_tuple = email.utils.parsedate_tz(pub_date_str)
        if parsed_tuple:
            pub_dt = datetime.fromtimestamp(
                email.utils.mktime_tz(parsed_tuple)
            )
            now = datetime.now()
            # Pokud je článek mladší než určeno v MAX_AGE_DAYS
            return (now - pub_dt) <= timedelta(days=max_days)
    except Exception as e:
        print(f"⚠️ Nepodařilo se přečíst datum '{pub_date_str}': {e}")
    # Pokud datum nelze přečíst, pro jistotu článek ponecháme
    return True


def fetch_google_news(query):
    encoded_query = urllib.parse.quote(query)
    url = f"https://news.google.com/rss/search?q={encoded_query}&hl=cs&ceid=CZ:cs"
    articles = []

    try:
        response = requests.get(url, headers=HEADERS, timeout=15)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, "xml")
            items = soup.find_all("item")

            for item in items:
                title = item.title.text if item.title else "Bez názvu"
                link = item.link.text if item.link else ""
                pub_date = (
                    item.pubDate.text if item.pubDate else "Neznámé datum"
                )

                source_tag = item.find("source")
                source_name = (
                    source_tag.text if source_tag else "Neznámý zdroj"
                )

                # 1. Filtrování spamu
                if (
                    "vietnam.vn" in link.lower()
                    or "vietnam.vn" in source_name.lower()
                ):
                    continue

                # 2. Kontrola stáří článku v Pythonu
                if not is_recent(pub_date, MAX_AGE_DAYS):
                    print(
                        f"⏰ Přeskočen starý článek ({pub_date}): {title[:40]}..."
                    )
                    continue

                articles.append(
                    {
                        "title": title,
                        "link": link,
                        "pub_date": pub_date,
                        "source": source_name,
                    }
                )
    except Exception as e:
        print(f"❌ Chyba při stahování zpráv: {e}")

    return articles


def build_email_body(articles):
    now_str = datetime.now().strftime("%d.%m.%Y v %H:%M")

    if not articles:
        return f"""
        <html>
        <body style="font-family: Arial, sans-serif; color: #333;">
            <h2 style="color: #1a5276;">📰 Real Estate Media Monitoring (CZ + SK)</h2>
            <p>Za poslední <b>{MAX_AGE_DAYS} dny</b> nebyly v médiích nalezeny žádné nové zmínky k projektům Cresco Real Estate.</p>
            <p style="font-size: 0.8em; color: #888;">Vygenerováno: {now_str}</p>
        </body>
        </html>
        """

    rows = "".join(
        f"<tr>"
        f"<td><b>{a['source']}</b></td>"
        f"<td><a href='{a['link']}' target='_blank' style='color: #1a5276; text-decoration: none;'><b>{a['title']}</b></a></td>"
        f"<td style='color: #666; font-size: 0.9em;'>{a['pub_date']}</td>"
        f"</tr>"
        for a in articles
    )

    return f"""
    <html>
    <body style="font-family: Arial, sans-serif; color: #333; line-height: 1.5;">
        <h2 style="color: #1a5276;">📰 Real Estate Media Monitoring (CZ + SK)</h2>
        <p>Sledované projekty: <b>Cresco Real Estate, SO-HO Residence, Slnečnice, Yards, River Park</b></p>
        <p>Nalezeno celkem <b>{len(articles)}</b> nových článků za poslední <b>{MAX_AGE_DAYS} dny</b>:</p>
        
        <table border="1" cellpadding="10" cellspacing="0" style="border-collapse: collapse; width: 100%; border-color: #e0e0e0;">
            <tr style="background-color: #f8f9fa;">
                <th style="text-align: left; width: 20%;">Zdroj</th>
                <th style="text-align: left; width: 55%;">Název článku</th>
                <th style="text-align: left; width: 25%;">Datum publikace</th>
            </tr>
            {rows}
        </table>
        <br>
        <hr style="border: 0; border-top: 1px solid #eee;">
        <p style="font-size: 0.8em; color: #888;">Automatický report vygenerován: {now_str}</p>
    </body>
    </html>
    """


def main():
    print(f"🔎 Spouštím Real Estate monitoring (Max stáří: {MAX_AGE_DAYS} dny)...")

    if not EMAIL_USER or not EMAIL_PASSWORD:
        print("❌ CHYBA: Chybí přístupové údaje v prostředí (Secrets)!")
        return

    articles = fetch_google_news(SEARCH_QUERY)
    print(f"📊 Načteno aktuálních článků: {len(articles)}")

    msg = MIMEMultipart()
    msg["Subject"] = (
        f"📰 REAL ESTATE MONITOR: Cresco & Projekty ({len(articles)} nových)"
    )
    msg["From"] = f"Media Monitor <{EMAIL_USER}>"
    msg["To"] = ", ".join(RECIPIENTS)
    msg["Reply-To"] = EMAIL_USER

    body_html = build_email_body(articles)
    msg.attach(MIMEText(body_html, "html"))

    try:
        print("✉️ Připojuji se k SMTP a odesílám e-mail...")
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(EMAIL_USER, EMAIL_PASSWORD)
            server.sendmail(EMAIL_USER, RECIPIENTS, msg.as_string())
        print("✅ E-mail byl úspěšně odeslán!")
    except Exception as e:
        print(f"❌ Chyba při odesílání e-mailu: {e}")


if __name__ == "__main__":
    main()
