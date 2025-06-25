import requests
import json
from typing import Dict, Any
import streamlit as st

def generate_product_ideas(user_request: str, parsed_request: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generate specific product ideas using Perplexity API based on parsed gift request
    
    Args:
        user_request: Original user request
        parsed_request: Structured gift request information
        
    Returns:
        Dictionary with product recommendations
    """
    perplexity_api_key = st.secrets["api_keys"]["perplexity"]

    # Extract relevant information from parsed request
    recipient = parsed_request.get('recipient', {})
    interests = parsed_request.get('interests', [])
    occasion = parsed_request.get('occasion', 'Not specified')
    budget = parsed_request.get('budget', {})
    categories = parsed_request.get('gift_categories', [])
    # Format interests string
    interests_str = ', '.join(interests) if interests else "No specific interests mentioned"
    
    # System prompt - defines the role and capabilities
    system_prompt = """You are an expert product research assistant specializing in gift recommendations for the Indian market. Your role is to research and recommend specific, currently available products that can be purchased online in India.

CAPABILITIES:
- Research real products available in Indian e-commerce platforms
- Provide exact product names with brand and model details
- Estimate accurate price ranges based on current market data
- Match products to recipient interests and occasions
- Focus on products with good availability and reviews

REQUIREMENTS FOR RECOMMENDATIONS:
1. Recommend 10 EXACT SPECIFIC products with precise brand names and model numbers
2. Each product must be:
   - Currently available in India
   - Purchasable online (Amazon, Flipkart, etc.)
   - HIGH-RATED with good customer reviews (4+ stars preferred)
   - HIGH-QUALITY from reputable brands
   - Appropriately matched to recipient interests
   - Within the specified budget range
   - Suitable for the occasion

DIVERSITY REQUIREMENTS:
- Spread recommendations ACROSS DIFFERENT CATEGORIES when possible
- Don't recommend multiple similar products from the same category
- Provide variety to give the user different gifting options
- Consider both practical and experiential gifts

QUALITY FOCUS:
- Prioritize well-reviewed products with high ratings
- Choose established brands with good reputation
- Focus on products known for durability and quality
- Mention specific quality indicators (ratings, reviews, certifications)

BUDGET CONSTRAINTS:
Before recommending a product, check if it is within the budget range. If it is not, do not recommend it.
If the product price is too low with respect to the budget range, do not recommend it.

OUTPUT FORMAT:
- Use EXACT product names as they appear on shopping websites
- Include specific brand names, model numbers, sizes, colors
- Mention product ratings and review counts when available
- Provide detailed explanations for each recommendation
- Include estimated price ranges based on current market data
- Explain why each product fits the recipient's profile
- Highlight quality aspects and customer satisfaction"""

    # User prompt - specific request with context
    user_prompt = f"""ORIGINAL REQUEST: {user_request}

PARSED INFORMATION:
- Recipient Type: {recipient.get('type', 'Not specified')}
- Age Group: {recipient.get('age_group', 'Not specified')}
- Relationship: {recipient.get('relationship', 'Not specified')}
- Gender: {recipient.get('gender', 'Not specified')}
- Occasion: {occasion}
- Interests: {interests_str}
- Budget: ₹{budget.get('min', 0)} - ₹{budget.get('max', 0)}

Gifting categories to think about:
{categories}

Please research and recommend specific gift products available in India that match this profile. Focus on products that are currently available on major Indian e-commerce platforms and provide comprehensive details for each recommendation. 
Dont be biased towards any particular brand or product or a single category.
IMPORTANT: Always stick to the budget range, do not give products that are outside the budget range (too high or too low).
Explore mutliple brands and categories to give a diverse set of recommendations.
"""

    # Perplexity API endpoint
    url = "https://api.perplexity.ai/chat/completions"
    
    headers = {
        "Authorization": f"Bearer {perplexity_api_key}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": "sonar-pro",
        "messages": [
            {
                "role": "system",
                "content": system_prompt
            },
            {
                "role": "user",
                "content": user_prompt
            }
        ],
        "temperature": 0.7,
        "max_tokens": 4000
    }
    
    try:
        # Disable SSL verification and suppress warnings
        requests.packages.urllib3.disable_warnings(requests.packages.urllib3.exceptions.InsecureRequestWarning)
        
        response = requests.post(url, headers=headers, json=payload, verify=False, timeout=30)
        response.raise_for_status()
        
        response_data = response.json()
        
        if 'choices' in response_data and len(response_data['choices']) > 0:
            content = response_data['choices'][0]['message']['content']
            
            return content
                
        else:
            return {"error": "No valid response from Perplexity API"}
            
    except requests.exceptions.RequestException as e:
        error_msg = f"API request failed: {str(e)}"
        if hasattr(e, 'response') and e.response is not None:
            try:
                error_details = e.response.json()
                error_msg += f" - Details: {error_details}"
            except:
                error_msg += f" - Response: {e.response.text}"
        return {"error": error_msg}
    except Exception as e:
        return {"error": f"Unexpected error: {str(e)}"}

if __name__ == "__main__":
    user_request = "I need a cricket bat for my friend"
    parsed_request = {'recipient': {'gender': 'Unisex', 'age_group': 'N/A', 'relationship': 'Friend', 'interests': ['Cricket', 'Sports']}, 'occasion': 'N/A', 'budget': {'min': 2000, 'max': 3000}, 'search_queries': ['Best cricket bats under 3000 INR', 'Lightweight cricket bats for beginners', 'Durable cricket bats for casual players'], 'gift_categories': ['High-quality cricket bats for recreational players', 'Cricket accessories like gloves, balls, or bat grips', 'Personalized cricket gear with name engraving']}
    print(generate_product_ideas(user_request, parsed_request))