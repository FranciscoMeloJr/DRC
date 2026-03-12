import http.server
import socketserver
import json
import os
import sys

# Add the parent directory to the path so we can import the engine
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

try:
    from advisor_engine import InfinispanDRCAdvisor
except ImportError:
    print("Error: advisor_engine.py not found in the parent directory.")
    sys.exit(1)

PORT = 8081

class BridgeHandler(http.server.SimpleHTTPRequestHandler):
    def do_POST(self):
        if self.path == '/analyze':
            content_length = int(self.headers['Content-Length'])
            yaml_data = self.rfile.read(content_length).decode('utf-8')


            # Run the Python Engine
            engine = InfinispanDRCAdvisor()
            engine.load_content(yaml_data)
            results = engine.analyze()


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
            super().do_POST()

    def translate_path(self, path):
        # Ensure the server looks for files inside the /js directory
        root = os.path.dirname(os.path.abspath(__file__))
        return os.path.join(root, path.lstrip('/'))

with socketserver.TCPServer(("", PORT), BridgeHandler) as httpd:
    print(f"🚀 Bridge Active: http://localhost:{PORT}")
    print(f"Serving from: {os.path.dirname(os.path.abspath(__file__))}")
    httpd.serve_forever()