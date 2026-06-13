"""
Input validators for security-sensitive user data.

Provides:
    validate_nmap_args(user_args) -> str   Sanitise nmap CLI arguments
"""

import re

# ---------------------------------------------------------------------------
# Whitelist — flags that are harmless to accept from users
# ---------------------------------------------------------------------------
_ALLOWED_NMAP_FLAGS: set[str] = {
    "-sS", "-sT", "-sU", "-sV", "-sC",
    "-T0", "-T1", "-T2", "-T3", "-T4", "-T5",
    "-Pn", "--open", "-A", "-O",
    "-p", "--top-ports", "--version-intensity", "--version-all",
    "--min-rate", "--max-rate", "--host-timeout",
}

# ---------------------------------------------------------------------------
# Blocklist — flags that can lead to RCE, information disclosure, or DoS
# ---------------------------------------------------------------------------
_BLOCKED_NMAP_FLAGS: set[str] = {
    "--script",          # NSE script engine — arbitrary Lua execution
    "-oN", "-oX", "-oG", "-oA",   # Output-file flags
    "--datadir",         # Override Nmap data dir
    "-iL",               # Read targets from attacker-controlled file
    "--resume",          # Resume a previous (possibly malicious) scan
    "--stylesheet",      # XSL stylesheet injection
    "--iflist",          # Enumerate network interfaces
    "--packet-trace",    # Verbose network trace
}

# Simple regex for validating port-range / port-list arguments
_PORT_RANGE_RE = re.compile(r"^[\d,\-:]+$")


def validate_nmap_args(user_args: str) -> str:
    """Validate and sanitise user-supplied nmap arguments.

    If *user_args* is empty the function returns a safe default.

    Parameters
    ----------
    user_args : str
        Raw arguments string (e.g. ``"-sS -sV -T4 --open -p 1-1000"``).

    Returns
    -------
    str
        Sanitised arguments string, guaranteed to contain only allowed flags.

    Raises
    ------
    ValueError
        If a blocked flag is detected.
    """
    if not user_args or not user_args.strip():
        return "-sT -sV -T4 --open"

    tokens: list[str] = user_args.strip().split()
    safe_tokens: list[str] = []
    i = 0

    while i < len(tokens):
        token = tokens[i]

        # --- Block dangerous flags immediately --------------------------------
        if token in _BLOCKED_NMAP_FLAGS:
            raise ValueError(
                f"Nmap flag '{token}' is not allowed for security reasons"
            )

        # --- Allow known safe standalone flags --------------------------------
        if token in _ALLOWED_NMAP_FLAGS:
            safe_tokens.append(token)
            i += 1
            continue

        # --- -p with port range / list ---------------------------------------
        if token == "-p" and i + 1 < len(tokens):
            port_arg = tokens[i + 1]
            if _PORT_RANGE_RE.match(port_arg):
                safe_tokens.extend((token, port_arg))
                i += 2
                continue
            # If the value looks suspicious, skip the flag+value entirely
            i += 2
            continue

        # --- --top-ports <N> -------------------------------------------------
        if token == "--top-ports" and i + 1 < len(tokens):
            if tokens[i + 1].isdigit():
                safe_tokens.extend((token, tokens[i + 1]))
                i += 2
                continue
            i += 2
            continue

        # --- --min-rate / --max-rate / --host-timeout / --version-intensity <N>[s] --
        if token in ("--min-rate", "--max-rate", "--host-timeout", "--version-intensity") and i + 1 < len(tokens):
            val = tokens[i + 1].rstrip("s")
            if val.isdigit():
                safe_tokens.extend((token, tokens[i + 1]))
                i += 2
                continue
            i += 2
            continue

        # --- Unknown / unrecognised flag — drop it silently -------------------
        i += 1

    return " ".join(safe_tokens) if safe_tokens else "-sS -sV -T4"


# ---------------------------------------------------------------------------
# SQLMap argument validation
# ---------------------------------------------------------------------------
_ALLOWED_SQLMAP_FLAGS: set[str] = {
    "--batch", "--flush-session", "--fresh-queries",
    "--no-cast", "--no-escape",
    "--random-agent", "--mobile",
    "--sql-query", "--sql-shell",
    "--tables", "--columns", "--dump", "--dump-all",
    "--banner", "--current-user", "--current-db",
    "--is-dba", "--users", "--passwords", "--privileges", "--roles",
    "--dbs", "--tables", "--columns", "--schema",
    "--count", "--exclude-sysdbs",
    "--hex",
    "--identify-waf",
}

