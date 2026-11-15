"""Template banks. The TEMPLATE decides the labels (sentiment, themes, style) - documented rule, never random.

A text = frame (decides sentiment + style) x theme phrase/noun (decides theme) x product slot.
template_id identifies the frame, e.g. EN-SARCASTIC-NEG-02, so evaluation can slice errors by template/style.
"""
from __future__ import annotations

import numpy as np

# ---------------------------------------------------------------- English theme phrase banks
# code: (noun, positive clauses, negative clauses, neutral clauses)
EN = {
    "delivery": ("delivery",
        ["the delivery was quick and the box arrived intact", "delivery came right on the promised day",
         "the courier was polite and careful"],
        ["the delivery was handled carelessly and the box was crushed", "nobody told me where my package was",
         "the courier left the parcel out in the rain"],
        ["the delivery came on Tuesday", "the package was handed to the building reception"]),
    "late_delivery": ("delivery time",
        ["it arrived a full day earlier than promised", "the express slot was honoured to the minute",
         "same-day delivery actually arrived the same day"],
        ["my order arrived three days late", "the delivery slot was missed twice in a row",
         "the package is a week overdue with no update"],
        ["the estimated delivery date moved by one day", "delivery took the usual five days"]),
    "billing": ("billing",
        ["the invoice was clear and easy to understand", "billing is transparent with no hidden fees",
         "the monthly statement is simple and accurate"],
        ["the invoice was wrong again this month", "I was billed for a plan I never chose",
         "billing added fees nobody explained"],
        ["the bill is generated on the first of each month", "I receive the invoice by email"]),
    "double_charge": ("payment",
        ["a duplicate charge was caught and reversed before I even noticed", "the payment went through exactly once",
         "my card was charged the correct amount"],
        ["I was charged twice for the same order", "my card shows a double charge for one subscription",
         "the payment was taken two times and nobody can explain why"],
        ["two pending charges appeared and one later dropped off", "the payment shows as processing on my statement"]),
    "app_performance": ("app",
        ["the app loads instantly and never freezes", "the latest update made everything much faster",
         "the app runs smoothly even on my old phone"],
        ["the app crashes every time I open it", "screens take forever to load",
         "the app freezes in the middle of checkout"],
        ["the app was updated to version 5 last week", "the app takes a few seconds to start"]),
    "customer_support": ("support team",
        ["the support agent solved my problem in one call", "support replied within minutes and was very kind",
         "the chat agent went above and beyond"],
        ["support kept me on hold for an hour", "the agent closed my ticket without fixing anything",
         "I explained the issue three times to three different agents"],
        ["I contacted support through chat", "support asked for my order number"]),
    "product_quality": ("build quality",
        ["the build quality feels premium and solid", "it still works perfectly after months of daily use",
         "the materials are sturdy and well finished"],
        ["it stopped working after two weeks", "the casing cracked on the first day",
         "the item arrived broken and feels cheap"],
        ["the product comes in two colours", "it is about the size of a paperback book"]),
    "pricing": ("price",
        ["the price is very fair for what you get", "it is great value for money",
         "the discount made it a real bargain"],
        ["it is far too expensive for what it does", "the price went up again without warning",
         "cheaper alternatives do exactly the same thing"],
        ["the price is listed per month", "there are three price tiers"]),
    "usability": ("interface",
        ["the interface is clean and easy to use", "I found every setting without a manual",
         "even my parents figured it out quickly"],
        ["the menus are confusing and badly organised", "simple tasks take far too many steps",
         "I can never find the settings I need"],
        ["the main menu has five tabs", "the settings are under the profile icon"]),
    "account_login": ("login",
        ["logging in with my fingerprint is effortless", "the password reset worked in seconds",
         "two-factor login is quick and reassuring"],
        ["I keep getting locked out of my account", "the login page rejects my correct password",
         "the verification code never arrives"],
        ["the login requires a one-time code", "I logged in from a new device"]),
    "refunds": ("refund",
        ["my refund arrived within two days", "the return and refund were completely hassle free",
         "they refunded me without any argument"],
        ["I am still waiting for my refund after a month", "the refund was rejected for no reason",
         "they promised a refund and then went silent"],
        ["the refund goes back to the original payment method", "refunds are processed within ten working days"]),
    "onboarding": ("setup",
        ["setup took less than five minutes", "the welcome guide made getting started easy",
         "pairing the device worked the first time"],
        ["the setup failed three times before it worked", "the onboarding instructions are missing steps",
         "activation got stuck on the first screen"],
        ["setup asks for your email and a password", "the setup guide has six steps"]),
}

