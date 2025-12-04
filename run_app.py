import streamlit.web.cli as stcli
import os, sys

def resolve_path(path):
    if getattr(sys, "frozen", False):
        basedir = sys._MEIPASS
    else:
        basedir = os.path.dirname(__file__)
    return os.path.join(basedir, path)

if __name__ == "__main__":
    import multiprocessing
    multiprocessing.freeze_support()
    
    # Set Playwright browser path to local directory
    if getattr(sys, "frozen", False):
        base_dir = os.path.dirname(sys.executable)
    else:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        
    browsers_path = os.path.join(base_dir, "browsers")
    os.environ["PLAYWRIGHT_BROWSERS_PATH"] = browsers_path
    
    # Check if browsers are installed
    if not os.path.exists(browsers_path):
        print(f"Browsers not found in {browsers_path}. Installing Chromium...")
        try:
            from playwright.__main__ import main as pw_main
            sys.argv = ["playwright", "install", "chromium"]
            pw_main()
            print("Browser installation complete.")
        except Exception as e:
            print(f"Failed to install browsers: {e}")
            input("Press Enter to exit...")
            sys.exit(1)

    # Check if running as scraper subprocess
    if len(sys.argv) > 1 and sys.argv[1] == "main.py":
        # Shift arguments so main.py sees them correctly
        # sys.argv is [exe, "main.py", "--keyword", ...]
        # main.py expects [script, "--keyword", ...]
        sys.argv = sys.argv[1:]
        import main
        sys.exit(main.main())

    try:
        app_path = resolve_path("app.py")
        
        # Deterministic port search
        import socket
        
        def is_port_in_use(port):
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                return s.connect_ex(('localhost', port)) == 0

        port = 8501
        while is_port_in_use(port):
            port += 1
        
        # Only open browser if this is the main process (not a reload)
        if os.environ.get("AMAZON_SCRAPER_RUNNING") is None:
            os.environ["AMAZON_SCRAPER_RUNNING"] = "true"
            
            import webbrowser
            import threading
            import time
            
            def open_browser():
                time.sleep(2) # Wait for server to start
                webbrowser.open(f"http://localhost:{port}")
                
            threading.Thread(target=open_browser).start()
        
        sys.argv = [
            "streamlit",
            "run",
            app_path,
            "--global.developmentMode=false",
            "--browser.gatherUsageStats=false",
            "--server.headless=true", # Disable auto-launch by Streamlit
            f"--server.port={port}",
            "--server.address=localhost",
        ]
        sys.exit(stcli.main())
    except Exception as e:
        print(f"An error occurred: {e}")
        import traceback
        traceback.print_exc()
        input("Press Enter to close...")
