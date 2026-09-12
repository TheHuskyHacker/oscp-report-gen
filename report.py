#!/usr/bin/env python3
"""
Husky Report — OSCP exam report generator.

Build your report incrementally during the exam, then generate
a clean OffSec-formatted markdown report ready for PDF conversion.

Stores data in a JSON workspace file so you can add machines,
steps, and flags as you go. Generates the final report with
one command when you're done.

No dependencies beyond Python 3.6+ stdlib.
"""

import argparse
import json
import os
import shutil
import sys
import textwrap
import time
from datetime import datetime
from pathlib import Path

# ───────────────── ANSI helpers ───────────────────────────

def _has_color():
    return hasattr(sys.stdout, "isatty") and sys.stdout.isatty()

_C = _has_color()

def _a(code, t): return f"\033[{code}m{t}\033[0m" if _C else t
def red(t):     return _a("91", t)
def green(t):   return _a("92", t)
def yellow(t):  return _a("93", t)
def blue(t):    return _a("94", t)
def cyan(t):    return _a("96", t)
def bold(t):    return _a("1", t)
def dim(t):     return _a("2", t)

BANNER = f"""
{cyan('    __  ____  _______ __ ____  __')}
{cyan('   / / / / / / / ___// //_/')}\\{cyan(' \\ \\/ /')}
{cyan('  / /_/ / / / /\\__ \\/ ,<')}   {cyan(' \\  /')}
{cyan(' / __  / /_/ /___/ / /| |')}  {cyan(' / /')}
{cyan('/_/ /_/\\____//____/_/ |_|')} {cyan('/_/')}
{red('    __  _____   ________ __ __________')}
{red('   / / / /   | / ____/ //_// ____/ __ \\\\')}
{red('  / /_/ / /| |/ /   / ,<  / __/ / /_/ /')}
{red(' / __  / ___ / /___/ /| |/ /___/ _, _/')}
{red('/_/ /_/_/  |_\\____/_/ |_/_____/_/ |_|')}

    {bold('O S C P   R E P O R T   G E N E R A T O R')}
    {dim('Hack the box. Not the formatting.')}
"""

# ───────────────── workspace ──────────────────────────────

DEFAULT_WORKSPACE = "oscp_report.json"

TEMPLATE = {
    "meta": {
        "student_id": "",
        "exam_date": "",
        "email": "",
        "osid": "",
        "created": "",
        "last_modified": "",
    },
    "machines": [],
}

MACHINE_TEMPLATE = {
    "name": "",
    "ip": "",
    "os": "",
    "points": 0,
    "difficulty": "",
    "hostname": "",
    "domain": "",
    "local_flag": "",
    "proof_flag": "",
    "ports": [],
    "enum_notes": "",
    "initial_access": {
        "vulnerability": "",
        "description": "",
        "steps": [],
    },
    "privilege_escalation": {
        "vulnerability": "",
        "description": "",
        "steps": [],
    },
    "post_exploitation": "",
    "screenshots": [],
    "additional_notes": "",
}

STEP_TEMPLATE = {
    "description": "",
    "command": "",
    "output": "",
    "screenshot": "",
}


def load_workspace(path):
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return None


