import streamlit as st
import requests
#import openai
import re
import json
from bs4 import BeautifulSoup
from g4f.client import Client
from collections import defaultdict
import imgkit

# from selenium import webdriver
# # Chrome
# # from selenium.webdriver.chrome.service import Service
# # from selenium.webdriver.chrome.options import Options
# # from webdriver_manager.chrome import ChromeDriverManager
# # Firefox
# from selenium.webdriver.firefox.service import Service
# from selenium.webdriver.firefox.options import Options
# from webdriver_manager.firefox import GeckoDriverManager

import time
from PIL import Image
import io

# ---------------------------
# Constants & Configurations
# ---------------------------
BRAND_VOICE_PROFILES = {
    # Original Profiles
    "Humorous": "Witty, playful, meme-aware",
    "Professional": "Authoritative, industry-specific, data-driven",
    "Casual": "Conversational, friendly, approachable",
    "Technical": "Detailed, jargon-rich, precision-focused",
    "Storytelling": "Narrative-driven, emotive, descriptive",
    "SEO-Optimized": "Keyword-focused, meta-aware, structured",
    
    # New Additions
    "Inspirational": "Uplifting, visionary, aspiration-driven",
    "Provocative": "Bold, controversial, boundary-pushing",
    "Minimalist": "Simplified, whitespace-loving, clarity-first",
    "Empathetic": "Compassionate, solution-oriented, audience-first",
    "Urgent": "Time-sensitive, FOMO-driven, action-inducing",
    "Luxury": "Exclusive, sensory-rich, prestige-focused",
    "Youthful": "Trend-riding, slang-friendly, emoji-positive",
    "Whimsical": "Imaginative, metaphor-heavy, rule-breaking",
    "Cultural Commentary": "Socially-aware, current-events-linked, perspective-driven"
}

CONTENT_STRUCTURES = {
    # Original Structures
    "Standard": ["Introduction", "Body", "Conclusion"],
    "Advanced": ["Executive Summary", "Problem Statement", "Solution", "Case Studies", "FAQ"],
    "Product-Focused": ["Features", "Benefits", "Use Cases", "Testimonials", "CTA"],
    
    # New Additions
    "Listicle": ["Hook-Driven Title", "Numbered Items", "Bite-Sized Explanations", "Shareable Takeaways"],
    "Problem-Solution": ["Pain Point Identification", "Root Cause Analysis", "Stepwise Resolution", "Prevention Tips"],
    "Comparative Analysis": ["Contender Overviews", "Feature Grid Comparison", "Strengths/Weaknesses", "Audience-Specific Recommendations"],
    "Case Study Deep Dive": ["Client Background", "Challenge Matrix", "Implementation Timeline", "Quantified Results", "Industry Implications"],
    "Trend Analysis": ["Emergence Timeline", "Key Drivers", "Market Impact", "Future Projections", "Adaptation Strategies"],
    "Interactive Guide": ["Choose-Your-Path Prompts", "Branching Scenarios", "Personalized Outcomes", "Feedback Loops"],
    "Myth-Busting": ["Common Misconceptions", "Fact-Based Corrections", "Expert Citations", "Reality-Check Actions"],
    "Cultural Deep Dive": ["Historical Context", "Current Manifestations", "Subculture Mapping", "Brand Relevance Bridge"]
}

# ---------------------------
# Helper Functions
# ---------------------------
def scrape_website_content(url):
    """Scrape website content using BeautifulSoup."""
    try:
        response = requests.get(url, timeout=15, headers={'User-Agent': 'Mozilla/5.0'})
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        main_content = soup.find('main') or soup.body
        meta_title = soup.title.string if soup.title else ''
        meta_desc_tag = soup.find('meta', attrs={'name': 'description'})
        meta_desc = meta_desc_tag['content'] if meta_desc_tag and meta_desc_tag.get('content') else ''
        content_elements = main_content.find_all(['h1', 'h2', 'h3', 'p', 'li', 'table'])
        cleaned_content = ' '.join([element.get_text(' ', strip=True) 
                                    for element in content_elements 
                                    if len(element.get_text(strip=True)) > 20])
        full_content = f"{meta_title} {meta_desc} {cleaned_content}"
        return re.sub(r'\s+', ' ', full_content)[:3500]
    except Exception as e:
        return f"Scraping Error: {str(e)}"

