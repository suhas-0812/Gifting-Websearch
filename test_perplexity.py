import requests
import json
import streamlit as st

def test_perplexity_connection():
    """
    Simple test to verify Perplexity API connection
    """
    try:
        # Get API key from secrets
        perplexity_api_key = st.secrets["api_keys"]["perplexity"]
        print(f"API Key loaded: {perplexity_api_key[:10]}...")
        
        # Simple test prompt
        test_prompt = "What is the capital of India?"
        
        # API endpoint
        url = "https://api.perplexity.ai/chat/completions"
        
        headers = {
            "Authorization": f"Bearer {perplexity_api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": "sonar-pro",
            "messages": [
                {
                    "role": "user",
                    "content": test_prompt
                }
            ],
            "temperature": 0.1,
            "max_tokens": 100
        }
        
        print("Making API request...")
        response = requests.post(url, headers=headers, json=payload)
        
        print(f"Status Code: {response.status_code}")
        print(f"Response Headers: {dict(response.headers)}")
        
        if response.status_code == 200:
            response_data = response.json()
            print("\n✅ SUCCESS!")
            print(f"Response: {json.dumps(response_data, indent=2)}")
            
            if 'choices' in response_data and len(response_data['choices']) > 0:
                content = response_data['choices'][0]['message']['content']
                print(f"\n📝 Answer: {content}")
            
        else:
            print(f"\n❌ FAILED!")
            print(f"Error: {response.text}")
            
    except Exception as e:
        print(f"\n💥 EXCEPTION: {str(e)}")

if __name__ == "__main__":
    test_perplexity_connection() 