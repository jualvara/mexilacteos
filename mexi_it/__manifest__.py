{
    "name": "Mexilacteos IT",
    "summary": "IT request module for Mexilacteos",
    "version": "18.0.1.0.0",
    "category": "Services",
    "author": "Mexilacteos",
    "license": "Other proprietary",
    "application": True,
    "depends": ["base", "mail", "hr", "maintenance"],
    "data": [
        "security/it_request_groups.xml",
        "security/ir.model.access.csv",
        "security/it_request_rules.xml",
        "data/it_request_sequence.xml",
        "views/it_request_views.xml",
        "views/it_request_dashboard.xml",
    ],
    "assets": {
        "web.assets_backend": [],
    },
    "images": ["static/description/icon.png"],
}
