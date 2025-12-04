import streamlit as st
import pandas as pd
import time
import os
import subprocess
import sys
import base64

st.set_page_config(page_title="Super Scraper", page_icon="🚀", layout="wide")

# Custom CSS for background
# Custom CSS for background
def set_background(image_data):
    bin_str = base64.b64encode(image_data).decode()
    page_bg_img = f"""
    <style>
    .stApp {{
        background-image: url("data:image/png;base64,{bin_str}");
        background-size: cover;
    }}
    </style>
    """
    st.markdown(page_bg_img, unsafe_allow_html=True)

def styled_message(text, type="info"):
    colors = {
        "info": {"color": "#0c5460", "border": "#bee5eb"},
        "success": {"color": "#155724", "border": "#c3e6cb"},
        "warning": {"color": "#856404", "border": "#ffeeba"},
        "error": {"color": "#721c24", "border": "#f5c6cb"}
    }
    style = colors.get(type, colors["info"])
    return f"""
    <div style="background-color: rgba(255, 255, 255, 0.8); padding: 10px; border-radius: 5px; margin-bottom: 10px; color: {style['color']}; border: 1px solid {style['border']};">
        {text}
    </div>
    """

# ... (rest of the file)

# Customization at the bottom
st.sidebar.markdown("---")
st.sidebar.header("Customization")
bg_image = st.sidebar.file_uploader("Background Image", type=["png", "jpg", "jpeg"])

CUSTOM_BG_FILE = "custom_background.png"

if bg_image:
    # User uploaded a new image
    bg_data = bg_image.read()
    # Save it
    with open(CUSTOM_BG_FILE, "wb") as f:
        f.write(bg_data)
    st.sidebar.success("Background saved!")
    set_background(bg_data)
elif os.path.exists(CUSTOM_BG_FILE):
    # Load existing custom background
    with open(CUSTOM_BG_FILE, "rb") as f:
        bg_data = f.read()
    set_background(bg_data)

# Title with Red Version
# Title with Red Version
# Create columns for layout
_, right_col = st.columns([1, 1])

with right_col:
    st.markdown("""
    <div style="background-color: rgba(255, 255, 255, 0.7); padding: 20px; border-radius: 10px; display: inline-block; margin-bottom: 20px;">
        <h1 style="margin: 0; padding: 0;">🚀 Super Scraper <span style="color:red;">v2.0</span></h1>
        <p style="margin: 10px 0 0 0; font-size: 1.1em;">The ultimate product scraper for Amazon, Newegg, and more.</p>
    </div>
    """, unsafe_allow_html=True)

# Sidebar Configuration
st.sidebar.header("Configuration")
keyword = st.sidebar.text_input("Search Keyword", "gaming laptop")
pages = st.sidebar.number_input("Number of Pages", min_value=1, max_value=10, value=1)
use_proxy = st.sidebar.checkbox("Use Proxies", value=False, help="Enable this to use free proxies (may be slow). Disable for faster local scraping.")
headless = st.sidebar.checkbox("Headless Mode", value=True, help="Run browser in background.")
source = st.sidebar.selectbox("Source", ["All", "Amazon", "Newegg", "BestBuy", "BH", "PCHome"], index=0)

output_file = "products.xlsx"

# Initialize session state for results if not present
if 'results' not in st.session_state:
    st.session_state['results'] = None

# Try to load existing file into session state on first run if not already loaded
if st.session_state['results'] is None and os.path.exists(output_file):
    try:
        st.session_state['results'] = pd.read_excel(output_file)
    except Exception:
        pass # Ignore if file is corrupt or unreadable

