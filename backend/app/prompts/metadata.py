"""
The "Artwork metadata" block shared by the user messages of docs 11.1 and
11.2 (§2). Fields with no value are left out, never labeled as missing
(RF-002 scenario 2; doc 09, §3).
"""

# Label and attribute, in the order of the user message template
FIELDS = (
    ("Title", "title"),
    ("Artist(s)", "artists"),
    ("Date", "date_display"),
    ("Period", "period"),
    ("Culture", "culture"),
    ("Classification", "classification"),
    ("Technique", "technique"),
    ("Medium", "medium"),
)


def format_metadata(metadata) -> str:
    lines = ["Artwork metadata:"]
    for label, attribute in FIELDS:
        value = getattr(metadata, attribute)
        if isinstance(value, list):
            value = ", ".join(value)
        if value:
            lines.append(f"- {label}: {value}")
    return "\n".join(lines)
