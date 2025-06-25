import asyncio
import json
import streamlit as st
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode, LLMConfig
from crawl4ai.extraction_strategy import LLMExtractionStrategy
from crawl4ai.content_scraping_strategy import WebScrapingStrategy

class Product(BaseModel):
    # Basic Product Info
    product: str = Field(..., description="Product name or title")
    brand: str = Field(..., description="Brand or manufacturer")
    product_description: str = Field(..., description="Detailed product description")
    everything_you_need_to_know: str = Field(default="", description="Comprehensive product information and specifications")
    why_we_love_it: str = Field(default="", description="Key selling points and unique features")
    price: str = Field(..., description="Current price of the product in INR without any currency symbol")
    website: str = Field(default="", description="Website or platform where product is sold")
    delivery_timeline: str = Field(default="", description="Expected delivery time")
    image_links: List[str] = Field(default_factory=list, description="List of product image URLs")
    
    # Demographics
    age_kids: str = Field(default="", description="Age range if product is for kids")
    gender: str = Field(default="", description="Target gender (Men/Women/Unisex/Kids)")
    price_bracket: str = Field(default="", description="Price category (Budget/Mid-range/Premium/Luxury)")
    cities: str = Field(default="", description="Cities where product is available")
    
    # Style & Occasion
    occasion: str = Field(default="", description="Suitable occasions for the product")
    style_tags: str = Field(default="", description="Style categories and tags")
    personas: str = Field(default="", description="Target customer personas")
    
    # Suitable Occasions (Boolean)
    valentines: bool = Field(default=False, description="Suitable for Valentine's Day")
    baby_shower: bool = Field(default=False, description="Suitable for Baby Shower")
    anniversaries_weddings: bool = Field(default=False, description="Suitable for Anniversaries & Weddings")
    birthdays: bool = Field(default=False, description="Suitable for Birthdays")
    house_warmings: bool = Field(default=False, description="Suitable for House Warmings")
    festivals: bool = Field(default=False, description="Suitable for Festivals")
    
    # Personality Suited (Boolean)
    fitness_sports_enthusiast: bool = Field(default=False, description="Suited for Fitness/Sports Enthusiasts")
    aesthete: bool = Field(default=False, description="Suited for Aesthetes")
    minimalist_functional: bool = Field(default=False, description="Suited for Minimalist/Functional personalities")
    maximalist: bool = Field(default=False, description="Suited for Maximalists")
    fashionable: bool = Field(default=False, description="Suited for Fashionable personalities")
    foodie: bool = Field(default=False, description="Suited for Foodies")
    wellness_seeker: bool = Field(default=False, description="Suited for Wellness Seekers")
    new_parent: bool = Field(default=False, description="Suited for New Parents")
    teenagers: bool = Field(default=False, description="Suited for Teenagers")
    working_professionals: bool = Field(default=False, description="Suited for Working Professionals")
    parents: bool = Field(default=False, description="Suited for Parents")
    bride_groom_to_be: bool = Field(default=False, description="Suited for Bride/Groom to be")


