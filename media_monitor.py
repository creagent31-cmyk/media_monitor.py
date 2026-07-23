import os
import smtplib
import urllib.parse
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from bs4 import BeautifulSoup
import requests

# Příjemci e-mailu
RECIPIENTS = ["jindra@cresco.cz", "petrjindr31@gmail.com"]

EMAIL_USER = os.environ.get("EMAIL_USER")
EMAIL_PASSWORD = os.environ.get("EMAIL_PASSWORD")

# Rozšířený dotaz: České i Slovenské projekty + klíčová slova za posledních 7 dní
SEARCH_QUERY = '("Cresco Real Estate" OR "Yards" OR "SO-HO" OR "River Park" OR "Slnečnice") when:7d'

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
}


def fetch_google_news(query):
    encoded_query = urllib.parse.quote(query)
    # Odstraněno omezení gl=CZ, aby Google vracel CZ i SK výsledky
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
            <h2>📰 Monitoring médií (CZ + SK)</h2>
            <p>Za posledních <b>7 dní</b> nebyly v médiích nalezeny žádné nové zmínky.</p>
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
        <h2 style="color: #1a5276;">📰 Monitoring médií (CZ + SK)</h2>
        <p>Sledovaná témata: <b>Cresco Real Estate, Yards, SO-HO, River Park, Slnečnice</b></p>
        <p>Nalezeno celkem <b>{len(articles)}</b> článků / zmínek za posledních 7 dní:</p>
        
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
    print(f"🔎 Spouštím monitorování médií (CZ/SK) pro: {SEARCH_QUERY}...")

    if not EMAIL_USER or not EMAIL_PASSWORD:
        print("❌ CHYBA: Chybí přístupové údaje v prostředí (Secrets)!")
        return

    articles = fetch_google_news(SEARCH_QUERY)
    print(f"📊 Načteno článků: {len(articles)}")

    msg = MIMEMultipart()
    msg["Subject"] = (
        f"📰 MEDIA REPORT (CZ/SK): Cresco & Projekty ({len(articles)} zmínek)"
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
        print("✅ E-mail s přehledem médií byl úspěšně odeslán!")
    except Exception as e:
        print(f"❌ Chyba při odesílání e-mailu: {e}")


if __name__ == "__main__":
    main()
