# Husky Report — OSCP Exam Report Generator

Build your report incrementally during the exam, then generate a clean OffSec-formatted markdown report with one command. Auto-converts to PDF if pandoc is installed.

Zero dependencies beyond Python 3.6+ stdlib. Husky Hacker branding.

---

## Install

```bash
git clone https://github.com/TheHuskyHacker/oscp-report-gen
cd huskyreport
chmod +x report.py
sudo ln -s $(pwd)/report.py /usr/local/bin/report
```

---

## Exam Day Workflow

```bash
# 1. Before the exam starts — initialize
report init

# 2. As you discover machines — add them
report add Box1 10.10.10.5 --os Linux --points 20
report add Box2 10.10.10.10 --os Windows --points 20
report add AD 10.10.10.100 --os Windows --points 40 --domain corp.local

# 3. As you hack — record what you find
report ports Box1 22/ssh 80/http 3306/mysql
report vuln Box1 initial "SQL Injection in login form" --desc "UNION-based SQLi in the user parameter"
report step Box1 initial "Discovered SQL injection" -c "sqlmap -u 'http://10.10.10.5/login' --dbs" -s screenshots/sqli.png
report step Box1 initial "Got SSH creds from database" -c "sqlmap ... -D webapp -T users --dump"
report flag Box1 local abc123def456

report vuln Box1 privesc "SUID binary abuse"
report step Box1 privesc "Found SUID custom binary" -c "find / -perm -4000 2>/dev/null"
report step Box1 privesc "Exploited PATH injection" -c "export PATH=/tmp:$PATH && /usr/bin/custom_backup"
report flag Box1 proof 789xyz000111

# 4. Check progress anytime
report status

# 5. After the exam — generate
report generate
```

---

## Commands

| Command | What It Does |
|---|---|
| `init` | Create a new report workspace (prompts for OSID, email, date) |
| `add <name> <ip>` | Add a machine with optional `--os`, `--points`, `--domain`, `--hostname` |
| `flag <machine> <local\|proof> <hash>` | Record a flag value |
| `ports <machine> <port/svc ...>` | Record open ports (e.g. `22/ssh 80/http`) |
| `vuln <machine> <initial\|privesc> <name>` | Name the vulnerability for a phase |
| `step <machine> <initial\|privesc> <desc>` | Add an exploitation step with `-c` command, `-s` screenshot |
| `note <machine> <enum\|post\|general> <text>` | Add freeform notes |
| `status` | Show current progress — machines, flags, steps |
| `quickadd` | Interactively add a complete machine writeup |
| `generate` | Build the final markdown report (auto-PDF if pandoc installed) |

---

## Report Output

The generated report includes:

- **Title page** with OSID, email, exam date
- **Table of contents** linked to each machine
- **Executive summary** table with all machines, flags, and points
- **Methodology** section (pre-written, OffSec-compliant)
- **Per-machine writeups** with:
  - Service enumeration table
  - Initial access steps with commands, output, and screenshots
  - Privilege escalation steps with commands, output, and screenshots
  - Flag values (local.txt and proof.txt)
  - Post-exploitation and additional notes

### PDF Conversion

If `pandoc` and `texlive-xetex` are installed, the report auto-converts to PDF:

```bash
sudo apt install pandoc texlive-xetex
report generate  # produces .md and .pdf
```

---

## Options

| Flag | Description | Default |
|---|---|---|
| `-w, --workspace` | Workspace JSON file | `oscp_report.json` |
| `-o, --output` | Report output filename | `OSCP_Exam_Report.md` |
| `--no-pdf` | Skip PDF conversion | off |
| `--force` | Overwrite existing workspace on init | off |

---

## Tips for Exam Day

- Run `report init` **before** the exam starts so you're not fumbling with setup
- Add machines and ports as soon as nmap finishes — takes 10 seconds
- Record steps as you go, not after — you'll forget the exact commands
- Use `report status` to see your progress at a glance
- Screenshots go in `./screenshots/` — reference them with `-s screenshots/filename.png`
- `quickadd` is great for machines you've already finished — fill in everything at once
- Generate the report immediately after the exam while it's fresh

---

## License

MIT
