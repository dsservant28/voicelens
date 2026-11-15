"""Hand-written sentiment + theme lexicons (en, es, hi, te, Hinglish). Written independently of the generator
(policy R4 forbids importing its phrase banks). Each pipeline_run stores a hash of this file, so every prediction
traces back to the exact lexicon version. Phrases are matched longest-first; a matched span is masked so its words
are not counted again (e.g. 'solved my problem' is positive, 'problem' alone is negative).
"""

EN = {
    "pos": """worked the first time|without a manual|worked in seconds|well finished|exactly once|went through|five stars|great job|within two days|good|great|excellent|love|loved|amazing|perfect|perfectly|happy|pleased|recommend|would recommend|smooth|
        smoothly|easy|effortless|fast|quick|quickly|helpful|friendly|reliable|impressed|satisfied|works well|worth it|
        worth every|hassle free|hassle-free|on time|promised day|right on time|ahead of schedule|solved|resolved|
        solved my problem|above and beyond|best|wonderful|awesome|intuitive|clear|flawless|seamless|thank you|thanks|
        glad|delighted|superb|brilliant|painless|fair price|value for money|well made|sturdy|polite|patient|
        works perfectly|still works|no complaints|pleasant|enjoy|enjoying|convenient|transparent|accurate|instantly|
        refunded quickly|got my money back|fixed|
        fair|fairly priced|faster|much faster|correct amount|caught and reversed|honoured|honored|to the minute|figured it out|refunded me|without any argument|loads instantly|runs smoothly|same day|less than five minutes|can't complain|cannot complain|no issues|no problems|acceptable|well worth|saves me time|spot on|exactly as described""",
    "neg": """bad|never chose|missed twice|missed|feels cheap|terrible|awful|horrible|worst|hate|disappointed|disappointing|frustrated|frustrating|angry|annoyed|
        useless|broken|broke|crash|crashes|crashed|crashing|freezes|freeze|frozen|slow|sluggish|late|delayed|overdue|
        never arrived|never arrives|never came|missing|rejects|rejected|locked out|charged twice|double charge|
        double charged|overcharged|overpriced|rip-off|ripoff|confusing|unhelpful|rude|ignored|went silent|no response|
        no reply|still waiting|cracked|poor|problem|issue|issues|fails|failed|failing|error|wasted|waste|unacceptable|
        nightmare|stuck|lost|damaged|hidden fee|hidden fees|went up|without warning|impossible|suffer|regret|worse|
        not working|doesn't work|does not work|stopped working|can't|cannot|unable|on hold|hours on hold|scam|refuse|
        refused|declined|wrong|fed up|cancelled|canceled|lagging|laggy|drains|unusable|mess|ridiculous|pathetic|
        carelessly|crushed|expected much better|expected better|without fixing|nobody can explain|no one can explain|two times|taken two times|too many steps|far too|too expensive|expensive|cheaper alternatives|for no reason|keep getting|three times|never find|can never find|in the rain|would not call|wouldn't call|careless|leaking|scratched|dented|confused|complicated|hard to find|keeps logging me out|logged out""",
    "neu": """okay|ok|fine|average|normal|nothing special|as expected|works as expected|for a while now|just noting|
        no strong feelings|neither good nor bad|standard|so-so|it is what it is""",
    "negators": "not|no|never|don't|doesn't|didn't|isn't|wasn't|aren't|won't|hardly|without",
    "contrast": "but|although|though|however|yet|whereas|except",
    "intens": "very|really|so|extremely|totally|completely|absolutely|super|incredibly|truly",
    "sarcasm": """love it when|truly a premium experience|premium experience|oh great|just great|great,|fantastic,|wonderful,|brilliant,|perfect,|amazing,|love how|love that|
        thanks for nothing|ten out of ten|10/10|would suffer again|yeah right|what a joy|just what i needed|
        exactly what i needed|my favourite part|my favorite part|nailed it|so glad i paid|best part|truly a masterpiece""",
    "mixed": "mixed feelings|mixed experience|love-hate|pros and cons|good and bad",
    "ambig": """not sure|i guess|maybe|hard to say|we'll see|we will see|time will tell|undecided|can't decide|
        don't know yet|not yet sure|too early to tell""",
}

