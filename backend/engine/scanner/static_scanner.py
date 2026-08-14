import os
import re
import json
import logging
from typing import List, Dict, Any

from engine.models import Finding
from engine.repository.models import SourceSnapshot

logger = logging.getLogger("codeloom.scanner.static")

IGNORE_DIRS = {
    ".git", "node_modules", "dist", "build", ".next", ".venv",
    "coverage", "vendor", "public/build", "__pycache__", ".idea", ".vscode"
}

TARGET_EXTENSIONS = {
    ".html", ".htm", ".jsx", ".tsx", ".js", ".ts", ".vue", ".svelte", ".css"
}

# =========================================================================
# SPECIALIZED CATEGORY AI AGENT PROMPTS
# =========================================================================
CATEGORY_AI_PROMPTS = {
    "accessibility": """You are the CodeLoom AI Accessibility Specialist Agent (WCAG 2.1/2.2 AA Expert).
Your job is to inspect source code files from the user's repository and identify genuine accessibility violations:
- WCAG 2.1 AA non-conformance
- Missing image alt attributes
- Icon buttons without aria-label / accessible text
- Empty / placeholder anchor hrefs
- Missing html lang attributes
- Non-interactive elements with click handlers missing keyboard role/tabindex
- Form controls missing associated labels
Return exact file paths, line numbers, and WCAG recommendations.""",

    "seo": """You are the CodeLoom AI SEO Specialist Agent (Search Engine Optimization & Indexing Expert).
Your job is to inspect source code files from the user's repository and identify genuine SEO flaws:
- Missing or empty page title tags
- Missing meta description tags
- Missing meta viewport tags for mobile indexing
- Multiple <h1> headings on a single document template
- Missing image alt attributes affecting search engine image indexing
Return exact file paths, line numbers, and SEO ranking optimizations.""",

    "performance": """You are the CodeLoom AI Performance Specialist Agent (Web Vitals & Asset Optimization Expert).
Your job is to inspect source code files from the user's repository and identify genuine performance bottlenecks:
- Unoptimized image loading (missing loading='lazy')
- Render-blocking synchronous external script tags in document head
- CSS @import statements causing sequential network requests
- Heavy inline Base64 data URIs (>2KB)
- Production console.log statements impacting main thread execution
Return exact file paths, line numbers, and Web Vitals remediation steps."""
}


