"""Static master data: product/channel taxonomy and the theme taxonomy. All names are fictional."""
from __future__ import annotations

from datetime import date

CATEGORIES = ("mobile_app", "subscription_plan", "smart_device", "delivery_service")

# (product_id, name, category, launched_at)
PRODUCTS = [
    ("PROD-0001", "Lumo Wallet", "mobile_app", date(2023, 3, 1)),
    ("PROD-0002", "TrekTrack", "mobile_app", date(2024, 6, 15)),
    ("PROD-0003", "Nestly Home", "mobile_app", date(2025, 2, 1)),
    ("PROD-0004", "StreamNest Premium", "subscription_plan", date(2022, 9, 1)),
    ("PROD-0005", "VaultBox Plus", "subscription_plan", date(2023, 11, 1)),
    ("PROD-0006", "FitLoop Annual", "subscription_plan", date(2024, 1, 10)),
    ("PROD-0007", "Aurelo Speaker", "smart_device", date(2023, 8, 20)),
    ("PROD-0008", "Velto Watch", "smart_device", date(2024, 10, 1)),
    ("PROD-0009", "Orbix Router", "smart_device", date(2022, 5, 5)),
    ("PROD-0010", "QuickDrop Express", "delivery_service", date(2021, 7, 1)),
    ("PROD-0011", "CrateFresh Weekly", "delivery_service", date(2023, 4, 1)),
    ("PROD-0012", "ParcelPal Same-Day", "delivery_service", date(2025, 1, 15)),
]

# (channel_id, name, type)
CHANNELS = [
    ("CHAN-01", "web_survey", "survey"),
    ("CHAN-02", "email_survey", "survey"),
    ("CHAN-03", "app_store", "review"),
    ("CHAN-04", "website_review", "review"),
    ("CHAN-05", "chat", "support"),
    ("CHAN-06", "email_support", "support"),
]

THEME_EFFECTIVE_FROM = date(2026, 1, 1)
# (theme_id, code, name, parent_theme_id, keywords, severity_weight 1-3)
THEMES = [
    ("THEME-000001", "delivery", "Delivery", None, "delivery|courier|package|parcel|box", 2),
    ("THEME-000002", "billing", "Billing", None, "invoice|bill|billing|fees|statement", 2),
    ("THEME-000003", "app_performance", "App performance", None, "app|crash|freeze|slow|load", 2),
    ("THEME-000004", "customer_support", "Customer support", None, "support|agent|hold|chat|ticket", 2),
    ("THEME-000005", "product_quality", "Product quality", None, "quality|broken|cracked|materials|build", 2),
    ("THEME-000006", "pricing", "Pricing", None, "price|expensive|value|discount|cost", 1),
    ("THEME-000007", "usability", "Usability", None, "interface|menu|settings|easy|confusing", 1),
    ("THEME-000008", "account_login", "Account & login", None, "login|password|locked|verification|account", 3),
    ("THEME-000009", "refunds", "Refunds", None, "refund|return|money back|reimburse", 3),
    ("THEME-000010", "onboarding", "Onboarding & setup", None, "setup|activation|getting started|pairing", 1),
    ("THEME-000011", "late_delivery", "Late delivery", "THEME-000001", "late|overdue|delayed|missed slot", 3),
    ("THEME-000012", "double_charge", "Double charge", "THEME-000002", "charged twice|double charge|duplicate charge", 3),
]
THEME_ID_BY_CODE = {t[1]: t[0] for t in THEMES}
OUT_OF_TAXONOMY_THEME_ID = "THEME-000999"   # used only by the THEME_OUTSIDE_TAXONOMY edge case

# Which themes are plausible for each product category (realistic distributions, documented rule).
APPLICABLE_THEMES = {
    "mobile_app": ["billing", "double_charge", "app_performance", "customer_support", "usability",
                   "account_login", "onboarding", "pricing", "refunds"],
    "subscription_plan": ["billing", "double_charge", "pricing", "refunds", "customer_support",
                          "account_login", "onboarding", "usability"],
    "smart_device": ["delivery", "late_delivery", "product_quality", "app_performance", "customer_support",
                     "pricing", "refunds", "onboarding", "usability"],
    "delivery_service": ["delivery", "late_delivery", "customer_support", "pricing", "refunds", "billing",
                         "product_quality", "usability"],
}

# Customers write in their preferred language. hi-Latn = code-mixed Hinglish in Latin script.
LANGUAGES = ("en", "es", "hi", "te", "hi-Latn")
LANGUAGE_WEIGHTS = (0.80, 0.05, 0.05, 0.05, 0.05)
REGION_BY_LANGUAGE = {
    "en": ("IN-North", "IN-South", "IN-East", "IN-West", "International"),
    "es": ("International",),
    "hi": ("IN-North", "IN-West", "IN-East"),
    "te": ("IN-South",),
    "hi-Latn": ("IN-North", "IN-West", "IN-South"),
}
SEGMENTS = ("consumer", "smb", "enterprise")
SEGMENT_WEIGHTS = (0.70, 0.20, 0.10)

FIRST_NAMES = ["Aarav", "Diya", "Kiran", "Meera", "Rohan", "Sana", "Vikram", "Lakshmi", "Arjun", "Priya",
               "Carlos", "Lucia", "Mateo", "Sofia", "Emma", "Liam", "Noah", "Olivia", "Ravi", "Anjali"]
LAST_NAMES = ["Rao", "Sharma", "Reddy", "Iyer", "Patel", "Nair", "Varma", "Gupta", "Garcia", "Lopez",
              "Smith", "Brown", "Khan", "Das", "Menon", "Joshi"]