def scrape_website_content_chatgpt(url):
    """Scrape website content using a ChatGPT-powered prompt (via g4f)."""
    prompt = f"""Please extract the main, unique, and relevant content from the following website URL. Ignore navigation menus, headers, footers, and ads. Return a concise summary suitable for generating a blog post.
URL: {url}"""
    try:
        client = Client()
        response = client.chat.completions.create(
            model="",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            #max_tokens=2000,
            web_search=True
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"ChatGPT Scraping Error: {str(e)}"

def build_advanced_prompt(config, voice_settings, output_type="Text"):
    """Construct a sophisticated prompt for content generation."""
    if config.get('structure') in CONTENT_STRUCTURES:
        structure_text = ", ".join(CONTENT_STRUCTURES[config['structure']])
    else:
        structure_text = config.get('structure', '')
    brand_line = f"Brand Name: {config['brand_name']}\n" if config.get("brand_name") else ""
    if output_type == "HTML":
        additional_prompt = ("Please output the content in valid HTML with semantic tags "
                             "(e.g. use <h3> for subheadings and <p> for paragraphs) and include schema.org microdata where applicable.")
    else:
        additional_prompt = ""
    prompt = f"""
{brand_line}Generate a {config['word_count']}-word {config['content_type'].lower()} for the {config['industry']} industry.
Primary Topic: {config['primary_topic']}
Target Audience: {', '.join(config['audience']) if config['audience'] else 'General'}
Tone: {voice_settings['tone']}
Writing Style: {voice_settings['style']}
Structure: {structure_text}
Seed Keywords: {config['keywords']}
Product Details: {config['product_details']}
Additional Description: {config['additional_desc']}
Advanced Media Integration: {', '.join(config['media_integration']) if config['media_integration'] else 'None'}
Call-to-Action Frequency: {voice_settings['cta_frequency']}
SEO Focus: {voice_settings['seo_intensity']}

{additional_prompt}
    """
    return prompt

def generate_custom_content(prompt, voice_settings):
    """Generate custom content using the chat-based AI."""
    try:
        client = Client()
        response = client.chat.completions.create(
            model="",  # Use GPT-4 model
            messages=[
                {"role": "system", "content": f"You are a {voice_settings['tone']} and {voice_settings['style']} content writer."},
                {"role": "user", "content": prompt}
            ],
            temperature=voice_settings['temperature'],
            max_tokens=4000,
            stop=["</article>"]
        )
        content = response.choices[0].message.content.strip()
        return sanitize_content(content)
    except Exception as e:
        return f"Generation Error: {str(e)}"

def clean_json_string(json_str):
    """Remove non-printable characters and unnecessary whitespace."""
    json_str = json_str.strip()
    json_str = re.sub(r'```json|```', '', json_str, flags=re.MULTILINE)
    return json_str

def generate_seo_metadata(content):
    """Generate comprehensive SEO metadata for the content in JSON."""
    try:
        client = Client()
        prompt = f"""
Generate complete SEO metadata for the following content (use only JSON output):
{content[:3000]}

The JSON output must include the following keys:
- primary_keyword (string)
- lsi_keywords (a comma-separated string of 5 keywords)
- meta_title (string, around 60 characters)
- meta_description (string, around 160 characters)
- slug (SEO-friendly slug)
- schema_markup (a valid JSON-LD string)
- internal_links (an array of 3 URL paths)

Output only the JSON.
"""
        response = client.chat.completions.create(
            model="",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3
        )
        seo_json = response.choices[0].message.content.strip()
        print(seo_json)
        cleaned_json = clean_json_string(seo_json)
        seo_data = json.loads(cleaned_json)
        return seo_data
    except Exception as e:
        print(e)
        return {
            "primary_keyword": "example-keyword",
            "lsi_keywords": "keyword1, keyword2, keyword3, keyword4, keyword5",
            "meta_title": "Example Meta Title",
            "meta_description": "Example meta description for the blog post.",
            "slug": "example-blog-post",
            "schema_markup": "{ 'schema': 'example' }",
            "internal_links": ["/link1", "/link2", "/link3"],
            "error": f"SEO Metadata Generation Error: {str(e)}"
        }

def sanitize_content(html):
    """Sanitize the generated HTML content if needed."""
    return html.replace("```", "")

def generate_blog_title_from_content(content, tone="neutral"):
    prompt = f"""
Based on the following content, generate a concise and compelling blog title that is SEO-optimized. Write the title in a {tone} tone.
Content: {content}
    """
    try:
        client = Client()
        response = client.chat.completions.create(
            model="",
            messages=[
                {"role": "system", "content": "You are a creative content writer."},
                {"role": "user", "content": prompt}
            ],
            temperature=1
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"Error generating title: {str(e)}"

def generate_meta_description(content):
    prompt = f"""
Based on the following content, create an SEO-optimized meta description (up to 130 characters) that is concise and clear.
Content: {content}
    """
    try:
        client = Client()
        response = client.chat.completions.create(
            model="",
            messages=[
                {"role": "system", "content": "You are an SEO expert."},
                {"role": "user", "content": prompt}
            ],
            temperature=1
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"Error generating meta description: {str(e)}"

def generate_meta_title(content):
    prompt = f"""
Create an SEO-optimized meta title for a blog post based on the following content, within a 50-character limit.
Content: {content}
    """
    try:
        client = Client()
        response = client.chat.completions.create(
            model="",
            messages=[
                {"role": "system", "content": "You are an SEO expert."},
                {"role": "user", "content": prompt}
            ],
            temperature=1
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"Error generating meta title: {str(e)}"

def generate_keywords(content):
    prompt = f"""
Based on the following content, generate a list of 5 SEO keywords (comma-separated) with high search volume and low competition.
Content: {content}
    """
    try:
        client = Client()
        response = client.chat.completions.create(
            model="",
            messages=[
                {"role": "system", "content": "You are an SEO expert."},
                {"role": "user", "content": prompt}
            ],
            temperature=1
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"Error generating keywords: {str(e)}"

def generate_blog_slug(title):
    slug = title.lower()
    slug = re.sub(r'[^a-z0-9\s-]', '', slug)
    slug = re.sub(r'[\s-]+', '-', slug)
    return slug.strip('-')

def generate_blog_excerpt(content):
    prompt = f"""
Write a concise excerpt (150-200 characters) summarizing the following blog post content for social media preview:
Content: {content}
    """
    try:
        client = Client()
        response = client.chat.completions.create(
            model="",
            messages=[
                {"role": "system", "content": "You are a creative content writer."},
                {"role": "user", "content": prompt}
            ],
            temperature=1
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"Error generating excerpt: {str(e)}"

def generate_faq_section(content):
    prompt = f"""
Based on the following blog content, generate an FAQ section with 5 common questions and answers.
Format the FAQ in HTML using <h3> for questions and <p> for answers.
Content: {content}
    """
    try:
        client = Client()
        response = client.chat.completions.create(
            model="",
            messages=[
                {"role": "system", "content": "You are a creative content writer."},
                {"role": "user", "content": prompt}
            ],
            temperature=1
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"Error generating FAQ section: {str(e)}"

def generate_schema_markup(content, title):
    prompt = f"""
Generate JSON-LD schema markup for a blog post with the title "{title}".
The blog post is about: {content}
Include: "@context", "@type", "headline", "description", "author", and "datePublished".
    """
    try:
        client = Client()
        response = client.chat.completions.create(
            model="",
            messages=[
                {"role": "system", "content": "You are an SEO expert."},
                {"role": "user", "content": prompt}
            ],
            temperature=1
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"Error generating schema markup: {str(e)}"

def get_screenshot_image2(url, delay=5000):
    try:
        options = {
            'format': 'png',              # Ensure output format
            'quality': 100,               # High quality
            'enable-local-file-access': '', # Fixes issues with some websites
            'javascript-delay': delay,    # Wait for JS to load (in milliseconds)
            'load-error-handling': 'ignore' # Prevents errors from breaking execution
        }

        img = imgkit.from_url(url, False, options=options)
        return img
    except Exception as e:
        return f"Error generating screenshot: {str(e)}"

# Function to capture full-page screenshot
def get_screenshot_image(url):
    try:
        options = {
            "format": "png",
            "quality": 100,
            "enable-local-file-access": "",
            "javascript-delay": 8000,  # Wait longer for JS-heavy sites
            "no-stop-slow-scripts": "",  # Prevent scripts from being stopped
            "load-error-handling": "ignore",  # Ignore minor errors
            "custom-header": [
                ("User-Agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
            ],  # Prevents websites from blocking wkhtmltoimage
            "custom-header-propagation": ""
            #"enable-backgrounds": "",  # Ensures full background images are loaded
        }

        # Generate image from URL
        img_data = imgkit.from_url(url, False, options=options)

        # Convert to an image format that Streamlit supports
        #image = Image.open(BytesIO(img_data))
        return img_data
    except Exception as e:
        return f"Error generating full-page screenshot: {str(e)}"

# def get_screenshot_image_chrome(url, wait_time=5):
#     try:
#         # Set up headless Chrome options
#         chrome_options = Options()
#         chrome_options.add_argument("--headless")  # Run in headless mode
#         chrome_options.add_argument("--window-size=1920x1080")  # Initial window size
#         chrome_options.add_argument("--disable-gpu")  # Disable GPU acceleration
#         chrome_options.add_argument("--no-sandbox")  # Bypass OS security model
#         chrome_options.add_argument("--disable-dev-shm-usage")  # Prevent limited resources issue
#         chrome_options.add_argument("--enable-features=NetworkService,NetworkServiceInProcess")

#         # Use WebDriver Manager to install ChromeDriver
#         driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)

#         # Open the webpage
#         driver.get(url)

#         # Wait for the page to load
#         time.sleep(wait_time)

#         # Get the total height of the page
#         total_height = driver.execute_script("return document.body.scrollHeight")
#         width = driver.execute_script("return document.body.scrollWidth")

#         # Resize the window to capture full height
#         driver.set_window_size(width, total_height)

#         # Take full-page screenshot
#         screenshot_png = driver.get_screenshot_as_png()

#         # Close the browser
#         driver.quit()

#         # Convert PNG data to a PIL image
#         image = Image.open(io.BytesIO(screenshot_png))
#         return image

#     except Exception as e:
#         return f"Error generating full-page screenshot: {str(e)}"

# def get_screenshot_image_firefox(url, wait_time=5):
#     try:
#         # Set up headless Firefox options
#         firefox_options = Options()
#         firefox_options.add_argument("--headless")  # Run in headless mode
#         firefox_options.add_argument("--width=1920")
#         firefox_options.add_argument("--height=1080")

#         # Use WebDriver Manager to install Geckodriver
#         driver = webdriver.Firefox(service=Service(GeckoDriverManager().install()), options=firefox_options)

#         # Open the webpage
#         driver.get(url)

#         # Wait for the page to load
#         time.sleep(wait_time)

#         # Get the total height of the page
#         total_height = driver.execute_script("return document.body.scrollHeight")
#         total_width = driver.execute_script("return document.body.scrollWidth")

#         # Resize the window to fit the full page
#         driver.set_window_size(total_width, total_height)

#         # Wait again for the new size to be applied
#         time.sleep(2)

#         # Take full-page screenshot
#         screenshot_png = driver.get_screenshot_as_png()

#         # Close the browser
#         driver.quit()

#         # Convert PNG data to a PIL image
#         image = Image.open(io.BytesIO(screenshot_png))
#         return image

#     except Exception as e:
#         return f"Error generating full-page screenshot: {str(e)}"

def generate_image_from_title(title):
    prompt = f'Generate a highly realistic image based on the title: "{title}". The image should be detailed, realistic, and exclude any text and relevant for blog posting.'
    try:
        client = Client()
        response = client.images.generate(
            model="midjourney", # flux
            prompt=prompt,
            response_format="url"
        )
        return response.data[0].url
    except Exception as e:
        return f"Error generating image: {str(e)}"

def get_youtube_link(content, youtube_api_key):
    query = f"{content} tutorial walkthrough review"
    base_url = "https://www.googleapis.com/youtube/v3/search"
    params = {
        "part": "snippet",
        "type": "video",
        "maxResults": 1,
        "q": query,
        "key": youtube_api_key
    }
    try:
        response = requests.get(base_url, params=params)
        data = response.json()
        if "items" in data and len(data["items"]) > 0:
            video_id = data["items"][0]["id"]["videoId"]
            return f"https://www.youtube.com/watch?v={video_id}"
        else:
            return "No results found."
    except Exception as e:
        return f"Error fetching YouTube link: {str(e)}"

# ---------------------------
# UI Components
# ---------------------------
def sidebar_config():
    st.sidebar.header("⚙️ Content Studio")
    with st.sidebar.expander("🎭 Brand Voice"):
        tone = st.selectbox("Tone Profile", list(BRAND_VOICE_PROFILES.keys()))
        style = st.selectbox("Writing Style", ["Copywriting", "Academic", "Journalistic", "Conversational", "Technical", "How-to guides", "Affiliate blog"])
        temperature = st.slider("Creativity", 0.0, 1.0, 0.7)
    with st.sidebar.expander("🔧 Advanced Settings"):
        seo_intensity = st.select_slider("SEO Focus", ["Light", "Moderate", "Aggressive"])
        cta_frequency = st.select_slider("CTA Frequency", ["None", "Subtle", "Balanced"])
        media_integration = st.multiselect("Media Types", ["Images", "Videos", "Infographics"])
    api_key = st.sidebar.text_input("OpenAI API Key", type="password", placeholder="Free for you...!!!")
    youtube_api_key = st.sidebar.text_input("YouTube API Key", type="password")
    return {
        "tone": tone,
        "style": style,
        "temperature": temperature,
        "seo_intensity": seo_intensity,
        "cta_frequency": cta_frequency,
        "media_integration": media_integration,
        "api_key": api_key,
        "youtube_api_key": youtube_api_key
    }

def main_input_section():
    st.header("📝 Content Architect")
    cols = st.columns([2, 1])
    with cols[0]:
        website_url = st.text_input("🌐 Source URL", "")
        # New: allow user to choose content source
        content_source = st.radio("Select Base Content Source", ["Website URL", "Custom Blog Post", "Both"])
        primary_topic = st.text_area("🎯 Core Topic", "The Future of Sustainable Fashion Technology")
        industry = st.selectbox("🏭 Industry", ["Fashion", "Tech", "Healthcare", "Education"])
        brand_name = st.text_input("🏢 Brand Name (Optional)", "")
    with cols[1]:
        content_type = st.selectbox("📑 Content Type", ["Blog Post", "Guide", "Case Study", "White Paper"])
        structure = st.selectbox("📐 Structure Profile", list(CONTENT_STRUCTURES.keys()))
        word_count = st.slider("📏 Word Target", 800, 5000, 1500)
        output_type = st.selectbox("🏭 Output Type", ["Text", "HTML"])
    with st.expander("🔑 Content DNA"):
        keywords = st.text_input("🧠 Seed Keywords", "sustainability, fashion tech, eco-materials")
        product_details = st.text_area("🛍 Product Details", "EcoWeave Fabric v2.0 with 50% recycled materials")
        audience = st.multiselect("🎯 Audience", ["Executives", "Developers", "Consumers", "Investors"])
        additional_desc = st.text_area("📝 Additional Description", "Discuss trends, innovations, and future prospects.")
    with st.expander("💡 Advanced Custom Options"):
        youtube_link = st.text_input("YouTube Link (optional)", "")
        image_link = st.text_input("Image Link (optional)", "")
        custom_blog_post = st.text_area("Custom Blog Post Override (HTML)", "")
        blog_title_override = st.text_input("Blog Title Override", "")
        meta_description_override = st.text_input("Meta Description Override", "")
        meta_title_override = st.text_input("Meta Title Override", "")
        seo_keywords_override = st.text_input("SEO Keywords Override", "")
        blog_slug_override = st.text_input("Blog Slug Override", "")
        blog_excerpt_override = st.text_input("Blog Excerpt Override", "")
        faq_section_override = st.text_area("FAQ Section Override (HTML)", "")
        schema_markup_override = st.text_area("Schema Markup Override (JSON-LD)", "")
        youtube_link_manual_override = st.text_input("YouTube Link Override", "")
        image_from_title_override = st.text_input("Image from Title Override (URL)", "")
    return {
        "website_url": website_url,
        "content_source": content_source,
        "primary_topic": primary_topic,
        "industry": industry,
        "brand_name": brand_name,
        "content_type": content_type,
        "structure": structure,
        "word_count": word_count,
        "output_type": output_type,
        "keywords": keywords,
        "product_details": product_details,
        "audience": audience,
        "additional_desc": additional_desc,
        "advanced_options": {
            "youtube_link": youtube_link,
            "image_link": image_link,
            "custom_blog_post": custom_blog_post,
            "blog_title_override": blog_title_override,
            "meta_description_override": meta_description_override,
            "meta_title_override": meta_title_override,
            "seo_keywords_override": seo_keywords_override,
            "blog_slug_override": blog_slug_override,
            "blog_excerpt_override": blog_excerpt_override,
            "faq_section_override": faq_section_override,
            "schema_markup_override": schema_markup_override,
            "youtube_link_manual_override": youtube_link_manual_override,
            "image_from_title_override": image_from_title_override
        }
    }

def display_content_package(content, seo_data, advanced_assets, export_content):
    tab1, tab2, tab3, tab4 = st.tabs(["📄 Content", "🔍 SEO Package", "🛠 Advanced Assets", "📤 Export"])
    with tab1:
        st.subheader("Generated Content")
        st.markdown(content, unsafe_allow_html=True)
    with tab2:
        st.subheader("SEO Package")
        st.write("Primary Keyword:", seo_data.get("primary_keyword", ""))
        st.write("LSI Keywords:", seo_data.get("lsi_keywords", ""))
        st.write("Meta Title:", seo_data.get("meta_title", ""))
        st.write("Meta Description:", seo_data.get("meta_description", ""))
        st.write("Slug:", seo_data.get("slug", ""))
        st.code(seo_data.get("schema_markup", ""), language="json")
        st.write("Internal Links:", ", ".join(seo_data.get("internal_links", [])))
    with tab3:
        st.subheader("Advanced Assets")
        st.write("**Blog Title:**  \n", advanced_assets.get("blog_title", ""))
        st.write("**Meta Title:**  \n", advanced_assets.get("meta_title", ""))
        st.write("**Meta Description:**  \n", advanced_assets.get("meta_description", ""))
        st.write("**SEO Keywords:**  \n", advanced_assets.get("seo_keywords", ""))
        st.write("**Blog Slug:**  \n", advanced_assets.get("blog_slug", ""))
        st.write("**Blog Excerpt:**  \n", advanced_assets.get("blog_excerpt", ""))
        st.markdown("## FAQ Section:")
        st.markdown(advanced_assets.get("faq_section", ""), unsafe_allow_html=True)
        st.code(advanced_assets.get("schema_markup", ""), language="json")
        if advanced_assets.get("screenshot"):
            if isinstance(advanced_assets["screenshot"], bytes):
                st.markdown("## Screenshots from Website:")
                st.image(advanced_assets["screenshot"], use_container_width=True)
            else:
                st.markdown("## Screenshots from Website:")
                st.info(advanced_assets["screenshot"])
        st.markdown("## Generated Image based on Title:")
        if advanced_assets.get("image_from_title") and advanced_assets["image_from_title"].startswith("http"):
            st.image(advanced_assets["image_from_title"])
        st.write("## YouTube Link:", advanced_assets.get("youtube_link", "Not Applicable"))
    with tab4:
        st.subheader("Export Options")
        export_format = st.radio("Format", ["HTML", "Markdown", "PDF"], horizontal=True)
        if st.button("💾 Generate Export"):
            file_data, file_name, mime = generate_export_file(export_format, export_content)
            if file_data:
                st.download_button("Download Exported File", data=file_data, file_name=file_name, mime=mime)
            else:
                st.error("Export failed. Please ensure required libraries are installed.")

def generate_export_file(export_format, export_content):
    combined_html = f"""<html>
  <head>
    <title>Exported Blog Post</title>
    <!-- SEO Metadata:
    {json.dumps(export_content.get('seo', {}), indent=2)}
    -->
  </head>
  <body>
    {export_content.get('content', '')}
  </body>
</html>
"""
    if export_format == "HTML":
        return combined_html, "blog_post.html", "text/html"
    elif export_format == "Markdown":
        try:
            import markdownify
            md = markdownify.markdownify(combined_html, heading_style="ATX")
        except ImportError:
            md = combined_html
        return md, "blog_post.md", "text/markdown"
    elif export_format == "PDF":
        try:
            import pdfkit
            pdf = pdfkit.from_string(combined_html, False)
            return pdf, "blog_post.pdf", "application/pdf"
        except Exception as e:
            st.error(f"PDF generation error: {e}")
            return None, None, None
    else:
        return None, None, None

def handle_multimedia(config):
    """Stub for multimedia integrations (images/videos)"""
    return {
        "images": [],
        "videos": []
    }

# ---------------------------
# Generation Flow with Progress Updates
# ---------------------------
def generate_blog_outputs(inputs, settings):
    # Set API keys
    #openai.api_key = settings.get("api_key", "")
    youtube_api_key = settings.get("youtube_api_key", "")
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    step = 0
    total_steps = 12

    # Step 1: Prepare base content based on user's choice
    status_text.text("Step 1 of 12: Preparing base content...")
    website_url = inputs["website_url"].strip()
    content_source = inputs.get("content_source", "Website URL")
    
    scraped_content = ""
    if content_source in ["Website URL", "Both"] and website_url:
        # Scrape using BeautifulSoup
        bs_content = scrape_website_content(website_url)
        # Scrape using ChatGPT-powered prompt
        cgpt_content = scrape_website_content_chatgpt(website_url)
        scraped_content = bs_content + "\n\n" + cgpt_content

    custom_blog_post = inputs["advanced_options"].get("custom_blog_post", "").strip()
    if content_source == "Custom Blog Post":
        base_content = custom_blog_post
    elif content_source == "Website URL":
        base_content = scraped_content
    elif content_source == "Both":
        # Combine custom blog post and scraped content (custom takes priority)
        base_content = (custom_blog_post + "\n\n" if custom_blog_post else "") + scraped_content
    else:
        base_content = ""
    step += 1
    progress_bar.progress(int(step/total_steps * 100))
    
    # Step 2: Build advanced prompt
    status_text.text("Step 2 of 12: Building prompt...")
    advanced_opts = inputs["advanced_options"]
    config = {
        "primary_topic": inputs["primary_topic"],
        "industry": inputs["industry"],
        "brand_name": inputs.get("brand_name", ""),
        "content_type": inputs["content_type"],
        "structure": inputs["structure"],
        "word_count": inputs["word_count"],
        "keywords": inputs["keywords"],
        "product_details": inputs["product_details"],
        "audience": inputs["audience"],
        "additional_desc": inputs["additional_desc"],
        "media_integration": advanced_opts.get("image_link") and ["Images"] or []
    }
    output_type = inputs["output_type"] or "Text"
    prompt = build_advanced_prompt(config, settings, output_type)
    step += 1
    progress_bar.progress(int(step/total_steps * 100))
    
    # Step 3: Generate core content via GPT
    status_text.text("Step 3 of 12: Generating core content via GPT...")
    generated_content = generate_custom_content(prompt, settings)
    step += 1
    progress_bar.progress(int(step/total_steps * 100))
    
    # Step 4: Generate additional assets using helper functions
    status_text.text("Step 4 of 12: Generating additional assets...")
    step += 1
    progress_bar.progress(int(step/total_steps * 100))
    
    # Use the custom blog post override if provided; otherwise, use generated content
    custom_blog_post = advanced_opts.get("custom_blog_post").strip() or generated_content
    # Here base_content is already set based on the content source selection
    base_content = custom_blog_post if content_source == "Custom Blog Post" else base_content
    
    status_text.text("Step 5 of 12: Generating blog title...")
    auto_blog_title = base_content and generate_blog_title_from_content(base_content, tone=settings["tone"]) or ""
    step += 1
    progress_bar.progress(int(step/total_steps * 100))
    
    status_text.text("Step 6 of 12: Generating meta description...")
    auto_meta_desc = base_content and generate_meta_description(base_content) or ""
    step += 1
    progress_bar.progress(int(step/total_steps * 100))
    
    status_text.text("Step 7 of 12: Generating meta title...")
    auto_meta_title = base_content and generate_meta_title(base_content) or ""
    step += 1
    progress_bar.progress(int(step/total_steps * 100))
    
    status_text.text("Step 8 of 12: Generating SEO keywords...")
    auto_seo_keywords = base_content and generate_keywords(base_content) or ""
    step += 1
    progress_bar.progress(int(step/total_steps * 100))
    
    status_text.text("Step 9 of 12: Generating blog slug...")
    auto_blog_slug = auto_blog_title and generate_blog_slug(auto_blog_title) or ""
    step += 1
    progress_bar.progress(int(step/total_steps * 100))
    
    status_text.text("Step 10 of 12: Generating blog excerpt...")
    auto_blog_excerpt = base_content and generate_blog_excerpt(base_content) or ""
    step += 1
    progress_bar.progress(int(step/total_steps * 100))
    
    status_text.text("Step 11 of 12: Generating FAQ section and schema markup...")
    auto_faq_section = base_content and generate_faq_section(base_content) or ""
    auto_schema_markup = (base_content and auto_blog_title) and generate_schema_markup(base_content, auto_blog_title) or ""
    step += 1
    progress_bar.progress(int(step/total_steps * 100))
    
    # Step 12: Generate SEO metadata package and handle multimedia
    status_text.text("Step 12 of 12: Generating SEO metadata and handling multimedia...")
    seo_data = base_content and generate_seo_metadata(base_content) or {}
    multimedia = handle_multimedia(inputs)
    step += 1
    progress_bar.progress(int(step/total_steps * 100))
    
    status_text.text("All steps completed!")
    
    advanced_assets = {
        "blog_title": advanced_opts.get("blog_title_override").strip() or auto_blog_title,
        "meta_description": advanced_opts.get("meta_description_override").strip() or auto_meta_desc,
        "meta_title": advanced_opts.get("meta_title_override").strip() or auto_meta_title,
        "seo_keywords": advanced_opts.get("seo_keywords_override").strip() or auto_seo_keywords,
        "blog_slug": advanced_opts.get("blog_slug_override").strip() or auto_blog_slug,
        "blog_excerpt": advanced_opts.get("blog_excerpt_override").strip() or auto_blog_excerpt,
        "faq_section": advanced_opts.get("faq_section_override").strip() or auto_faq_section,
        "schema_markup": advanced_opts.get("schema_markup_override").strip() or auto_schema_markup,
        "youtube_link": advanced_opts.get("youtube_link_manual_override").strip() or advanced_opts.get("youtube_link").strip(),
        "image_from_title": advanced_opts.get("image_from_title_override").strip() or (auto_blog_title and generate_image_from_title(auto_blog_title) or ""),
        "screenshot": website_url and get_screenshot_image(website_url) or ""
    }
    
    outputs = {
        "Custom Blog Post": custom_blog_post,
        "SEO Package": seo_data,
        "Advanced Assets": advanced_assets,
        "Scraped Content": scraped_content,
        "Generated Content": generated_content,
        "Multimedia": multimedia
    }
    return outputs

# ---------------------------
# Main App Execution
# ---------------------------
def main():
    st.set_page_config(page_title="Advanced Blog & Content Studio", layout="wide", page_icon="🧠")
    
    settings = sidebar_config()
    
    with st.form("content_form"):
        inputs = main_input_section()
        submitted = st.form_submit_button("🚀 Generate Content Masterpiece")
    
    if submitted:
        with st.spinner("🧠 Generating content and assets..."):
            outputs = generate_blog_outputs(inputs, settings)
            st.session_state["content_package"] = outputs
        st.success("Content generation completed!")
    
    if "content_package" in st.session_state:
        pkg = st.session_state["content_package"]
        export_content = {
            "content": pkg.get("Custom Blog Post", ""),
            "seo": pkg.get("SEO Package", {})
        }
        display_content_package(pkg["Custom Blog Post"], pkg["SEO Package"], pkg["Advanced Assets"], export_content)

if __name__ == "__main__":
    main()
