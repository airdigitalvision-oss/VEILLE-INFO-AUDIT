import os
import json
import re
import feedparser
import resend

RESEND_API_KEY = os.environ.get("RESEND_API_KEY")
EMAIL_DESTINATAIRE = os.environ.get("EMAIL_DESTINATAIRE")

if RESEND_API_KEY:
    resend.api_key = RESEND_API_KEY

# Flux RSS 100% fonctionnels et accessibles
RSS_FEEDS = [
    {
        "source": "Le Monde - Économie",
        "url": "https://www.lemonde.fr/economie/rss_full.xml",
        "categorie": "Fiscalité"
    },
    {
        "source": "Les Echos - Finance",
        "url": "https://www.lesechos.fr/rss/rss_finance.xml",
        "categorie": "Comptabilité"
    },
    {
        "source": "Journal Officiel (Légifrance)",
        "url": "https://www.legifrance.gouv.fr/rss/jo.xml",
        "categorie": "Audit"
    }
]

def nettoyer_html(texte):
    if not texte:
        return "Pas de description disponible."
    clean = re.sub(r'<[^>]+>', '', texte)
    clean = ' '.join(clean.split())
    return clean[:200] + "..." if len(clean) > 200 else clean

articles_traites = []

for feed_info in RSS_FEEDS:
    feed = feedparser.parse(feed_info["url"])
    
    for entry in feed.entries[:3]:
        titre = entry.get("title", "Sans titre")
        lien = entry.get("link", "#")
        raw_desc = entry.get("summary", entry.get("description", ""))
        resume = nettoyer_html(raw_desc)

        articles_traites.append({
            "source": feed_info["source"],
            "titre": titre,
            "lien": lien,
            "categorie": feed_info["categorie"],
            "resume": resume,
            "impact_pratique": f"Information importante relative au domaine : {feed_info['categorie']}."
        })

print(f"Total d'articles récupérés : {len(articles_traites)}")

# Enregistrement dans data.json
with open("data.json", "w", encoding="utf-8") as f:
    json.dump(articles_traites, f, ensure_ascii=False, indent=2)

# Envoi de l'e-mail
if articles_traites and RESEND_API_KEY and EMAIL_DESTINATAIRE:
    html_email = "<div style='font-family: sans-serif;'>"
    html_email += "<h2>Veille Fiscale & Comptable du jour</h2><hr/>"
    for art in articles_traites:
        html_email += f"""
        <div style='margin-bottom: 15px; padding: 10px; background: #f1f5f9; border-left: 4px solid #0284c7;'>
            <strong style='color: #0284c7;'>[{art['categorie']}] — {art['source']}</strong>
            <h3 style='margin: 5px 0;'><a href='{art['lien']}'>{art['titre']}</a></h3>
            <p style='font-size: 13px; color: #334155;'>{art['resume']}</p>
        </div>
        """
    html_email += "</div>"

    try:
        resend.Emails.send({
            "from": "Veille <onboarding@resend.dev>",
            "to": [EMAIL_DESTINATAIRE],
            "subject": f"Veille du jour ({len(articles_traites)} actualités)",
            "html": html_email
        })
        print("E-mail envoyé avec succès !")
    except Exception as e:
        print(f"Erreur envoi mail : {e}")
