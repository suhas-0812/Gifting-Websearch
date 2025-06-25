import json
import requests
from typing import Dict, Any
import streamlit as st
from datetime import datetime

def parse_gift_request(user_input: str) -> Dict[str, Any]:
    """
    Parse a natural language gift request using Azure OpenAI to extract structured information
    
    Args:
        user_input: Free-form text describing the gift need
        api_key: Azure OpenAI API key
        
    Returns:
        Dictionary with structured gift request information
    """
    
    # Azure OpenAI configuration from secrets
    azure_endpoint = st.secrets["azure_openai"]["endpoint"]
    deployment_name = st.secrets["azure_openai"]["deployment_name"]
    api_version = st.secrets["azure_openai"]["api_version"]
    api_key = st.secrets["api_keys"]["azure_openai"]

    today = datetime.now().strftime("%Y-%m-%d")
    
    # Construct the parsing prompt
    prompt = f"""
Analyze this gift request and extract structured information, with special focus on personalizing categories based on interests:

USER REQUEST: {user_input}

Extract and return the following information in JSON format:

{{
    "recipient": {{
        "gender": "Inferred gender if clear from context, otherwise unisex",
        "age_group": "Age group if mentioned or can be inferred (child, teen, adult, senior)",
        "relationship": "Relationship to gift giver",
        "interests": "List of interests or hobbies mentioned or implied, including subtle preferences that can be inferred from the request, if not mentioned keep it as N/A"
    }},
    "occasion": "The gift occasion (birthday, anniversary, etc.)",
    "budget": {{
        "min": "Minimum budget in INR (75% of  if not specified)",
        "max": "Maximum budget in INR from context"
    }},
    "search_queries": [
        "2-3 search-ready queries for gift discovery based on the context"
    ],
    "gift_categories": [
        "Generate 2-3 highly personalized gift categories that are:",
        "- Should be a simple array of strings",
        "- Deeply tailored to the recipient's specific interests and hobbies",
        "- Connected to their lifestyle and preferences",
        "- Relevant to their current life stage and relationship",
        "- Matched to their potential skill level in their interests",
        "- Considerate of how they might use or experience the gift",
        "- Should be within the budget range"
    ]
}}

IMPORTANT:
- All monetary values should be in INR
- Generate specific, targeted search queries
- Include both explicit and implied interests
- If budget is "under X", use 70 percent of X as min and X as max
- If any field is unclear, fill it with N/A.
- If budget is not mentioned, use 2000 - 3000 INR as default value
- If the user has given a budget of X, minimum budget should be atleast 70% of X and maximum should be X

CATEGORY PERSONALIZATION GUIDELINES:
1. Interest-Based Specificity:
   * Instead of "Gardening Tools", use "Indoor Herb Garden Essentials" for someone interested in both gardening and cooking
   * Instead of "Books", use "Historical Fiction from the Colonial Era" for a history buff
   * Instead of "Tech Gadgets", use "Smart Home Automation for Plant Care" for a tech-savvy gardener

2. Lifestyle Integration:
   * Consider daily routines and habits
   * Think about space/living situation
   * Account for time availability
   * Consider skill level in their interests

3. Cultural Context:
   * Include Indian cultural elements if relevant
   * Consider local availability and brands
   * Account for regional preferences
   * Include both modern and traditional options

4. Experience Level:
   * Beginner-friendly if it's a new interest
   * Advanced tools for experienced hobbyists
   * Upgrades to existing equipment/collections
   * Learning and skill development options

5. Relationship Context:
   * Match gift significance to relationship
   * Consider shared experiences/memories
   * Account for gift-giving history
   * Include meaningful personalization options

Each category should be:
- Uniquely tailored to this specific recipient
- Detailed enough to guide product selection
- Broad enough to include multiple gift options
- Relevant to current Indian market availability
- Within the specified budget range

Note: If the query is too specific, generate 1 category.

Return ONLY the JSON object, no additional text.
"""

    # Azure OpenAI API call
    url = f"{azure_endpoint}/openai/deployments/{deployment_name}/chat/completions?api-version={api_version}"
    
    headers = {
        "Content-Type": "application/json",
        "api-key": api_key
    }
    
    payload = {
        "messages": [
            {
                "role": "user",
                "content": prompt
            }
        ],
        "temperature": 0,
        "max_tokens": 1000,
        "response_format": { "type": "json_object" }
    }
    
    try:
        # Make the API request
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        
        # Parse response
        response_data = response.json()
        
        if 'choices' in response_data and len(response_data['choices']) > 0:
            content = response_data['choices'][0]['message']['content']
            
            # Parse the JSON response
            try:
                parsed_data = json.loads(content.strip())
                return parsed_data
                
            except json.JSONDecodeError as e:
                return {
                    "error": f"Failed to parse Azure OpenAI response: {str(e)}",
                    "raw_content": content,
                    "content_length": len(content),
                    "content_repr": repr(content)
                }
                
        else:
            return {"error": "No valid response from Azure OpenAI"}
            
    except requests.exceptions.RequestException as e:
        error_msg = f"Azure OpenAI API request failed: {str(e)}"
        if hasattr(e, 'response') and e.response is not None:
            try:
                error_details = e.response.json()
                error_msg += f" - Details: {error_details}"
            except:
                error_msg += f" - Response: {e.response.text}"
        return {"error": error_msg}
    except Exception as e:
        return {"error": f"Unexpected error: {str(e)}"}