# ---------------------------------------------------------------- English frames: (style, sentiment) -> frames
# slots: {p}/{n}/{u} = positive/negative/neutral clause of the theme, {noun}, {product};
# mixed: {a} = positive clause of theme A, {b} = negative clause of theme B. Upper-case slot = capitalised.
EN_FRAMES = {
    ("plain", "positive"): ["{P}. Really happy with {product}.", "Honestly, {p}. Great job.",
                            "{P}, would recommend {product}.", "Five stars: {p}."],
    ("plain", "negative"): ["{N}. Very disappointed with {product}.", "{N}. This is unacceptable.",
                            "Really frustrated: {n}.", "{N}. I expected much better from {product}."],
    ("plain", "neutral"): ["{U}.", "Using {product} for a while now. {U}.", "Just noting that {u}."],
    ("mixed", "mixed"): ["{A}, but {b}.", "{B}, although {a}.", "Mixed feelings about {product}: {a}, yet {b}."],
    ("sarcastic", "negative"): ["Oh great, {n}. Just perfect.", "Wow, {n}. Exactly what I wanted from {product}.",
                                "Love it when {n}. Truly a premium experience.",
                                "Fantastic, {n}. Ten out of ten, would suffer again."],
    ("negation", "positive"): ["The {noun} is not bad at all, to be honest.",
                               "Can't complain about the {noun}, no issues whatsoever."],
    ("negation", "negative"): ["The {noun} is not good, not even close.",
                               "I would not call the {noun} acceptable."],
    ("ambiguous", "neutral"): ["The {noun} is... well, it's the {noun}.", "{Noun}? It is what it is.",
                               "Not sure how I feel about the {noun} yet.",
                               "The {noun} could be better, could be worse."],
}
# English style mix per sentiment (documented rule; style is chosen before the frame).
EN_STYLE_MIX = {
    "positive": (("plain", 0.80), ("negation", 0.20)),
    "negative": (("plain", 0.70), ("sarcastic", 0.18), ("negation", 0.12)),
    "neutral": (("plain", 0.75), ("ambiguous", 0.25)),
    "mixed": (("mixed", 1.0),),
}

# ---------------------------------------------------------------- multilingual: 12 frames + 12 nouns per language
ML_NOUNS = {
    "es": {"delivery": "la entrega", "late_delivery": "el tiempo de entrega", "billing": "la facturación",
           "double_charge": "el cobro", "app_performance": "la app", "customer_support": "el soporte al cliente",
           "product_quality": "la calidad del producto", "pricing": "el precio", "usability": "la interfaz",
           "account_login": "el inicio de sesión", "refunds": "el reembolso",
           "onboarding": "la configuración inicial"},
    "hi": {"delivery": "डिलीवरी", "late_delivery": "डिलीवरी का समय", "billing": "बिलिंग", "double_charge": "पेमेंट",
           "app_performance": "ऐप", "customer_support": "कस्टमर सपोर्ट", "product_quality": "प्रोडक्ट की क्वालिटी",
           "pricing": "कीमत", "usability": "इंटरफ़ेस", "account_login": "लॉगिन", "refunds": "रिफंड",
           "onboarding": "सेटअप"},
    "te": {"delivery": "డెలివరీ", "late_delivery": "డెలివరీ సమయం", "billing": "బిల్లింగ్", "double_charge": "పేమెంట్",
           "app_performance": "యాప్", "customer_support": "కస్టమర్ సపోర్ట్", "product_quality": "ప్రొడక్ట్ క్వాలిటీ",
           "pricing": "ధర", "usability": "ఇంటర్‌ఫేస్", "account_login": "లాగిన్", "refunds": "రీఫండ్",
           "onboarding": "సెటప్"},
    "hi-Latn": {"delivery": "delivery", "late_delivery": "delivery time", "billing": "billing",
                "double_charge": "payment", "app_performance": "app", "customer_support": "customer support",
                "product_quality": "product quality", "pricing": "price", "usability": "interface",
                "account_login": "login", "refunds": "refund", "onboarding": "setup"},
}
ML_FRAMES = {  # language -> sentiment -> frames; {x} noun; mixed: {a} liked, {b} disliked
    "es": {
        "positive": ["{X} es excelente, estoy muy satisfecho.", "Muy contento con {x}, funciona de maravilla.",
                     "{X} de {product} es genial, lo recomiendo."],
        "negative": ["{X} es terrible, muy decepcionado.", "Estoy harto, {x} es un desastre.",
                     "{X} de {product} deja mucho que desear."],
        "neutral": ["{X} es normal, nada especial.", "Sobre {x}: funciona como se espera.", "{X} es aceptable."],
        "mixed": ["{A} es excelente, pero {b} es terrible.", "Me gusta {a}, aunque {b} deja mucho que desear.",
                  "{A} está bien, pero {b} es un desastre."],
    },
    "hi": {
        "positive": ["{x} के साथ मेरा अनुभव बहुत अच्छा रहा।", "{x} से मैं बहुत खुश हूँ।",
                     "{x} शानदार है, सबको सलाह दूँगा।"],
        "negative": ["{x} के साथ मेरा अनुभव बहुत खराब रहा।", "{x} से मैं बहुत परेशान हूँ।",
                     "{x} बिल्कुल बेकार है, बहुत निराशा हुई।"],
        "neutral": ["{x} ठीक-ठाक है।", "{x} के बारे में कुछ खास कहने को नहीं है।", "{x} सामान्य है।"],
        "mixed": ["{a} शानदार है, लेकिन {b} बिल्कुल बेकार है।", "{a} से खुश हूँ, पर {b} से बहुत परेशान हूँ।",
                  "{a} के साथ अनुभव अच्छा रहा, लेकिन {b} बेकार है।"],
    },
    "te": {
        "positive": ["{x} చాలా బాగుంది.", "{x} తో చాలా సంతోషంగా ఉన్నాను.",
                     "{x} అద్భుతంగా ఉంది, అందరికీ సిఫార్సు చేస్తాను."],
        "negative": ["{x} అస్సలు బాగాలేదు.", "{x} తో చాలా ఇబ్బందిగా ఉంది.",
                     "{x} చాలా ఘోరంగా ఉంది, చాలా నిరాశ చెందాను."],
        "neutral": ["{x} పర్వాలేదు.", "{x} గురించి ప్రత్యేకంగా చెప్పడానికి ఏమీ లేదు.", "{x} మామూలుగా ఉంది."],
        "mixed": ["{a} బాగుంది, కానీ {b} చాలా ఘోరంగా ఉంది.", "{a} తో సంతోషం, కానీ {b} తో చాలా ఇబ్బంది.",
                  "{a} అద్భుతంగా ఉంది, కానీ {b} అస్సలు బాగాలేదు."],
    },
    "hi-Latn": {
        "positive": ["{X} bahut achha hai, full satisfied.", "{product} ka {x} ekdum mast hai yaar.",
                     "{X} super hai, sabko recommend karunga."],
        "negative": ["{X} bilkul bekaar hai, very disappointed.", "Yaar {x} ka bahut bura haal hai, totally fed up.",
                     "{product} ka {x} ekdum third class hai."],
        "neutral": ["{X} theek-thaak hai.", "{X} normal hai, kuch special nahi.",
                    "{X} ke baare mein kuch khaas nahi kehna."],
        "mixed": ["{A} achha hai but {b} bilkul bekaar hai.", "{A} mast hai, lekin {b} ne pareshan kar diya.",
                  "{A} se khush hoon par {b} third class hai."],
    },
}

