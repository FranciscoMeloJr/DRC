import subprocess
import os
import uuid
import re

class YATDAWrapper:
    def __init__(self, raw_content):
        self.raw_content = raw_content.strip() if raw_content else ""
        self.yatda_script = os.path.join(os.getcwd(), "tools", "yatda.sh")

    def analyze(self):
        # Corner Case: Empty File
        if not self.raw_content:
            return {"success": False, "stderr": "Analysis Failed: The uploaded file is empty."}

        dump_id = uuid.uuid4().hex
        temp_input = f"tdump_{dump_id}.txt"
        main_report = f"{temp_input}.yatda"
        cpu_sidecar = f"{temp_input}.yatda-cpu"
        gc_sidecar = f"{temp_input}.yatda-gc-cpu"

        try:
            # Corner Case: Filesystem Permissions
            with open(temp_input, "w") as f:
                f.write(self.raw_content)

            # 2. Execute with Hard Timeout
            try:
                result = subprocess.run(
                    ["bash", self.yatda_script, "-u", "never", temp_input],
                    capture_output=True, 
                    text=True, 
                    timeout=45 # Increased slightly for very large dumps
                )
            except subprocess.TimeoutExpired:
                return {"success": False, "stderr": "YATDA Analysis timed out after 45 seconds (File may be too large or script stalled)."}

            # 3. Read and Sanitize the main report file
            if os.path.exists(main_report):
                with open(main_report, "r") as f:
                    report_content = f.read()
                
                # --- 🧹 AGGRESSIVE PATH SCRUBBING ---
                # This catches "Summary of file://", "Summarizing file://", etc.
                # and replaces the whole line with a clean professional header.
                report_content = re.sub(
                    r"###.*?file://.*? ###", 
                    "### THREAD DUMP ANALYSIS SUMMARY ###", 
                    report_content
                )
                
                # Secondary pass to ensure "input_stream" doesn't have the path either
                report_content = report_content.replace(temp_input, "ANALYSIS_TARGET")
                # -------------------------
            else:
                # Corner Case: Truncated/Invalid Dump
                error_detail = result.stderr if result.stderr else "Script produced no output. File might not be a valid Java Thread Dump."
                report_content = f"⚠️ YATDA could not parse this file.\nDetails: {error_detail}"

            return {
                "success": True,
                "type": "JVM_THREAD_DUMP",
                "raw_output": report_content
            }

        except Exception as e:
            return {"success": False, "stderr": f"Bridge Internal Error: {str(e)}"}
            
        finally:
            # Triple Cleanup
            for f in [temp_input, main_report, cpu_sidecar, gc_sidecar]:
                if os.path.exists(f):
                    try:
                        os.remove(f)
                    except:
                        pass