def format_perplexity_output(perplexity_response: str) -> Dict[str, Any]:
    """
    Format Perplexity's raw response into structured JSON using Azure OpenAI
    
    Args:
        perplexity_response: Raw response from Perplexity API
        
    Returns:
        Structured product recommendations
    """
    
    # Azure OpenAI configuration from secrets
    azure_endpoint = st.secrets["azure_openai"]["endpoint"]
    deployment_name = st.secrets["azure_openai"]["deployment_name"]
    api_version = st.secrets["azure_openai"]["api_version"]
    api_key = st.secrets["api_keys"]["azure_openai"]
    
    format_prompt = f"""
Take the following product recommendations from Perplexity and format them into a structured JSON format:

PERPLEXITY RESPONSE:
{perplexity_response}

Please format this into the following JSON structure:

{{
    "product_ideas": [
        {{
            "name": "EXACT product name with brand and model",
            "category": "Product category",
            "estimated_price_range": {{
                "min": number,
                "max": number
            }},
            "why_recommended": "Brief explanation of fit",
            "search_keywords": [
                "Exact search terms to find this specific product"
            ]
        }}
    ]
}}

IMPORTANT:
- Extract the exact product names mentioned in the Perplexity response
- Price values must be numbers only (no currency symbols or commas)
- If price ranges are mentioned, extract min and max values
- Create appropriate search keywords for each product
- Ensure all products are properly categorized

Return ONLY the JSON object, no additional text.
"""

    # Azure OpenAI API call
    url = f"{azure_endpoint}/openai/deployments/{deployment_name}/chat/completions?api-version={api_version}"
    
    headers = {
        "Content-Type": "application/json",
        "api-key": api_key
    }
    
    payload = {
        "messages": [
            {
                "role": "user",
                "content": format_prompt
            }
        ],
        "temperature": 0.1,
        "max_tokens": 4000,
        "response_format": { "type": "json_object" }
    }
    
    try:
        # Make the API request
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        
        # Parse response
        response_data = response.json()
        
        if 'choices' in response_data and len(response_data['choices']) > 0:
            content = response_data['choices'][0]['message']['content']
            
            # Parse the JSON response
            try:
                parsed_data = json.loads(content.strip())
                
                # Validate and clean up the response
                if "product_ideas" in parsed_data:
                    for product in parsed_data["product_ideas"]:
                        # Ensure price range values are numbers
                        price_range = product.get("estimated_price_range", {})
                        try:
                            price_range["min"] = int(float(str(price_range.get("min", 0)).replace('₹', '').replace(',', '').strip()))
                            price_range["max"] = int(float(str(price_range.get("max", 0)).replace('₹', '').replace(',', '').strip()))
                        except (ValueError, TypeError):
                            price_range["min"] = 0
                            price_range["max"] = 0
                        product["estimated_price_range"] = price_range
                
                return parsed_data
                
            except json.JSONDecodeError as e:
                return {
                    "error": f"Failed to parse Azure OpenAI response: {str(e)}",
                    "raw_content": content,
                    "content_length": len(content),
                    "content_repr": repr(content)
                }
                
        else:
            return {"error": "No valid response from Azure OpenAI"}
            
    except requests.exceptions.RequestException as e:
        error_msg = f"Azure OpenAI API request failed: {str(e)}"
        if hasattr(e, 'response') and e.response is not None:
            try:
                error_details = e.response.json()
                error_msg += f" - Details: {error_details}"
            except:
                error_msg += f" - Response: {e.response.text}"
        return {"error": error_msg}
    except Exception as e:
        return {"error": f"Unexpected error: {str(e)}"}