AGENT_REPLIES = [  # support-agent messages: not customer feedback, never labelled
    "Thanks for reaching out. I'm looking into this now.",
    "Sorry for the trouble. Could you share your order number?",
    "I've escalated this to our specialist team.",
    "This should now be resolved. Please let us know if anything else comes up.",
    "Thank you for your patience while we investigate.",
]

_SENT_CODE = {"positive": "POS", "negative": "NEG", "neutral": "NEU", "mixed": "MIX"}


def _cap(s: str) -> str:
    return s[:1].upper() + s[1:] if s else s


def _pick(rng: np.random.Generator, seq):
    return seq[int(rng.integers(len(seq)))]


def render(rng: np.random.Generator, language: str, sentiment: str, theme: str, product: str,
           second_theme: str | None = None) -> dict:
    """Render one feedback text and return it with the labels its template implies.

    `theme`/`second_theme` are theme codes. For sentiment 'mixed', `theme` is the liked aspect and
    `second_theme` the disliked one; both are gold themes.
    """
    if sentiment == "mixed" and not second_theme:
        raise ValueError("mixed sentiment needs two themes")
    themes = [theme] if sentiment != "mixed" else [theme, second_theme]
    if language == "en":
        styles, weights = zip(*EN_STYLE_MIX[sentiment])
        style = styles[int(rng.choice(len(styles), p=np.array(weights)))]
        frames = EN_FRAMES[(style, sentiment)]
        fi = int(rng.integers(len(frames)))
        noun, pos, neg, neu = EN[theme]
        p, n, u = _pick(rng, pos), _pick(rng, neg), _pick(rng, neu)
        b = _pick(rng, EN[second_theme][2]) if second_theme else n
        text = frames[fi].format(p=p, P=_cap(p), n=n, N=_cap(n), u=u, U=_cap(u), noun=noun, Noun=_cap(noun),
                                 a=p, A=_cap(p), b=b, B=_cap(b), product=product)
        template_id = f"EN-{style.upper()}-{_SENT_CODE[sentiment]}-{fi + 1:02d}"
    else:
        nouns = ML_NOUNS[language]
        frames = ML_FRAMES[language][sentiment]
        fi = int(rng.integers(len(frames)))
        x = nouns[theme]
        b = nouns[second_theme] if second_theme else x
        text = frames[fi].format(x=x, X=_cap(x), a=x, A=_cap(x), b=b, product=product)
        template_id = f"{language.upper()}-{_SENT_CODE[sentiment]}-{fi + 1:02d}"
        style = "multilingual"   # every non-English text is in the multilingual slice; sentiment says if mixed
    return {"text": text, "sentiment": sentiment, "themes": themes, "style": style,
            "template_id": template_id, "language": language}
