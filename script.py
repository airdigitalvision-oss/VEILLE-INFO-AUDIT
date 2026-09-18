import os
import json
import re
import urllib.request
import feedparser
from datetime import datetime
import resend

RESEND_API_KEY = os.environ.get("RESEND_API_KEY")
EMAIL_DESTINATAIRE = os.environ.get("EMAIL_DESTINATAIRE")

if RESEND_API_KEY:
    resend.api_key = RESEND_API_KEY

# Sources officielles et spécialisées stables
RSS_FEEDS = [
    {
        "source": "Légifrance - Droit Fiscal",
        "url": "https://www.legifrance.gouv.fr/",
        "categorie": "Fiscalité"
    },
    {
        "source": "Bercy Infos Entreprises",
        "url": "https://www.economie.gouv.fr/particuliers",
        "categorie": "Fiscalité"
    },
    {
        "source": "Haute Autorité de l'Audit (H2A)",
        "url": "https://h2a-france.org",
        "categorie": "Audit"
    },
    {
        "source": "CNCC / Audit",
        "url": "https://www.cncc.fr",
        "categorie": "Audit"
    },
    {
        "source": "ANC (Comptabilité)",
        "url": "https://www.anc.gouv.fr/",
        "categorie": "Comptabilité"
    }
]

def nettoyer_html(texte):
    if not texte:
        return "Consulter la publication officielle pour le détail."
    clean = re.sub(r'<[^>]+>', '', texte)
    clean = ' '.join(clean.split())
    return clean[:220] + "..." if len(clean) > 220 else clean

def format_date(entry):
    # Extraction de la date de publication
    published = entry.get("published_parsed") or entry.get("updated_parsed")
    if published:
        return f"{published.tm_mday:02d}/{published.tm_mon:02d}/{published.tm_year}"
    return datetime.now().strftime("%d/%m/%Y")

articles_traites = []
headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0'}

for feed_info in RSS_FEEDS:
    try:
        req = urllib.request.Request(feed_info["url"], headers=headers)
        with urllib.request.urlopen(req, timeout=8) as response:
            xml_data = response.read()
            feed = feedparser.parse(xml_data)

            for entry in feed.entries[:4]:
                titre = entry.get("title", "Publication officielle")
                lien = entry.get("link", "#")
                raw_desc = entry.get("summary", entry.get("description", ""))
                date_pub = format_date(entry)

                articles_traites.append({
                    "source": feed_info["source"],
                    "titre": titre,
                    "lien": lien,
                    "categorie": feed_info["categorie"],
                    "date": date_pub,
                    "resume": nettoyer_html(raw_desc),
                    "impact_pratique": f"Publication du {date_pub} — À intégrer dans la veille réglementaire {feed_info['categorie']}."
                })
    except Exception as e:
        print(f"Erreur avec le flux {feed_info['source']}: {e}")

# Fallback si le flux BOFiP/Fiscalité principal est muet
fiscalite_presente = any(a["categorie"] == "Fiscalité" for a in articles_traites)
if not fiscalite_presente:
    date_jour = datetime.now().strftime("%d/%m/%Y")
    articles_traites.append({
        "source": "BOFiP-Impôts (DGFIP)",
        "titre": "Actualités réglementaires et commentaires de doctrine fiscale",
        "lien": "https://bofip.impots.gouv.fr/",
        "categorie": "Fiscalité",
        "date": date_jour,
        "resume": "Consultez les édictions et rescrits fiscaux récents publiés au Bulletin Officiel des Finances Publiques.",
        "impact_pratique": f"Publication du {date_jour} — À intégrer dans la veille réglementaire Fiscalité."
    })

print(f"Total d'articles enregistrés : {len(articles_traites)}")

with open("data.json", "w", encoding="utf-8") as f:
    json.dump(articles_traites, f, ensure_ascii=False, indent=2)

# Envoi de l'e-mail
if articles_traites and RESEND_API_KEY and EMAIL_DESTINATAIRE:
    html_email = "<div style='font-family: sans-serif; color: #0f172a;'>"
    html_email += f"<h2>Veille Fiscale, Comptable & Audit du {datetime.now().strftime('%d/%m/%Y')}</h2><hr/>"
    for art in articles_traites:
        html_email += f"""
        <div style='margin-bottom: 12px; padding: 10px; background: #f8fafc; border-left: 4px solid #2563eb;'>
            <small style='color: #64748b;'>{art['date']} — <strong>[{art['categorie']}]</strong> {art['source']}</small>
            <h3 style='margin: 4px 0;'><a href='{art['lien']}' style='color: #1e293b;'>{art['titre']}</a></h3>
            <p style='font-size: 12px; color: #475569;'>{art['resume']}</p>
        </div>
        """
    html_email += "</div>"

    try:
        resend.Emails.send({
            "from": "Veille Officielle <onboarding@resend.dev>",
            "to": [EMAIL_DESTINATAIRE],
            "subject": f"Veille Hebdo & Quotidienne — {len(articles_traites)} actualités",
            "html": html_email
        })
        print("E-mail envoyé avec succès !")
    except Exception as e:
        print(f"Erreur envoi mail : {e}")
