# sources.py
# Curated candidate RSS feed URLs — healthcare, pharma, medtech, hospital, insurance, policy
# Separated into India-specific and Global sources for balanced briefing creation.

INDIA_FEEDS = [
    # Google News India Healthcare & Pharma Aggregator (High freshness & broad coverage)
    "https://news.google.com/rss/search?q=healthcare+india+OR+pharma+india+OR+medtech+india+OR+CDSCO+OR+Ayushman+Bharat&hl=en-IN&gl=IN&ceid=IN:en",
    
    # ET HealthWorld (Economic Times India)
    "https://health.economictimes.indiatimes.com/rss/topstories",
    "https://health.economictimes.indiatimes.com/rss/pharma",
    "https://health.economictimes.indiatimes.com/rss/medical-devices",
    "https://health.economictimes.indiatimes.com/rss/policy",
    "https://health.economictimes.indiatimes.com/rss/hospitals",

    # Express Healthcare & Express Pharma India
    "https://www.expresshealthcare.in/feed",
    "https://www.expresspharma.in/feed",

    # Business Today India Health
    "https://www.businesstoday.in/rss/health.xml",
    "https://www.pharmabiz.com/rss",
]

GLOBAL_FEEDS = [
    # Global health / science news
    "https://www.fiercehealthcare.com/rss/xml",
    "https://www.statnews.com/feed/",
    "https://www.beckershospitalreview.com/rss/all-news.rss",
    "https://www.medscape.com/rss/public-health",
    "https://rss.nytimes.com/services/xml/rss/nyt/Health.xml",
    "https://www.bbc.co.uk/news/health/rss.xml",

    # Global Pharma / biotech
    "https://www.fiercepharma.com/rss/xml",
    "https://www.biopharmadive.com/feeds/news/",

    # Global Medtech / devices
    "https://www.fiercebiotech.com/rss/xml",
    "https://www.medtechdive.com/feeds/news/",
    "https://medcitynews.com/feed/",

    # Global Policy & Regulation
    "https://kffhealthnews.org/feed/",
    "https://www.fda.gov/about-fda/contact-fda/subscribe-enews/rss-feeds-fda.html",
]

# Combined list: India feeds listed first to ensure strong representation
CANDIDATE_FEEDS = INDIA_FEEDS + GLOBAL_FEEDS