async def extract_product_data(
    url: str,
    azure_provider: str = "azure/gpt-4o",
    api_token: str = "",
    base_url: str = "",
    show_usage: bool = False
) -> Dict[str, Any]:
    """
    Extract comprehensive product data from a product page URL.
    
    Args:
        url: Product page URL to crawl
        azure_provider: Azure provider format (e.g., "azure/gpt-4o")
        api_token: Azure OpenAI API token
        base_url: Azure OpenAI base URL
        show_usage: Whether to show token usage stats
        
    Returns:
        Dict containing extracted product data or error information
    """
    try:
        import os
        
        # Set environment variables for Streamlit Cloud
        os.environ['PLAYWRIGHT_BROWSERS_PATH'] = '/tmp/playwright'
        
        # Configure LLM
        llm_config = LLMConfig(
            provider=azure_provider,
            api_token=api_token,
            base_url=base_url
        )
        
        llm_strategy = LLMExtractionStrategy(
            llm_config=llm_config,
            schema=Product.model_json_schema(),
            extraction_type="schema",
            instruction="""Extract comprehensive product information from this product page and analyze it to fill ALL fields:

            BASIC INFO: Extract product name, brand, detailed description, specifications, key selling points, price (always should be in INR), website, delivery info.

            PRODUCT DESCRIPTION: Extract the product description as it isfrom the page.

            EVERYTHING YOU NEED TO KNOW: Specific details about the products as it is from the page.
            
            IMAGE LINKS: Extract ONLY product-related image URLs from the page. Focus on main product images, product gallery images, product zoom images, and product variant images. EXCLUDE logos, banners, ads, navigation icons, or any non-product images. Include only full URLs of images that show the actual product being sold.
            
            DEMOGRAPHICS: Determine target gender, age range (if for kids), price bracket (Budget/Mid-range/Premium/Luxury), and available cities.
            
            STYLE & OCCASIONS: Identify suitable occasions, style tags, and target personas.
            
            BOOLEAN OCCASIONS: Analyze if product is suitable for:
            - Valentine's Day, Baby Shower, Anniversaries & Weddings, Birthdays, House Warmings, Festivals
            
            BOOLEAN PERSONALITIES: Determine if product suits these personality types:
            - Fitness/Sports Enthusiast, Aesthete, Minimalist/Functional, Maximalist, Fashionable, Foodie, Wellness Seeker, New Parent, Teenagers, Working Professionals, Parents, Bride/Groom to be
            
            Be analytical and thoughtful about the boolean fields - consider the product type, style, and use case.
            Return only ONE comprehensive product object.""",
            chunk_token_threshold=3000,
            overlap_rate=0.1,
            apply_chunking=False,
            input_format="markdown",
            extra_args={"temperature": 0.0, "max_tokens": 2000}
        )

        # Build crawler config with Streamlit Cloud optimizations
        crawl_config = CrawlerRunConfig(
            extraction_strategy=llm_strategy,
            cache_mode=CacheMode.BYPASS,
            word_count_threshold=20000,  # ~80k tokens (4 chars per token, ~5 chars per word)
            only_text=True,  # Extract only text content
            remove_overlay_elements=True,  # Remove popups, ads, etc.
            magic=False,  # Disable smart content extraction
            page_timeout=45000,  # Reduced timeout for cloud environment
            delay_before_return_html=1.0  # Reduced delay
        )

        # Create browser config with cloud-optimized settings
        browser_cfg = BrowserConfig(
            headless=True,
            browser_type="chromium",
            user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )

        async with AsyncWebCrawler(config=browser_cfg) as crawler:
            result = await crawler.arun(url=url, config=crawl_config)

            if result.success:
                data = json.loads(result.extracted_content)
                
                # Handle case where data is a list (take first item) or dict
                if isinstance(data, list):
                    if len(data) > 0:
                        product_data = data[0]
                    else:
                        return {"success": False, "error": "No products found in extracted data"}
                else:
                    product_data = data

                if show_usage:
                    llm_strategy.show_usage()

                return {
                    "success": True,
                    "data": product_data,
                    "url": url
                }
            else:
                return {
                    "success": False,
                    "error": f"Crawling failed: {result.error_message}",
                    "url": url
                }
                
    except ImportError as e:
        return {
            "success": False,
            "error": f"Missing dependencies: {str(e)}",
            "url": url
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Extraction error: {str(e)}",
            "url": url
        }


def extract_product_sync(
    url: str,
    azure_provider: str = "azure/gpt-4o",
    api_token: str = "",
    base_url: str = "",
    show_usage: bool = False
) -> Dict[str, Any]:
    """
    Synchronous wrapper for extract_product_data.
    
    Args:
        url: Product page URL to crawl
        azure_provider: Azure provider format (e.g., "azure/gpt-4o")
        api_token: Azure OpenAI API token
        base_url: Azure OpenAI base URL
        show_usage: Whether to show token usage stats
        
    Returns:
        Dict containing extracted product data or error information
    """
    return asyncio.run(extract_product_data(url, azure_provider, api_token, base_url, show_usage))


async def main():
    """Example usage - only runs when script is executed directly"""
    # Example configuration
    url = "https://www.amazon.in/JBL-Bluetooth-Dustproof-PartyBoost-Personalization/dp/B09V7WS4PP?th=1"
    azure_provider = "azure/gpt-4o"
    api_token = st.secrets["api_keys"]["azure_openai"]
    base_url = st.secrets["azure_openai"]["endpoint"]
    
    result = await extract_product_data(url, azure_provider, api_token, base_url, show_usage=True)
    
    if result["success"]:
        print(json.dumps(result["data"], indent=2, ensure_ascii=False))
    else:
        print(f"Error: {result['error']}")


if __name__ == "__main__":
    asyncio.run(main())