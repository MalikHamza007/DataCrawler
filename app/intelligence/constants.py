RULE_VERSION = "m6-v1"

DEVELOPER_RULES = (
    ("OFFICIAL_DEVELOPER_LANGUAGE", "Official source identifies development activity", 25, ("property developer", "real estate developer", "development company", "we develop", "our developments")),
    ("OFFICIAL_PROJECT_PORTFOLIO", "Official portfolio contains projects", 25, ("project_name",)),
    ("EXPLICIT_DEVELOPED_BY", "Explicit developed-by relationship", 25, ("developed by", "a project by", "owned and developed by")),
    ("AUTHORIZED_DEALER", "Authorized dealer language", -35, ("authorized dealer",)),
    ("PROPERTY_CONSULTANT", "Property consultant or dealer language", -30, ("property consultant", "property dealer")),
    ("BUYING_SELLING", "Buying and selling services", -25, ("buying and selling", "buy sell rent")),
    ("MARKETING_PARTNER", "Sales or marketing partner language", -25, ("sales and marketing by", "exclusive marketing partner", "authorized sales partner")),
    ("CONSTRUCTION_ONLY", "Construction contractor language", 0, ("general contractor", "civil contractor", "construction services", "epc contractor")),
)

PROJECT_RULES = (
    ("OFFICIAL_PROJECT_PAGE", "Official project website evidence", 25, ("project_website",)),
    ("PORTFOLIO_PROJECT", "Project appears in an official portfolio", 25, ("project_name",)),
    ("PROJECT_TYPE", "Real-estate project type evidence", 10, ("project_project_type", "project_type")),
    ("LAHORE_LOCATION", "Lahore location evidence", 10, ("lahore", "confirmed_lahore", "probable_lahore")),
    ("DEVELOPER_RELATIONSHIP", "Developer relationship evidence", 20, ("developer_relationship", "developed by", "a project by")),
    ("PROJECT_STATUS", "Construction, booking or handover status", 5, ("booking_open", "under_construction", "completed", "delivered", "ongoing")),
    ("GENERIC_OFFICE", "Generic property or booking office name", -20, ("property office", "booking office", "investment consultant")),
    ("BROKER_LANGUAGE", "Broker or agency evidence", -35, ("property dealer", "real estate agency", "broker")),
)
