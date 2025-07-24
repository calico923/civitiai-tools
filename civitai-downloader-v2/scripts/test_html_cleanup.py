#!/usr/bin/env python3
"""
Test script for HTML cleanup functionality
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.utils.html_cleaner import HTMLCleaner

def test_html_cleanup():
    """Test HTML cleanup functionality"""
    
    # Test case 1: Complex HTML from API
    html_content = '''<p>This version add more data. The high resolution images are created by using v1.0 LoRA and img2img upscaling.<br />I also add more character in to this model as well.</p>
<p>Trained on <a target="_blank" rel="ugc" href="https://civitai.com/models/833294/noobai-xl-nai-xl?modelVersionId=1190596"><strong>NoobAI-XL (NAI-XL) V-Pred 1.0-Version</strong></a></p>
<ul><li><p>change<code>min_snr_gamma</code> from 5 to 0</p></li><li><p>should produce closer lighting/blacks to base model</p></li></ul>'''
    
    print("Original HTML:")
    print(html_content)
    print("\n" + "="*50 + "\n")
    
    cleaned = HTMLCleaner.clean_html(html_content)
    print("Cleaned text:")
    print(cleaned)
    print("\n" + "="*50 + "\n")
    
    # Test case 2: Model data cleanup
    model_data = {
        "id": 12345,
        "name": "Test Model",
        "description": "<p>This is a <strong>test</strong> model with <a href='#'>link</a>.</p>",
        "trainedWords": ["test", "trigger"],
        "modelVersions": [
            {
                "id": 1,
                "description": "<ul><li>Version 1 feature</li><li>Another feature</li></ul>"
            }
        ]
    }
    
    print("Original model data:")
    print(model_data)
    print("\n" + "="*50 + "\n")
    
    cleaned_model = HTMLCleaner.clean_model_description(model_data)
    print("Cleaned model data:")
    print(cleaned_model)
    print("\n" + "="*50 + "\n")
    
    # Test case 3: trainedWords should be preserved
    print("trainedWords preserved:", cleaned_model.get("trainedWords"))

if __name__ == "__main__":
    test_html_cleanup()