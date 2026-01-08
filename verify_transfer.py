from system.tools import sandbox_tool, research_tool
import os

print("🔍 Verifying Asset Transfer...")

# 1. Verify Tools
try:
    code_res = sandbox_tool.execute_python_code("print('Sandbox Test')")
    if code_res["status"] == "success":
        print("✅ Sandbox Tool: Active")
    else:
        print(f"❌ Sandbox Tool: Failed ({code_res})")
except Exception as e:
    print(f"❌ Sandbox Tool: Import Error {e}")

try:
    research_res = research_tool.perform_deep_research("Test Topic", 1)
    if research_res["status"] == "success":
        print("✅ Research Tool: Active")
    else:
        print(f"❌ Research Tool: Failed ({research_res})")
except Exception as e:
    print(f"❌ Research Tool: Import Error {e}")

# 2. Verify Personas
personas = ["refactoring_specialist.md", "sovereign_sysadmin.md", "api_designer.md", "prompt_architect.md"]
missing_personas = []
for p in personas:
    if not os.path.exists(f"system/personas/{p}"):
        missing_personas.append(p)

if not missing_personas:
    print("✅ Personas: All Transferred")
else:
    print(f"❌ Personas: Missing {missing_personas}")

# 3. Verify Workflows
workflows = ["ubuntu_security_hardening.md", "data_backup_verification.md"]
missing_wf = []
for w in workflows:
    if not os.path.exists(f".agent/workflows/{w}"):
        missing_wf.append(w)

if not missing_wf:
    print("✅ Workflows: All Transferred")
else:
    print(f"❌ Workflows: Missing {missing_wf}")