ES = {
    "pos": """me gusta|está bien|bien|genial|excelente|bueno|buena|recomiendo|lo recomiendo|me encanta|encanta|perfecto|perfecta|rápido|rápida|
        fácil|contento|contenta|feliz|satisfecho|satisfecha|maravilla|gracias|increíble|estupendo|útil|amable""",
    "neg": """malo|mala|terrible|pésimo|pésima|horrible|deja mucho que desear|decepcionado|decepcionada|decepción|lento|
        lenta|tarde|retraso|problema|problemas|caro|cara|molesto|molesta|frustrado|frustrada|fatal|desastre|
        no funciona|nunca llegó|roto|rota|error|inaceptable|peor""",
    "neu": "normal|nada especial|como se espera|funciona como se espera|regular|aceptable|ni bueno ni malo|correcto",
    "negators": "no|nunca|ni|tampoco|sin",
    "contrast": "pero|aunque|sin embargo|mientras que",
    "intens": "muy|super|bastante|realmente|totalmente|demasiado",
    "sarcasm": "qué maravilla,|genial,|perfecto,|qué bien,",
    "mixed": "sentimientos encontrados",
    "ambig": "no estoy seguro|no estoy segura|quizás|tal vez|ya veremos|no sé todavía",
}

HI = {   # Devanagari; substring matching (no word boundaries)
    "pos": "अच्छा|अच्छी|अच्छे|बढ़िया|खुश|शानदार|बेहतरीन|पसंद|धन्यवाद|आसान|संतुष्ट|शुक्रिया|उत्कृष्ट|तेज़",
    "neg": "बेकार|खराब|ख़राब|परेशान|निराश|बुरा|बुरी|घटिया|धीमा|देरी|शिकायत|गुस्सा|नाराज़|समस्या|दिक्कत|बकवास|बेहद बुरा",
    "neu": "सामान्य|ठीक-ठाक|ठीक ठाक|कुछ खास नहीं|औसत|ठीक है",
    "negators": "नहीं|न|मत",
    "contrast": "लेकिन|पर|मगर|परंतु|किंतु",
    "intens": "बहुत|बेहद|काफी|एकदम",
    "sarcasm": "वाह,|क्या बात है,",
    "mixed": "",
    "ambig": "पता नहीं|शायद|कह नहीं सकते",
}

TE = {   # Telugu; substring matching
    "pos": "బాగుంది|బాగా|సంతోషం|సంతోషంగా|అద్భుతం|అద్భుతంగా|నచ్చింది|సులభం|ధన్యవాదాలు|మంచి|సూపర్|ఆనందం",
    "neg": "బాగాలేదు|బాగోలేదు|ఇబ్బంది|ఇబ్బందిగా|నిరాశ|ఘోరం|ఘోరంగా|చెత్త|దారుణం|దారుణంగా|కోపం|సమస్య|ఆలస్యం|నెమ్మది|వేస్ట్",
    "neu": "సాధారణం|సాధారణంగా|పర్వాలేదు|ప్రత్యేకంగా చెప్పడానికి ఏమీ లేదు|ఓకే|మామూలుగా|మామూలు",
    "negators": "లేదు|కాదు",
    "contrast": "కానీ|అయితే",
    "intens": "చాలా|బాగా|మరీ|అస్సలు",
    "sarcasm": "వాహ్,",
    "mixed": "",
    "ambig": "తెలియదు|ఏమో|చూడాలి",
}

HINGLISH = {   # Latin-script Hindi; English lexicon is applied as well
    "pos": "achha|accha|acha|achchha|badhiya|mast|khush|zabardast|shandaar|pasand|bahut badhiya|dhanyavaad|shukriya",
    "neg": "bekaar|bekar|third class|ghatiya|bura|buri|bakwas|pareshan|kharab|faltu|gussa|bura haal|dikkat|jhanjhat",
    "neu": "theek-thaak|theek thaak|thik thak|thik-thak|chalta hai|kuch khaas nahi|theek hai|normal",
    "negators": "nahi|nahin|mat|na",
    "contrast": "par|lekin|magar|but",
    "intens": "bahut|ekdum|bilkul|kaafi|totally|ekdam",
    "sarcasm": "wah,|waah,|kya baat hai,",
    "mixed": "",
    "ambig": "pata nahi|shayad|dekhte hain",
}

