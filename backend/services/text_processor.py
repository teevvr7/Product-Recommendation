import re
from typing import List, Dict, Any
import nltk
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
from nltk.stem import WordNetLemmatizer

# Initialize NLTK components
# Ensure required corpora are available
try:
    _lemmatizer = WordNetLemmatizer()
    _stop_words = set(stopwords.words("english"))
except LookupError:
    nltk.download("punkt", quiet=True)
    nltk.download("stopwords", quiet=True)
    nltk.download("wordnet", quiet=True)
    nltk.download("punkt_tab", quiet=True)
    _lemmatizer = WordNetLemmatizer()
    _stop_words = set(stopwords.words("english"))

def clean_text_proper(text: str) -> str:
    """
    Applies the identical text cleaning and preprocessing pipeline used in the training notebook:
    1. Lowercase conversion
    2. Removal of special characters, digits, and punctuation (regex [^a-zA-Z\\s])
    3. Tokenization into individual words
    4. Stopwords removal & filtering of short tokens (length <= 2)
    5. WordNet lemmatization
    """
    if not isinstance(text, str) or not text.strip():
        return ""
    
    # 1. Lowercase
    text = text.lower()
    
    # 2. Keep only alphabetic characters and spaces
    text = re.sub(r"[^a-zA-Z\s]", "", text)
    
    # 3. Tokenize
    tokens = word_tokenize(text)
    
    # 4. Remove stopwords, short tokens (len <= 2), and lemmatize
    cleaned_tokens = [
        _lemmatizer.lemmatize(token)
        for token in tokens
        if token not in _stop_words and len(token) > 2
    ]
    
    return " ".join(cleaned_tokens)

def analyze_query_tokens(raw_text: str) -> Dict[str, Any]:
    """
    Detailed breakdown of query processing for user transparency & UI diagnostics.
    """
    if not isinstance(raw_text, str):
        return {"raw": "", "cleaned": "", "tokens": [], "stop_words_removed": []}
    
    lowered = raw_text.lower()
    alpha_only = re.sub(r"[^a-zA-Z\s]", "", lowered)
    tokens = word_tokenize(alpha_only)
    
    removed_stops = [t for t in tokens if t in _stop_words or len(t) <= 2]
    lemmatized = [_lemmatizer.lemmatize(t) for t in tokens if t not in _stop_words and len(t) > 2]
    
    return {
        "raw": raw_text,
        "cleaned": " ".join(lemmatized),
        "tokens": lemmatized,
        "stop_words_removed": removed_stops,
    }
