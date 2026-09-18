import os
import json
import re
import feedparser
import resend

RESEND_API_KEY = os.environ.get("RESEND_API_KEY")
EMAIL_DESTINATAIRE = os.environ.get("EMAIL_DESTINATAIRE")

resend.api_key = RESEND_API_KEY

# 1. Flux RSS stables et vérifiés
RSS_FEEDS = [
    {
        "source": "BOFiP-Impôts",
        "url": "https://bofip.impots.gouv.fr/bofip/ext/rss/actualites.xml",
        "categorie": "Fiscalité"
    },
    {
        "source": "Bercy Infos",
        "url": "https://www.economie.gouv.fr/rss/rss-actualites",
        "categorie": "Fiscalité"
    },
    {
        "source": "ANC (Comptabilité)",
        "url": "https://www.anc.gouv.fr/cms/render/live/fr/sites/anc/home/actualites.rss",
        "categorie": "Comptabilité"
    }
]

def nettoyer_html(texte):
    """ Supprime les balises HTML et raccourcit le texte pour le résumé """
    if not texte:
        return ""
    clean = re.sub(r'<[^>]+>', '', texte)
    clean = ' '.join(clean.split())
    return clean[:250] + "..." if len(clean) > 250 else clean

articles_traites = []

# 2. Lecture et extraction déterministe
for feed_info in RSS_FEEDS:
    # Utilisation d'un User-Agent pour éviter d'être bloqué par les serveurs officiels
    feed = feedparser.parse(feed_info["url"], request_headers={'User-Agent': 'Mozilla/5.0'})
    
    for entry in feed.entries[:5]:
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
            "impact_pratique": f"Consulter l'actualité officielle sur le site {feed_info['source']} pour les modalités d'application."
        })

print(f"Total d'articles récupérés : {len(articles_traites)}")

# 3. Sauvegarde Réelle et Correction du Bug json.dump
with open("data.json", "w", encoding="utf-8") as f:
    json.dump(articles_traites, f, ensure_ascii=False, indent=2)

# 4. Envoi de l'e-mail récapitulatif
html_email = """
<div style="font-family: Arial, sans-serif; color: #1e293b; max-width: 600px; margin: auto;">
    <h2 style="color: #0f172a; border-bottom: 2px solid #3b82f6; padding-bottom: 8px;">
        📂 Veille Fiscale & Comptable du Jour
    </h2>
"""

if not articles_traites:
    html_email += "<p>Aucune nouvelle actualité disponible aujourd'hui sur les flux.</p>"
else:
    for art in articles_traites:
        html_email += f"""
        <div style="margin-bottom: 16px; padding: 12px; border-left: 4px solid #3b82f6; background-color: #f8fafc; border-radius: 4px;">
            <span style="font-size: 10px; font-weight: bold; color: #2563eb; text-transform: uppercase;">[{art['categorie']}] — {art['source']}</span>
            <h3 style="margin: 4px 0; font-size: 14px;"><a href="{art['lien']}" style="color: #0f172a; text-decoration: none;">{art['titre']}</a></h3>
            <p style="font-size: 12px; color: #475569; margin: 6px 0;">{art['resume']}</p>
        </div>
        """

html_email += "</div>"

if RESEND_API_KEY and EMAIL_DESTINATAIRE:
    try:
        resend.Emails.send({
            "from": "Veille <onboarding@resend.dev>",
            "to": [EMAIL_DESTINATAIRE],
            "subject": f"Veille du jour — {len(articles_traites)} actualités",
            "html": html_email
        })
        print("E-mail envoyé avec succès !")
    except Exception as e:
        print(f"Erreur d'envoi mail : {e}")
