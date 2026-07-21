import os
import smtplib
import urllib.parse
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from bs4 import BeautifulSoup
import requests

# Příjemci e-mailu
RECIPIENTS = ["jindra@cresco.cz", "petrjindr31@gmail.com"]

# Načtení přihlašovacích údajů z prostředí GitHub Actions
EMAIL_USER = os.environ.get("EMAIL_USER")
EMAIL_PASSWORD = os.environ.get("EMAIL_PASSWORD")

# Rozšířený dotaz: Hledá "Cresco Real Estate" OR "Yards" OR "SO-HO" za posledních 7 dní
SEARCH_QUERY = '("Cresco Real Estate" OR "Yards" OR "SO-HO") when:7d'

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        " (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
}


def fetch_google_news(query):
    """Stáhne a vyparsuje články z Google News RSS za posledních 7 dní."""
    encoded_query = urllib.parse.quote(query)
    url = f"https://news.google.com/rss/search?q={encoded_query}&hl=cs&gl=CZ&ceid=CZ:cs"

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

                # Získání zdroje (např. iDNES, E15, Hospodářské noviny)
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
        print(f"❌ Chyba při stahování zpráv z Google News: {e}")

    return articles


def build_email_body(articles):
    """Sestaví přehledný HTML e-mail s články."""
    if not articles:
        return """
        <html>
        <body style="font-family: Arial, sans-serif; color: #333;">
            <h2>📰 Monitoring médií: Cresco, Yards, SO-HO</h2>
            <p>Za posledních <b>7 dní</b> nebyly v médiích nalezeny žádné nové zmínky.</p>
        </body>
        </html>
        """

    html = f"""
    <html>
    <body style="font-family: Arial, sans-serif; color: #333;">
        <h2 style="color: #1a5276;">📰 Monitoring médií za posledních 7 dní</h2>
        <p>Sledovaná témata: <b>Cresco Real Estate, Yards, SO-HO</b></p>
        <p>Nalezeno celkem <b>{len(articles)}</b> článků / zmínek:</p>
        <table border="1" cellpadding="8" cellspacing="0" style="border-collapse: collapse; width: 100%; border-color: #ddd;">
            <tr style="background-color: #f2f2f2;">
                <th style="text-align: left;">Zdroj</th>
                <th style="text-align: left;">Název článku</th>
                <th style="text-align: left;">Datum publikace</th>
            </tr>
    """

    for art in articles:
        html += f"""
            <tr>
                <td><b>{art['source']}</b></td>
                <td><a href="{art['link']}" target="_blank" style="color: #2980b9; text-decoration: none;"><b>{art['title']}</b></a></td>
                <td style="color: #666; font-size: 0.9em;">{art['pub_date']}</td>
            </tr>
        """

    html += """
        </table>
        <br>
        <p style="font-size: 0.8em; color: #888;">Tento e-mail byl automaticky vygenerován systémem Media Monitor.</p>
    </body>
    </html>
    """
    return html


def main():
    print(
        f"🔎 Spouštím monitorování médií pro: {SEARCH_QUERY} (posledních 7 dní)..."
    )

    if not EMAIL_USER or not EMAIL_PASSWORD:
        print(
            "❌ CHYBA: Chybí přístupové údaje EMAIL_USER nebo EMAIL_PASSWORD v Secrets!"
        )
        return

    articles = fetch_google_news(SEARCH_QUERY)
    print(f"📊 Načteno článků: {len(articles)}")

    msg = MIMEMultipart()
    msg["Subject"] = (
        f"📰 MEDIA REPORT: Cresco / Yards / SO-HO ({len(articles)} zmínek za 7 dní)"
    )
    msg["From"] = f"Media Monitor <{EMAIL_USER}>"
    msg["To"] = ", ".join(RECIPIENTS)

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
