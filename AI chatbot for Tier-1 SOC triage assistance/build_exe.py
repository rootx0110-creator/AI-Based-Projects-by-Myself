"""Build a single-file Windows executable with PyInstaller.

Usage:
    pip install -r requirements.txt
    python build_exe.py
"""
import PyInstaller.__main__
import os

HERE = os.path.dirname(os.path.abspath(__file__))

PyInstaller.__main__.run([
    os.path.join(HERE, "run.py"),
    "--name=SOC_Triage_Assistant",
    "--onefile",
    # Bundle the UI templates next to app/server.py inside the bundle
    "--add-data=" + os.path.join("app", "templates") + os.pathsep + os.path.join("app", "templates"),
    "--hidden-import=app.skills.phishing_skill",
    "--hidden-import=app.skills.malware_skill",
    "--hidden-import=app.skills.credential_skill",
    "--hidden-import=app.skills.network_skill",
    "--hidden-import=app.skills.vulnerability_skill",
    "--hidden-import=app.skills.exfiltration_skill",
    "--hidden-import=app.skills.playbook_skill",
    "--hidden-import=app.skills.summary_skill",
    "--hidden-import=app.engine.ioc_extractor",
    "--hidden-import=app.engine.mitre_mapper",
    "--hidden-import=app.engine.severity_engine",
    "--hidden-import=app.engine.skills_runner",
    "--hidden-import=app.engine.brain",
    "--hidden-import=app.engine.llm",
    "--hidden-import=app.demo_data",
    "--hidden-import=app.report_generator",
    "--collect-submodules=app",
    "--noconfirm",
    "--clean",
])
