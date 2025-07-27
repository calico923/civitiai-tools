#!/usr/bin/env python3
"""Extract useful information from model descriptions."""

import re
from html import unescape
from typing import Dict, List, Optional

def extract_useful_description(html_text: str) -> str:
    """
    Extract useful information from HTML description:
    1. 基本説明 (first 1-2 sentences)
    2. 推奨設定 (Sampler, Steps, CFG)
    3. プロンプト例 (positive/negative examples)
    """
    if not html_text:
        return ""
    
    # HTMLエンティティをデコード
    text = unescape(html_text)
    
    # HTMLタグを除去
    text = re.sub(r'<[^>]+>', ' ', text)
    
    # 複数の空白を1つに
    text = re.sub(r'\s+', ' ', text).strip()
    
    # Extract components
    basic_desc = extract_basic_description(text)
    settings = extract_settings(text)
    prompts = extract_prompt_examples(text)
    
    # Combine extracted parts
    result_parts = []
    
    if basic_desc:
        result_parts.append(basic_desc)
    
    if settings:
        result_parts.append(f"Settings: {settings}")
    
    if prompts:
        result_parts.append(f"Prompts: {prompts}")
    
    result = " | ".join(result_parts)
    
    # Limit total length
    if len(result) > 400:
        result = result[:400] + "..."
    
    return result

def extract_basic_description(text: str) -> str:
    """Extract basic description (first 1-2 sentences)."""
    
    # Remove common noise patterns first
    text = remove_noise_patterns(text)
    
    # Split into sentences
    sentences = re.split(r'[.!?。！？]\s+', text)
    
    # Take first 1-2 meaningful sentences
    basic_sentences = []
    for sentence in sentences:
        sentence = sentence.strip()
        
        # Skip if too short or contains noise keywords
        if len(sentence) < 10:
            continue
        if is_noise_sentence(sentence):
            continue
            
        basic_sentences.append(sentence)
        
        # Stop after 2 sentences or 150 chars
        if len(basic_sentences) >= 2 or len(" ".join(basic_sentences)) > 150:
            break
    
    return " ".join(basic_sentences)

def extract_settings(text: str) -> str:
    """Extract recommended settings."""
    
    settings_patterns = [
        # Sampler patterns
        r'(?i)sampler?\s*:?\s*([A-Za-z+\s\d]+?)(?:\s|$|,|\|)',
        r'(?i)sampling\s+method\s*:?\s*([A-Za-z+\s\d]+?)(?:\s|$|,|\|)',
        
        # Steps patterns  
        r'(?i)steps?\s*:?\s*(\d+[-~]*\d*)',
        r'(?i)sampling\s+steps?\s*:?\s*(\d+[-~]*\d*)',
        
        # CFG patterns
        r'(?i)cfg\s*(?:scale)?\s*:?\s*([\d.]+[-~]*[\d.]*)',
        
        # Schedule patterns
        r'(?i)schedule\s*(?:type)?\s*:?\s*([A-Za-z\s]+?)(?:\s|$|,|\|)',
    ]
    
    settings = []
    text_lower = text.lower()
    
    for pattern in settings_patterns:
        matches = re.findall(pattern, text)
        for match in matches:
            match = match.strip()
            if match and len(match) < 30:  # Reasonable length
                settings.append(match)
    
    # Deduplicate and limit
    unique_settings = list(dict.fromkeys(settings))[:5]
    return ", ".join(unique_settings) if unique_settings else ""

def extract_prompt_examples(text: str) -> str:
    """Extract prompt examples."""
    
    prompt_patterns = [
        # Positive prompts
        r'(?i)positive\s*:?\s*([^\\n]+?)(?=negative|$|\.|settings)',
        r'(?i)prompt\s*:?\s*([^\\n]+?)(?=negative|$|\.|settings)',
        
        # Negative prompts  
        r'(?i)negative\s*:?\s*([^\\n]+?)(?=positive|$|\.|settings)',
    ]
    
    prompts = []
    
    for pattern in prompt_patterns:
        matches = re.findall(pattern, text)
        for match in matches:
            match = match.strip()
            if match and 10 < len(match) < 100:  # Reasonable length
                prompts.append(match)
    
    # Take first 2 examples
    return " / ".join(prompts[:2]) if prompts else ""

def remove_noise_patterns(text: str) -> str:
    """Remove common noise patterns."""
    
    # Remove URLs
    text = re.sub(r'https?://[^\s]+', '', text)
    
    # Remove version mentions
    text = re.sub(r'(?i)v\d+\.\d+|\bversion\s+\d+', '', text)
    
    # Remove pixai/civitai references
    text = re.sub(r'(?i)pixai\s*-[^.]*', '', text)
    text = re.sub(r'(?i)civitai\s*-[^.]*', '', text)
    
    # Remove model names in brackets
    text = re.sub(r'\[[^\]]+\]', '', text)
    
    # Remove social media mentions
    text = re.sub(r'(?i)discord|patreon|ko-fi[^.]*', '', text)
    
    return text.strip()

def is_noise_sentence(sentence: str) -> bool:
    """Check if sentence contains mostly noise."""
    
    noise_keywords = [
        'pixai', 'civitai', 'discord', 'patreon', 'ko-fi',
        'hugging face', 'github', 'repository', 'download',
        'version', 'update', 'changelog', 'license',
        'rules', 'commercial use', 'terms', 'conditions'
    ]
    
    sentence_lower = sentence.lower()
    
    # Count noise keywords
    noise_count = sum(1 for keyword in noise_keywords if keyword in sentence_lower)
    
    # If more than 30% of words are noise, skip
    words = sentence.split()
    if len(words) > 0 and (noise_count / len(words)) > 0.3:
        return True
    
    # Skip very short sentences
    if len(sentence) < 15:
        return True
    
    return False

# Test the extraction logic
if __name__ == "__main__":
    # Test with sample descriptions
    test_cases = [
        """<p><strong>Zero nans — Noobai-based SDXL vPred Merge</strong></p><p>A lineart-focused, sketch-style SDXL model merge built on <strong>NoobaiXLNAIXL_vPred1</strong>. Use Danbooru tags & artist tags.</p><p>🔧 Recommended Settings Sampler: Euler cfg++ Steps: 28 CFG: 1</p>""",
        
        """<pre><code>--prompt--
(explicit|general), masterpiece, best quality, 
anime coloring (if you need)
--negative--
lowres, worst quality, bad quality, bad anatomy</code></pre><p><strong>Recommend settings</strong> Sampling method: Euler a Steps: 20~40 CFG Scale: 4~7</p>"""
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n=== Test Case {i} ===")
        print(f"Input length: {len(test_case)} chars")
        result = extract_useful_description(test_case)
        print(f"Output: {result}")
        print(f"Output length: {len(result)} chars")