def save_workspace(data, path):
    data["meta"]["last_modified"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def find_machine(data, identifier):
    """Find a machine by name or IP."""
    identifier = identifier.lower().strip()
    for m in data["machines"]:
        if m["name"].lower() == identifier or m["ip"] == identifier:
            return m
    return None


# ═══════════════════════════════════════════════════════════
#                    COMMANDS
# ═══════════════════════════════════════════════════════════

def cmd_init(args):
    """Initialize a new report workspace."""
    path = args.workspace

    if os.path.exists(path) and not args.force:
        print(f"  {yellow('[!]')} Workspace already exists: {path}")
        print(f"  {dim('    Use --force to overwrite')}")
        return

    data = json.loads(json.dumps(TEMPLATE))
    data["meta"]["created"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Interactive setup
    print(f"\n  {bold(cyan('Report Setup'))}\n")
    data["meta"]["osid"] = input(f"  OSID (e.g. OS-12345): ").strip()
    data["meta"]["email"] = input(f"  Email: ").strip()
    data["meta"]["exam_date"] = input(f"  Exam date (YYYY-MM-DD): ").strip() or datetime.now().strftime("%Y-%m-%d")

    # Create screenshots directory
    screenshots_dir = os.path.join(os.path.dirname(path) or ".", "screenshots")
    Path(screenshots_dir).mkdir(exist_ok=True)

    save_workspace(data, path)
    print(f"\n  {green('[+]')} Workspace created: {bold(path)}")
    print(f"  {green('[+]')} Screenshots dir: {bold(screenshots_dir)}")
    print(f"\n  {dim('Next: Add machines with:')}  {cyan(f'python3 report.py add <name> <ip>')}\n")


def cmd_add_machine(args):
    """Add a machine to the report."""
    data = load_workspace(args.workspace)
    if not data:
        print(f"  {red('[!]')} No workspace found. Run {bold('init')} first.")
        return

    # Check for duplicates
    if find_machine(data, args.name) or find_machine(data, args.ip):
        print(f"  {yellow('[!]')} Machine already exists: {args.name} / {args.ip}")
        return

    machine = json.loads(json.dumps(MACHINE_TEMPLATE))
    machine["name"] = args.name
    machine["ip"] = args.ip
    machine["os"] = args.os or ""
    machine["points"] = args.points or 0
    machine["hostname"] = args.hostname or ""
    machine["domain"] = args.domain or ""

    data["machines"].append(machine)
    save_workspace(data, args.workspace)
    print(f"  {green('[+]')} Added machine: {bold(args.name)} ({args.ip})")
    print(f"  {dim('    Next: Add flags, steps, or ports')}\n")


def cmd_flag(args):
    """Record a flag for a machine."""
    data = load_workspace(args.workspace)
    if not data:
        print(f"  {red('[!]')} No workspace found. Run {bold('init')} first.")
        return

    machine = find_machine(data, args.machine)
    if not machine:
        print(f"  {red('[!]')} Machine not found: {args.machine}")
        _list_machines(data)
        return

    if args.type == "local":
        machine["local_flag"] = args.value
        print(f"  {green('[+]')} {machine['name']} local.txt: {bold(args.value)}")
    elif args.type == "proof":
        machine["proof_flag"] = args.value
        print(f"  {green('[+]')} {machine['name']} proof.txt: {bold(args.value)}")

    save_workspace(data, args.workspace)


def cmd_ports(args):
    """Record open ports for a machine."""
    data = load_workspace(args.workspace)
    if not data:
        print(f"  {red('[!]')} No workspace found. Run {bold('init')} first.")
        return

    machine = find_machine(data, args.machine)
    if not machine:
        print(f"  {red('[!]')} Machine not found: {args.machine}")
        _list_machines(data)
        return

    # Parse port entries: "22/ssh", "80/http", "445/smb"
    for entry in args.ports:
        parts = entry.split("/", 1)
        port_num = parts[0].strip()
        service = parts[1].strip() if len(parts) > 1 else ""
        machine["ports"].append({"port": port_num, "service": service})

    save_workspace(data, args.workspace)
    print(f"  {green('[+]')} Added {len(args.ports)} port(s) to {machine['name']}")


def cmd_step(args):
    """Add an exploitation step to a machine."""
    data = load_workspace(args.workspace)
    if not data:
        print(f"  {red('[!]')} No workspace found. Run {bold('init')} first.")
        return

    machine = find_machine(data, args.machine)
    if not machine:
        print(f"  {red('[!]')} Machine not found: {args.machine}")
        _list_machines(data)
        return

    step = json.loads(json.dumps(STEP_TEMPLATE))
    step["description"] = args.description
    step["command"] = args.command or ""
    step["output"] = args.output or ""
    step["screenshot"] = args.screenshot or ""

    phase = args.phase
    if phase == "initial":
        machine["initial_access"]["steps"].append(step)
        section = "Initial Access"
    elif phase == "privesc":
        machine["privilege_escalation"]["steps"].append(step)
        section = "Privilege Escalation"
    else:
        machine["initial_access"]["steps"].append(step)
        section = "Initial Access"

    save_workspace(data, args.workspace)
    step_num = len(machine["initial_access"]["steps"] if phase == "initial"
                   else machine["privilege_escalation"]["steps"])
    print(f"  {green('[+]')} {machine['name']} → {section} step {step_num}: {args.description[:60]}")


def cmd_vuln(args):
    """Set the vulnerability name for a phase."""
    data = load_workspace(args.workspace)
    if not data:
        print(f"  {red('[!]')} No workspace found. Run {bold('init')} first.")
        return

    machine = find_machine(data, args.machine)
    if not machine:
        print(f"  {red('[!]')} Machine not found: {args.machine}")
        _list_machines(data)
        return

    phase = args.phase
    if phase == "initial":
        machine["initial_access"]["vulnerability"] = args.name
        machine["initial_access"]["description"] = args.desc or ""
    else:
        machine["privilege_escalation"]["vulnerability"] = args.name
        machine["privilege_escalation"]["description"] = args.desc or ""

    save_workspace(data, args.workspace)
    print(f"  {green('[+]')} {machine['name']} → {phase} vulnerability: {bold(args.name)}")


def cmd_note(args):
    """Add freeform notes to a machine."""
    data = load_workspace(args.workspace)
    if not data:
        print(f"  {red('[!]')} No workspace found. Run {bold('init')} first.")
        return

    machine = find_machine(data, args.machine)
    if not machine:
        print(f"  {red('[!]')} Machine not found: {args.machine}")
        _list_machines(data)
        return

    section = args.section
    if section == "enum":
        machine["enum_notes"] += args.text + "\n"
    elif section == "post":
        machine["post_exploitation"] += args.text + "\n"
    else:
        machine["additional_notes"] += args.text + "\n"

    save_workspace(data, args.workspace)
    print(f"  {green('[+]')} Note added to {machine['name']} ({section})")


def cmd_status(args):
    """Show current report status."""
    data = load_workspace(args.workspace)
    if not data:
        print(f"  {red('[!]')} No workspace found. Run {bold('init')} first.")
        return

    meta = data["meta"]
    print(f"\n  {bold(cyan('Report Status'))}")
    print(f"  {dim('─' * 40)}")
    print(f"  OSID:      {meta.get('osid', 'not set')}")
    print(f"  Email:     {meta.get('email', 'not set')}")
    print(f"  Exam date: {meta.get('exam_date', 'not set')}")
    print(f"  Modified:  {meta.get('last_modified', 'never')}")

    total_points = 0
    print(f"\n  {bold('Machines:')}")

    if not data["machines"]:
        print(f"    {dim('None added yet')}")
    else:
        for m in data["machines"]:
            local = green("✓") if m["local_flag"] else red("✗")
            proof = green("✓") if m["proof_flag"] else red("✗")
            ia_steps = len(m["initial_access"]["steps"])
            pe_steps = len(m["privilege_escalation"]["steps"])
            pts = m.get("points", 0)
            total_points += pts if m["proof_flag"] else 0

            os_label = f" ({m['os']})" if m["os"] else ""
            pts_label = f" [{pts}pts]" if pts else ""

            print(f"    {bold(m['name'])} {dim(m['ip'])}{dim(os_label)}{dim(pts_label)}")
            print(f"      local.txt: {local}  proof.txt: {proof}")
            print(f"      Initial access: {ia_steps} steps  |  Privesc: {pe_steps} steps")

            ia_vuln = m["initial_access"].get("vulnerability", "")
            pe_vuln = m["privilege_escalation"].get("vulnerability", "")
            if ia_vuln:
                print(f"      Vuln (initial): {dim(ia_vuln)}")
            if pe_vuln:
                print(f"      Vuln (privesc): {dim(pe_vuln)}")

    flags_captured = sum(1 for m in data["machines"] if m["proof_flag"])
    total_machines = len(data["machines"])
    print(f"\n  {bold('Progress:')} {flags_captured}/{total_machines} machines rooted")
    if total_points:
        print(f"  {bold('Points:')} {total_points}")
    print()


def _list_machines(data):
    """Helper to list machine names."""
    if data["machines"]:
        names = [f"{m['name']} ({m['ip']})" for m in data["machines"]]
        print(f"  {dim('Available machines: ' + ', '.join(names))}")


# ═══════════════════════════════════════════════════════════
#               REPORT GENERATION
# ═══════════════════════════════════════════════════════════

def cmd_generate(args):
    """Generate the final markdown report."""
    data = load_workspace(args.workspace)
    if not data:
        print(f"  {red('[!]')} No workspace found. Run {bold('init')} first.")
        return

    meta = data["meta"]
    machines = data["machines"]

    if not machines:
        print(f"  {red('[!]')} No machines in workspace — nothing to generate")
        return

    output_file = args.output or "OSCP_Exam_Report.md"

    lines = []

    def w(text=""):
        lines.append(text)

    # ── Title page ──
    w("---")
    w(f"title: \"OSCP Penetration Test Report\"")
    w(f"author: \"{meta.get('osid', 'OSID')}\"")
    w(f"date: \"{meta.get('exam_date', datetime.now().strftime('%Y-%m-%d'))}\"")
    w("---")
    w()
    w("# OSCP Penetration Test Report")
    w()
    w(f"**Student ID:** {meta.get('osid', '')}")
    w(f"**Email:** {meta.get('email', '')}")
    w(f"**Exam Date:** {meta.get('exam_date', '')}")
    w()
    w("---")
    w()

    # ── Table of Contents ──
    w("## Table of Contents")
    w()
    w("1. [Executive Summary](#executive-summary)")
    w("2. [Methodology](#methodology)")
    for i, m in enumerate(machines, 3):
        anchor = m["name"].lower().replace(" ", "-").replace(".", "")
        w(f"{i}. [{m['name']} ({m['ip']})](#{anchor})")
    w()
    w("---")
    w()

    # ── Executive Summary ──
    w("## Executive Summary")
    w()
    rooted = [m for m in machines if m["proof_flag"]]
    user_only = [m for m in machines if m["local_flag"] and not m["proof_flag"]]
    total_pts = sum(m.get("points", 0) for m in rooted)

    w(f"During the OSCP examination, {len(rooted)} out of {len(machines)} target machines "
      f"were fully compromised (proof.txt obtained). ", )
    if user_only:
        w(f"An additional {len(user_only)} machine(s) were partially compromised (local.txt obtained). ")
    w()

    w("| Machine | IP | OS | Local | Proof | Points |")
    w("|---|---|---|---|---|---|")
    for m in machines:
        local = "✓" if m["local_flag"] else "✗"
        proof = "✓" if m["proof_flag"] else "✗"
        pts = m.get("points", "-")
        os_val = m.get("os", "-")
        w(f"| {m['name']} | {m['ip']} | {os_val} | {local} | {proof} | {pts} |")
    w()
    w("---")
    w()

    # ── Methodology ──
    w("## Methodology")
    w()
    w("The following methodology was applied to each target machine:")
    w()
    w("1. **Reconnaissance & Enumeration** — Port scanning with nmap, service fingerprinting, "
      "and targeted enumeration of discovered services (web directories, SMB shares, SNMP, etc.)")
    w("2. **Vulnerability Analysis** — Identification of exploitable vulnerabilities, "
      "misconfigurations, and attack vectors based on enumeration findings")
    w("3. **Exploitation** — Initial access through identified vulnerabilities to obtain "
      "a foothold on the target system")
    w("4. **Privilege Escalation** — Elevation of privileges from the initial foothold "
      "to root/SYSTEM access")
    w("5. **Post-Exploitation** — Flag retrieval, credential harvesting, and documentation "
      "of the full attack chain")
    w()
    w("**Tools used:** nmap, gobuster, Burp Suite, Impacket, BloodHound, Evil-WinRM, "
      "GodPotato, Mimikatz, and standard Kali Linux utilities.")
    w()
    w("---")
    w()

    # ── Machine writeups ──
    for m in machines:
        w(f"## {m['name']} ({m['ip']})")
        w()

        # Info table
        w("| Property | Value |")
        w("|---|---|")
        w(f"| IP Address | {m['ip']} |")
        if m.get("hostname"):
            w(f"| Hostname | {m['hostname']} |")
        if m.get("domain"):
            w(f"| Domain | {m['domain']} |")
        if m.get("os"):
            w(f"| Operating System | {m['os']} |")
        if m.get("points"):
            w(f"| Points | {m['points']} |")
        w()

        # Ports
        if m["ports"]:
            w("### Service Enumeration")
            w()
            w("| Port | Service |")
            w("|---|---|")
            for p in m["ports"]:
                w(f"| {p['port']} | {p['service']} |")
            w()

        # Enum notes
        if m.get("enum_notes", "").strip():
            w("#### Enumeration Notes")
            w()
            w(m["enum_notes"].strip())
            w()

        # Initial Access
        ia = m["initial_access"]
        w("### Initial Access")
        w()
        if ia.get("vulnerability"):
            w(f"**Vulnerability:** {ia['vulnerability']}")
            w()
        if ia.get("description"):
            w(ia["description"])
            w()

        for i, step in enumerate(ia["steps"], 1):
            w(f"**Step {i}: {step['description']}**")
            w()
            if step.get("command"):
                w("```bash")
                w(step["command"])
                w("```")
                w()
            if step.get("output"):
                w("```")
                w(step["output"])
                w("```")
                w()
            if step.get("screenshot"):
                w(f"![{step['description']}]({step['screenshot']})")
                w()

        if m.get("local_flag"):
            w(f"**local.txt:** `{m['local_flag']}`")
            w()

        # Privilege Escalation
        pe = m["privilege_escalation"]
        w("### Privilege Escalation")
        w()
        if pe.get("vulnerability"):
            w(f"**Vulnerability:** {pe['vulnerability']}")
            w()
        if pe.get("description"):
            w(pe["description"])
            w()

        for i, step in enumerate(pe["steps"], 1):
            w(f"**Step {i}: {step['description']}**")
            w()
            if step.get("command"):
                w("```bash")
                w(step["command"])
                w("```")
                w()
            if step.get("output"):
                w("```")
                w(step["output"])
                w("```")
                w()
            if step.get("screenshot"):
                w(f"![{step['description']}]({step['screenshot']})")
                w()

        if m.get("proof_flag"):
            w(f"**proof.txt:** `{m['proof_flag']}`")
            w()

        # Post-exploitation
        if m.get("post_exploitation", "").strip():
            w("### Post-Exploitation")
            w()
            w(m["post_exploitation"].strip())
            w()

        # Additional notes
        if m.get("additional_notes", "").strip():
            w("### Additional Notes")
            w()
            w(m["additional_notes"].strip())
            w()

        w("---")
        w()

    # Write the report
    report_content = "\n".join(lines)
    with open(output_file, "w") as f:
        f.write(report_content)

    print(f"  {green('[+]')} Report generated: {bold(output_file)}")
    print(f"  {dim(f'    {len(machines)} machines, {len(lines)} lines')}")

    # Try PDF conversion
    if not args.no_pdf and shutil.which("pandoc"):
        pdf_file = output_file.replace(".md", ".pdf")
        print(f"  {cyan('[*]')} Converting to PDF with pandoc...")
        import subprocess
        result = subprocess.run(
            ["pandoc", output_file, "-o", pdf_file,
             "--pdf-engine=xelatex",
             "-V", "geometry:margin=1in",
             "-V", "fontsize=11pt",
             "--highlight-style=tango",
             "--toc"],
            capture_output=True, text=True,
        )
        if result.returncode == 0:
            print(f"  {green('[+]')} PDF generated: {bold(pdf_file)}")
        else:
            # Try with pdflatex or wkhtmltopdf
            result2 = subprocess.run(
                ["pandoc", output_file, "-o", pdf_file,
                 "-V", "geometry:margin=1in"],
                capture_output=True, text=True,
            )
            if result2.returncode == 0:
                print(f"  {green('[+]')} PDF generated: {bold(pdf_file)}")
            else:
                print(f"  {yellow('[*]')} PDF conversion failed — submit the markdown")
                print(f"  {dim(f'    Error: {result.stderr[:100]}')}")
    elif not args.no_pdf:
        print(f"\n  {dim('Tip: Install pandoc for auto PDF conversion:')}")
        print(f"  {dim('  sudo apt install pandoc texlive-xetex')}")

    print()


# ═══════════════════════════════════════════════════════════
#                     QUICKADD
# ═══════════════════════════════════════════════════════════

def cmd_quickadd(args):
    """Interactively add a complete machine writeup."""
    data = load_workspace(args.workspace)
    if not data:
        print(f"  {red('[!]')} No workspace found. Run {bold('init')} first.")
        return

    print(f"\n  {bold(cyan('Quick Add Machine'))}\n")

    name = input("  Machine name: ").strip()
    ip = input("  IP address: ").strip()

    if find_machine(data, name) or find_machine(data, ip):
        print(f"  {yellow('[!]')} Machine already exists")
        return

    machine = json.loads(json.dumps(MACHINE_TEMPLATE))
    machine["name"] = name
    machine["ip"] = ip
    machine["os"] = input("  OS (Linux/Windows): ").strip()
    machine["points"] = int(input("  Points (10/20/25): ").strip() or "0")
    machine["hostname"] = input("  Hostname (optional): ").strip()
    machine["domain"] = input("  Domain (optional): ").strip()

    # Ports
    print(f"\n  {dim('Enter ports (e.g. 22/ssh 80/http 445/smb). Empty line when done:')}")
    while True:
        port_input = input("    Port: ").strip()
        if not port_input:
            break
        parts = port_input.split("/", 1)
        port_num = parts[0].strip()
        service = parts[1].strip() if len(parts) > 1 else ""
        machine["ports"].append({"port": port_num, "service": service})

    # Initial access
    print(f"\n  {bold('Initial Access')}")
    machine["initial_access"]["vulnerability"] = input("  Vulnerability name: ").strip()
    machine["initial_access"]["description"] = input("  Description: ").strip()

    print(f"  {dim('Add exploitation steps. Empty description when done:')}")
    while True:
        desc = input("    Step description: ").strip()
        if not desc:
            break
        cmd = input("    Command (optional): ").strip()
        screenshot = input("    Screenshot path (optional): ").strip()
        machine["initial_access"]["steps"].append({
            "description": desc,
            "command": cmd,
            "output": "",
            "screenshot": screenshot,
        })

    machine["local_flag"] = input("\n  local.txt flag: ").strip()

    # Privesc
    print(f"\n  {bold('Privilege Escalation')}")
    machine["privilege_escalation"]["vulnerability"] = input("  Vulnerability name: ").strip()
    machine["privilege_escalation"]["description"] = input("  Description: ").strip()

    print(f"  {dim('Add privesc steps. Empty description when done:')}")
    while True:
        desc = input("    Step description: ").strip()
        if not desc:
            break
        cmd = input("    Command (optional): ").strip()
        screenshot = input("    Screenshot path (optional): ").strip()
        machine["privilege_escalation"]["steps"].append({
            "description": desc,
            "command": cmd,
            "output": "",
            "screenshot": screenshot,
        })

    machine["proof_flag"] = input("\n  proof.txt flag: ").strip()

    data["machines"].append(machine)
    save_workspace(data, args.workspace)
    print(f"\n  {green('[+]')} Added {bold(name)} with full writeup!")
    print(f"  {dim('    Run')} {cyan('generate')} {dim('when ready to build the report')}\n")


# ═══════════════════════════════════════════════════════════
#                        CLI
# ═══════════════════════════════════════════════════════════

def parse_args():
    p = argparse.ArgumentParser(
        description="Husky Report — OSCP exam report generator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent("""\
            Workflow:
              1. report.py init                              # Set up workspace
              2. report.py add box1 10.10.10.5 --os Linux    # Add machines
              3. report.py flag box1 local <hash>            # Record flags
              4. report.py step box1 initial "Found SQLi"    # Add steps
              5. report.py vuln box1 initial "SQL Injection" # Name the vuln
              6. report.py generate                          # Build the report

            Or use quickadd for interactive machine entry:
              report.py quickadd

            Examples:
              report.py add DC01 10.10.10.5 --os Windows --points 40 --domain corp.local
              report.py flag DC01 proof abc123def456
              report.py step DC01 initial "Nmap scan" -c "nmap -sCV 10.10.10.5" -s screenshots/nmap.png
              report.py step DC01 privesc "SeImpersonate abuse" -c "GodPotato.exe -cmd cmd"
              report.py vuln DC01 initial "AS-REP Roasting" --desc "Pre-auth disabled on svc_sql"
              report.py generate -o report.md
        """),
    )

    p.add_argument("-w", "--workspace", default=DEFAULT_WORKSPACE,
                   help=f"Workspace JSON file (default: {DEFAULT_WORKSPACE})")

    sub = p.add_subparsers(dest="cmd", help="Command")

    # init
    init = sub.add_parser("init", help="Initialize a new report workspace")
    init.add_argument("--force", action="store_true", help="Overwrite existing workspace")

    # add
    add = sub.add_parser("add", help="Add a machine")
    add.add_argument("name", help="Machine name (e.g. Box1, DC01)")
    add.add_argument("ip", help="Machine IP address")
    add.add_argument("--os", help="Operating system (Linux/Windows)")
    add.add_argument("--points", type=int, help="Point value (10/20/25/40)")
    add.add_argument("--hostname", help="Machine hostname")
    add.add_argument("--domain", help="AD domain name")

    # flag
    flag = sub.add_parser("flag", help="Record a flag")
    flag.add_argument("machine", help="Machine name or IP")
    flag.add_argument("type", choices=["local", "proof"], help="Flag type")
    flag.add_argument("value", help="Flag hash value")

    # ports
    ports = sub.add_parser("ports", help="Record open ports")
    ports.add_argument("machine", help="Machine name or IP")
    ports.add_argument("ports", nargs="+", help="Ports (e.g. 22/ssh 80/http 445/smb)")

    # step
    step = sub.add_parser("step", help="Add an exploitation step")
    step.add_argument("machine", help="Machine name or IP")
    step.add_argument("phase", choices=["initial", "privesc"], help="Phase")
    step.add_argument("description", help="Step description")
    step.add_argument("-c", "--command", help="Command used")
    step.add_argument("-o", "--output", help="Command output (brief)")
    step.add_argument("-s", "--screenshot", help="Screenshot file path")

    # vuln
    vuln = sub.add_parser("vuln", help="Set vulnerability name for a phase")
    vuln.add_argument("machine", help="Machine name or IP")
    vuln.add_argument("phase", choices=["initial", "privesc"], help="Phase")
    vuln.add_argument("name", help="Vulnerability name")
    vuln.add_argument("--desc", help="Vulnerability description")

    # note
    note = sub.add_parser("note", help="Add freeform notes")
    note.add_argument("machine", help="Machine name or IP")
    note.add_argument("section", choices=["enum", "post", "general"], help="Section")
    note.add_argument("text", help="Note text")

    # status
    sub.add_parser("status", help="Show report progress")

    # quickadd
    sub.add_parser("quickadd", help="Interactively add a complete machine")

    # generate
    gen = sub.add_parser("generate", help="Generate the final report")
    gen.add_argument("-o", "--output", default="OSCP_Exam_Report.md",
                     help="Output filename (default: OSCP_Exam_Report.md)")
    gen.add_argument("--no-pdf", action="store_true",
                     help="Skip PDF conversion even if pandoc is available")

    return p.parse_args()


def main():
    args = parse_args()
    print(BANNER)

    if not args.cmd:
        print(f"  Usage: python3 report.py {{init,add,flag,step,vuln,ports,note,status,quickadd,generate}}")
        print(f"\n  {bold('Quick start:')}")
        print(f"    {cyan('python3 report.py init')}")
        print(f"    {cyan('python3 report.py add Box1 10.10.10.5 --os Linux --points 20')}")
        print(f"    {cyan('python3 report.py quickadd')}  {dim('(interactive)')}")
        print(f"    {cyan('python3 report.py generate')}\n")
        sys.exit(0)

    cmds = {
        "init": cmd_init,
        "add": cmd_add_machine,
        "flag": cmd_flag,
        "ports": cmd_ports,
        "step": cmd_step,
        "vuln": cmd_vuln,
        "note": cmd_note,
        "status": cmd_status,
        "quickadd": cmd_quickadd,
        "generate": cmd_generate,
    }

    handler = cmds.get(args.cmd)
    if handler:
        handler(args)
    else:
        print(f"  {red('[!]')} Unknown command: {args.cmd}")


if __name__ == "__main__":
    main()
