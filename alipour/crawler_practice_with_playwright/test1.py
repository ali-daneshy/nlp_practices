import re
import requests
import xml.etree.ElementTree as ET
from urllib.parse import urljoin
from playwright.sync_api import Playwright, sync_playwright, expect
import time

def extract_links_from_xml(xml_source, is_url=True, custom_tags=None, custom_attrs=None):
    """
    Extract all links from an XML file or URL, handling namespaces.
    Args:
        xml_source (str): Path to XML file or URL of the XML content
        is_url (bool): True if xml_source is a URL, False if it's a local file
        custom_tags (list): Additional XML tags to check for links (e.g., ['loc'])
        custom_attrs (list): Additional XML attributes to check for links
    Returns:
        list: List of unique links found in the XML
    """
    # Default tags and attributes
    default_tags = ['loc', 'a', 'link', 'url']  # loc first for sitemaps
    default_attrs = ['href', 'src', 'url']
    
    # Combine default and custom tags/attributes
    link_tags = default_tags + (custom_tags or [])
    link_attributes = default_attrs + (custom_attrs or [])
    
    # Sitemap namespace
    namespace = {'sitemap': 'http://www.sitemaps.org/schemas/sitemap/0.9'}
    
    links = set()
    
    try:
        # Fetch XML content from URL or read from file
        if is_url:
            print(f"Fetching XML from URL: {xml_source}")
            response = requests.get(xml_source)
            response.raise_for_status()
            xml_content = response.text
        else:
            print(f"Reading XML from file: {xml_source}")
            with open(xml_source, 'r', encoding='utf-8') as file:
                xml_content = file.read()

        # Parse XML content
        print("Parsing XML content...")
        root = ET.fromstring(xml_content)
        
        # Recursive function to find links in elements
        def find_links(element, depth=0):
            indent = "  " * depth
            tag_name = element.tag.split('}')[-1]  # Strip namespace
            print(f"{indent}Checking element: {element.tag} (local: {tag_name})")
            
            # Check attributes for links
            for attr in link_attributes:
                if attr in element.attrib:
                    link = element.attrib[attr]
                    if link:
                        print(f"{indent}Found link in attribute '{attr}': {link}")
                        if is_url:
                            link = urljoin(xml_source, link)
                        links.add(link)

            # Check for link-like tags (namespace-aware)
            for tag in link_tags:
                if tag_name == tag or element.tag == f"{{http://www.sitemaps.org/schemas/sitemap/0.9}}{tag}":
                    if element.text and element.text.strip():
                        print(f"{indent}Found link in tag '{tag}': {element.text.strip()}")
                        links.add(element.text.strip())

            # Recursively check child elements
            for child in element:
                find_links(child, depth + 1)

        # Start parsing from root
        find_links(root)
        print(f"Total unique links found: {len(links)}")
        return sorted(list(links))

    except requests.exceptions.RequestException as e:
        print(f"Error fetching URL: {e}")
        return []
    except ET.ParseError as e:
        print(f"Error parsing XML: {e}")
        return []
    except FileNotFoundError as e:
        print(f"File not found: {e}")
        return []
    except Exception as e:
        print(f"Unexpected error: {e}")
        return []

def run(playwright: Playwright) -> None:
    browser = playwright.firefox.launch(headless=False)
    context = browser.new_context()
    page = context.new_page()

    try:
        print("Navigating to Zoomit homepage...")
        page.goto('https://www.zoomit.ir/')
        time.sleep(5)  # Reduced wait time for efficiency
        try:
            page.get_by_role("button", name="Close overlay").click()
            print("Closed overlay")
        except Exception as e:
            print("No overlay found or error closing overlay:", e)

        for i in range(20):
            xml_url = f"https://www.zoomit.ir/sitemap/article-{i+1}.xml"
            print(f"\nProcessing sitemap: {xml_url}")
            links = extract_links_from_xml(xml_url, is_url=True)
            if not links:
                print(f"No links found in {xml_url}")
                continue
            for link in links:
                try:
                    print(f"Visiting: {link}")
                    page.goto(link, timeout=30000)  # 30-second timeout
                    time.sleep(1)  # Brief pause to ensure page load
                    title = page.locator('h1.sc-9996cfc-0.ieMlRF').inner_text()
                    print(f"Title: {title}")
                    time.sleep(1)  # Brief pause to avoid overwhelming server
                except Exception as e:
                    print(f"Error processing {link}: {e}")
                    continue

    except Exception as e:
        print(f"Unexpected error in run function: {e}")
    finally:
        print("Closing browser...")
        context.close()
        browser.close()

with sync_playwright() as playwright:
    run(playwright)