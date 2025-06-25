import streamlit as st
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from openai_calls import parse_gift_request, format_perplexity_output
from perplexity_calls import generate_product_ideas
from serpcalls import get_product_links
from llmextract import extract_product_sync
import datetime
import subprocess
import sys

# Page configuration
st.set_page_config(
    page_title="AI Gift Recommender",
    page_icon="🎁",
    layout="wide"
)

# Install Playwright browsers on first run (for Streamlit Cloud)
@st.cache_resource
def install_playwright():
    try:
        # Only install chromium browser (dependencies handled by packages.txt)
        subprocess.run([sys.executable, "-m", "playwright", "install", "chromium"], 
                      check=True, capture_output=True, text=True)
        return True
    except subprocess.CalledProcessError as e:
        st.error(f"Playwright browser installation failed: {e.stderr}")
        return False
    except Exception as e:
        st.error(f"Unexpected error installing Playwright: {e}")
        return False

# Install browsers

# Title and description
st.title("🎁 AI-Powered Gift Recommender")

# Main interface
user_input = st.text_area(
    "Describe your gift requirements:",
    placeholder="Example: Looking for a birthday gift for my dad who loves gardening under ₹2000",
    help="Provide details like occasion, recipient, interests, and budget"
)

if st.button("🔍 Find Gift Ideas", type="primary"):
    if not user_input:
        st.error("Please enter your gift requirements!")
        st.stop()
    
    # Process the request
    with st.spinner("Analyzing your request..."):
        progress_bar = st.progress(0)
        # Parse the request using Azure OpenAI
        parsed_request = parse_gift_request(user_input)
        progress_bar.progress(0.2)
        if "error" in parsed_request:
            st.error(f"Error analyzing request: {parsed_request['error']}")
            st.stop()
        st.write(f"✅ [{datetime.datetime.now().strftime('%H:%M:%S')}] Parsed request using Azure OpenAI")
        
        perplexity_recommendations = generate_product_ideas(user_input, parsed_request)
        progress_bar.progress(0.4)
        if "error" in perplexity_recommendations:
            st.error(f"Error generating product ideas: {perplexity_recommendations['error']}")
            st.stop()
        st.write(f"✅ [{datetime.datetime.now().strftime('%H:%M:%S')}] Generated product ideas using Perplexity")
        
        formatted_output = format_perplexity_output(perplexity_recommendations)
        progress_bar.progress(0.6)
        if "error" in formatted_output:
            st.error(f"Error formatting product ideas: {formatted_output['error']}")
            st.stop()
        st.write(f"✅ [{datetime.datetime.now().strftime('%H:%M:%S')}] Formatted output using Azure OpenAI")

        results = {
            "products": [
                {"name": product.get("name", "")} for product in formatted_output.get("product_ideas", [])
            ]
        }


        # Process products in parallel
        length = len(results["products"])
        with ThreadPoolExecutor(max_workers=10) as executor:
            future_to_product = {executor.submit(get_product_links, product["name"]): product for product in results["products"]}
            count = 0
            for future in as_completed(future_to_product):
                product = future_to_product[future]
                product["link"] = future.result()
                count += 1
                if count % 2 == 0 or count == length:  # Show progress every 2 products or at the end
                    st.write(f"🔍 [{datetime.datetime.now().strftime('%H:%M:%S')}] Processed {count} of {length} products")
        st.write(f"✅ [{datetime.datetime.now().strftime('%H:%M:%S')}] Fetched product links using SerpAPI")
        progress_bar.progress(0.8)

        # Extract product metadata in parallel
        with ThreadPoolExecutor(max_workers=10) as executor:
            future_to_product = {
                executor.submit(
                    lambda p: extract_product_sync(
                        p["link"],
                        azure_provider="azure/gpt-4o",
                        api_token=st.secrets["api_keys"]["azure_openai"],
                        base_url=st.secrets["azure_openai"]["endpoint"]
                    ) if "link" in p and p["link"] else {"success": False, "error": "No link available"},
                    product
                ): product 
                for product in results["products"]
            }
            metadata_count = 0
            for future in as_completed(future_to_product):
                product = future_to_product[future]
                try:
                    metadata = future.result()
                    if metadata.get("success"):
                        product["metadata"] = metadata["data"]
                    else:
                        product["metadata"] = None
                except Exception as e:
                    product["metadata"] = {
                        "success": False,
                        "error": f"Extraction failed: {str(e)}",
                        "url": product.get("link", "")
                    }
                metadata_count += 1
                if metadata_count % 2 == 0 or metadata_count == len(results['products']):  # Show progress every 2 extractions
                    st.write(f"📊 [{datetime.datetime.now().strftime('%H:%M:%S')}] Extracted metadata for {metadata_count} of {len(results['products'])} products")
        st.write(f"✅ [{datetime.datetime.now().strftime('%H:%M:%S')}] Extracted product metadata using crawl4ai")
        progress_bar.progress(1.0)

        # Display results in a nice format
        st.success("🎉 Found amazing gift recommendations for you!")
        st.markdown("---")
        
        for i, product in enumerate(results["products"]):
            # Create a styled card container
            with st.container():
                st.markdown(f"""
                <div style="
                    background: #2E86AB;
                    padding: 20px;
                    border-radius: 12px;
                    margin: 20px 0;
                    box-shadow: 0 4px 16px rgba(46, 134, 171, 0.2);
                ">
                    <h2 style="color: white; margin: 0; font-size: 24px;">🎁 Gift Option #{i+1}</h2>
                </div>
                """, unsafe_allow_html=True)
                
                # Create columns for layout
                col1, col2 = st.columns([1, 2])
                
                with col1:
                    # Display product image with styling
                    if product.get("metadata") and product["metadata"] and product["metadata"].get("image_links"):
                        image_links = product["metadata"]["image_links"]
                        if image_links and len(image_links) > 0:
                            try:
                                st.image(image_links[0], width=200, caption="📸 Product Image")
                            except:
                                st.image("https://via.placeholder.com/200x200?text=No+Image", width=200)
                        else:
                            st.image("https://via.placeholder.com/200x200?text=No+Image", width=200)
                    else:
                        st.image("https://via.placeholder.com/200x200?text=No+Image", width=200)
                
                with col2:
                    # Product name with styling
                    st.markdown(f"""
                    <h3 style="
                        color: #2E86AB;
                        font-size: 28px;
                        margin: 0 0 15px 0;
                        font-weight: bold;
                    ">🏷️ {product.get("name", "Unknown Product")}</h3>
                    """, unsafe_allow_html=True)
                    
                    # Brand and price with consistent styling
                    if product.get("metadata") and product["metadata"]:
                        brand = product["metadata"].get("brand", "Unknown Brand")
                        price = product["metadata"].get("price", "Price not available")
                        
                        col_brand, col_price = st.columns(2)
                        with col_brand:
                            st.markdown(f"""
                            <div style="
                                background: #f8f9fa;
                                padding: 10px;
                                border-radius: 8px;
                                border-left: 4px solid #2E86AB;
                            ">
                                <strong style="color: #2E86AB;">🏢 Brand:</strong><br>
                                <span style="font-size: 18px; color: #495057;">{brand}</span>
                            </div>
                            """, unsafe_allow_html=True)
                        
                        with col_price:
                            price_display = f"₹{price}" if price != "Price not available" else price
                            st.markdown(f"""
                            <div style="
                                background: #f8f9fa;
                                padding: 10px;
                                border-radius: 8px;
                                border-left: 4px solid #6c757d;
                            ">
                                <strong style="color: #6c757d;">💰 Price:</strong><br>
                                <span style="font-size: 18px; color: #495057; font-weight: bold;">{price_display}</span>
                            </div>
                            """, unsafe_allow_html=True)
                    
                    st.markdown("<br>", unsafe_allow_html=True)
                    
                    # Product link with cool button
                    if product.get("link"):
                        st.markdown(f"""
                        <a href="{product['link']}" target="_blank" style="
                            background: #2E86AB;
                            color: white;
                            padding: 12px 24px;
                            text-decoration: none;
                            border-radius: 8px;
                            font-weight: bold;
                            display: inline-block;
                            margin: 10px 0;
                            box-shadow: 0 2px 8px rgba(46, 134, 171, 0.3);
                            transition: all 0.2s;
                        " onmouseover="this.style.background='#1f5f7a'; this.style.transform='translateY(-2px)'" onmouseout="this.style.background='#2E86AB'; this.style.transform='translateY(0)'">
                            🛒 View Product
                        </a>
                        """, unsafe_allow_html=True)
                    
                    # Product description or error
                    if product.get("metadata") and product["metadata"]:
                        # Check if there's an error in metadata
                        if product["metadata"].get("success") == False or product["metadata"].get("error"):
                            error_msg = product["metadata"].get("error", "Unknown error occurred during extraction")
                            st.markdown(f"""
                            <div style="
                                background: #fff3cd;
                                padding: 15px;
                                border-radius: 8px;
                                margin: 15px 0;
                                border-left: 4px solid #ffc107;
                            ">
                                <strong style="color: #856404;">⚠️ Error:</strong><br>
                                <span style="color: #856404; line-height: 1.6;">{error_msg}</span>
                            </div>
                            """, unsafe_allow_html=True)
                        elif product["metadata"].get("product_description"):
                            st.markdown(f"""
                            <div style="
                                background: #f8f9fa;
                                padding: 15px;
                                border-radius: 8px;
                                margin: 15px 0;
                                border-left: 4px solid #2E86AB;
                            ">
                                <strong style="color: #2E86AB;">📝 Description:</strong><br>
                                <span style="color: #495057; line-height: 1.6;">{product["metadata"]["product_description"]}</span>
                            </div>
                            """, unsafe_allow_html=True)
                    else:
                        # No metadata available
                        st.markdown(f"""
                        <div style="
                            background: #f8d7da;
                            padding: 15px;
                            border-radius: 8px;
                            margin: 15px 0;
                            border-left: 4px solid #dc3545;
                        ">
                            <strong style="color: #721c24;">❌ Error:</strong><br>
                            <span style="color: #721c24; line-height: 1.6;">No product information could be extracted</span>
                        </div>
                        """, unsafe_allow_html=True)
                
                # Expandable details section with cool styling
                if product.get("metadata") and product["metadata"]:
                    with st.expander("🔍 View Complete Details", expanded=False):
                        metadata = product["metadata"]
                        
                        # Tabs for organized information
                        tab1, tab2, tab3 = st.tabs(["📋 Product Info", "🎯 Suitability", "📸 Images"])
                        
                        with tab1:
                            st.markdown("### 📋 Complete Product Information")
                            
                            # Basic product info in styled containers
                            info_items = [
                                ("🏷️ Product", metadata.get("product")),
                                ("📝 Description", metadata.get("product_description")),
                                ("💡 Everything You Need to Know", metadata.get("everything_you_need_to_know")),
                                ("❤️ Why We Love It", metadata.get("why_we_love_it")),
                                ("🌐 Website", metadata.get("website")),
                                ("🚚 Delivery Timeline", metadata.get("delivery_timeline"))
                            ]
                            
                            for icon_title, value in info_items:
                                if value:
                                    st.markdown(f"""
                                    <div style="
                                        background: #f8f9fa;
                                        padding: 15px;
                                        border-radius: 10px;
                                        margin: 10px 0;
                                        border-left: 4px solid #2E86AB;
                                    ">
                                        <strong style="color: #2E86AB;">{icon_title}:</strong><br>
                                        <span style="color: #495057;">{value}</span>
                                    </div>
                                    """, unsafe_allow_html=True)
                            
                            # Demographics in columns
                            st.markdown("### 👥 Demographics")
                            demo_col1, demo_col2 = st.columns(2)
                            
                            with demo_col1:
                                demo_items = [
                                    ("👶 Age (Kids)", metadata.get('age_kids', 'N/A')),
                                    ("⚧️ Gender", metadata.get('gender', 'N/A')),
                                    ("💰 Price Bracket", metadata.get('price_bracket', 'N/A'))
                                ]
                                for icon_title, value in demo_items:
                                    st.markdown(f"**{icon_title}:** {value}")
                            
                            with demo_col2:
                                demo_items2 = [
                                    ("🏙️ Cities", metadata.get('cities', 'N/A')),
                                    ("🎉 Occasion", metadata.get('occasion', 'N/A')),
                                    ("🏷️ Style Tags", metadata.get('style_tags', 'N/A'))
                                ]
                                for icon_title, value in demo_items2:
                                    st.markdown(f"**{icon_title}:** {value}")
                            
                            st.markdown(f"**👤 Personas:** {metadata.get('personas', 'N/A')}")
                        
                        with tab2:
                            st.markdown("### 🎯 Suitability Analysis")
                            
                            # Boolean occasions with consistent styling
                            st.markdown("#### 🎊 Suitable Occasions")
                            occasion_items = [
                                ("💕 Valentine's", metadata.get('valentines', False)),
                                ("🍼 Baby Shower", metadata.get('baby_shower', False)),
                                ("💒 Anniversaries & Weddings", metadata.get('anniversaries_weddings', False)),
                                ("🎂 Birthdays", metadata.get('birthdays', False)),
                                ("🏠 House Warmings", metadata.get('house_warmings', False)),
                                ("🎆 Festivals", metadata.get('festivals', False))
                            ]
                            
                            occasion_cols = st.columns(3)
                            for i, (icon_title, value) in enumerate(occasion_items):
                                with occasion_cols[i % 3]:
                                    bg_color = "#e8f4f8" if value else "#f8f9fa"
                                    border_color = "#2E86AB" if value else "#dee2e6"
                                    text_color = "#2E86AB" if value else "#6c757d"
                                    status = "✅ Yes" if value else "⚪ No"
                                    st.markdown(f"""
                                    <div style="
                                        background: {bg_color};
                                        padding: 8px;
                                        border-radius: 8px;
                                        margin: 5px 0;
                                        border-left: 3px solid {border_color};
                                    ">
                                        <strong style="color: {text_color};">{icon_title}:</strong><br>
                                        <span style="color: {text_color};">{status}</span>
                                    </div>
                                    """, unsafe_allow_html=True)
                        
                            # Boolean personalities
                            st.markdown("#### 👥 Suitable Personalities")
                            personality_items = [
                                ("🏃 Fitness/Sports Enthusiast", metadata.get('fitness_sports_enthusiast', False)),
                                ("🎨 Aesthete", metadata.get('aesthete', False)),
                                ("⚡ Minimalist/Functional", metadata.get('minimalist_functional', False)),
                                ("🌟 Maximalist", metadata.get('maximalist', False)),
                                ("👗 Fashionable", metadata.get('fashionable', False)),
                                ("🍕 Foodie", metadata.get('foodie', False)),
                                ("🧘 Wellness Seeker", metadata.get('wellness_seeker', False)),
                                ("👶 New Parent", metadata.get('new_parent', False)),
                                ("🎮 Teenagers", metadata.get('teenagers', False)),
                                ("💼 Working Professionals", metadata.get('working_professionals', False)),
                                ("👨‍👩‍👧‍👦 Parents", metadata.get('parents', False)),
                                ("💒 Bride/Groom to be", metadata.get('bride_groom_to_be', False))
                            ]
                            
                            personality_cols = st.columns(2)
                            for i, (icon_title, value) in enumerate(personality_items):
                                with personality_cols[i % 2]:
                                    bg_color = "#e8f4f8" if value else "#f8f9fa"
                                    border_color = "#2E86AB" if value else "#dee2e6"
                                    text_color = "#2E86AB" if value else "#6c757d"
                                    status = "✅ Yes" if value else "⚪ No"
                                    st.markdown(f"""
                                    <div style="
                                        background: {bg_color};
                                        padding: 8px;
                                        border-radius: 8px;
                                        margin: 5px 0;
                                        border-left: 3px solid {border_color};
                                    ">
                                        <strong style="color: {text_color};">{icon_title}:</strong><br>
                                        <span style="color: {text_color};">{status}</span>
                                    </div>
                                    """, unsafe_allow_html=True)
                        
                        with tab3:
                            st.markdown("### 📸 Product Images Gallery")
                            
                            if metadata.get("image_links") and len(metadata["image_links"]) > 0:
                                # Display all images in a grid
                                num_images = len(metadata["image_links"])
                                cols_per_row = 3
                                for i in range(0, num_images, cols_per_row):
                                    cols = st.columns(cols_per_row)
                                    for j, col in enumerate(cols):
                                        if i + j < num_images:
                                            with col:
                                                try:
                                                    st.image(metadata["image_links"][i + j], width=150)
                                                    st.caption(f"📷 Image {i + j + 1}")
                                                except:
                                                    st.error(f"❌ Image {i + j + 1}: Failed to load")
                            else:
                                st.info("📷 No product images available")
                else:
                    st.error("⚠️ Detailed information not available for this product")
                
                # Clean separator
                st.markdown("""
                <div style="
                    height: 2px;
                    background: #dee2e6;
                    margin: 30px 0;
                    border-radius: 1px;
                "></div>
                """, unsafe_allow_html=True)