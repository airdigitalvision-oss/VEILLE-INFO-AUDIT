import os
import json
import feedparser
import resend
import google.generativeai as genai

# Configuration de l'API Gemini
GEMINI_KEY = os.environ.get("GEMINI_API_KEY")
genai.configure(api_key=GEMINI_KEY)
model = genai.GenerativeModel("gemini-2.5-flash")

# Configuration de Resend
RESEND_KEY = os.environ.get("RESEND_API_KEY")
EMAIL_TO = os.environ.get("EMAIL_DESTINATAIRE")
if RESEND_KEY:
    resend.api_key = RESEND_KEY

# Sources RSS officielles
RSS_FEEDS = {
    "BOFiP": "https://bofip.impots.gouv.fr/bofip/ext-rss.xml",
    "Bercy Infos": "https://www.economie.gouv.fr/rss/rss-bercy-infos",
    "Journal Officiel": "https://www.legifrance.gouv.fr/rss/jo"
}

def charger_nouvelles():
    articles = []
    for source, url in RSS_FEEDS.items():
        feed = feedparser.parse(url)
        for entry in feed.entries[:3]:
            articles.append({
                "source": source,
                "titre": entry.title,
                "lien": entry.link,
                "resume_brut": entry.get("summary", "")
            })
    return articles

def analyser_avec_gemini(articles):
    if not articles:
        return []
    
    prompt = f"""
    Tu es un expert-comptable et fiscaliste senior.
    Analyse les actualités suivantes et génère un résumé structuré au format JSON pur (sans balises markdown).
    
    Articles :
    {json.dumps(articles, ensure_ascii=False)}

    Format de réponse attendu (liste d'objets JSON) :
    [
      {{
        "source": "Nom de la source",
        "titre": "Titre explicite",
        "categorie": "Fiscalité / Comptabilité / Audit / Droit",
        "mots_cles": ["TVA", "IS", etc.],
        "resume": "Résumé clair en 2 phrases",
        "impact_pratique": "Ce que ça change pour le cabinet ou le client",
        "lien": "Lien officiel"
      }}
    ]
    """
    
    response = model.generate_content(prompt)
    texte_clean = response.text.replace("```json", "").replace("```", "").strip()
    try:
        return json.loads(texte_clean)
    except:
        return articles

def envoyer_email(synthese):
    if not RESEND_KEY or not EMAIL_TO:
        print("Clé Resend ou Email manquant. Saut de l'envoi d'e-mail.")
        return

    # Construction du contenu HTML de l'e-mail
    html_content = "<h2>Voici votre Veille Fiscale & Comptable du jour</h2><hr>"
    for item in synthese:
        html_content += f"""
        <div style='margin-bottom: 20px; padding: 10px; border-left: 4px solid #0055ff;'>
            <span style='background: #e1ecf4; color: #00529b; padding: 3px 8px; border-radius: 3px; font-size: 12px;'>{item.get('categorie', 'Général')}</span>
            <h3 style='margin: 5px 0;'><a href='{item.get('lien', '#')}'>{item.get('titre')}</a></h3>
            <p><strong>Source :</strong> {item.get('source')}</p>
            <p><strong>Résumé :</strong> {item.get('resume')}</p>
            <p><strong>Impact pratique :</strong> {item.get('impact_pratique')}</p>
        </div>
        """

    try:
        resend.Emails.send({
            "from": "Veille <onboarding@resend.dev>",
            "to": [EMAIL_TO],
            "subject": "📊 Veille Fiscale & Comptable du Jour",
            "html": html_content
        })
        print("E-mail envoyé avec succès !")
    except Exception as e:
        print(f"Erreur lors de l'envoi de l'e-mail : {e}")

def main():
    brut = charger_nouvelles()
    synthese = analyser_avec_gemini(brut)
    
    # Sauvegarde des résultats
    with open("data.json", "w", encoding="utf-8") as f:
        json.dump(synthese, f, ensure_ascii=False, indent=2)
    
    # Envoi de la veille par e-mail
    envoyer_email(synthese)
    print("Mise à jour et envoi terminés !")

if __name__ == "__main__":
    main()