if st.sidebar.button("Start Scraping"):
    if not keyword:
        st.markdown(styled_message("Please enter a keyword.", "error"), unsafe_allow_html=True)
    else:
        with right_col:
            status_text = st.empty()
            progress_bar = st.progress(0)
        
        status_text.markdown(styled_message(f"Starting scraper for '{keyword}'...", "info"), unsafe_allow_html=True)
        
        try:
            # Remove existing file to avoid showing old results on failure
            if os.path.exists(output_file):
                os.remove(output_file)
            
            # Clear current session results
            st.session_state['results'] = None

            # Construct command
            source_arg = source.lower()
            if source == "BestBuy": source_arg = "bestbuy"
            if source == "BH": source_arg = "bh"
            if source == "PCHome": source_arg = "pchome"
            if source == "All": source_arg = "all"
            
            cmd = [sys.executable, "main.py", "--keyword", keyword, "--pages", str(pages), "--source", source_arg]
            if not use_proxy:
                cmd.append("--no-proxy")
            if headless:
                cmd.append("--headless")
                
            # Run subprocess
            with st.spinner("Scraping in progress..."):
                # Show styled message for progress as well since spinner might be subtle
                status_text.markdown(styled_message(f"Scraping in progress for '{keyword}'... This may take a while.", "info"), unsafe_allow_html=True)
                process = subprocess.run(cmd, capture_output=True, text=True)
                
            if process.returncode == 0:
                progress_bar.progress(100)
                st.markdown(styled_message("Scraping completed!", "success"), unsafe_allow_html=True)
                
                # Load new results into session state
                if os.path.exists(output_file):
                    st.session_state['results'] = pd.read_excel(output_file)
                else:
                    st.markdown(styled_message("Scraper finished but no output file was found.", "warning"), unsafe_allow_html=True)
                    
            else:
                st.markdown(styled_message("Scraper failed.", "error"), unsafe_allow_html=True)
                st.text("Error Output:")
                st.code(process.stderr)
                
        except Exception as e:
            st.markdown(styled_message(f"An error occurred: {e}", "error"), unsafe_allow_html=True)

# Debugging Info
st.sidebar.markdown("---")
st.sidebar.subheader("Debug Info")
st.sidebar.text(f"Session State Keys: {list(st.session_state.keys())}")
st.sidebar.text(f"Results in State: {st.session_state.get('results') is not None}")
st.sidebar.text(f"File Exists: {os.path.exists(output_file)}")

# Display Results from Session State
if st.session_state.get('results') is not None:
    try:
        df = st.session_state['results']
        
        st.subheader("Results")
        
        # Pagination Controls at the bottom
        col1, col2 = st.columns([1, 3])
        
        with col1:
            rows_per_page = st.selectbox("Rows per page", [20, 30, 50, 100], index=0, key="rows_per_page_select")
        
        total_rows = len(df)
        total_pages = (total_rows - 1) // rows_per_page + 1
        
        with col2:
            # Ensure value is within bounds
            if "page_input" not in st.session_state:
                st.session_state["page_input"] = 1
            
            # Adjust if out of bounds (e.g. if rows_per_page changed)
            if st.session_state["page_input"] > total_pages:
                st.session_state["page_input"] = 1
                
            current_page = st.number_input("Page", min_value=1, max_value=total_pages, value=1, key="page_input")
        
        # Calculate slice
        start_idx = (current_page - 1) * rows_per_page
        end_idx = start_idx + rows_per_page
        
        # Display Dataframe directly (removed st.empty for simplicity)
        st.caption(f"Showing rows {start_idx + 1} to {min(end_idx, total_rows)} of {total_rows}")
        st.dataframe(df.iloc[start_idx:end_idx])
        
        # Export CSV
        csv = df.to_csv(index=False).encode('utf-8-sig')
        st.download_button(
            label="Download Results as CSV",
            data=csv,
            file_name='products.csv',
            mime='text/csv',
            key="download_csv_btn"
        )
        st.info(f"Data saved to `{output_file}`")
    except Exception as e:
        st.markdown(styled_message(f"Error displaying results: {e}", "error"), unsafe_allow_html=True)
        st.exception(e) # Show full traceback for debugging
            
st.sidebar.markdown("---")
st.sidebar.info("Note: Free proxies can be unstable. If scraping fails, try disabling proxies.")


