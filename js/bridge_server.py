import http.server
import socketserver
import json
import os
import sys
import datetime
from pathlib import Path

# ==========================================
# 1. PATH & ENGINE INSTRUMENTATION
# ==========================================
print("--- 🔍 CONTAINER PATH DEBUG ---")
base_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.abspath(os.path.join(base_dir, '..'))

print(f"CWD: {os.getcwd()}")
print(f"Base Dir: {base_dir}")
print(f"Parent Dir: {parent_dir}")

# Inject parent dir into sys.path to find /agent and engine files
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

target_engine = os.path.join(parent_dir, 'advisor_engine.py')
print(f"Checking Engine: {target_engine} | Exists: {os.path.exists(target_engine)}")
print("--- 🏁 END DEBUG ---\n")

# ==========================================
# 2. ENVIRONMENT & SECRET VALIDATION
# ==========================================
# Dynamic PORT with fallback
try:
    PORT = int(os.getenv("PORT", 8080))
except ValueError:
    PORT = 8080

# Mandatory AI Secrets
REQUIRED_VARS = ["USER_KEY", "MODEL_API", "MODEL_ID"]
missing = [v for v in REQUIRED_VARS if not os.getenv(v)]

if missing:
    print(f"❌ CRITICAL ERROR: Missing Env Vars: {', '.join(missing)}")
    print("Ensure your OCP Secret 'drc-ai-credentials' is mapped in deployment.yaml")

print(f"✅ Environment Verified. Listening on Port: {PORT}")

# ==========================================
# 3. IMPORTS
# ==========================================
from agent.agent import chat_with_tools
try:
    from advisor_engine import DRCAdvisor
    print("🚀 SUCCESS: Advisor Engine ready.")
except ImportError as e:
    print(f"💥 IMPORT FAILED: {e}")
    sys.exit(1)
# --- PORT CONFIGURATION ---
# Use the PORT env var provided by OCP, default to 8080 if not set
try:
    PORT = int(os.getenv("PORT", 8080))
    print(f"📡 Configuration: Server will listen on Port {PORT}")
except ValueError:
    print("⚠️ Warning: Invalid PORT env var. Falling back to 8080.")
    PORT = 8080

# --- SECRET VERIFICATION ---
REQUIRED_SECRETS = ["USER_KEY", "MODEL_API", "MODEL_ID"]
missing_secrets = [s for s in REQUIRED_SECRETS if not os.getenv(s)]

if missing_secrets:
    print("\n" + "!" * 50)
    print(f"CRITICAL: Missing Environment Variables: {', '.join(missing_secrets)}")
    print("Check your OCP Secret 'drc-ai-credentials'.")
    print("!" * 50 + "\n")

# --- BRIDGE HANDLER ---
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
        # 1. JVM SPECIFIC ENDPOINT
        if self.path == '/api/analyze-jvm':
            try:
                content_length = int(self.headers.get('Content-Length', 0))
                raw_log = self.rfile.read(content_length).decode('utf-8')

                from jvm.advisor_jvm import JVMAdvisor
                expert = JVMAdvisor(raw_log)
                report_tree = expert.analyze()

                summary = {}
                for section in report_tree.values():
                    if isinstance(section, dict) and "Crit" in section:
                        crit = section["Crit"].upper()
                        summary[crit] = summary.get(crit, 0) + 1

                response_data = {
                    "metadata": {
                        "generated_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "summary": summary,
                        "isJVM": True
                    },
                    "results": [report_tree]
                }

                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(json.dumps(response_data).encode())
            except Exception as e:
                print(f"❌ JVM API Error: {str(e)}")
                self.send_response(200) 
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({
                    "metadata": {"summary": {}, "isJVM": True, "error": True},
                    "results": [],
                    "error_msg": str(e)
                }).encode())

        # 2. BOT SYNTHESIS ENDPOINT
        elif self.path == '/api/bot-chat':
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