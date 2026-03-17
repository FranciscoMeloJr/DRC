import http.server
import socketserver
import json
import os
import sys

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

#try:
#    from advisor_engine import InfinispanDRCAdvisor
#except ImportError:
#    print("Error: advisor_engine.py not found in the parent directory.")
#    sys.exit(1)

# Updated try/except for bridge_server.py
try:
    from advisor_engine import InfinispanDRCAdvisor
    print("SUCCESS: advisor_engine imported.")
except ImportError as e:
    print(f"--- REAL IMPORT ERROR: {e} ---")
    import traceback
    traceback.print_exc()
    sys.exit(1)

PORT = 8080

class BridgeHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self, debug=True):
        # 1. Handle the Logo/Static files (Since they live outside the /js folder)
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
        # 2. Now 'engine' is defined in the module scope and accessible here
        engine = InfinispanDRCAdvisor()
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
        if self.path == '/api/analyze':
            content_length = int(self.headers['Content-Length'])
            yaml_data = self.rfile.read(content_length).decode('utf-8')

            eval_header = self.headers.get('X-DRC-Eval-Undefined', 'false').lower()
            eval_undefined = (eval_header == 'false')

            # Run the Python Engine
            engine = InfinispanDRCAdvisor()
            engine.load_content(yaml_data, eval_header=eval_undefined)
            results = engine.analyze()
            print(f"DEBUG DATA: {json.dumps(results, indent=2)}")

            # Tally the summary findings (Required for the JS Face KPIs)
            summary = {}
            for r in results:
                for f in r.get('findings', []):
                    crit = f.get('crit', 'NOTICE').upper()
                    summary[crit] = summary.get(crit, 0) + 1

            response_data = {
                "metadata": {
                    "generated_at": "Live Analysis",
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

with socketserver.TCPServer(("", PORT), BridgeHandler) as httpd:
    print(f"🚀 Bridge Active: http://localhost:{PORT}")
    print(f"Serving from: {os.path.dirname(os.path.abspath(__file__))}")
    httpd.serve_forever()