_BLOCKED_SQLMAP_FLAGS: set[str] = {
    "--os-cmd", "--os-shell", "--os-pwn",
    "--reg-read", "--reg-add", "--reg-del",
    "--file-read", "--file-write", "--file-dest",
    "--hostname", "--priv-esc",
    "--search",
    "--udf-inject", "--shm-file",
    "-r", "--proxy", "--tor",
    "--output-dir",
    "--save", "--update",
}

_TAMPER_SCRIPTS: set[str] = {
    "apostrophemask", "apostrophenullencode", "appendnullbyte",
    "base64encode", "between", "bluecoat", "chardoubleencode",
    "charencode", "charunicodeencode", "charunicodeescape",
    "commalesslimit", "commalessmid", "commentbeforeparentheses",
    "concat2concatws", "equaltolike", "escapequotes",
    "greatest", "halfversionedmorekeywords", "hex2char",
    "htmlencode", "ifnull2casewhenisnull", "ifnull2ifisnull",
    "informationschemacomment", "least", "lowercase",
    "modsecurityversioned", "modsecurityzeroversioned",
    "multiplespaces", "ord2ascii", "overlongutf8",
    "overlongutf8more", "percentage", "plus2concat",
    "plus2fnconcat", "randomcase", "randomcomments",
    "securesphere", "space2comment", "space2dash",
    "space2hash", "space2morehash", "space2morecomment",
    "space2mssqlblank", "space2mssqlhash", "space2mysqlblank",
    "space2mysqldash", "space2plus", "space2randomblank",
    "sp_password", "substring2leftright", "symboliclogical",
    "unionalltounion", "unmagicquotes", "uppercase",
    "varnish", "versionedkeywords", "versionedmorekeywords",
    "xforwardedfor",
}


def validate_sqlmap_args(user_args: str) -> str:
    """Validate and sanitise user-supplied sqlmap arguments.

    If *user_args* is empty the function returns a safe default.

    Parameters
    ----------
    user_args : str
        Raw arguments string (e.g. ``"--batch --risk 2 --level 3"``).

    Returns
    -------
    str
        Sanitised arguments string, guaranteed to contain only allowed flags.

    Raises
    ------
    ValueError
        If a blocked flag is detected.
    """
    if not user_args or not user_args.strip():
        return "--batch"

    tokens: list[str] = user_args.strip().split()
    safe_tokens: list[str] = []
    i = 0

    while i < len(tokens):
        token = tokens[i]

        if token in _BLOCKED_SQLMAP_FLAGS:
            raise ValueError(
                f"Sqlmap flag '{token}' is not allowed for security reasons"
            )

        # Flags that require a value — checked before standalone flags
        if token in ("--risk", "--level", "--threads", "--time-sec", "--retries") and i + 1 < len(tokens):
            val = tokens[i + 1]
            if val.isdigit():
                safe_tokens.extend((token, val))
                i += 2
                continue
            if val.startswith("--"):
                i += 1
                continue
            i += 2
            continue

        if token == "--dbms" and i + 1 < len(tokens):
            dbms = tokens[i + 1].upper()
            if dbms in ("MYSQL", "POSTGRESQL", "MSSQL", "ORACLE", "SQLITE", "ACCESS", "FIREBIRD", "MAXDB", "SYBASE", "DB2", "HSQLDB", "INFORMIX"):
                safe_tokens.extend((token, dbms))
                i += 2
                continue
            if tokens[i + 1].startswith("--"):
                i += 1
                continue
            i += 2
            continue

        if token == "--tamper" and i + 1 < len(tokens):
            scripts = [s.strip() for s in tokens[i + 1].split(",") if s.strip() in _TAMPER_SCRIPTS]
            if scripts:
                safe_tokens.extend((token, ",".join(scripts)))
                i += 2
                continue
            if tokens[i + 1].startswith("--"):
                i += 1
                continue
            i += 2
            continue

        if token in ("--csrf-token", "--csrf-url", "--sql-query", "--eval", "--data", "-T", "-C", "--start", "--stop") and i + 1 < len(tokens):
            if tokens[i + 1].startswith("--"):
                i += 1
                continue
            safe_tokens.extend((token, tokens[i + 1]))
            i += 2
            continue

        # Standalone flags (no value required)
        if token in _ALLOWED_SQLMAP_FLAGS:
            safe_tokens.append(token)
            i += 1
            continue

        # Unknown flag — drop silently
        i += 1

    return " ".join(safe_tokens) if safe_tokens else "--batch"