class StaticScanner:
    """
    Scans a local repository snapshot for genuine accessibility, SEO, and performance
    issues across HTML, JSX, TSX, Vue, Svelte, JS, TS, and CSS files.
    """

    def __init__(self):
        pass

    async def scan_repository(self, snapshot: SourceSnapshot, categories: List[str]) -> List[Finding]:
        """
        Scans all relevant source code files in the local repository directory
        and returns actual findings strictly matching the selected categories.
        """
        findings: List[Finding] = []
        repo_path = snapshot.local_path
        logger.info(f"Starting static scan on real repository at {repo_path} for categories: {categories}")

        if not os.path.isdir(repo_path):
            logger.error(f"Repository path does not exist: {repo_path}")
            return findings

        # Determine active category filters strictly
        active_cats = set(categories)
        if "all" in active_cats:
            scan_a11y = True
            scan_seo = True
            scan_perf = True
        else:
            scan_a11y = "accessibility" in active_cats
            scan_seo = "seo" in active_cats
            scan_perf = "performance" in active_cats

        logger.info(f"Category scan flags -> Accessibility: {scan_a11y}, SEO: {scan_seo}, Performance: {scan_perf}")

        # Walk through source files
        file_count = 0
        for root, dirs, files in os.walk(repo_path):
            dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]

            for file in files:
                ext = os.path.splitext(file)[1].lower()
                if ext not in TARGET_EXTENSIONS:
                    continue

                full_path = os.path.join(root, file)
                rel_path = os.path.relpath(full_path, repo_path).replace("\\", "/")
                file_count += 1

                try:
                    with open(full_path, "r", encoding="utf-8", errors="ignore") as f:
                        lines = f.readlines()
                except Exception as e:
                    logger.warning(f"Could not read file {rel_path}: {e}")
                    continue

                # Run Category Specialist Agents strictly according to flags
                if scan_a11y:
                    findings.extend(self._scan_accessibility(rel_path, lines, ext))

                if scan_seo:
                    findings.extend(self._scan_seo(rel_path, lines, ext))

                if scan_perf:
                    findings.extend(self._scan_performance(rel_path, lines, ext))

        logger.info(f"Completed static scan across {file_count} files. Total genuine findings matching categories {categories}: {len(findings)}")
        return findings

    # =========================================================================
    # 1. ACCESSIBILITY RULES ANALYZER (Accessibility Specialist Agent)
    # =========================================================================
    def _scan_accessibility(self, file_path: str, lines: List[str], ext: str) -> List[Finding]:
        findings: List[Finding] = []

        # Check for HTML missing lang attribute
        if ext in (".html", ".htm"):
            content = "".join(lines)
            if "<html" in content.lower() and not re.search(r'<html[^>]*\blang\s*=', content, re.IGNORECASE):
                first_line = 1
                for idx, line in enumerate(lines, 1):
                    if "<html" in line.lower():
                        first_line = idx
                        break
                findings.append(Finding(
                    rule_id="html-has-lang",
                    title="<html> element missing lang attribute",
                    description="The <html> element must have a valid lang attribute (e.g. lang='en') for screen reader language engine initialization.",
                    severity="serious",
                    category="accessibility",
                    affected_selectors=["html"],
                    representative_snippet=lines[first_line - 1].strip() if lines else "<html>",
                    source_matches=[{
                        "filePath": file_path,
                        "lineNumber": first_line,
                        "confidence": "high",
                        "exactMatchVerified": True,
                        "sourceCode": lines[first_line - 1].strip() if lines else "<html>"
                    }]
                ))

        for line_num, raw_line in enumerate(lines, 1):
            line = raw_line.strip()

            # Rule: img missing alt
            if "<img" in line.lower():
                if not re.search(r'\balt\s*=', line, re.IGNORECASE):
                    findings.append(Finding(
                        rule_id="jsx-a11y/alt-text",
                        title="Image missing required alt attribute",
                        description="Image element is missing an alt attribute. Provide textual descriptions for screen readers or alt='' for decorative graphics.",
                        severity="serious",
                        category="accessibility",
                        affected_selectors=["img"],
                        representative_snippet=line,
                        source_matches=[{
                            "filePath": file_path,
                            "lineNumber": line_num,
                            "confidence": "high",
                            "exactMatchVerified": True,
                            "sourceCode": line
                        }]
                    ))

            # Rule: Button missing text or aria-label
            if "<button" in line.lower():
                if not re.search(r'\baria-label\s*=', line, re.IGNORECASE) and not re.search(r'\baria-labelledby\s*=', line, re.IGNORECASE):
                    if "/>" in line or re.search(r'<button[^>]*>\s*<i[^>]*>.*?</i>\s*</button>', line, re.IGNORECASE):
                        findings.append(Finding(
                            rule_id="button-name",
                            title="Icon button missing accessible label (aria-label)",
                            description="Buttons containing only icon elements or empty text must have an explicit aria-label or title for assistive technology.",
                            severity="serious",
                            category="accessibility",
                            affected_selectors=["button"],
                            representative_snippet=line,
                            source_matches=[{
                                "filePath": file_path,
                                "lineNumber": line_num,
                                "confidence": "high",
                                "exactMatchVerified": True,
                                "sourceCode": line
                            }]
                        ))

            # Rule: Anchor with empty or javascript/hash href
            if "<a " in line.lower() or "<a\t" in line.lower():
                if re.search(r'href=["\'](?:#|javascript:void\(0\)?;?|)["\']', line, re.IGNORECASE):
                    findings.append(Finding(
                        rule_id="link-name",
                        title="Anchor link with dummy or empty href attribute",
                        description="Links pointing to '#' or 'javascript:void(0)' degrade keyboard navigation. Use a <button> for interactive actions instead.",
                        severity="moderate",
                        category="accessibility",
                        affected_selectors=["a"],
                        representative_snippet=line,
                        source_matches=[{
                            "filePath": file_path,
                            "lineNumber": line_num,
                            "confidence": "high",
                            "exactMatchVerified": True,
                            "sourceCode": line
                        }]
                    ))

            # Rule: Input field missing accessible label or aria-label
            if "<input" in line.lower() and not re.search(r'type=["\'](?:hidden|submit|button|reset)["\']', line, re.IGNORECASE):
                if not re.search(r'\b(aria-label|aria-labelledby|id)\s*=', line, re.IGNORECASE):
                    findings.append(Finding(
                        rule_id="a11y-input-label",
                        title="Form input field missing accessible label or id",
                        description="Input elements must have an associated <label>, aria-label, or aria-labelledby for screen reader identification.",
                        severity="serious",
                        category="accessibility",
                        affected_selectors=["input"],
                        representative_snippet=line,
                        source_matches=[{
                            "filePath": file_path,
                            "lineNumber": line_num,
                            "confidence": "high",
                            "exactMatchVerified": True,
                            "sourceCode": line
                        }]
                    ))

            # Rule: Non-interactive element with click handler
            if (("onclick=" in line.lower() or "@click=" in line.lower() or "onclick={" in line.lower()) and
                ("<div" in line.lower() or "<span" in line.lower())):
                if "role=" not in line.lower() and "tabindex" not in line.lower():
                    findings.append(Finding(
                        rule_id="a11y-non-interactive-click",
                        title="Non-interactive element with click event listener",
                        description="Non-interactive elements (<div/span>) with click handlers must have role='button' and tabIndex='0' for keyboard users.",
                        severity="moderate",
                        category="accessibility",
                        affected_selectors=["div", "span"],
                        representative_snippet=line,
                        source_matches=[{
                            "filePath": file_path,
                            "lineNumber": line_num,
                            "confidence": "high",
                            "exactMatchVerified": True,
                            "sourceCode": line
                        }]
                    ))

        return findings

    # =========================================================================
    # 2. SEO RULES ANALYZER (SEO Specialist Agent)
    # =========================================================================
    def _scan_seo(self, file_path: str, lines: List[str], ext: str) -> List[Finding]:
        findings: List[Finding] = []

        if ext in (".html", ".htm", ".jsx", ".tsx"):
            content = "".join(lines)

            # Rule: Missing meta description in HTML files
            if ext in (".html", ".htm") and "<head" in content.lower():
                if not re.search(r'<meta[^>]*name=["\']description["\']', content, re.IGNORECASE):
                    head_line = 1
                    for idx, line in enumerate(lines, 1):
                        if "<head" in line.lower():
                            head_line = idx
                            break
                    findings.append(Finding(
                        rule_id="seo-missing-meta-description",
                        title="Missing Meta Description Tag",
                        description="HTML document is missing a <meta name='description'> tag. Search engines rely on meta descriptions for search results snippets.",
                        severity="serious",
                        category="seo",
                        affected_selectors=["head"],
                        representative_snippet=lines[head_line - 1].strip() if lines else "<head>",
                        source_matches=[{
                            "filePath": file_path,
                            "lineNumber": head_line,
                            "confidence": "high",
                            "exactMatchVerified": True,
                            "sourceCode": lines[head_line - 1].strip() if lines else "<head>"
                        }]
                    ))

                # Rule: Missing viewport meta tag
                if not re.search(r'<meta[^>]*name=["\']viewport["\']', content, re.IGNORECASE):
                    findings.append(Finding(
                        rule_id="seo-missing-viewport",
                        title="Missing Viewport Meta Tag for Mobile Indexing",
                        description="Document is missing a <meta name='viewport' content='width=device-width, initial-scale=1'> tag required for mobile SEO.",
                        severity="serious",
                        category="seo",
                        affected_selectors=["head"],
                        representative_snippet="<head>",
                        source_matches=[{
                            "filePath": file_path,
                            "lineNumber": 1,
                            "confidence": "high",
                            "exactMatchVerified": True,
                            "sourceCode": "<head>"
                        }]
                    ))

                # Rule: Missing Title Tag
                if not re.search(r'<title>[^<]*</title>', content, re.IGNORECASE):
                    findings.append(Finding(
                        rule_id="seo-missing-title",
                        title="Missing or Empty Title Tag",
                        description="Document is missing a <title> tag or it is empty. This is critical for search rankings and tab displays.",
                        severity="serious",
                        category="seo",
                        affected_selectors=["head"],
                        representative_snippet="<head>",
                        source_matches=[{
                            "filePath": file_path,
                            "lineNumber": 1,
                            "confidence": "high",
                            "exactMatchVerified": True,
                            "sourceCode": "<head>"
                        }]
                    ))

                # Rule: Missing Favicon
                if not re.search(r'<link[^>]*rel=["\'](?:shortcut )?icon["\']', content, re.IGNORECASE):
                    findings.append(Finding(
                        rule_id="seo-missing-favicon",
                        title="Missing Favicon",
                        description="Document is missing a link to a favicon. Google renders favicons prominently in mobile search results.",
                        severity="moderate",
                        category="seo",
                        affected_selectors=["head"],
                        representative_snippet="<head>",
                        source_matches=[{
                            "filePath": file_path,
                            "lineNumber": 1,
                            "confidence": "high",
                            "exactMatchVerified": True,
                            "sourceCode": "<head>"
                        }]
                    ))

                # Rule: Accidental No-Index
                if re.search(r'<meta[^>]*name=["\']robots["\'][^>]*content=["\'][^"\']*noindex', content, re.IGNORECASE):
                    noindex_line = 1
                    for idx, line in enumerate(lines, 1):
                        if "noindex" in line.lower() and "robots" in line.lower():
                            noindex_line = idx
                            break
                    findings.append(Finding(
                        rule_id="seo-noindex-accidental",
                        title="Accidental No-Index Directive",
                        description="Document contains a <meta name='robots' content='noindex'> tag. This completely blocks search engines from indexing the page.",
                        severity="critical",
                        category="seo",
                        affected_selectors=["head"],
                        representative_snippet="<head>",
                        source_matches=[{
                            "filePath": file_path,
                            "lineNumber": noindex_line,
                            "confidence": "high",
                            "exactMatchVerified": True,
                            "sourceCode": lines[noindex_line - 1].strip() if lines else "<head>"
                        }]
                    ))

            # Rule: Multiple H1 tags on same page template
            h1_count = len(re.findall(r'<h1[\s>]', content, re.IGNORECASE))
            if h1_count > 1:
                first_h1_line = 1
                for idx, line in enumerate(lines, 1):
                    if "<h1" in line.lower():
                        first_h1_line = idx
                        break
                findings.append(Finding(
                    rule_id="seo-multiple-h1",
                    title="Multiple <h1> headings detected in single template",
                    description=f"Found {h1_count} <h1> elements in file. Search engines prefer a single <h1> heading per document hierarchy.",
                    severity="moderate",
                    category="seo",
                    affected_selectors=["h1"],
                    representative_snippet=lines[first_h1_line - 1].strip() if lines else "<h1>",
                    source_matches=[{
                        "filePath": file_path,
                        "lineNumber": first_h1_line,
                        "confidence": "high",
                        "exactMatchVerified": True,
                        "sourceCode": lines[first_h1_line - 1].strip() if lines else "<h1>"
                    }]
                ))
            
            # Rule: Missing JSON-LD Structured Data
            if ext in (".html", ".htm") and "<head" in content.lower():
                if not re.search(r'application/ld\+json', content, re.IGNORECASE):
                    head_line = 1
                    for idx, line in enumerate(lines, 1):
                        if "<head" in line.lower():
                            head_line = idx
                            break
                    findings.append(Finding(
                        rule_id="seo-missing-jsonld",
                        title="Missing JSON-LD Structured Data",
                        description="Document is missing Schema.org structured data (application/ld+json). Rich snippets dramatically improve CTR.",
                        severity="serious",
                        category="seo",
                        affected_selectors=["head"],
                        representative_snippet="<head>",
                        source_matches=[{
                            "filePath": file_path,
                            "lineNumber": head_line,
                            "confidence": "high",
                            "exactMatchVerified": True,
                            "sourceCode": lines[head_line - 1].strip() if lines else "<head>"
                        }]
                    ))

            # Rule: Missing Open Graph / Social Metadata
            if ext in (".html", ".htm") and "<head" in content.lower():
                if not re.search(r'og:title', content, re.IGNORECASE) and not re.search(r'twitter:card', content, re.IGNORECASE):
                    head_line = 1
                    for idx, line in enumerate(lines, 1):
                        if "<head" in line.lower():
                            head_line = idx
                            break
                    findings.append(Finding(
                        rule_id="seo-missing-opengraph",
                        title="Missing Open Graph / Social Metadata",
                        description="Document is missing Open Graph (og:title, og:image) or Twitter Card tags. These are critical for social media sharing and click-through rates.",
                        severity="serious",
                        category="seo",
                        affected_selectors=["head"],
                        representative_snippet="<head>",
                        source_matches=[{
                            "filePath": file_path,
                            "lineNumber": head_line,
                            "confidence": "high",
                            "exactMatchVerified": True,
                            "sourceCode": lines[head_line - 1].strip() if lines else "<head>"
                        }]
                    ))

            # Rule: Missing Canonical Tag
            if ext in (".html", ".htm") and "<head" in content.lower():
                if not re.search(r'rel=["\']canonical["\']', content, re.IGNORECASE):
                    head_line = 1
                    for idx, line in enumerate(lines, 1):
                        if "<head" in line.lower():
                            head_line = idx
                            break
                    findings.append(Finding(
                        rule_id="seo-missing-canonical",
                        title="Missing Canonical Tag",
                        description="Document is missing a <link rel='canonical'> tag. Search engines use this to prevent duplicate content indexing.",
                        severity="moderate",
                        category="seo",
                        affected_selectors=["head"],
                        representative_snippet="<head>",
                        source_matches=[{
                            "filePath": file_path,
                            "lineNumber": head_line,
                            "confidence": "high",
                            "exactMatchVerified": True,
                            "sourceCode": lines[head_line - 1].strip() if lines else "<head>"
                        }]
                    ))
            
            # Rule: Poor Semantic Structure (No <main>, <article>, or <section>)
            if ext in (".html", ".htm", ".jsx", ".tsx"):
                if not re.search(r'<(main|article|section|nav|aside)[\s>]', content, re.IGNORECASE):
                    body_line = 1
                    for idx, line in enumerate(lines, 1):
                        if "<body" in line.lower() or "return" in line.lower() or "render(" in line.lower():
                            body_line = idx
                            break
                    findings.append(Finding(
                        rule_id="seo-poor-semantics",
                        title="Poor Semantic HTML5 Structure",
                        description="Document relies entirely on non-semantic tags (like <div>). Search engines struggle to identify the main content area without <main>, <article>, or <section> tags.",
                        severity="moderate",
                        category="seo",
                        affected_selectors=["body"],
                        representative_snippet=lines[body_line - 1].strip() if lines else "<body>",
                        source_matches=[{
                            "filePath": file_path,
                            "lineNumber": body_line,
                            "confidence": "medium",
                            "exactMatchVerified": True,
                            "sourceCode": lines[body_line - 1].strip() if lines else "<body>"
                        }]
                    ))
        
        for line_num, raw_line in enumerate(lines, 1):
            line = raw_line.strip()
            # Rule: Img tag missing alt for SEO crawlers
            if "<img" in line.lower() and not re.search(r'\balt\s*=', line, re.IGNORECASE):
                findings.append(Finding(
                    rule_id="seo-img-alt-missing",
                    title="Image missing alt text for search engine crawlers",
                    description="Search engine crawlers cannot parse image contents without descriptive alt text attributes.",
                    severity="moderate",
                    category="seo",
                    affected_selectors=["img"],
                    representative_snippet=line,
                    source_matches=[{
                        "filePath": file_path,
                        "lineNumber": line_num,
                        "confidence": "high",
                        "exactMatchVerified": True,
                        "sourceCode": line
                    }]
                ))

        return findings

    # =========================================================================
    # 3. PERFORMANCE RULES ANALYZER (Performance Specialist Agent)
    # =========================================================================
    def _scan_performance(self, file_path: str, lines: List[str], ext: str) -> List[Finding]:
        findings: List[Finding] = []

        for line_num, raw_line in enumerate(lines, 1):
            line = raw_line.strip()

            # Rule: Image missing loading="lazy"
            if "<img" in line.lower() and "loading=" not in line.lower():
                findings.append(Finding(
                    rule_id="perf-missing-lazy-loading",
                    title="Unoptimized Image Loading (Missing loading='lazy')",
                    description="Images without loading='lazy' are downloaded immediately, blocking initial rendering performance.",
                    severity="moderate",
                    category="performance",
                    affected_selectors=["img"],
                    representative_snippet=line,
                    source_matches=[{
                        "filePath": file_path,
                        "lineNumber": line_num,
                        "confidence": "high",
                        "exactMatchVerified": True,
                        "sourceCode": line
                    }]
                ))

            # Rule: Synchronous external script in HTML head/body
            if ext in (".html", ".htm") and "<script" in line.lower() and "src=" in line.lower():
                if not re.search(r'\b(defer|async|type=["\']module["\'])\b', line, re.IGNORECASE):
                    findings.append(Finding(
                        rule_id="perf-sync-script",
                        title="Render-blocking synchronous external script",
                        description="External <script src='...'> tags without defer or async block HTML parsing and delay initial paint.",
                        severity="serious",
                        category="performance",
                        affected_selectors=["script"],
                        representative_snippet=line,
                        source_matches=[{
                            "filePath": file_path,
                            "lineNumber": line_num,
                            "confidence": "high",
                            "exactMatchVerified": True,
                            "sourceCode": line
                        }]
                    ))

            # Rule: CSS @import statement
            if ext in (".css", ".html") and "@import" in line:
                if re.search(r'@import\s+(?:url\()?["\'][^"\']+["\']', line):
                    findings.append(Finding(
                        rule_id="perf-css-import",
                        title="CSS @import statement detected",
                        description="Using @import in CSS forces sequential network roundtrips, significantly delaying First Contentful Paint.",
                        severity="moderate",
                        category="performance",
                        affected_selectors=["@import"],
                        representative_snippet=line,
                        source_matches=[{
                            "filePath": file_path,
                            "lineNumber": line_num,
                            "confidence": "high",
                            "exactMatchVerified": True,
                            "sourceCode": line
                        }]
                    ))

            # Rule: Heavy Base64 inline image URI (> 2KB)
            if "data:image/" in line and ";base64," in line and len(line) > 2000:
                findings.append(Finding(
                    rule_id="perf-inline-base64-image",
                    title="Heavy inline Base64 data URI image",
                    description="Inlining large images directly in source files inflates HTML/JS bundle sizes and prevents browser HTTP caching.",
                    severity="moderate",
                    category="performance",
                    affected_selectors=["data-uri"],
                    representative_snippet=line[:120] + "... [base64 truncated]",
                    source_matches=[{
                        "filePath": file_path,
                        "lineNumber": line_num,
                        "confidence": "high",
                        "exactMatchVerified": True,
                        "sourceCode": line[:120] + "..."
                    }]
                ))

            # Rule: Leftover debug console.log in JS/TS/JSX/TSX
            if ext in (".js", ".ts", ".jsx", ".tsx") and "console.log(" in line:
                if not line.startswith("//") and not line.startswith("/*"):
                    findings.append(Finding(
                        rule_id="perf-console-log",
                        title="Leftover production console.log statement",
                        description="Console logging in production code degrades JS execution speed and pollutes browser main thread telemetry.",
                        severity="minor",
                        category="performance",
                        affected_selectors=["console"],
                        representative_snippet=line,
                        source_matches=[{
                            "filePath": file_path,
                            "lineNumber": line_num,
                            "confidence": "high",
                            "exactMatchVerified": True,
                            "sourceCode": line
                        }]
                    ))

        return findings
