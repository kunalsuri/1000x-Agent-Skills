# Threat model and limits

What this tool defends against, what it does not, and why the distinction is
written down rather than left implied.

## The two surfaces

A skill bundle is code and instruction at once, and the two fail differently.

**The instruction surface** is every byte of text an agent reads into its
context: `SKILL.md`, the reference documents, and any data file the skill
loads. Text here is not documentation; it is input to a system that acts on
what it reads. A sentence in a reference file is executable in the only
sense that matters.

**The execution surface** is every file the machine can run: scripts, hooks,
lifecycle steps, and anything the language runtime loads on its own. It is
larger than the set of files `SKILL.md` mentions, and the difference between
those two sets is where the published bypasses live.

## What is defended

| Class | Checks | Notes |
|---|---|---|
| Instruction smuggling | `EXT-INVISIBLE-UNICODE`, `EXT-BIDI-CONTROL`, `EXT-HIDDEN-DIRECTIVE`, `EXT-TRIGGER-ABUSE` | Text the model reads and a reviewer does not |
| Execution without invocation | `EXT-AUTORUN`, `EXT-GIT-HOOK`, `EXT-GIT-CONFIG-EXEC`, `EXT-AGENT-HOOKS` | The class the documented bypasses used |
| Review evasion | `EXT-WHITESPACE-INFLATION`, `EXT-LONG-LINE`, `EXT-ENCODED-BLOB`, `EXT-OBFUSCATION`, `EXT-BYTECODE` | Content shaped to be unreadable |
| Unreviewable content | `EXT-NATIVE-BINARY`, `EXT-OPAQUE-BINARY`, `EXT-NESTED-ARCHIVE`, `EXT-UNDECODABLE-*`, `EXT-OVERSIZE-FILE` | Reported as unverified, never as clean |
| Capability dishonesty | `EXT-CAP-UNDECLARED` | The code exceeds the bundle's own claims |
| Over-privilege | `EXT-OVER-PRIVILEGE`, `EXT-TOOL-GRANT` | What installing actually grants |
| Silent update | `EXT-DIGEST-MISMATCH` | The bundle is no longer what was reviewed |
| Scope escape | `EXT-SYMLINK-ESCAPE`, `EXT-SYMLINK` | Paths that reach outside the bundle |

## What is not defended

Stated as flatly as possible, because a limit a reader has to infer is a
limit that will surprise them.

1. **Intent.** Static analysis reports what code can do. It cannot decide
   whether doing it is legitimate. A backup tool and an exfiltration tool
   read files and open sockets in exactly the same way; they differ only in
   where the bytes go and whether you agreed to it.

2. **Non-Python code.** Only Python is parsed. Shell, JavaScript, Ruby and
   the rest get a pattern scan, which any author who has seen the patterns
   can step around. Every such file is reported as `EXT-UNVERIFIABLE-CODE`
   rather than being quietly counted as checked.

3. **Archives.** Nothing is extracted; extracting hostile archives is its
   own class of vulnerability. A nested archive is reported and its contents
   are entirely unknown.

4. **Symlink targets.** Links are reported and never followed.

5. **Dependencies.** A `requirements.txt` or `package.json` naming a hostile
   package will pass. Nothing is resolved, downloaded or inspected.

6. **Runtime behaviour.** Nothing executes, so anything that only appears at
   runtime -- a payload fetched on first use, behaviour gated on a date or a
   hostname -- is invisible here.

7. **A determined, informed author.** Every check in this tool is published
   in this repository. Someone who reads it can evade it. That is true of
   every static scanner and is the reason the recommendation below is
   layered rather than singular.

## Why a clean result is not a safety claim

Researchers have bypassed every publicly documented agent-skill scanner,
including those maintained by large organisations, using techniques that
required no novel research: padding to exceed a reading limit, shipping
precompiled bytecode, indirection through an archive, and persuading a
model-based reviewer in prose. The Cloud Security Alliance's conclusion was
that investment in scanner patterns alone produces marginally better
scanners that fall to marginally better obfuscation.

This tool is therefore written to be one layer, and to say so. Its verdict
vocabulary has no word for safe: `no_known_findings` is a statement about
the scan, not about the bundle.

## Recommended layers

Run more than one thing, from more than one author.

- **[NVIDIA SkillSpector](https://github.com/NVIDIA/skillspector)**
  (Apache-2.0). The closest open-source equivalent to this tool and the most
  complete: many more patterns, YARA signatures, dependency CVE lookups,
  SARIF output for CI. `skillspector scan ./bundle --no-llm` runs offline.
- **[Snyk agent-scan](https://github.com/snyk/agent-scan)** (Apache-2.0),
  formerly Invariant Labs' `mcp-scan`. Scans skills and MCP servers together.
  Requires an account and network access, so it complements an offline tool
  rather than replacing one.
- **Cisco DefenseClaw skill-scanner.** Signature and dataflow based, with an
  optional model-judged layer.
- **[OWASP Agentic Skills Top 10](https://owasp.org/www-project-agentic-skills-top-10/)**
  as the shared taxonomy. Findings from this tool carry `AST` identifiers so
  results can be compared across scanners.
- **Sandboxed execution** for anything consequential. A container with no
  network and no access to real user data, running the bundle's own test
  suite, catches the runtime-only behaviour no static tool can.
- **Least privilege at install time.** Grant the smallest tool set the skill
  needs, and do not install skills on a machine that holds material you
  cannot afford to lose.

## On what this record is for

The JSON record exists to be kept. It states the ruleset version, the bundle
digest, the findings and the date, so that "what did we check, and when"
has an answer that does not depend on anyone's memory. It is a log of a
scan. It is not a certification, and it does not transfer responsibility for
an installation from the person installing to the person who wrote the
scanner.
