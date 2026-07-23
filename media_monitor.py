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

# Maximální stáří článku ve dnech
MAX_AGE_DAYS = 2

# ULTRA-STRICKÝ DOTAZ: Pouze 100% jednoznačné fráze bez obecných slov
SEARCH_QUERY = (
    '("Cresco Real Estate" OR "Cresco Group" OR "SO-HO Residence" OR "SO-HO Rezidencie" OR '
    '"Slnečnice Bratislava" OR "rezidencia Slnečnice" OR "projekt Slnečnice" OR '
    '"River Park Bratislava" OR "Yards Žižkov") '
    "-site:vietnam.vn -site:prazsky.denik.cz"
)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
}


def is_recent(pub_date_str, max_days):
    """Zkontroluje, zda je datum v RSS opravdu mladší než max_days."""
    try:
        parsed_tuple = email.utils.parsedate_tz(pub_date_str)
        if parsed_tuple:
            pub_dt = datetime.fromtimestamp(
                email.utils.mktime_tz(parsed_tuple)
            )
            now = datetime.now()
            return (now - pub_dt) <= timedelta(days=max_days)
    except Exception as e:
        print(f"⚠️ Nepodařilo se přečíst datum '{pub_date_str}': {e}")
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

                # Filtrování spamu z Vietnamu
                if (
                    "vietnam.vn" in link.lower()
                    or "vietnam.vn" in source_name.lower()
                ):
                    continue

                # Kontrola stáří článku
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
        <!DOCTYPE html>
        <html>
        <head><meta charset="utf-8"></head>
        <body style="font-family: Arial, sans-serif; color: #333; line-height: 1.5;">
            <h2 style="color: #1a5276;">📰 Real Estate Media Monitoring</h2>
            <p>Za poslední <b>{MAX_AGE_DAYS} dny</b> nebyly v médiích nalezeny žádné nové zmínky k vašim projektům.</p>
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
    <!DOCTYPE html>
    <html>
    <head><meta charset="utf-8"></head>
    <body style="font-family: Arial, sans-serif; color: #333; line-height: 1.5;">
        <h2 style="color: #1a5276;">📰 Real Estate Media Monitoring</h2>
        <p>Sledované projekty: <b>Cresco Real Estate, SO-HO Residence, Slnečnice Bratislava, Yards Žižkov, River Park Bratislava</b></p>
        <p>Nalezeno celkem <b>{len(articles)}</b> nových přesných článků za poslední <b>{MAX_AGE_DAYS} dny</b>:</p>
        
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
    print(
        f"🔎 Spouštím ustra-přesný monitoring (Max stáří: {MAX_AGE_DAYS} dny)..."
    )

    if not EMAIL_USER or not EMAIL_PASSWORD:
        print("❌ CHYBA: Chybí přístupové údaje v prostředí (Secrets)!")
        return

    articles = fetch_google_news(SEARCH_QUERY)
    print(f"📊 Načteno aktuálních článků: {len(articles)}")

    msg = MIMEMultipart("alternative")
    msg["Subject"] = (
        f"📰 REAL ESTATE MONITOR: Cresco & Projekty ({len(articles)} zmínek)"
    )
    msg["From"] = f"Media Monitor <{EMAIL_USER}>"
    msg["To"] = ", ".join(RECIPIENTS)
    msg["Reply-To"] = EMAIL_USER

    body_html = build_email_body(articles)
    msg.attach(MIMEText(body_html, "html", "utf-8"))

    try:
        print("✉️ Připojuji se k SMTP a odesílám e-mail...")
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(EMAIL_USER, EMAIL_PASSWORD)
            server.sendmail(EMAIL_USER, RECIPIENTS, msg.as_string())
        print("✅ Čistý e-mail byl úspěšně odeslán!")
    except Exception as e:
        print(f"❌ Chyba při odesílání e-mailu: {e}")


if __name__ == "__main__":
    main()
