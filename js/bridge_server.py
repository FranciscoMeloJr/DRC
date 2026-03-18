import http.server
import socketserver
import json
import os
import sys
from pathlib import Path

# --- DEBUG INSTRUMENTATION ---
print("--- CONTAINER PATH DEBUG ---")
print(f"Current Working Directory (CWD): {os.getcwd()}")
print(f"Script File (file): {__file__}")

# Calculate the paths
base_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.abspath(os.path.join(base_dir, '..'))

print(f"Calculated Base Dir: {base_dir}")
print(f"Calculated Parent Dir (..): {parent_dir}")

if os.path.exists(parent_dir):
    print(f"Parent Directory Contents: {os.listdir(parent_dir)}")
else:
    print("CRITICAL: Parent Directory does not exist!")

target_file = os.path.join(parent_dir, 'advisor_engine.py')
print(f"Checking for file: {target_file}")
print(f"File exists?: {os.path.exists(target_file)}")
print("--- END DEBUG ---\n")
# --- END DEBUG ---

# Add the parent directory to the path so we can import the engine
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
agent_dir = os.path.join(parent_dir, 'agent')

from agent.agent import chat_with_tools # Ensure your pathing is correct

try:
    from advisor_engine import DRCAdvisor
    print("SUCCESS: advisor_engine imported.")
except ImportError as e:
    print(f"--- REAL IMPORT ERROR: {e} ---")
    import traceback
    traceback.print_exc()
    sys.exit(1)

PORT = 8080

class BridgeHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self, debug=True):
        # 1. Handle Favicon specifically to stop 404s
        if self.path in ['/favicon.ico', '/static/drc.png']:
            try:
                # Path logic: bridge_server.py in drc/js/
                js_dir = Path(__file__).parent.absolute()
                icon_path = js_dir.parent / 'static' / 'drc.png'

                if icon_path.exists():
                    img_data = icon_path.read_bytes()
                    self.send_response(200)
                    self.send_header('Content-type', 'image/png')
                    self.send_header('Content-Length', len(img_data))
                    self.end_headers()
                    self.wfile.write(img_data)
                    return
            except Exception as e:
                print(f"[FAVICON ERROR]: {e}")

        # 2. Handle the Logo/Static files (Since they live outside the /js folder)
        if self.path.startswith('/static/'):
            try:
                # Calculate path to the 'static' folder (one level up from /js)
                base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                file_path = os.path.join(base_path, self.path.lstrip('/'))
                if debug:
                    print(base_path)
                    print(file_path)

                with open(file_path, 'rb') as f:
                    self.send_response(200)
                    # Set the correct header for images
                    if file_path.endswith(".png"):
                        self.send_header('Content-Type', 'image/png')
                    self.end_headers()
                    self.wfile.write(f.read())
                return
            except Exception as e:
                print(f"Static file error: {e}")
                self.send_error(404, "Static file not found")
                return
        # 3. Now 'engine' is defined in the module scope and accessible here
        engine = DRCAdvisor()
        if self.path == '/api/rules':
            try:
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                
                # Check if kcs_db exists on the engine instance
                pretty_json = json.dumps(engine.kcs_db, indent=4)
                self.wfile.write(pretty_json.encode('utf-8'))
                return
            except Exception as e:
                print(f"Error serving rules: {e}")
                self.send_error(500, str(e))
            return

        return super().do_GET()

    def do_POST(self):
        #1. Handle Bot Synthesis Endpoint
        if self.path == '/api/bot-chat':
            # 1. THE GUARD: Check environment before doing anything else
                required_keys = ["MODEL_API", "MODEL_ID", "USER_KEY"]
                if not all(os.getenv(k) for k in required_keys):
                    self.send_response(200) # Request was received, but we have a status to report
                    self.send_header('Content-type', 'application/json')
                    self.end_headers()
                    self.wfile.write(json.dumps({"response": -1}).encode())
                    return -1

                # 2. PROCEED: If keys exist, continue with your existing agent call logic
                try:
                    content_length = int(self.headers.get('Content-Length', 0))
                    post_data = self.rfile.read(content_length).decode('utf-8')
                    payload = json.loads(post_data)
                    
                    user_message = payload.get("message", "")
                    chat_history = payload.get("history", [])
                    # Pull the context from sessionStorage sent by the UI
                    context_data = payload.get("context", None)

                    # Pass context to the agent so it "sees" the YAML findings
                    ai_response, updated_history = chat_with_tools(user_message, chat_history, context=context_data)
                    
                    self.send_response(200)
                    self.send_header('Content-type', 'application/json')
                    self.end_headers()
                    
                    response_body = {
                        "reply": ai_response,
                        "history": updated_history
                    }
                    self.wfile.write(json.dumps(response_body).encode())
                
                except Exception as e:
                    # Log the real error to your console for debugging
                    print(f"[AGENT ERROR]: {str(e)}")
                    
                    # Send a polite "Friendly" error back to the Chat UI
                    self.send_response(200) # Still 200 so the fetch doesn't crash the UI
                    self.send_header('Content-type', 'application/json')
                    self.end_headers()
                    
                    fail_msg = {
                        "reply": "I'm having a hard time with that request right now. Please check my connection to the model API.",
                        "history": chat_history # Keep history intact so they can try again
                    }
                    self.wfile.write(json.dumps(fail_msg).encode())
        #2. Analyze
        elif self.path == '/api/analyze':
            content_length = int(self.headers['Content-Length'])
            yaml_data = self.rfile.read(content_length).decode('utf-8')

            eval_header = self.headers.get('X-DRC-Eval-Undefined', 'false').lower()
            eval_undefined = (eval_header == 'false')

            # Run the Python Engine
            engine = DRCAdvisor()
            engine.load_content(yaml_data, eval_header=eval_undefined)
            results = engine.analyze()
            print(f"DEBUG DATA: {json.dumps(results, indent=2, default=str)}")

            # Tally the summary findings (Required for the JS Face KPIs)
            summary = {}
            for r in results:
                for f in r.get('findings', []):
                    crit = f.get('crit', 'NOTICE').upper()
                    summary[crit] = summary.get(crit, 0) + 1

            response_data = {
                "metadata": {
                    "generated_at": "DRC Analysis",
                    "summary": summary
                },
                "results": results
            }


            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(response_data).encode())
        else:
            # Instead of calling super(), we send a proper 404 error
            self.send_error(404, "Endpoint not found")

    def translate_path(self, path):
        # Ensure the server looks for files inside the /js directory
        root = os.path.dirname(os.path.abspath(__file__))
        return os.path.join(root, path.lstrip('/'))

    def generate_synthesis(self, results):
            """Builds the customer-facing report narrative with fail-safe logic"""
            
            # Pull the last user message from a header if you want to be precise, 
            # but usually, we just check if results exist.
            if not results:
                return "I haven't seen any analysis results yet. Please upload a YAML/XML first! o/"

            report = "### 🤖 DRC ADVISOR SYNTHESIS (v2.3 Charizard)\n"
            report += "--------------------------------------------------\n"
            
            found_data = False
            for res in results:
                name = res.get('name', 'Unknown').upper()
                findings = res.get('findings', [])
                
                if findings:
                    found_data = True
                    report += f"**RESOURCE:** {name}\n"
                    for f in findings:
                        icon = "🚨" if f.get('crit') == "CRITICAL" else "⚠️"
                        report += f"{icon} {f.get('ref')}\n"
                    report += "\n"

            if not found_data:
                return "Analysis complete: No issues detected. Nothing to synthesize! ✅"

            report += "**EXPERT RECOMMENDATION:**\n"
            report += "This synthesis incorporates collaborative engineering feedback. "
            report += "For high-performance clusters, ensure ZGC is tuned per KCS 5437451.\n"
            report += "--------------------------------------------------"
            return report

with socketserver.TCPServer(("", PORT), BridgeHandler) as httpd:
    print(f"🚀 Bridge Active: http://localhost:{PORT}")
    print(f"Serving from: {os.path.dirname(os.path.abspath(__file__))}")
    httpd.serve_forever()