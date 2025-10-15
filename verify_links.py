#!/usr/bin/env python3
"""
Comprehensive link verification for OS documentation.
Checks navigation links, TOC anchors, cross-references, and README links.
"""

import re
import os
from pathlib import Path
from collections import defaultdict

class LinkVerifier:
    def __init__(self, docs_dir):
        self.docs_dir = Path(docs_dir)
        self.files = list(self.docs_dir.rglob("*.md"))
        self.errors = []
        self.warnings = []
        self.stats = {
            'nav_links': 0,
            'toc_entries': 0,
            'cross_refs': 0,
            'readme_links': 0,
            'total_checked': 0,
        }

    def read_file(self, filepath):
        """Read file content with error handling."""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            self.errors.append(f"Error reading {filepath}: {e}")
            return ""

    def extract_headers(self, content):
        """Extract all headers from markdown content."""
        headers = {}
        # Match headers with numbering: ## 1. Title or ### 2.1. Subtitle
        pattern = r'^(#{1,6})\s+(\d+(?:\.\d+)*\.?)\s+(.+)$'
        for match in re.finditer(pattern, content, re.MULTILINE):
            level = len(match.group(1))
            number = match.group(2).rstrip('.')
            title = match.group(3).strip()
            # Generate anchor (lowercase, replace spaces with hyphens, remove special chars)
            anchor_text = title.lower()
            # Remove emojis and special characters
            anchor_text = re.sub(r'[^\w\s-]', '', anchor_text)
            anchor_text = re.sub(r'[-\s]+', '-', anchor_text).strip('-')
            # Format: number-title (e.g., "2-what-is-a-thread" or "21-threads-vs-processes")
            anchor = f"{number.replace('.', '')}-{anchor_text}"
            headers[anchor] = {'level': level, 'number': number, 'title': title, 'full': f"{number}. {title}"}
        return headers

    def extract_toc_links(self, content):
        """Extract all TOC links from content."""
        toc_links = []
        # Match markdown links: [Text](#anchor) or [Text](file.md#anchor)
        pattern = r'\[([^\]]+)\]\((#[^\)]+)\)'
        for match in re.finditer(pattern, content):
            text = match.group(1)
            anchor = match.group(2)[1:]  # Remove leading #
            toc_links.append({'text': text, 'anchor': anchor})
        return toc_links

    def extract_nav_links(self, content):
        """Extract Previous/Next navigation links."""
        nav_links = {'previous': None, 'next': None}

        # Match: **Previous:** [Text](link) | **Next:** [Text](link)
        prev_pattern = r'\*\*Previous:\*\*\s*\[([^\]]+)\]\(([^\)]+)\)'
        next_pattern = r'\*\*Next:\*\*\s*\[([^\]]+)\]\(([^\)]+)\)'

        prev_match = re.search(prev_pattern, content)
        if prev_match:
            nav_links['previous'] = {'text': prev_match.group(1), 'link': prev_match.group(2)}

        next_match = re.search(next_pattern, content)
        if next_match:
            nav_links['next'] = {'text': next_match.group(1), 'link': next_match.group(2)}

        return nav_links

    def extract_all_markdown_links(self, content):
        """Extract all markdown links from content."""
        links = []
        # Match: [Text](link) or [Text](file.md#anchor)
        pattern = r'\[([^\]]+)\]\(([^\)]+)\)'
        for match in re.finditer(pattern, content):
            text = match.group(1)
            link = match.group(2)
            # Skip anchor-only links (handled separately)
            if not link.startswith('#'):
                links.append({'text': text, 'link': link})
        return links

    def resolve_link_path(self, source_file, link):
        """Resolve relative link path to absolute path."""
        source_dir = source_file.parent

        # Split link and anchor
        if '#' in link:
            file_part, anchor_part = link.split('#', 1)
        else:
            file_part, anchor_part = link, None

        if not file_part:
            # Anchor-only link in same file
            target_file = source_file
        else:
            # Resolve relative path
            target_file = (source_dir / file_part).resolve()

        return target_file, anchor_part

    def verify_navigation_links(self):
        """Verify all Previous/Next navigation links."""
        print("🔍 Checking navigation links...")

        nav_chain = defaultdict(dict)

        for filepath in sorted(self.files):
            if filepath.name == 'README.md':
                continue

            content = self.read_file(filepath)
            nav_links = self.extract_nav_links(content)

            rel_path = filepath.relative_to(self.docs_dir)

            # Check previous link
            if nav_links['previous']:
                self.stats['nav_links'] += 1
                self.stats['total_checked'] += 1
                target_file, anchor = self.resolve_link_path(filepath, nav_links['previous']['link'])

                if not target_file.exists():
                    self.errors.append(f"❌ {rel_path}: Previous link broken -> {nav_links['previous']['link']}")
                else:
                    nav_chain[str(rel_path)]['previous'] = target_file.relative_to(self.docs_dir)

            # Check next link
            if nav_links['next']:
                self.stats['nav_links'] += 1
                self.stats['total_checked'] += 1
                target_file, anchor = self.resolve_link_path(filepath, nav_links['next']['link'])

                if not target_file.exists():
                    self.errors.append(f"❌ {rel_path}: Next link broken -> {nav_links['next']['link']}")
                else:
                    nav_chain[str(rel_path)]['next'] = target_file.relative_to(self.docs_dir)

        # Verify bidirectional chain
        print("  Verifying navigation chain bidirectionality...")
        for file_path, links in nav_chain.items():
            if 'next' in links:
                next_file = str(links['next'])
                if next_file in nav_chain:
                    if 'previous' in nav_chain[next_file]:
                        if str(nav_chain[next_file]['previous']) != file_path:
                            self.warnings.append(f"⚠️  Navigation chain broken: {file_path} -> {next_file} (not bidirectional)")

    def verify_toc_anchors(self):
        """Verify all TOC anchor links match actual headers."""
        print("🔍 Checking TOC anchor links...")

        for filepath in sorted(self.files):
            content = self.read_file(filepath)
            rel_path = filepath.relative_to(self.docs_dir)

            # Extract headers and TOC links
            headers = self.extract_headers(content)
            toc_links = self.extract_toc_links(content)

            for toc_link in toc_links:
                self.stats['toc_entries'] += 1
                self.stats['total_checked'] += 1

                anchor = toc_link['anchor']

                # Check if anchor exists in headers
                if anchor not in headers:
                    # Try to find similar anchors
                    similar = [h for h in headers.keys() if anchor.replace('-', '') in h.replace('-', '')]
                    if similar:
                        self.errors.append(f"❌ {rel_path}: TOC anchor not found: #{anchor} (similar: {similar[0]})")
                    else:
                        self.errors.append(f"❌ {rel_path}: TOC anchor not found: #{anchor}")

            # Check for headers not in TOC (warning only)
            if toc_links and headers:
                toc_anchors = {link['anchor'] for link in toc_links}
                header_anchors = set(headers.keys())
                missing = header_anchors - toc_anchors
                if missing and len(missing) < len(header_anchors):  # Don't warn if no TOC at all
                    for anchor in missing:
                        self.warnings.append(f"⚠️  {rel_path}: Header not in TOC: {headers[anchor]['title']}")

    def verify_cross_references(self):
        """Verify all cross-reference links between documents."""
        print("🔍 Checking cross-reference links...")

        for filepath in sorted(self.files):
            content = self.read_file(filepath)
            rel_path = filepath.relative_to(self.docs_dir)

            # Extract all markdown links (excluding TOC)
            links = self.extract_all_markdown_links(content)

            for link_data in links:
                link = link_data['link']

                # Skip external links
                if link.startswith('http://') or link.startswith('https://'):
                    continue

                self.stats['cross_refs'] += 1
                self.stats['total_checked'] += 1

                target_file, anchor = self.resolve_link_path(filepath, link)

                # Check if target file exists
                if not target_file.exists():
                    self.errors.append(f"❌ {rel_path}: Broken link -> {link}")
                    continue

                # If anchor specified, check if it exists
                if anchor:
                    target_content = self.read_file(target_file)
                    target_headers = self.extract_headers(target_content)

                    if anchor not in target_headers:
                        self.errors.append(f"❌ {rel_path}: Anchor not found in {target_file.name}: #{anchor}")

    def verify_readme_links(self):
        """Verify all README links."""
        print("🔍 Checking README links...")

        readme_files = [f for f in self.files if f.name == 'README.md']

        for filepath in sorted(readme_files):
            content = self.read_file(filepath)
            rel_path = filepath.relative_to(self.docs_dir)

            # Extract all links
            links = self.extract_all_markdown_links(content)
            links.extend(self.extract_toc_links(content))  # Include anchor links

            for link_data in links:
                if 'link' in link_data:
                    link = link_data['link']
                elif 'anchor' in link_data:
                    link = '#' + link_data['anchor']
                else:
                    continue

                # Skip external links
                if link.startswith('http://') or link.startswith('https://'):
                    continue

                self.stats['readme_links'] += 1
                self.stats['total_checked'] += 1

                target_file, anchor = self.resolve_link_path(filepath, link)

                # Check if target file exists
                if not target_file.exists():
                    self.errors.append(f"❌ {rel_path}: Broken README link -> {link}")
                    continue

                # If anchor specified, check if it exists
                if anchor:
                    target_content = self.read_file(target_file)
                    target_headers = self.extract_headers(target_content)

                    if anchor not in target_headers:
                        # For README, also check if it's a TOC-style anchor without numbering
                        alt_anchor = re.sub(r'^\d+(?:\.\d+)*-', '', anchor)
                        if alt_anchor not in target_headers:
                            self.errors.append(f"❌ {rel_path}: Anchor not found in {target_file.name}: #{anchor}")

    def run_verification(self):
        """Run all verification checks."""
        print("=" * 80)
        print("📋 LINK VERIFICATION REPORT")
        print("=" * 80)
        print()

        self.verify_navigation_links()
        self.verify_toc_anchors()
        self.verify_cross_references()
        self.verify_readme_links()

        print()
        print("=" * 80)
        print("📊 STATISTICS")
        print("=" * 80)
        print(f"Navigation links checked: {self.stats['nav_links']}")
        print(f"TOC entries checked: {self.stats['toc_entries']}")
        print(f"Cross-references checked: {self.stats['cross_refs']}")
        print(f"README links checked: {self.stats['readme_links']}")
        print(f"Total links checked: {self.stats['total_checked']}")
        print()

        print("=" * 80)
        print("🐛 ISSUES FOUND")
        print("=" * 80)

        if self.errors:
            print(f"\n❌ ERRORS ({len(self.errors)}):")
            for error in sorted(set(self.errors)):
                print(f"  {error}")
        else:
            print("\n✅ No errors found!")

        if self.warnings:
            print(f"\n⚠️  WARNINGS ({len(self.warnings)}):")
            for warning in sorted(set(self.warnings)):
                print(f"  {warning}")
        else:
            print("\n✅ No warnings!")

        print()
        print("=" * 80)

        return len(self.errors) == 0


if __name__ == "__main__":
    docs_dir = "/Users/jason/Files/Practice/demo-little-things/operating-systems/docs"
    verifier = LinkVerifier(docs_dir)
    success = verifier.run_verification()
    exit(0 if success else 1)