LEXICONS = {"en": [EN], "es": [ES], "hi": [HI], "te": [TE], "hi-Latn": [HINGLISH, EN]}

# Contrast markers used to split clauses for themes (one theme per clause), all languages.
CLAUSE_SPLIT = "but|although|though|however|yet|whereas|pero|aunque|sin embargo|lekin|magar|लेकिन|मगर|परंतु|కానీ|అయితే"

# Language detection markers (Latin script); Indic scripts are detected by Unicode range.
ES_MARKERS = "el|la|los|las|de|del|es|muy|lo|que|con|por|para|una|un|pero|sobre|mucho"
HINGLISH_MARKERS = "hai|hoon|hu|ka|ki|ke|se|bahut|yaar|ekdum|bilkul|nahi|achha|par|kya|mera|mujhe|bhi"

# Theme cue terms by theme CODE (theme ids are resolved from raw.theme at runtime; DB keywords are added too).
THEMES = {
    "delivery": """delivery|delivered|courier|package|parcel|shipment|shipping|arrived|driver|entrega|envío|paquete|
        डिलीवरी|पार्सल|డెలివరీ|పార్సెల్""",
    "late_delivery": """late|same day|same-day|express slot|on time|to the minute|delivery slot|arrived early|overdue|delayed|missed slot|delivery time|days late|never arrived|still not delivered|
        tiempo de entrega|retraso|डिलीवरी समय|देरी|డెలివరీ సమయం|ఆలస్యం""",
    "billing": """billing|billed|never chose|charged for|invoice|bill|statement|payment|charges|charge|charged|pending charge|card|factura|cobro|pago|
        facturación|बिलिंग|पेमेंट|బిల్లింగ్|బిల్లు|పేమెంట్""",
    "double_charge": """charged twice|correct amount|exactly once|went through|two times|taken twice|duplicate|charged again|double charge|double charged|duplicate charge|two charges|twice for|cobro doble|
        cobrado dos veces|दो बार|डबल चार्ज|రెండుసార్లు|డబుల్ ఛార్జ్""",
    "app_performance": """app|crash|crashes|freeze|freezes|slow|loading|load|lag|laggy|battery|update|version|
        aplicación|ऐप|యాప్""",
    "customer_support": """support|agents|explained the issue|agent|chat|hold|ticket|helpline|call centre|call center|representative|soporte|
        atención al cliente|सपोर्ट|कस्टमर सपोर्ट|సపోర్ట్|కస్టమర్ సపోర్ట్""",
    "product_quality": """quality|item|feels cheap|colours|colors|well finished|finish|broken|cracked|materials|build|durable|sturdy|works perfectly|daily use|defective|stopped working|durability|
        calidad|क्वालिटी|गुणवत्ता|క్వాలిటీ|నాణ్యత""",
    "pricing": "price|cheaper|alternatives|too expensive|worth the money|subscription fee|pricing|expensive|value|discount|cost|plan price|precio|कीमत|दाम|ధర",
    "usability": """interface|setting|without a manual|figured it out|too many steps|simple tasks|find the settings|intuitive|menu|settings|easy to use|confusing|navigation|layout|design|button|interfaz|उपयोग|
        इंटरफेस|इंटरफ़ेस|ఇంటర్‌ఫేస్|ఇంటర్ఫేస్""",
    "account_login": """login|logging in|logged in|fingerprint|password reset|log in|password|locked|verification|account|sign in|otp|two-factor|contraseña|
        inicio de sesión|cuenta|लॉगिन|पासवर्ड|లాగిన్|పాస్‌వర్డ్""",
    "refunds": "refund|refunds|refunded|returns|return|money back|reimburse|reembolso|devolución|रिफंड|पैसे वापस|రీఫండ్",
    "onboarding": """setup|set up|activation|getting started|pairing|onboarding|instructions|setup guide|configuración|
        instalación|सेटअप|సెటప్""",
}


def terms(s: str) -> list[str]:
    """'a|b|\\n c' -> ['a', 'b', 'c'] (lower-cased, de-duplicated, longest first)."""
    out = {t.strip().lower() for t in s.replace("\n", "").split("|") if t.strip()}
    return sorted(out, key=lambda t: (-len(t), t))
