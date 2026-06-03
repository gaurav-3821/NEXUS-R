import sys
import os
sys.path.insert(0, os.getcwd())
from modules.web_ui.src.launcher import start_dashboard_server
start_dashboard_server(workspace=os.getcwd(), host="127.0.0.1", start_port=8000, interactive=False)
