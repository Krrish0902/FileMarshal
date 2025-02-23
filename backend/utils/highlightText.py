def highlight_text(text, query):
    """Split text into parts to be highlighted"""
    lower_text = text.lower()
    lower_query = query.lower()
    parts = []
    last_idx = 0
    
    idx = lower_text.find(lower_query)
    while idx != -1:
        if idx > last_idx:
            parts.append({"text": text[last_idx:idx], "highlight": False})
        parts.append({"text": text[idx:idx + len(query)], "highlight": True})
        last_idx = idx + len(query)
        idx = lower_text.find(lower_query, last_idx)
    
    if last_idx < len(text):
        parts.append({"text": text[last_idx:], "highlight": False})
    
    return parts