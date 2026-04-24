import requests
import re
from collections import Counter
from config import OLLAMA_URL, OLLAMA_MODEL

class KeywordGenerator:
    def __init__(self, ollama_url=OLLAMA_URL, model=OLLAMA_MODEL):
        self.generate_url = f"{ollama_url}/api/generate"
        self.model = model

    def generate_keyword(self, chunk_text: str) -> str:
        # Try Ollama first
        keyword = self._try_ollama(chunk_text)
        if keyword:
            return keyword
        # Fallback to local extraction
        return self._extract_keyword_locally(chunk_text)

    def _try_ollama(self, text: str) -> str:
        prompt = f"""Generate a single short search query (3-5 words) for a stock video that best represents this text. Only output the query, no extra words.

Text: {text}
Query:"""

        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.2,
                "top_k": 20,
                "num_predict": 50
            }
        }
        try:
            response = requests.post(self.generate_url, json=payload, timeout=30)
            if response.status_code == 200:
                result = response.json()
                keyword = result.get("response", "").strip().strip('"')
                if keyword and len(keyword) > 1:
                    return keyword
        except requests.exceptions.ConnectionError:
            print("Ollama server not reachable. Using fallback keyword extraction.")
        except Exception as e:
            print(f"Ollama error: {e}")
        return None

    def _extract_keyword_locally(self, text: str) -> str:
        """Simple fallback: extract the most frequent significant word."""
        words = re.findall(r'\b[A-Za-z]{3,}\b', text)
        stopwords = {'the', 'and', 'that', 'this', 'with', 'from', 'have', 'are', 'for', 'not', 'but', 'was', 'you', 'they', 'she', 'he', 'it', 'of', 'to', 'in', 'is', 'on', 'at', 'by'}
        content_words = [w.lower() for w in words if w.lower() not in stopwords]
        if not content_words:
            return "nature background"
        from collections import Counter
        common = Counter(content_words).most_common(1)
        keyword = common[0][0]
        if len(content_words) > 1:
            keyword = keyword + " " + content_words[1]
        return keyword