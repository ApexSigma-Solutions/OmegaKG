from bs4 import BeautifulSoup
import logging

logger = logging.getLogger(__name__)

def parse_html_content(html_content: str, url: str) -> list:
    """Factory: Selects parser based on URL."""
    soup = BeautifulSoup(html_content, 'html.parser')
    if "aistudio.google.com" in url:
        return _parse_ai_studio(soup)
    elif "nano-gpt.com" in url:
        return _parse_nano_gpt(soup)
    return _parse_generic_fallback(soup)

def _parse_ai_studio(soup: BeautifulSoup) -> list:
    messages = []
    # More specific selectors to avoid capturing containers
    chunks = soup.select('[class*="message-user"], [class*="message-model"], [class*="user-prompt"], [class*="model-response"]')
    
    if not chunks: 
        # Fallback to slightly broader but still safe check if specific classes fail
        chunks = soup.find_all(['div', 'section'], class_=lambda x: x and ('message-content' in x or 'text-content' in x))
        
    if not chunks: return _parse_generic_fallback(soup)

    for chunk in chunks:
        text = chunk.get_text(separator="\n", strip=True)
        if text:
            # Determine role based on class presence
            classes = " ".join(chunk.get("class", []))
            if "user" in classes or "prompt" in classes:
                role = "user"
            else:
                role = "assistant"
            messages.append({"role": role, "content": text})
    return messages

def _parse_nano_gpt(soup: BeautifulSoup) -> list:
    messages = []
    # Nano-GPT often uses Tailwind 'whitespace-pre-wrap' for chat bubbles
    bubbles = soup.select('div.whitespace-pre-wrap')
    if not bubbles: return _parse_generic_fallback(soup)

    for bubble in bubbles:
        text = bubble.get_text(separator="\n", strip=True)
        if not text: continue
        
        # Robust role detection: check parent for user/assistant indicators
        # Nano-GPT usually wraps user messages in a specific container or has distinct classes
        is_user = False
        parent = bubble.find_parent()
        while parent:
            p_classes = parent.get("class", [])
            if any("user" in c for c in p_classes):
                is_user = True
                break
            if any("assistant" in c or "bot" in c for c in p_classes):
                is_user = False # Explicitly assistant
                break
            parent = parent.find_parent()
            
        role = "user" if is_user else "assistant"
        messages.append({"role": role, "content": text})
    return messages

def _parse_generic_fallback(soup: BeautifulSoup) -> list:
    paras = soup.find_all('p')
    full_text = "\n\n".join([p.get_text() for p in paras])
    return [
        {"role": "system", "content": "Parsed via generic fallback"},
        {"role": "assistant", "content": full_text[:3000]}
    ]