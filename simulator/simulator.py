import subprocess
import os
import json

def get_oc_client(user=None, pw=None):
    """
    Checks for provided creds, then OCP_USER/OCP_PASSCODE env vars.
    Returns True if login succeeds or is assumed via ServiceAccount.
    Returns False if an explicit login attempt fails.
    """
    # Priority: 1. Manual Args (from UI) -> 2. Env Vars -> 3. ServiceAccount
    final_user = user or os.getenv("OCP_USER")
    final_pw = pw or os.getenv("OCP_PASSCODE")
    server = os.getenv("OCP_SERVER", "https://api.ocp.local:6443")

    if final_user and final_pw:
        login_cmd = ["oc", "login", server, "-u", final_user, "-p", final_pw, "--insecure-skip-tls-verify"]
        result = subprocess.run(login_cmd, capture_output=True, text=True, timeout=10)
        
        if result.returncode != 0:
            print(f"❌ OCP Login Failed for {final_user}")
            return False
        print(f"✅ OCP Login Success for {final_user}")
    
    return True

def run_dry_run(yaml_content, token=None, server=None):
    """
    v2.5 OCP Simulator - Token Auth Build
    """
    # 1. Resolve Identity
    final_server = server or os.getenv("OCP_SERVER")
    final_token = token or os.getenv("OCP_TOKEN")

    # If we are missing either, trigger the -1 popup
    if not final_server or not final_token:
        return {"success": False, "status": -1, "stderr": "OCP Token or Server URL missing."}

    try:
        # 2. LOGIN VIA TOKEN
        login_cmd = [
            "oc", "login", final_server,
            f"--token={final_token}",
            "--insecure-skip-tls-verify"
        ]
        login_proc = subprocess.run(login_cmd, capture_output=True, text=True, timeout=15)
        
        if login_proc.returncode != 0:
            return {"success": False, "status": -1, "stderr": f"Token Login Failed: {login_proc.stderr}"}

        # 3. DRY RUN (remains the same)
        temp_file = f"sim_{os.getpid()}.yaml"
        with open(temp_file, "w") as f:
            f.write(yaml_content)

        cmd = ["oc", "apply", "-f", temp_file, "--dry-run=server"]
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        return {
            "success": result.returncode == 0,
            "stdout": result.stdout,
            "stderr": result.stderr
        }
    finally:
        if os.path.exists(temp_file): os.remove(temp_file)